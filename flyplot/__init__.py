import os
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtCore import Slot
from PySide6 import QtWidgets, QtGui, QtCore
from functools import partial
from . parser import Parser3DGraphFile

PKG_DIR = os.path.dirname(os.path.abspath(__file__))


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


class GraphContextMenu(QtWidgets.QMenu):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self.actions = {}

        # Пункт Вид по умолчанию
        self.actions["home"] = QtGui.QAction("Вид по умолчанию", self)
        # Тригеры настраиваются в композирующем классе
        # self.actions["defView"].triggered.connect(self.action1)
        icon = QtGui.QPixmap(os.path.join(PKG_DIR, "icons/home.svg"))
        self.actions["home"].setIcon(icon)
        self.addAction(self.actions["home"])

        # Пункт Очистить
        self.actions["clean"] = QtGui.QAction("Очистить", self)
        icon = QtGui.QPixmap(os.path.join(PKG_DIR, "icons/clean.svg"))
        self.actions["clean"].setIcon(icon)
        self.addAction(self.actions["clean"])

        # Пункт Скопировать
        self.actions["copy"] = QtGui.QAction("Копировать", self)
        icon = QtGui.QPixmap(os.path.join(PKG_DIR, "icons/copy.svg"))
        self.actions["copy"].setIcon(icon)
        self.addAction(self.actions["copy"])

        # Пункт Сохранить
        self.actions["save"] = QtGui.QAction("Сохранить", self)
        icon = QtGui.QPixmap(os.path.join(PKG_DIR, "icons/save.svg"))
        self.actions["save"].setIcon(icon)
        self.addAction(self.actions["save"])


class Area(gl.GLMeshItem):
    def __init__(self,
                 pos=[0, 0, 0],
                 radius=1.0,
                 length=0.1,
                 color=pg.mkColor("g")):
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
                         color=self.color,
                         glOptions='opaque')
        self.translate(*self.pos)
        self.translate(0, 0, -self.length)

    def setColor(self, c):
        self.color = pg.mkColor(c)
        super().setColor(c)


class Graph3DWidjet(gl.GLViewWidget):
    def __init__(self, data_file="", *args, **kargs):
        super().__init__(*args, **kargs)

        # Задаём цвет фона по умолчанию стоит черный, будет белый
        self.setBackgroundColor("w")

        self.graphs = []
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
        self.setFocusPolicy(QtCore.Qt.StrongFocus)  # type: ignore

        if data_file:
            self.addChart(data_file)

        # Ставим вид по умолчанию
        self.goDefView()

        self.ct_menu = GraphContextMenu()
        self.ct_menu.actions["home"].triggered.connect(self.goDefView)
        self.ct_menu.actions["clean"].triggered.connect(self.Clean)
        self.ct_menu.actions["copy"].triggered.connect(self.keyCtrlCAction)
        self.ct_menu.actions["save"].triggered.connect(self.saveAction)

        # self.__testDebug()

        # area = Area(pos=[1100, -1900, 0], radius=500)
        # self.addItem(area)
        # self.areas.append(area)
        # self.addArea(pos=[1100, -1900, 0], radius=500, color=pg.mkColor("g"),i=0)

    def addArea(self,
                pos=[0, 0, 0],
                radius=1.0,
                color=pg.mkColor("g"),
                i=None):

        if not i:
            i = len(self.areas)
        area = Area(pos=pos, radius=radius, color=color)
        self.addItem(area)
        # ЧТобы рисовалось раньше графика
        area.setDepthValue(-100)
        self.areas.insert(i, area)

    def contextMenuEvent(self, ev: QtGui.QContextMenuEvent):
        self.ct_menu.exec(self.mapToGlobal(ev.pos()))

    def setMenu(self, menu):
        self.menu = menu

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
        self.areas = []
        self.__initAxis()
        self.__initGrid()
        # Ставим вид по умолчанию
        self.goDefView()

        if hasattr(self, "menu"):
            self.menu.listCharts.clear()
            self.menu.listCharts.hide()
            self.menu.areasTable.Clean()

        # self.__testDebug()

    def mouseMoveEvent(self, ev):
        lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
        if not hasattr(self, 'mousePos'):
            self.mousePos = lpos
        diff = lpos - self.mousePos

        x = diff.x()
        y = diff.y()

        self.mousePos = lpos
        if ev.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self.orbit(-x, y)
        elif ev.buttons() == QtCore.Qt.MouseButton.MiddleButton:
            self.pan(x, y, 0, relative='view')

        self.paintGridByDirection()

    def mousePressEvent(self, ev):
        self.mousePos = ev.position() if hasattr(ev, 'position') else ev.localPos()

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

    def updChart(self, chart_name, pos):
        for chart in self.graphs:
            if chart["name"] == chart_name:
                break
        else:
            return

        plt: gl.GLLinePlotItem = chart["plt"]

        plt.setData(pos=pos, color=pg.mkColor(
            chart["color"]), width=1, antialias=True)

    def addChart(self, data_file: str):
        chart = self.__parseData(data_file)
        if chart:
            stdcolors = "brkgy"
            cindex = len(self.graphs) % len(stdcolors)
            chart["color"] = stdcolors[cindex]
            # Создаём объект 3D графика
            plt = gl.GLLinePlotItem(
                pos=chart["coords"], color=pg.mkColor(chart["color"]), width=1, antialias=True)
            # Добавляем его на наш виджет
            self.addItem(plt)
            chart["plt"] = plt
            self.graphs.append(chart)

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
            self.goDefView()

            if hasattr(self, "menu"):
                self.menu.listCharts.add_chart(chart)
                if self.isVisible():
                    self.menu.listCharts.show()

    def reDraw(self):
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

        # Переходим в вид по умолчанию, чтобы были видны
        # Все графики в пространстве
        self.goDefView()

    def __parseData(self, data_file: str):
        p = Parser3DGraphFile()
        chart = p.load(data_file)
        if chart["err"]:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText(f'График типа "{chart["type"]}" а не 3D')
            msg_box.exec()
            return None
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
        # Если нажали Ctrl + C
        if event.key() == QtCore.Qt.Key_C and event.modifiers() == QtCore.Qt.ControlModifier:  # type: ignore
            self.keyCtrlCAction()
        super().keyPressEvent(event)

    @ Slot()
    def keyCtrlCAction(self):
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

    @ Slot()
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


