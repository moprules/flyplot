
import os
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtCore import Slot, Qt
from PySide6 import QtWidgets, QtGui

from .icons import get_icon
from .parser import Parser3DChartFile


class Text3DItem(gl.GLImageItem):
    def __init__(self,
                 text,
                 fontFamily: str = "Arial",
                 size: int = 100,
                 color=(0, 0, 0, 255)):
        self.font = QtGui.QFont()
        self.setText(text, fontFamily, size, color, isUpd=False)

        self.width = self.size * len(self.text)
        self.height = self.size*2

        data = self.__convertTextToData()
        super().__init__(data, smooth=True)

        self.resetTransform()

    def resetTransform(self):
        super().resetTransform()
        self.translate(-self.height/2, -self.width/2, 0)
        self.myRotate(-90, "z")

    def myTranslate(self, dx, dy, dz):
        dx, dy = -dy, dx
        self.translate(dx, dy, dz, local=True)

    def myRotate(self, angle, axi):
        r = {"x": 0, "y": 0, "z": 0}
        r[axi] = 1
        r["x"], r["y"] = r["y"], r["x"]

        self.myTranslate(self.width/2, -self.height/2, 0)
        self.rotate(angle, r["x"], r["y"], r["z"], local=True)
        self.myTranslate(-self.width/2, self.height/2, 0)

    def setColor(self, color, isUpd=True):
        # Переводим  в BGR, тут так это работает
        color = pg.mkColor(color)
        r = color.red()
        g = color.green()
        b = color.blue()
        a = color.alpha()

        self.color = pg.mkColor((b, g, r, a))

        if isUpd:
            data = self.__convertTextToData()
            self.setData(data)

    def setFont(self, fontFamily=None, size=None, color=None, isUpd=True):
        if fontFamily:
            self.font.setFamily(fontFamily)

        if size:
            self.size = size
            self.font.setPixelSize(size)

        if color:
            self.setColor(color, isUpd=False)

        if isUpd:
            data = self.__convertTextToData()
            self.setData(data)

    def setText(self, text, fontFamily=None, size=None, color=None, isUpd=True):
        self.text = str(text)
        self.setFont(fontFamily, size, color, isUpd=False)
        if isUpd:
            data = self.__convertTextToData()
            self.setData(data)

    def __convertTextToData(self):
        # Создаем QImage и устанавливаем его размер
        # длина - высота текста * количество символов
        img = QtGui.QImage(self.width, self.height,
                           QtGui.QImage.Format_ARGB32)  # type: ignore
        # Заполняем все одним цветом, чтобы не было помех
        img.fill(0)

        # Создаем объект QPainter для определения размера текста
        with QtGui.QPainter(img) as paintSizer:
            # Задаём программное сглаживание текста
            paintSizer.setRenderHint(
                QtGui.QPainter.TextAntialiasing)  # type: ignore
            # Устанавливаем цвет и прозрачность текста
            paintSizer.setPen(self.color)
            # Шрифт текста
            paintSizer.setFont(self.font)

            text_rect = paintSizer.boundingRect(img.rect(), 0, self.text)

            self.width = text_rect.width()
            self.height = text_rect.height()

        # Создаём новое изображенеи с меньшими размерами
        img = QtGui.QImage(self.width, self.height,
                           QtGui.QImage.Format_ARGB32)  # type: ignore
        # Заполняем все одним цветом, чтобы не было помех
        img.fill(0)
        # Создаем объект QPainter для рисования в QImage
        with QtGui.QPainter(img) as painter:
            # Задаём программное сглаживание текста
            painter.setRenderHint(
                QtGui.QPainter.TextAntialiasing)  # type: ignore
            # Устанавливаем цвет и прозрачность текста
            painter.setPen(self.color)
            # Шрифт текста
            painter.setFont(self.font)
            # Рисуем текст
            painter.drawText(img.rect(), self.text)

        # Переводим изображение в байты
        buffer = img.constBits().tobytes()  # type: ignore
        # Преобразуем баты в массив numpy
        data = np.ndarray(shape=(img.height(), img.width(), 4),
                          dtype=np.uint8, buffer=buffer)
        return data


