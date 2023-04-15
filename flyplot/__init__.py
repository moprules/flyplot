import os
import math
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtCore import Slot
from PySide6 import QtWidgets, QtGui, QtCore


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


class Graph3DWidjet(gl.GLViewWidget):
    def __init__(self, data_file="", *args, **kargs):
        super().__init__(*args, **kargs)

        # Задаём цвет фона по умолчанию стоит черный, будет белый
        self.setBackgroundColor("w")

        self.graphs = []
        self.axis = {}
        self.grid = {}
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
        self.setFocusPolicy(QtCore.Qt.StrongFocus)  # type: ignore

        if data_file:
            self.addChart(data_file)

        # Ставим вид по умолчанию
        self.goDefView()

        # self.__testDebug()

    def __testDebug(self):
        for ax in "xyz":
            axi = Text3DItem(ax, size=400)
            self.addItem(axi)
            d = {"x": 0, "y": 0, "z": 0}
            d[ax] = 500
            axi.translate(d["x"], d["y"], d["z"])

    def Clean(self):
        self.clear()
        self.graphs = []
        self.axis = {}
        self.grid = {}
        self.__initAxis()
        self.__initGrid()
        # Ставим вид по умолчанию
        self.goDefView()

        # self.__testDebug()

    def mouseMoveEvent(self, ev):

        lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
        diff = lpos - self.mousePos
        self.mousePos = lpos

        if ev.buttons() == QtCore.Qt.MouseButton.RightButton:
            self.orbit(-diff.x(), diff.y())
        elif ev.buttons() == QtCore.Qt.MouseButton.MiddleButton:
            self.pan(diff.x(), diff.y(), 0, relative='view')

        self.paintGridByDirection()

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
            self.grid[gg].setColor((0, 0, 0, 50))
            # Добавляем объект сетки на 3D сцену
            self.addItem(self.grid[gg])

        # перерисовываем всю 3D сетку
        self.paintGrid()

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
        for chart in self.graphs:
            for ax in "xyz":
                axi = self.axis[ax]
                axi["min"] = min(chart["axis"][ax]["min"], axi["min"])
                axi["max"] = max(chart["axis"][ax]["max"], axi["max"])

        # Округляем эти значения с точность шага сетки
        for ax in "xyz":
            axi = self.axis[ax]
            space = axi["space"]
            for mod in ("min", "max"):
                val = axi[mod]
                sign = 1 if val >= 0 else -1
                val = math.ceil(abs(val)/space)*space
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
            ddY += l.height / 2 + label["step"]
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
            ddY += l.height / 2 + label["step"]
            # Перемещение завист от положения оси Z
            l.myTranslate(0, -z["direction"]*ddY, 0)
            # Кажду метку для красоты поворачиваем на маленький угол
            # l.myRotate(rX, "x")
            # Шаг между подписями
            ddY += label["step"]

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

    def addChart(self, data_file: str):
        chart = self.__parseData(data_file)
        if chart:
            # Создаём объект 3D графика
            plt = gl.GLLinePlotItem(
                pos=chart["coords"], color=pg.mkColor('b'), width=1, antialias=True)
            # Добавляем его на наш виджет
            self.addItem(plt)
            self.graphs.append(chart)

            # Перестраиваем сетку под новый график
            self.recalcAxis()
            self.paintGrid()

            for ax in "xyz":
                d = chart["axis"][ax]
                axiName = d["name"] + ", " + d["dim"]
                # Добавляем новые подписи оси нужно
                self.addLabel(ax, axiName)
                # Пересчитываем подписи делений
                self.recalcValuesAxis(ax)
                self.paintAxis(ax)

            # Переходим в вид по умолчанию, чтобы были видны
            # Все графики в пространстве
            self.goDefView()

    def __parseData(self, data_file: str):
        chart = {}
        with open(data_file) as f:
            chart["name"] = f.readline().split("name: ")[-1].strip()

            chart["type"] = f.readline().split("type: ")[-1].strip()

            if chart["type"] != "3D":
                msg_box = QtWidgets.QMessageBox()
                msg_box.setWindowTitle("Ошибка")
                msg_box.setText(f'График типа "{chart["type"]}" а не 3D')
                msg_box.exec()
                return None

            chart["axis"] = {}
            for _ in range(3):
                # Получаем ось - x, y, z
                ax, data = f.readline().split(":")
                # Поолучаем её название и размерность
                name, dim = map(lambda s: s.strip(), data.split("|"))
                chart["axis"][ax] = {"name": name, "dim": dim}

            # Считываем пустую строку, там идентификатор начала точек графика
            f.readline()
            # Массивы точек
            chart["coords"] = []
            # Массив точек времени
            chart["times"] = []

            # Крафйние точки куба, вмещающего график
            p1 = np.zeros(3)
            p2 = np.zeros(3)

            isFirst = True
            for line in f:
                # Очищаем строку
                line = line.strip()
                # Пропускаем пустые строки и комментарии
                if not line or line[0].isalpha():
                    continue
                # Флаг, что началься новый блок
                if line.startswith("points"):
                    break
                # Обрабатываем координаты точек
                time, data = line.split("->")
                chart["times"].append(float(time))
                curX, curY, curZ = map(float, data.split())
                chart["coords"].append((curX, curY, curZ))
                if isFirst:
                    p1[:] = curX, curY, curZ  # type: ignore
                    p2[:] = curX, curY, curZ  # type: ignore
                    isFirst = False
                else:
                    p1[0] = min(p1[0], curX)  # type: ignore
                    p1[1] = min(p1[1], curY)  # type: ignore
                    p1[2] = min(p1[2], curZ)  # type: ignore

                    p2[0] = max(p2[0], curX)  # type: ignore
                    p2[1] = max(p2[1], curY)  # type: ignore
                    p2[2] = max(p2[2], curZ)  # type: ignore

            chart["axis"]["x"]["min"] = p1[0]
            chart["axis"]["y"]["min"] = p1[1]
            chart["axis"]["z"]["min"] = p1[2]

            chart["axis"]["x"]["max"] = p2[0]
            chart["axis"]["y"]["max"] = p2[1]
            chart["axis"]["z"]["max"] = p2[2]

        return chart

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
            # Перерисовые подписи оси
            self.paintAxis(ax)

    def recalcValuesAxis(self, ax):
        # Обновляем значения делений осей
        axi = self.axis[ax]
        # Удаляем все подписи делений на оси
        for v in axi["value"]["mas"]:
            self.removeItem(v)
        # Очищаем список подписей
        axi["value"]["mas"].clear()
        # Вычисляем новое количество делений
        target_cnt = axi["size"] // axi["space"] + 1
        # добавляем нужно количетсво меток с текстом
        # Первое значение будет минимумов
        first = axi["min"]
        # Получаем размер текста меток
        size = axi["value"]["size"]
        for i in range(target_cnt):
            # for i in range(1):
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

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        super().keyPressEvent(event)

        # Если нажали Ctrl + C
        if event.key() == QtCore.Qt.Key_C and event.modifiers() == QtCore.Qt.ControlModifier:  # type: ignore
            # Если получится копируем изображение в буфер обмена
            img = self.readCutQImage()
            if img:
                QtWidgets.QApplication.clipboard().setImage(img)

    def goDefView(self):
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


