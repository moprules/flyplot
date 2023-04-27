"""
Модуль для парсинга файлов
"""
import os
import io


class Parser3DGraphFile:
    ids = ["name", "type", "coords", "cube", "areas", "x", "y", "z"]

    def __init__(self):
        self.chart = {}
        # Обязательные элементы
        self.chart["path"]: str = ""
        self.chart["short_path"]: str = ""
        self.chart["type"]: str = ""
        self.chart["axis"]: dict = {}
        self.chart["axis"]["x"]: dict = {
            "name": "", "dim": "", "min": 0, "max": 0}
        self.chart["axis"]["y"]: dict = {
            "name": "", "dim": "", "min": 0, "max": 0}
        self.chart["axis"]["z"]: dict = {
            "name": "", "dim": "", "min": 0, "max": 0}
        # Массивы точек
        self.chart["coords"]: list = []
        # Массив точек времени
        self.chart["times"]: list = []

        # Необязательные элементы
        self.chart["name"]: str = ""
        self.chart["cube"]: list = []
        self.chart["areas"]: list[list[float, float, float, float]] = []

        # Ошибка в процессе парсинга
        self.chart["err"]: str = ""

    def skip(self, f: io.TextIOWrapper):
        id = ""
        line = f.readline()
        while line:
            idd = self.check_id(line)
            if idd:
                id = idd
                break
            line = f.readline()
        return id, line.strip()

    def check_id(self, line: str):
        line = line.strip()
        id = ""
        for idd in self.ids:
            if line.startswith(idd):
                id = idd
                break
        return id

    def do_by_id(self, id: str, line: str, f: io.TextIOWrapper):

        l: str = ""
        if id == "name":
            l = self.setName(line)
        elif id == "type":
            l = self.setType(line)
        elif id in "xyz":
            l = self.setAxis(id, line)
        elif id == "cube":
            l = self.setCube(f)
        elif id == "areas":
            l = self.setAreas(f)
        elif id == "coords":
            l = self.setCoords(f)

        id = self.check_id(l)
        if id:
            self.do_by_id(id, l, f)

    def setPath(self, data_file):
        self.chart["path"] = os.path.abspath(data_file)
        # получение имени файла
        filename = os.path.basename(self.chart["path"])
        # получение имени папки
        dirname = os.path.basename(os.path.dirname(self.chart["path"]))
        # короткий путь до файла
        self.chart["short_path"] = os.path.join(dirname, filename)

    def setName(self, line: str):
        self.chart["name"] = line.split("name: ")[-1].strip()
        return ""

    def setType(self, line: str):
        self.chart["type"] = line.split("type: ")[-1].strip().upper()
        if self.chart["type"] != "3D":
            self.chart["err"] = f'График типа "{self.chart["type"]}", а не 3D'

        return ""

    def setAxis(self, axi: str, line: str):
        # Получаем ось - x, y, z
        _, data = line.split(":")
        # Поолучаем её название и размерность
        name, dim = map(lambda s: s.strip(), data.split("|"))
        self.chart["axis"][axi]["name"] = name
        self.chart["axis"][axi]["dim"] = dim
        return ""

    def setCube(self, f: io.TextIOWrapper):
        line = f.readline()
        while line and line[0].isdigit():
            point = [float(x) for x in line.split()]
            self.chart["cube"].append(point)
            line = f.readline()

        for p in self.chart["cube"]:
            for i, ax in enumerate("xyz"):
                axi = self.chart["axis"][ax]
                axi["min"] = min(axi["min"], p[i])
                axi["max"] = max(axi["max"], p[i])

        return line

    def setAreas(self, f: io.TextIOWrapper):
        line = f.readline()
        while line and line[0].isdigit():
            circle = [float(x) for x in line.split()]
            self.chart["areas"].append(circle)
            line = f.readline()

        for c in self.chart["areas"]:
            for i, ax in enumerate("xy"):
                axi = self.chart["axis"][ax]
                axi["min"] = min(axi["min"], c[i+1]-c[0])
                axi["max"] = max(axi["max"], c[i+1]+c[0])

        return line

    def setCoords(self, f: io.TextIOWrapper):
        # Крафйние точки куба, вмещающего график
        p1 = [self.chart["axis"][ax]["min"] for ax in "xyz"]
        p2 = [self.chart["axis"][ax]["max"] for ax in "xyz"]

        line = f.readline()
        while line and line[0].isdigit():
            # Очищаем строку
            line = line.strip()
            # Обрабатываем координаты точек
            time, data = line.split("->")
            self.chart["times"].append(float(time))
            curX, curY, curZ = map(float, data.split())
            self.chart["coords"].append((curX, curY, curZ))
            p1[0] = min(p1[0], curX)
            p1[1] = min(p1[1], curY)
            p1[2] = min(p1[2], curZ)

            p2[0] = max(p2[0], curX)
            p2[1] = max(p2[1], curY)
            p2[2] = max(p2[2], curZ)
            line = f.readline()

        for i, ax in enumerate("xyz"):
            self.chart["axis"][ax]["min"] = p1[i]
            self.chart["axis"][ax]["max"] = p2[i]

        return line

    def load(self, data_file: str):
        self.setPath(data_file)

        with open(data_file, "r", encoding="utf-8") as f:
            id, line = self.skip(f)
            while id:
                self.do_by_id(id, line, f)
                id, line = self.skip(f)

        return self.chart