class ColorButton(QtWidgets.QPushButton):
    def __init__(self, color=pg.mkColor("r"), size=24, width=2, parent=None):
        super().__init__(parent)
        self.color = color
        self.size = size
        self.width = width
        self.setFixedHeight(size)
        self.setIcon(self.createIcon())

    def createIcon(self):
        pixmap = QtGui.QPixmap(self.size, self.size)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        color = QtGui.QColor(self.color)
        pen = painter.pen()
        pen.setColor(color)
        pen.setWidth(self.width)

        brush = painter.brush()
        brush.setColor(color)
        brush.setStyle(QtCore.Qt.SolidPattern)
        painter.setBrush(brush)
        painter.setPen(pen)

        r = self.size - self.width*2
        painter.drawEllipse(self.width, self.width, r, r)

        painter.end()

        icon = QtGui.QIcon(pixmap)
        return icon

    def setColor(self, color):
        self.color = pg.mkColor(color)
        self.setIcon(self.createIcon())


class ChartListWidget(QtWidgets.QListWidget):

    def __init__(self, graph: Graph3DWidjet, *args, **kargs):
        super().__init__(*args, **kargs)
        self.graph = graph

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                           QtWidgets.QSizePolicy.Minimum)

    def add_chart(self, chart: dict):
        # Кнопка поменять цвет графика
        color_button = ColorButton(color=pg.mkColor(chart["color"]))
        color_button.setFlat(True)
        color_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                   QtWidgets.QSizePolicy.Minimum)

        label = QtWidgets.QLabel(chart["short_path"])
        label.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                            QtWidgets.QSizePolicy.MinimumExpanding)
        # Кнопка убрать график
        del_button = QtWidgets.QPushButton()
        icon = QtGui.QPixmap(os.path.join(PKG_DIR, "icons/del.svg"))
        del_button.setIcon(icon)
        del_button.setFlat(True)
        del_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                 QtWidgets.QSizePolicy.Fixed)

        item_layout = QtWidgets.QHBoxLayout()
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.addWidget(color_button)
        item_layout.addWidget(label)
        item_layout.addWidget(del_button)
        item_widget = QtWidgets.QWidget()
        item_widget.setLayout(item_layout)
        item = QtWidgets.QListWidgetItem(self)
        item.setSizeHint(item_widget.sizeHint())
        self.setItemWidget(item, item_widget)
        self.setCurrentRow(self.count()-1)

        color_button.clicked.connect(
            partial(self.change_color, color_button, item))
        del_button.clicked.connect(partial(self.remove_item, item))

    @Slot()
    def change_color(self, color_button: ColorButton, item: QtWidgets.QListWidgetItem):
        colorDlg = QtWidgets.QColorDialog()
        i = self.row(item)
        chart = self.graph.graphs[i]
        last_color = pg.mkColor(chart["color"])
        colorDlg.setCurrentColor(last_color)
        if colorDlg.exec() == QtWidgets.QColorDialog.Accepted:
            cur_color = colorDlg.selectedColor()
            chart["color"] = cur_color
            plt: gl.GLLinePlotItem = chart["plt"]
            plt.setData(color=cur_color, width=1, antialias=True)
            color_button.setColor(cur_color)

    @Slot()
    def remove_item(self, item: QtWidgets.QListWidgetItem):
        row = self.row(item)
        self.takeItem(row)
        chart = self.graph.graphs.pop(row)
        self.graph.removeItem(chart["plt"])

        # Если не осталось элементов
        if not self.count():
            # Скрываем список графиков
            self.hide()
            # Очищаем график
            self.graph.Clean()
        else:
            self.graph.reDraw()