class Area3D(gl.GLMeshItem):
    def __init__(self,
                 pos=[0, 0, 0],
                 radius=50,
                 color=pg.mkColor("g"),
                 length=0.1):
        self.pos = pos
        self.radius = radius
        self.length = length
        self.color = color
        cylinder = gl.MeshData.cylinder(rows=50,
                                        cols=50,
                                        radius=[0, self.radius],
                                        length=self.length)
        super().__init__(meshdata=cylinder,
                         smooth=True,
                         shader='balloon',
                         color=pg.mkColor(self.color),
                         glOptions='opaque')
        self.translate(*self.pos)
        self.translate(0, 0, -self.length)

    def setColor(self, c):
        self.color = pg.mkColor(c)
        super().setColor(c)


class Plot3DWidjet(gl.GLViewWidget):
    def __init__(self, parent, *args, **kargs):
        super().__init__(*args, **kargs)
        self.my_parent = parent

        # Задаём цвет фона по умолчанию стоит черный, будет белый
        self.setBackgroundColor("w")

        self.charts = []
        self.axis = {}
        self.grid = {}
        self.areas = []
        self.__initAxis()
        self.__initGrid()

        # Задаём размеры виджета
        screen_size = self.screen().size()
        # Минимальные размеры графика
        min_width = round(screen_size.width() / 2.5)
        min_height = round(screen_size.height() / 2)
        self.setMinimumSize(min_width, min_height)
        # график не может быть больше размеров экрана
        self.setMaximumSize(screen_size)
        # график можно расширять
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,  # type: ignore
                           QtWidgets.QSizePolicy.Expanding)  # type: ignore
        # Фокус остаётся на графике
        self.setFocusPolicy(Qt.StrongFocus)  # type: ignore

        # Ставим вид по умолчанию
        self.homeAction()

        # self.__testDebug()
    def __initAxis(self):
        for ax in "xyz":
            axi = self.axis[ax] = {}
            axi["min"] = 0
            axi["max"] = 1000
            axi["space"] = 100
            axi["size"] = axi["max"] - axi["min"]
            axi["delta"] = (axi["min"] + axi["max"]) / 2
            # Основное направление оси
            axi["amax"] = max(axi["max"], axi["min"], key=lambda x: abs(x))
            axi["amin"] = min(axi["max"], axi["min"], key=lambda x: abs(x))
            # направление оси по умолчанию считаем нормальным
            axi["direction"] = 1
            if axi["amin"] > 0:
                axi["direction"] = -1
            # Делений оси
            axi["value"] = {"size": axi["space"]*0.6, "offset": axi["space"]*0.4,
                            "angle": 15, "mas": []}
            # Подписей осей
            axi["label"] = {"size": 100, "offset": 200,
                            "step": 100, "angle": 15, "mas": []}

    def __initGrid(self):
        for gg in ("xy", "xz", "yz"):
            # Создаем одну из плоскостей 3D сетки
            self.grid[gg] = gl.GLGridItem()
            # Задаём цвет - черный и немного прозрачный
            self.grid[gg].setColor((0, 0, 0, 255))
            # Добавляем объект сетки на 3D сцену
            self.addItem(self.grid[gg])

        # перерисовываем всю 3D сетку
        self.paintGrid()

    def paintGrid(self):
        # проходим все плоскости сетки
        for gg in self.grid:
            # Сбрасываем положение плоскости
            self.grid[gg].resetTransform()
            # Задаём размер плоскости сетки
            size = (self.axis[ax]["size"] for ax in gg)
            self.grid[gg].setSize(*size)
            # Задаём шаг сетки
            space = (self.axis[ax]["space"] for ax in gg)
            self.grid[gg].setSpacing(*space)

        # Поворачиваем плоскти в нужном направлении
        # Плоскость xy поворачивать не нужно
        self.grid["xz"].rotate(90, 1, 0, 0)
        # Плоскость yz нужно повернуть два раза
        self.grid["yz"].rotate(90, 0, 0, 1)
        self.grid["yz"].rotate(90, 0, 1, 0)

        for gg in self.grid:
            # Перемещения по координатам xyz
            d = {"x": 0, "y": 0, "z": 0}
            # Задаём перемещения внутри плоскости
            for ax in gg:
                d[ax] = self.axis[ax]["delta"]
            # Ось перпендикулярная плоскости
            n = list(set("xyz") - set(gg))[0]
            # Перемещенеи относительно нормали
            # По умолчанию ставим в позицию минимальную по модулю
            d[n] = self.axis[n]["amin"]
            if self.axis[n]["amin"] == self.axis[n]["max"]:
                self.axis[n]["direction"] = -1
            # Перемещаем плоскость в нужное положение относительно центра координат
            self.grid[gg].translate(d["x"], d["y"], d["z"])

        # Тепер для каждой плоскости рассмотрим как она расположена относительно камеры
        # плоскости нужно переместить по нормали если она стоит "спиной" к камере
        self.paintGridByDirection()

    def paintGridByDirection(self):
        """
        Перерисовыем плоскости относительно камеры так,
        Чтобы нормали плоскостей смотрели на кмеру
        """
        camPos = self.cameraPosition()
        for gg in self.grid:
            # Ось нормальная плоскости
            n = list(set("xyz") - set(gg))[0]
            v = {"x": 0, "y": 0, "z": 0}
            v[n] = self.axis[n]["direction"] * self.axis[n]["size"]
            qVector = QtGui.QVector3D(v["x"], v["y"], v["z"])
            angle = camPos.angle(qVector)
            if angle is not None and angle > 90:
                self.grid[gg].translate(v["x"], v["y"], v["z"])
                self.axis[n]["direction"] *= -1
                # Перерисовываем метки осей расположенные в плоскости
                for ax in "xyz":
                    self.paintAxis(ax)

    def paintAxis(self, axis_name: str):
        if axis_name == "x":
            self.__paintLabelX()
            self.__paintValuesX()
        elif axis_name == "y":
            self.__paintLabelY()
            self.__paintValuesY()
        else:
            # иначе считаем, что это z
            self.__paintLabelZ()
            self.__paintValuesZ()

    def __paintLabelX(self):
        """
        Перерисовка содержимого оси X
        """
        x = self.axis["x"]
        y = self.axis["y"]
        z = self.axis["z"]

        label = x["label"]
        if not label["mas"]:
            return

        for l in label["mas"]:
            l.resetTransform()

        dX = x["delta"]

        dY = y["max"]
        if y["direction"] < 0:
            dY = y["min"]
        dZ = z["min"]
        if z["direction"] < 0:
            dZ = z["max"]

        rZ = 0
        if y["direction"] > 0:
            rZ = 180
        rX = 0
        if z["direction"] < 0:
            rX = 180

        # Найденные перемещения применяем ко всем осям
        for l in label["mas"]:
            l.myTranslate(dX, dY, dZ)
            l.myRotate(rZ, "z")
            l.myRotate(rX, "x")
            # все надписи выравниваем по краю плоскости
            # И добавляем начальное смещенеи
            ddY = -z["direction"]*l.height / 2
            # Перемещение завист от положения оси Z
            l.myTranslate(0, ddY, 0)

        # Положение надписей относительно друг друга
        # Начальный отступ от оси
        ddY = label["offset"]
        # Поворот каждой подписи
        rX = label["angle"]*z["direction"]
        for l in label["mas"]:
            ddY += l.height / 2
            # Перемещение завист от положения оси Z
            l.myTranslate(0, -z["direction"]*ddY, 0)
            # Кажду метку для красоты поворачиваем на маленький угол
            # l.myRotate(rX, "x")
            # Шаг между подписями
            ddY += label["step"]

    def __paintLabelY(self):
        """
        Перерисовка содержимого оси Y
        """
        x = self.axis["x"]
        y = self.axis["y"]
        z = self.axis["z"]
        label = y["label"]

        if not label["mas"]:
            return

        for l in label["mas"]:
            l.resetTransform()

        dX = x["max"]
        if x["direction"] < 0:
            dX = x["min"]

        dY = y["delta"]

        dZ = z["min"]
        if z["direction"] < 0:
            dZ = z["max"]

        rZ = x["direction"]*90
        rX = 0
        if z["direction"] < 0:
            rX = 180

        # Найденные перемещения применяем ко всем осям
        for l in label["mas"]:
            l.myTranslate(dX, dY, dZ)
            l.myRotate(rZ, "z")
            l.myRotate(rX, "x")
            # все надписи выравниваем по краю плоскости
            # И добавляем начальное смещенеи
            ddY = -z["direction"]*l.height / 2
            # Перемещение завист от положения оси Z
            l.myTranslate(0, ddY, 0)

        # Положение надписей относительно другг друга
        # Начальный отступ от оси
        ddY = label["offset"]
        # Поворот каждой подписи
        rX = label["angle"]*z["direction"]
        for l in label["mas"]:
            ddY += l.height / 2
            # Перемещение завист от положения оси Z
            l.myTranslate(0, -z["direction"]*ddY, 0)
            # Кажду метку для красоты поворачиваем на маленький угол
            # l.myRotate(rX, "x")
            # Шаг между подписями
            ddY += label["step"]

    def __paintLabelZ(self):
        """Перерисовка содержимого оси Z"""
        x = self.axis["x"]
        y = self.axis["y"]
        z = self.axis["z"]
        label = z["label"]

        if not label["mas"]:
            return

        for l in label["mas"]:
            l.resetTransform()

        dX = x["max"]
        if x["direction"] < 0:
            dX = x["min"]

        dY = y["min"]
        if y["direction"] < 0:
            dY = y["max"]

        dZ = z["delta"]

        rZ = 0
        if y["direction"] > 0:
            rZ = 180
        rX = 90
        rZZ = -90*x["direction"]*z["direction"]*y["direction"]

        # Найденные перемещения применяем ко всем осям
        for l in label["mas"]:
            l.myTranslate(dX, dY, dZ)
            l.myRotate(rZ, "z")
            l.myRotate(rX, "x")
            l.myRotate(rZZ, "z")
            # все надписи выравниваем по краю плоскости
            # И добавляем начальное смещенеи
            ddY = -z["direction"]*l.height / 2
            # # Перемещение завист от положения оси Z
            l.myTranslate(0, ddY, 0)

        # Положение надписей относительно другг друга
        # Начальный отступ от оси
        ddY = label["offset"]
        # Поворот каждой подписи
        rX = label["angle"]*z["direction"]
        for l in label["mas"]:
            ddY += l.height / 2
            # Перемещение завист от положения оси Z
            l.myTranslate(0, -z["direction"]*ddY, 0)
            # Кажду метку для красоты поворачиваем на маленький угол
            # l.myRotate(rX, "x")
            # Шаг между подписями
            ddY += label["step"]

    def __paintValuesX(self):
        """
        Перерисовка значений делений оси X
        """
        x = self.axis["x"]
        y = self.axis["y"]
        z = self.axis["z"]

        value = x["value"]
        if not value["mas"]:
            return

        for v in value["mas"]:
            v.resetTransform()

        dX = x["min"]

        dY = y["max"]
        if y["direction"] < 0:
            dY = y["min"]
        dZ = z["min"]
        if z["direction"] < 0:
            dZ = z["max"]

        rZ = 90*x["direction"]
        rX = 0
        if z["direction"] < 0:
            rX = 180

        # Положение надписей относительно друг друга
        # Начальный отступ от оси
        # Поворот каждой подписи
        rY = -value["angle"]*x["direction"]*y["direction"]
        # Найденные перемещения применяем ко всем осям
        for v in value["mas"]:
            v.myTranslate(dX, dY, dZ)
            v.myRotate(rZ, "z")
            v.myRotate(rX, "x")
            # все надписи выравниваем по краю плоскости
            # И добавляем начальное смещенеи
            ddX = value["offset"]+v.width / 2
            # Перемещение завист от положения оси Y и X
            v.myTranslate(x["direction"]*y["direction"]*ddX, 0, 0)

            # v.myTranslate(-x["direction"]*y["direction"]*v.width / 2, 0, 0)
            # v.myRotate(rY, "y")
            # v.myTranslate(x["direction"]*y["direction"]*v.width / 2, 0, 0)

        # Пробегаемся по всем подписям значений кроме первой
        ddY = 0
        for v in value["mas"][1:]:
            # Шаг между подписями
            ddY += x["space"]
            # Перемещение завист от положения оси Z
            v.myTranslate(0, -x["direction"]*z["direction"]*ddY, 0)

    def __paintValuesY(self):
        """
        Перерисовка значений делений оси Y
        """
        x = self.axis["x"]
        y = self.axis["y"]
        z = self.axis["z"]

        value = y["value"]
        if not value["mas"]:
            return

        for v in value["mas"]:
            v.resetTransform()

        dX = x["max"]
        if x["direction"] < 0:
            dX = x["min"]

        dY = y["min"]

        dZ = z["min"]
        if z["direction"] < 0:
            dZ = z["max"]

        rZ = 0
        if y["direction"] > 0:
            rZ = 180

        rX = 0
        if z["direction"] < 0:
            rX = 180

        # Положение надписей относительно друг друга
        # Поворот каждой подписи
        rY = value["angle"]*x["direction"]*y["direction"]
        # Найденные перемещения применяем ко всем осям
        for v in value["mas"]:
            v.myTranslate(dX, dY, dZ)
            v.myRotate(rZ, "z")
            v.myRotate(rX, "x")
            # все надписи выравниваем по краю плоскости
            # И добавляем начальное смещенеи
            ddX = value["offset"]+v.width / 2
            # Перемещение завист от положения оси Y и X
            v.myTranslate(-x["direction"]*y["direction"]*ddX, 0, 0)

            # v.myTranslate(x["direction"]*y["direction"]*v.width / 2, 0, 0)
            # v.myRotate(rY, "y")
            # v.myTranslate(-x["direction"]*y["direction"]*v.width / 2, 0, 0)

        # Пробигаемся по всем подписям значений кроме первой
        ddY = 0
        for v in value["mas"][1:]:
            # Шаг между подписями
            ddY += y["space"]
            # Перемещение завист от положения оси Z
            v.myTranslate(0, -y["direction"]*z["direction"]*ddY, 0)

        # в зависимости от пложения оси Z сдвигаем первую или последнюю метку
        # Чтобы они не пересекались с плоскостью
        if y["direction"] > 0:
            # Метка которую нужно двигать
            valMove = value["mas"][0]
        else:
            valMove = value["mas"][-1]

        ddY = -z["direction"] * v.height / 2
        valMove.myTranslate(0, ddY, 0)

    def __paintValuesZ(self):
        """
        Перерисовка значений делений оси Z
        """
        """Перерисовка содержимого оси Z"""
        x = self.axis["x"]
        y = self.axis["y"]
        z = self.axis["z"]
        value = z["value"]

        if not value["mas"]:
            return

        for v in value["mas"]:
            v.resetTransform()

        dX = x["max"]
        if x["direction"] < 0:
            dX = x["min"]

        dY = y["min"]
        if y["direction"] < 0:
            dY = y["max"]

        dZ = z["min"]

        rZ = 0
        if y["direction"] > 0:
            rZ = 180
        rX = 90

        # Положение надписей относительно друг друга
        # Поворот каждой подписи
        rY = value["angle"]*x["direction"]*y["direction"]
        for v in value["mas"]:
            v.myTranslate(dX, dY, dZ)
            v.myRotate(rZ, "z")
            v.myRotate(rX, "x")
            # все надписи выравниваем по краю плоскости
            # И добавляем начальное смещенеи
            ddX = value["offset"]+v.width / 2
            # Перемещение завист от положения оси X и Y
            v.myTranslate(-x["direction"]*y["direction"]*ddX, 0, 0)

            # v.myTranslate(x["direction"]*y["direction"]*v.width / 2, 0, 0)
            # v.myRotate(rY, "y")
            # v.myTranslate(-x["direction"]*y["direction"]*v.width / 2, 0, 0)

        # Пробигаемся по всем подписям значений кроме первой
        ddY = 0
        for v in value["mas"][1:]:
            # Шаг между подписями
            ddY += z["space"]
            # Перемещение завист от положения оси Z
            v.myTranslate(0, ddY, 0)

        # в зависимости от пложения оси Z сдвигаем первую или последнюю метку
        # Чтобы они не пересекались с плоскостью
        if z["direction"] > 0:
            # Метка которую нужно двигать
            valMove = value["mas"][0]
        else:
            valMove = value["mas"][-1]

        ddY = z["direction"] * v.height / 2
        valMove.myTranslate(0, ddY, 0)

    def addChart(self, chart: dict):
        stdcolors = "brkgy"
        cindex = len(self.charts) % len(stdcolors)
        chart["color"] = stdcolors[cindex]
        # Создаём объект 3D графика
        plt = gl.GLLinePlotItem(
            pos=chart["coords"], color=pg.mkColor(chart["color"]), width=1, antialias=True)
        # Добавляем его на наш виджет
        self.addItem(plt)
        chart["plt"] = plt
        self.charts.append(chart)

        # Перестраиваем сетку под новый график
        self.recalcAxis()
        self.paintGrid()

        for ax in "xyz":
            # Пересчитываем подписи для оси
            self.recalcLabelAxis(ax)
            # Собираем ноую подпись
            d = chart["axis"][ax]
            axiName = d["name"] + ", " + d["dim"]
            # Добавляем новую подпись оси если нужно
            self.addLabel(ax, axiName)
            # Пересчитываем подписи делений оси
            self.recalcValuesAxis(ax)
            # Наконец рисуем саму ось
            self.paintAxis(ax)

        # Переходим в вид по умолчанию, чтобы были видны
        # Все графики в пространстве
        self.homeAction()
    
    def addLabel(self, ax, text, isForce=False):
        isFind = False
        # Настройки подписей для оси ax
        label = self.axis[ax]["label"]
        for tObj in label["mas"]:
            if tObj.text == text:
                isFind = True
        if (not isFind) or isForce:
            size = label["size"]
            tObj = Text3DItem(text, size=size)
            self.addItem(tObj)
            label["mas"].append(tObj)

    def recalcAxis(self):
        # Сбрасываем старые значения
        for ax in "xyz":
            axi = self.axis[ax]
            axi["min"] = 0
            axi["max"] = 0
            axi["size"] = 0
            axi["delta"] = 0
            axi["amax"] = 0
            axi["amin"] = 0

        # Получаем предельные значения для сетки графика
        for chart in self.charts:
            for ax in "xyz":
                axi = self.axis[ax]
                axi["min"] = min(chart["axis"][ax]["min"], axi["min"])
                axi["max"] = max(chart["axis"][ax]["max"], axi["max"])

        if self.areas:
            for area in self.areas:
                for i, ax in enumerate("xy"):
                    axi = self.axis[ax]
                    axi["min"] = min(axi["min"], area.pos[i]-area.radius)
                    axi["max"] = max(axi["max"], area.pos[i]+area.radius)

        # Размер решётки окрургляем до сотен
        for ax in "xyz":
            axi = self.axis[ax]
            axi["space"] = (axi["max"] - axi["min"])/10
            axi["space"] = np.ceil(axi["space"]/100)*100
        min_space_ax = min("xyz", key=lambda el: self.axis[el]["space"])
        min_space = self.axis[min_space_ax]["space"]

        # Округляем эти значения с точность шага сетки
        for ax in "xyz":
            axi = self.axis[ax]
            space = axi["space"]
            for mod in ("min", "max"):
                val = axi[mod]
                sign = np.sign(val)
                val = np.ceil(abs(val)/space)*space
                axi[mod] = sign*val

        for ax in "xyz":
            axi = self.axis[ax]
            # Получаем размеры сетки
            axi["size"] = axi["max"] - axi["min"]
            # И смещенеи относительно 0
            axi["delta"] = (axi["max"] + axi["min"]) / 2
            axi["amax"] = max(axi["max"],
                              axi["min"],
                              key=lambda x: abs(x))
            axi["amin"] = min(axi["max"],
                              axi["min"],
                              key=lambda x: abs(x))
            axi["direction"] = 1
            if axi["amin"] == axi["max"]:
                axi["direction"] = -1

            # Параметры текста
            # Делений оси
            axi["value"]["size"] = min_space*0.6
            axi["value"]["offset"] = min_space*0.4
            # Подписей осей
            axi["label"]["size"] = min_space
            axi["label"]["offset"] = 2*min_space
            axi["label"]["step"] = min_space

    def recalcLabelAxis(self, ax):
        # Обновляем подписи оси ax
        axi = self.axis[ax]
        # Удаляем все подписи на оси
        label_text = []
        for l in axi["label"]["mas"]:
            label_text.append(l.text)
            self.removeItem(l)
        # Очищаем список подписей
        axi["label"]["mas"].clear()

        size = axi["label"]["size"]
        for text in label_text:
            # создаём подпись оси
            label = Text3DItem(text, size=size)
            # Добавляем в массив для отслеживания
            axi["label"]["mas"].append(label)
            # Добаляем подпись на график
            self.addItem(label)

    def recalcValuesAxis(self, ax):
        # Обновляем значения делений осей
        axi = self.axis[ax]
        # Удаляем все подписи делений на оси
        for v in axi["value"]["mas"]:
            self.removeItem(v)
        # Очищаем список подписей
        axi["value"]["mas"].clear()
        # Вычисляем новое количество делений
        target_cnt = int(axi["size"] // axi["space"] + 1)
        # добавляем нужно количетсво меток с текстом
        # Первое значение будет минимумов
        first = axi["min"]
        # Получаем размер текста меток
        size = axi["value"]["size"]
        for i in range(target_cnt):
            # Получаем значение деления до 2 сотых
            val = round(first + i * axi["space"], 2)
            # преобразуем в текст
            text = str(val)
            # создаём подпись деления
            axiVal = Text3DItem(text, size=size)
            # Добавляем в массив для отслеживания
            axi["value"]["mas"].append(axiVal)
            # Добаляем подпись деления на график
            self.addItem(axiVal)

    def findIndexChart(self, data_file: str) -> int:
        data_file = os.path.abspath(data_file)
        i_res = -1
        for i, chart in enumerate(self.charts):
            if chart["path"] == data_file:
                i_res = i
                break
        return i_res

    def setChartPoints(self, i: int = None, data_file: str = None):
        if i is None:
            i = self.findIndexChart(data_file)
        if i == -1:
            return
        chart = self.chart[i]
        plt: gl.GLLinePlotItem = chart["plt"]
        plt.setData(pos=chart["coords"], width=1, antialias=True)

    def setChartColor(self, color, i: int = None, data_file: str = None):
        if i is None:
            i = self.findIndexChart(data_file)
        if i == -1:
            return
        chart = self.chart[i]
        plt: gl.GLLinePlotItem = chart["plt"]
        plt.setData(color=pg.mkColor(color), width=1, antialias=True)

    def delChart(self, i: int = None, data_file: str = None):
        if i is None:
            i = self.findIndexChart(data_file)
        if i == -1:
            return
        chart = self.charts.pop(i)
        plt: gl.GLLinePlotItem = chart["plt"]
        self.removeItem(plt)
        self.reDraw()

    def addArea(self,
                pos=[0, 0, 0],
                radius=1.0,
                color=pg.mkColor("g"),
                i=None):
        if not i:
            i = len(self.areas)
        area = Area3D(pos=pos, radius=radius, color=color)
        self.addItem(area)
        # ЧТобы рисовалось раньше графика
        area.setDepthValue(-100)
        self.areas.insert(i, area)

    def setAreaColor(self, color, i: int = None):
        area = self.areas[i]
        area.setColor(color)

    def delArea(self, i: int):
        area = self.areas.pop(i)
        self.removeItem(area)

    def reDraw(self):
        if (not self.areas) and (not self.charts):
            self.cleanAction()
            return
        # Перестраиваем сетку под новый график
        self.recalcAxis()
        self.paintGrid()

        for ax in "xyz":
            # Пересчитываем подписи для оси
            self.recalcLabelAxis(ax)
            # Пересчитываем подписи делений оси
            self.recalcValuesAxis(ax)
            # Наконец рисуем саму ось
            self.paintAxis(ax)

    def readCutQImage(self) -> QtGui.QImage | None:
        """
        Считываем обрезанное изображение с виджета
        Пустое место залитое цветм фона обрезается
        """
        img = self.readQImage()
        bg_color = QtGui.QColor.fromRgbF(*self.opts['bgcolor'])

        bottom = 0
        left = 0
        top = img.height()-1
        right = img.width()-1

        for y in range(img.height()):
            isFind = False
            bottom = y
            for x in range(img.width()):
                if img.pixelColor(x, y) != bg_color:
                    isFind = True
                    break
            if isFind:
                break

        for y in range(img.height()-1, bottom-1, -1):
            isFind = False
            top = y
            for x in range(img.width()):
                if img.pixelColor(x, y) != bg_color:
                    isFind = True
                    break
            if isFind:
                break

        for x in range(img.width()):
            left = x
            isFind = False
            for y in range(bottom, top+1):
                if img.pixelColor(x, y) != bg_color:
                    isFind = True
                    break
            if isFind:
                break

        for x in range(img.width()-1, left-1, -1):
            right = x
            isFind = False
            for y in range(bottom, top+1):
                if img.pixelColor(x, y) != bg_color:
                    isFind = True
                    break
            if isFind:
                break

        width = right - left + 1
        height = top - bottom + 1
        if width > 1 and height > 1:
            return img.copy(left, bottom, width, height)
        return None

    def contextMenuEvent(self, ev: QtGui.QContextMenuEvent):
        # Само контекстное меню
        contextMenu = QtWidgets.QMenu(self)

        # Пункт Вид по умолчанию
        homeAction = QtGui.QAction("Вид по умолчанию")
        icon = get_icon("home")
        homeAction.setIcon(icon)
        homeAction.triggered.connect(self.homeAction)
        contextMenu.addAction(homeAction)

        # Пункт Очистить
        cleanAction = QtGui.QAction("Очистить")
        icon = get_icon("clean")
        cleanAction.setIcon(icon)
        cleanAction.triggered.connect(self.cleanAction)
        contextMenu.addAction(cleanAction)

        # Пункт Скопировать
        copyAction = QtGui.QAction("Копировать")
        icon = get_icon("copy")
        copyAction.setIcon(icon)
        copyAction.triggered.connect(self.copyAction)
        contextMenu.addAction(copyAction)

        # Пункт Сохранить
        saveAction = QtGui.QAction("Сохранить")
        icon = get_icon("save")
        saveAction.setIcon(icon)
        saveAction.triggered.connect(self.saveAction)
        contextMenu.addAction(saveAction)

        contextMenu.exec(self.mapToGlobal(ev.pos()))

    @ Slot()
    def homeAction(self):
        # Верхняя точка куба сетки
        pos = {ax: self.axis[ax]["amax"] for ax in "xyz"}
        # Отдаляем камеру чуть дальше
        for ax in "xyz":
            pos[ax] *= 1.8

        azi = 0
        if pos["x"] != 0:
            azi = np.arctan(pos["y"]/pos["x"])
            if pos["y"] == 0:
                if pos["x"] < 0:
                    azi = np.pi
        else:
            azi = np.pi / 2
            if pos["y"] <= 0:
                azi *= -1

        elv = 0
        distXY = (pos["x"]**2 + pos["y"]**2) ** 0.5
        if distXY != 0:
            elv = np.arctan(pos["z"]/distXY)
        else:
            if pos["z"] < 0:
                elv = np.pi

        dist = (pos["x"]**2 + pos["y"]**2 + pos["z"]**2) ** 0.5

        # Приводим углы в градусы
        azi = np.rad2deg(azi)
        elv = np.rad2deg(elv)

        center = QtGui.QVector3D(0, 0, 0)
        self.setCameraPosition(
            pos=center,
            elevation=0,
            azimuth=0,
            distance=0)
        self.setCameraPosition(
            elevation=elv,
            azimuth=azi,
            distance=dist)

        self.paintGridByDirection()

    @ Slot()
    def cleanAction(self):
        self.clear()
        self.charts = []
        self.axis = {}
        self.grid = {}
        self.areas = []
        self.__initAxis()
        self.__initGrid()
        # Ставим вид по умолчанию
        self.homeAction()

        # if hasattr(self, "menu"):
        #     self.menu.listCharts.clear()
        #     self.menu.areasTable.Clean()
        self.my_parent.cleanAction()

    @ Slot()
    def copyAction(self):
        # Если получится копируем изображение в буфер обмена
        img = self.readCutQImage()
        if img:
            QtWidgets.QApplication.clipboard().setImage(img)

    @ Slot()
    def saveAction(self):
        img = self.readCutQImage()
        if img:
            fileName = QtWidgets.QFileDialog.getSaveFileName(
                None, "Save File", "test.png", "Images (*.png *.jpg)")[0]  # type: ignore
            if fileName:
                img.save(fileName)
        else:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText("На графике ничего нет")
            msg_box.exec()

    def mouseMoveEvent(self, ev):
        lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
        if not hasattr(self, 'mousePos'):
            self.mousePos = lpos
        diff = lpos - self.mousePos

        x = diff.x()
        y = diff.y()

        self.mousePos = lpos
        if ev.buttons() == Qt.MouseButton.LeftButton:
            self.orbit(-x, y)
        elif ev.buttons() == Qt.MouseButton.MiddleButton:
            self.pan(x, y, 0, relative='view')

        self.paintGridByDirection()

    def mousePressEvent(self, ev):
        self.mousePos = ev.position() if hasattr(ev, 'position') else ev.localPos()
