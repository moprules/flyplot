import os
from PySide6 import QtGui


PKG_DIR = os.path.dirname(os.path.abspath(__file__))


def get_icon(icon_name: str) -> QtGui.QPixmap:
    return QtGui.QPixmap(os.path.join(PKG_DIR, f"{icon_name}.svg"))