class AreasTable(QtWidgets.QTableWidget):
    def __init__(self, graph: Graph3DWidjet):
        super().__init__()

        self.graph = graph
        self.del_btns = []
        self.color_btns = []

        # Установка количества строк и столбцов в таблице
        self.setRowCount(0)
        self.setColumnCount(6)

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                           QtWidgets.QSizePolicy.Minimum)

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.cellChanged.connect(self.handleCellChanged)

        # Заголовки столбцов
        self.headers = ["Цвет", "Радиус", "X", "Y", "Z", ""]
        self.setHorizontalHeaderLabels(["Цвет", "Радиус", "X", "Y", "Z", ""])

        self.addAreaRow()

    def addAreaRow(self, color=pg.mkColor("g"), radisus="", x="", y="", z="", chart: dict = {}):
        row = self.rowCount()
        # Увеличиваем количество строк
        self.setRowCount(row + 1)
        # Выставляем размер строки
        self.setRowHeight(row, 20)

        # Кнопка изменения цвета строки
        color_button = ColorButton(color=pg.mkColor(color))
        color_button.setFlat(True)
        color_button.setFocusPolicy(QtCore.Qt.NoFocus)
        color_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                   QtWidgets.QSizePolicy.Minimum)
        color_button.clicked.connect(partial(self.change_color, color_button))
        self.setCellWidget(row, 0, color_button)
        self.color_btns.append(color_button)

        # Кнопка удаления строки
        del_button = QtWidgets.QPushButton()
        del_button.setFocusPolicy(QtCore.Qt.NoFocus)
        icon = QtGui.QPixmap(os.path.join(PKG_DIR, "icons/del.svg"))
        del_button.setIcon(icon)
        del_button.setFlat(True)
        del_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                 QtWidgets.QSizePolicy.Minimum)
        del_button.clicked.connect(partial(self.delAreaRow, del_button))
        self.setCellWidget(row, 5, del_button)
        self.del_btns.append(del_button)

        self.resizeColumnsToContents()

    @Slot()
    def change_color(self, color_button: ColorButton):
        try:
            colorDlg = QtWidgets.QColorDialog()
            last_color = pg.mkColor(color_button.color)
            colorDlg.setCurrentColor(last_color)
            if colorDlg.exec() == QtWidgets.QColorDialog.Accepted:
                cur_color = colorDlg.selectedColor()
                color_button.setColor(cur_color)
                i = self.color_btns.index(color_button)
                area = self.graph.areas[i]
                area.setColor(cur_color)
        except:
            return

    def delAreaRow(self, del_button):
        try:
            i = self.del_btns.index(del_button)
            self.del_btns.pop(i)
            self.color_btns.pop(i)
            self.removeRow(i)
            area = self.graph.areas.pop(i)
            self.graph.removeItem(area)
        except:
            pass
        if not self.rowCount():
            self.addAreaRow()

    def Clean(self):
        for row in range(self.rowCount(), -1, -1):
            try:
                del_button = self.del_btns[row]
                self.delAreaRow(del_button)
            except:
                pass

    @Slot()
    def handleCellChanged(self, row, col):
        if self.signalsBlocked():
            return
        item = self.item(row, col)
        if item:
            isFlaot = True
            try:
                f = float(item.text())
            except:
                isFlaot = False
            if isFlaot:
                # Если есть столбец радиус
                # столбец Радиус
                radiusCol = self.item(row, 1)
                if radiusCol and radiusCol.text():
                    # Задаём координаты
                    self.blockSignals(True)
                    for j in (2, 3, 4):
                        item = self.item(row, j)
                        if not item or (item and not item.text()):
                            self.setItem(
                                row, j, QtWidgets.QTableWidgetItem("0"))

                    self.blockSignals(False)

                # Если все параметры поля верны
                if all(self.item(row, j) for j in (1, 2, 3, 4)):
                    # Получаем параметры поля
                    radius, *pos = map(float, (self.item(row, j).text()
                                               for j in (1, 2, 3, 4)))
                    try:
                        color = self.color_btns[row].color
                    except:
                        return
                    try:
                        area = self.graph.areas.pop(row)
                        self.graph.removeItem(area)
                    except:
                        pass
                    self.graph.addArea(pos=pos, radius=radius,
                                       color=pg.mkColor(color), i=row)
            else:
                self.blockSignals(True)
                item.setText("")
                self.blockSignals(False)


