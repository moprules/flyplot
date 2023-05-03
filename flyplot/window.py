import os
import pyqtgraph as pg
from PySide6 import QtCore
from PySide6.QtCore import Slot, Qt
from PySide6 import QtWidgets, QtGui
from functools import partial

from .icons import get_icon
from .d3 import Plot3DWidjet
from .d2 import Plot2DWidjet
from .parser import Parser2DChartFile, Parser3DChartFile


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
        pixmap.fill(Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        color = QtGui.QColor(self.color)
        pen = painter.pen()
        pen.setColor(color)
        pen.setWidth(self.width)

        brush = painter.brush()
        brush.setColor(color)
        brush.setStyle(Qt.SolidPattern)
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

    def __init__(self, plotter: Plot3DWidjet| Plot2DWidjet, *args, **kargs):
        super().__init__(*args, **kargs)
        self.plotter = plotter
        self.setMinimumWidth(300)

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                           QtWidgets.QSizePolicy.Minimum)

    def addChart(self, chart: dict):
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
        icon = get_icon("del")
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
            partial(self.changeColor, color_button, item))
        del_button.clicked.connect(partial(self.delChart, item))

    @Slot()
    def changeColor(self, color_button: ColorButton, item: QtWidgets.QListWidgetItem):
        colorDlg = QtWidgets.QColorDialog()
        i = self.row(item)
        last_color = pg.mkColor(color_button.color)
        colorDlg.setCurrentColor(last_color)
        if colorDlg.exec() == QtWidgets.QColorDialog.Accepted:
            cur_color = colorDlg.selectedColor()
            self.plotter.setChartColor(cur_color, i)
            color_button.setColor(cur_color)

    @Slot()
    def delChart(self, item: QtWidgets.QListWidgetItem):
        row = self.row(item)
        self.takeItem(row)
        self.plotter.delChart(row)


class AreasTable(QtWidgets.QTableWidget):
    def __init__(self, plotter: Plot3DWidjet):
        super().__init__()

        self.setMinimumWidth(300)

        self.plotter = plotter
        self.del_btns = []
        self.color_btns = []

        # Установка количества строк и столбцов в таблице
        self.setRowCount(0)
        self.setColumnCount(6)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cellChanged.connect(self.handleCellChanged)

        # Заголовки столбцов
        self.headers = ["Цвет", "Радиус", "X", "Y", "Z", ""]
        self.setHorizontalHeaderLabels(self.headers)

        self.addArea()

    def contextMenuEvent(self, event):
        # Создаем контекстное меню
        contextMenu = QtWidgets.QMenu(self)

        # Добавляем пункты меню
        addAction = QtGui.QAction('Добавить')
        icon = get_icon("add")
        addAction.setIcon(icon)
        addAction.triggered.connect(self.addArea)

        clearAction = QtGui.QAction('Очистить')
        icon = get_icon("clean")
        clearAction.setIcon(icon)
        clearAction.triggered.connect(self.Clean)

        contextMenu.addAction(addAction)
        contextMenu.addAction(clearAction)

        # Показываем контекстное меню
        contextMenu.exec(event.globalPos())

    @Slot()
    def addArea(self, radius="", x="", y="", z="", color=pg.mkColor("g")):
        row = self.rowCount()
        # Если у нас последняя строка пустая, то заполняем её
        isOld = False
        if row >= 1:
            isEmpty = True
            for c in (1, 2, 3, 4):
                item = self.item(row-1, c)
                if item and item.text():
                    isEmpty = False
                    break
            if isEmpty:
                isOld = True
                row -= 1

        # Увеличиваем количество строк
        self.setRowCount(row + 1)
        # Выставляем размер строки
        self.setRowHeight(row, 20)

        # Кнопка изменения цвета строки
        if not isOld:
            color_button = ColorButton(color=pg.mkColor(color))
            color_button.setFlat(True)
            color_button.setFocusPolicy(Qt.NoFocus)
            color_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                       QtWidgets.QSizePolicy.Minimum)
            color_button.clicked.connect(
                partial(self.changeColor, color_button))
            self.setCellWidget(row, 0, color_button)
            self.color_btns.append(color_button)

        # Радиус области
        self.setItem(row, 1, QtWidgets.QTableWidgetItem(str(radius)))
        self.setItem(row, 2, QtWidgets.QTableWidgetItem(str(x)))
        self.setItem(row, 3, QtWidgets.QTableWidgetItem(str(y)))
        self.setItem(row, 4, QtWidgets.QTableWidgetItem(str(z)))

        # Кнопка удаления строки
        if not isOld:
            del_button = QtWidgets.QPushButton()
            del_button.setFocusPolicy(Qt.NoFocus)
            icon = get_icon("del")
            del_button.setIcon(icon)
            del_button.setFlat(True)
            del_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                     QtWidgets.QSizePolicy.Minimum)
            del_button.clicked.connect(partial(self.delArea, del_button))
            self.setCellWidget(row, 5, del_button)
            self.del_btns.append(del_button)

        self.myResize()
    
    def myResize(self):
        width = 300
        a = self.sizeHint().width()
        self.resizeColumnsToContents()
        # средня ширина столбца
        average_width = width // self.columnCount() - 3
        for i in range(self.columnCount()):
            self.setColumnWidth(i, average_width)

    @Slot()
    def changeColor(self, color_button: ColorButton):
        try:
            colorDlg = QtWidgets.QColorDialog()
            last_color = pg.mkColor(color_button.color)
            colorDlg.setCurrentColor(last_color)
            if colorDlg.exec() == QtWidgets.QColorDialog.Accepted:
                cur_color = colorDlg.selectedColor()
                color_button.setColor(cur_color)
                i = self.color_btns.index(color_button)
                self.plotter.setAreaColor(cur_color, i)
        except:
            return

    @Slot()
    def delArea(self, del_button):
        try:
            i = self.del_btns.index(del_button)
            self.del_btns.pop(i)
            self.color_btns.pop(i)
            self.removeRow(i)
            self.plotter.delArea(i)
        except:
            pass
        if not self.rowCount():
            self.addArea()

    @Slot()
    def Clean(self):
        for del_button in self.del_btns:
            self.delArea(del_button)

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
                        self.plotter.delArea(row)
                    except:
                        pass
                    self.plotter.addArea(pos=pos, radius=radius,
                                         color=pg.mkColor(color), i=row)
            else:
                self.blockSignals(True)
                item.setText("")
                self.blockSignals(False)


