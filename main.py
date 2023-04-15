import sys
from flyplot import Graph3DWindow
from PySide6 import QtWidgets

if __name__ == '__main__':

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    w = Graph3DWindow()
    w.show()
    sys.exit(app.exec())
