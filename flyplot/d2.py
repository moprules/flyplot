import os
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6 import QtCore
from PySide6.QtCore import Slot, Qt
from PySide6 import QtWidgets, QtGui

from .icons import get_icon


class Area2D(gl.GLMeshItem):
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


class Plot2DWidjet(pg.PlotWidget):
    def __init__(self, parent, *args, **kargs):
        super().__init__(*args, **kargs)
        self.my_parent = parent

        # Задаём цвет фона по умолчанию стоит черный, будет белый
        self.setBackground("w")

        self.charts = []
        self.areas = []

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

        self.setMenuEnabled(False)

        self.showGrid(x = True, y = True, alpha = 0.4)

        for axis in ("bottom", "left"):
            axis = self.getAxis(axis)
            labelStyle = {'color': '#000', 'font-size': '12pt'}
            axis.setLabel(**labelStyle)
            axis.showLabel()
        
        self.legend = self.addLegend()
        self.legend.hide()

        # Ставим вид по умолчанию
        self.homeAction()

    def addChart(self, chart: dict):
        stdcolors = "brkgy"
        cindex = len(self.charts) % len(stdcolors)
        chart["color"] = stdcolors[cindex]
        # Создаём объект 2D графика
        pen = pg.mkPen(color=chart["color"], width=2)
        plt = self.plot(chart["x"], chart["y"], pen=pen)
        chart["plt"] = plt
        self.charts.append(chart)
        self.setLegend()

        # Переходим в вид по умолчанию, чтобы были видны
        # Все графики в пространстве
        self.homeAction()
    
    def setLegend(self):
        self.legend.clear()
        textXmas = []
        textY = ""
        for chart in self.charts:
            textY = chart["axis"]["y"]["name"]
            if chart["axis"]["y"]["dim"]:
                textY += ", " + chart["axis"]["y"]["dim"]
            textX = chart["axis"]["x"]["name"]
            if chart["axis"]["x"]["dim"]:
                textX += ", " + chart["axis"]["x"]["dim"]
            if textX not in textXmas:
                textXmas.append(textX)
            self.legend.addItem(chart["plt"], textY)
        
        if len(self.charts) > 1:
            self.legend.show()
            textY = "values"
        else:
            self.legend.hide()

        self.setLabel(axis='left', text=textY)
        self.setLabel(axis='bottom', text=" | ".join(textXmas))
        

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
        chart = self.charts[i]
        plt = chart["plt"]
        plt.setData(chart["x"], chart["y"])
        self.homeAction()

    def updChartPoints(self, data_file: str, x: list, y: list):
        i = self.findIndexChart(data_file)
        if i == -1:
            return
        chart = self.charts[i]
        chart["x"].extend(x)
        chart["y"].extend(y)
        plt = chart["plt"]
        plt.setData(chart["x"], chart["y"])
        self.homeAction()

    def setChartColor(self, color, i: int = None, data_file: str = None):
        if i is None:
            i = self.findIndexChart(data_file)
        if i == -1:
            return
        chart = self.charts[i]
        plt = chart["plt"]
        plt.setPen(pg.mkPen(color))

    def delChart(self, i: int = None, data_file: str = None):
        if i is None:
            i = self.findIndexChart(data_file)
        if i == -1:
            return
        chart = self.charts.pop(i)
        plt = chart["plt"]
        self.removeItem(plt)
        self.homeAction()

        if not self.charts:
            self.cleanAction()

    def addArea(self,
                pos=[0, 0, 0],
                radius=1.0,
                color=pg.mkColor("g"),
                i=None):
        if not i:
            i = len(self.areas)
        area = Area2D(pos=pos, radius=radius, color=color)
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

    def readCutQImage(self) -> QtGui.QImage | None:
        return self.grab().toImage()

    @ Slot()
    def homeAction(self):
        self.autoRange()

    @ Slot()
    def cleanAction(self):
        self.clear()
        self.charts = []
        self.areas = []

        self.setLabel(axis='left', text="")
        self.setLabel(axis='bottom', text="")
        # Ставим вид по умолчанию
        self.homeAction()

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
    
    def getDescription(self):
        return " | ".join(chart["name"] for chart in self.charts)