class MenuLayout(QtWidgets.QVBoxLayout):
    def __init__(self, parent, *args, **kargs):
        super().__init__(*args, **kargs)
        self.my_parent = parent
        self.plotter: Plot3DWidjet| Plot2DWidjet = self.my_parent.plotter

        self.setAlignment(Qt.AlignTop)  # type: ignore

        buttonAddChart = QtWidgets.QPushButton(text="Добавить График")
        icon = get_icon("add")
        buttonAddChart.setIcon(icon)
        buttonAddChart.clicked.connect(self.addChart)
        self.addWidget(buttonAddChart)

        self.listCharts = ChartListWidget(self.plotter)
        self.addWidget(self.listCharts)


        labelArea =  QtWidgets.QLabel(text="Области")
        labelArea.setAlignment(Qt.AlignLeft)
        labelArea.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                   QtWidgets.QSizePolicy.Minimum)
        self.addWidget(labelArea)

        self.areasTable = AreasTable(self.plotter)
        self.addWidget(self.areasTable)

        spacer = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)  # type: ignore
        self.addSpacerItem(spacer)

    @ Slot()
    def addChart(self):
        dialog = QtWidgets.QFileDialog(
            parent=None,
            caption="Выберете файл расчёта",
            directory=os.path.abspath("."))
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)  # type: ignore
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)  # type: ignore
        if dialog.exec():
            for data_file in dialog.selectedFiles():
                self.my_parent.addChart(data_file)


class PlotWindow(QtWidgets.QWidget):
    def __init__(self, main_window=None, chart_type="3D", data_file: str = "", *args, **kargs):
        super().__init__(*args, **kargs)
        self.main_window = main_window
        self.chart_type = chart_type

        # Получаем окно 3d графика
        if self.chart_type == "3D":
            self.plotter = Plot3DWidjet(self)
        else:
            self.plotter = Plot2DWidjet(self)

        # Задаём лаяут по умолчанию
        self.__layout = QtWidgets.QHBoxLayout(self)

        self.menu = MenuLayout(self)
        # Добавим туда меню для графика
        self.__layout.addLayout(self.menu)
        # Добавим туда сам график
        self.__layout.addWidget(self.plotter, 1)
        # Приклеиваем компоненты к верху виджета
        self.__layout.setAlignment(Qt.AlignTop)  # type: ignore

        if data_file:
            self.addChart(data_file)

        # Разрешить перетаскивание
        self.setAcceptDrops(True)

        self.setWindowTitle(f"Просмотр графиков {self.chart_type}")
        icon = get_icon("grafic")
        self.setWindowIcon(icon)

    def parseData(self, data_file: str):
        if self.chart_type == "3D":
            p = Parser3DChartFile()
        else:
            p = Parser2DChartFile()
        chart = p.load(data_file)
        if chart["err"]:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText(chart["err"])
            msg_box.exec()
            return None
        return chart

    def addChart(self, data_file: str = "", chart: dict = {}):
        if data_file:
            chart = self.parseData(data_file)
        if chart:
            self.plotter.addChart(chart)
            self.menu.listCharts.addChart(chart)
            if chart["areas"]:
                for (radius, *pos) in chart["areas"]:
                    self.plotter.addArea(pos=pos, radius=radius)
                    self.menu.areasTable.addArea(radius, *pos)

    def updChart(self, file_patch, **kargs):
        if self.chart_type == "3D":
            self.plotter.updChartPoints(file_patch, kargs["pos"])
        else:
            self.plotter.updChartPoints(file_patch, kargs["x"], kargs["y"])

    def cleanAction(self):
        self.menu.listCharts.clear()
        self.menu.areasTable.Clean()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            data_file = url.toLocalFile()
            self.addChart(data_file)

    def closeEvent(self, event: QtGui.QCloseEvent):
        # сообщаем главному окну, что детское окно было закрыто
        if self.main_window:
            self.main_window.wasClosed(self)
        super().closeEvent(event)
    
    def getDescription(self):
        return self.plotter.getDescription()