class Menu3DLayout(QtWidgets.QVBoxLayout):
    def __init__(self, graph: Graph3DWidjet, *args, **kargs):
        super().__init__(*args, **kargs)

        self.graph = graph

        self.setAlignment(QtCore.Qt.AlignTop)  # type: ignore

        buttonAddGraph = QtWidgets.QPushButton(text="Добавить")
        icon = QtGui.QPixmap(os.path.join(PKG_DIR, "icons/add.svg"))
        buttonAddGraph.setIcon(icon)
        buttonAddGraph.clicked.connect(self.loadChart)
        self.addWidget(buttonAddGraph)

        # testButton = QtWidgets.QPushButton(text="Тест")
        # testButton.clicked.connect(self.onTestButton)
        # self.addWidget(testButton)

        self.listCharts = ChartListWidget(self.graph)
        self.addWidget(self.listCharts)

        self.areasTable = AreasTable(self.graph)
        self.addWidget(self.areasTable)

        spacer = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)  # type: ignore
        self.addSpacerItem(spacer)

    @ Slot()
    def loadChart(self):
        dialog = QtWidgets.QFileDialog(
            parent=None,
            caption="Выберете файл расчёта",
            directory=os.path.abspath("."))
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)  # type: ignore
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)  # type: ignore
        if dialog.exec():
            for data_file in dialog.selectedFiles():
                self.graph.addChart(data_file)

    @ Slot()
    def onTestButton(self):
        for chart in self.graph.graphs:
            if chart["name"] == "Matlab":
                break
        else:
            return
        self.graph.removeItem(chart["plt"])


class Graph3DWindow(QtWidgets.QWidget):
    def __init__(self, data_file: str = "", *args, **kargs):
        super().__init__(*args, **kargs)

        self.setWindowTitle("Просмотр графиков")
        icon = QtGui.QPixmap(os.path.join(PKG_DIR, "icons/grafic.svg"))
        self.setWindowIcon(icon)

        # названия файла с данными для графика
        self.data_file = data_file
        # Получаем окно 3d графика
        self.graph = Graph3DWidjet()

        # Задаём лаяут по умолчанию
        self.__layout = QtWidgets.QHBoxLayout(self)

        self.menu = Menu3DLayout(self.graph)
        self.graph.setMenu(self.menu)
        # Добавим туда меню для графика
        self.__layout.addLayout(self.menu)
        # Добавим туда сам график
        self.__layout.addWidget(self.graph, 1)
        # Приклеиваем компоненты к верху виджета
        self.__layout.setAlignment(QtCore.Qt.AlignTop)  # type: ignore

        if self.data_file:
            self.graph.addChart(self.data_file)

        # Разрешить перетаскивание
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            data_file = url.toLocalFile()
            self.graph.addChart(data_file)