class Menu3DLayout(QtWidgets.QVBoxLayout):
    def __init__(self, graph: Graph3DWidjet, *args, **kargs):
        super().__init__(*args, **kargs)

        self.graph = graph

        self.setAlignment(QtCore.Qt.AlignTop)  # type: ignore

        buttonAddGraph = QtWidgets.QPushButton(text="Добавить График")
        buttonAddGraph.clicked.connect(self.loadChart)
        self.addWidget(buttonAddGraph)

        buttonCamera = QtWidgets.QPushButton(text="Вид по умолчанию")
        buttonCamera.clicked.connect(self.onDefPosClick)
        self.addWidget(buttonCamera)

        testButton = QtWidgets.QPushButton(text="Тест")
        testButton.clicked.connect(self.onTestButton)
        self.addWidget(testButton)

        spacer = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)  # type: ignore
        self.addSpacerItem(spacer)

        buttonSave = QtWidgets.QPushButton(text="save")
        buttonSave.clicked.connect(self.saveChart)
        self.addWidget(buttonSave)

        buttonClean = QtWidgets.QPushButton(text="clean")
        buttonClean.clicked.connect(self.cleanChart)
        self.addWidget(buttonClean)

    @Slot()
    def saveChart(self):
        img = self.graph.readCutQImage()
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

    @Slot()
    def loadChart(self):
        dialog = QtWidgets.QFileDialog(
            parent=None,
            caption="Выберете файл расчёта",
            directory=os.path.abspath("."))
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)  # type: ignore
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)  # type: ignore
        if dialog.exec():
            data_file = dialog.selectedFiles()[0]
            self.graph.addChart(data_file)
            self.parentWidget().setWindowTitle(data_file)

    @Slot()
    def onDefPosClick(self):
        self.graph.goDefView()

    @Slot()
    def onTestButton(self):
        self.graph.paintAxis("y")

    @Slot()
    def cleanChart(self):
        self.graph.Clean()


class Graph3DWindow(QtWidgets.QWidget):
    def __init__(self, data_file: str = "", *args, **kargs):
        super().__init__(*args, **kargs)

        # названия файла с данными для графика
        self.data_file = data_file
        # Получаем окно 3d графика
        self.graph = Graph3DWidjet(data_file)

        # Задаём лаяут по умолчанию
        self.__layout = QtWidgets.QHBoxLayout(self)
        # Добавим туда сам график
        self.__layout.addWidget(self.graph, 1)
        self.menu = Menu3DLayout(self.graph)
        # Добавим туда меню для графика
        self.__layout.addLayout(self.menu)
        # Приклеиваем компоненты к верху виджета
        self.__layout.setAlignment(QtCore.Qt.AlignTop)  # type: ignore

        # Задаём заголовок виджета
        self.setWindowTitle(data_file)