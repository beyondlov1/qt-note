from posixpath import dirname
import sys
import random
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, Signal
import os
import json
import uuid

from TimeNormalizer import TimeNormalizer
import arrow  # 引入包


tn = TimeNormalizer()


def readFile(path):
    with open(path, encoding="utf-8") as f:
        contents = f.read()
        return contents


def writeFile(path, content):
    with open(path, "w") as f:
        f.write(content)


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.editText = MyTextEdit()
        self.editText.ctrlenter.connect(self.write_to_list)
        self.editText.ctrln.connect(self.clear_edit_text)
        self.editText.ctrldown.connect(self.next)
        self.editText.ctrlup.connect(self.pre)
        self.editText.ctrldelete.connect(self.delete_item)
        self.list = MyListWidget()
        self.list.deleted.connect(self.delete_item)
        self.list.entered.connect(self.focus_edit)
        self.list.itemSelectionChanged.connect(self.show_list_item)
        self.refresh_list()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.editText)
        self.layout.addWidget(self.list)


    def init_list(self,list:QtWidgets.QListWidget, data):
        for datum in data:
            item = QtWidgets.QListWidgetItem(list)
            item.setData(Qt.ItemDataRole.UserRole,datum)
            widget = MyListItemWidget()
            widget.rander(datum)
            item.setSizeHint(widget.sizeHint())
            list.setItemWidget(item, widget)
            list.addItem(item)
            
    @QtCore.Slot()
    def write_to_list(self):

        value = self.editText.toPlainText()
        parsed_obj = json.loads(tn.parse(self.editText.toPlainText()))
        print(parsed_obj)
        if "type" in parsed_obj and parsed_obj["type"] == "timestamp":
            value = value+"|"+parsed_obj["timestamp"]
        if "type" in parsed_obj and parsed_obj["type"] == "timedelta":
            delta = parsed_obj["timedelta"]
            arw = arrow.now().shift(years=delta["year"], months=delta["month"], days=delta["day"],
                                    hours=delta["hour"], minutes=delta["minute"], seconds=delta["second"])
            value = value+"|"+arw.format("YYYY-MM-DD HH:mm:ss")
            
        next_select = 0
        path = self.get_path()
        contents = self.read_contents(path)
        if self.editText.getData() and self.editText.getData()["id"]:
            id = self.editText.getData()["id"]
            for content in contents:
                if content["id"] == id:
                    content["value"] = value
                    break
                next_select += 1
        else:
            contents.append(    
                {"id": str(uuid.uuid4()), "value": value})
            next_select = len(contents) - 1
        writeFile(path, json.dumps(contents))
        self.refresh_list(next_select)
        self.clear_edit_text()

    def refresh_list(self, select=0):
        self.list.clear()
        path = self.get_path()
        contents = self.read_contents(path)
        self.init_list(self.list, contents)
        if contents:
            self.list.setCurrentRow(select)
        else:
            self.focus_edit()

    def get_path(self):
        return os.path.join(dirname(sys.argv[0]),"note.list")
        # return "/media/beyond/70f23ead-fa6d-4628-acf7-c82133c03245/home/beyond/Documents/python-project/qt/hello.list"

    def read_contents(self, path):
        if os.path.exists(path):
            content = readFile(path)
            if content:
                contents = json.loads(content)
            else:
                contents = []
        else:
            contents = []
        return contents

    @QtCore.Slot()
    def show_list_item(self):
        if self.list.selectedItems():
            item: QtWidgets.QListWidgetItem = self.list.selectedItems()[0]
            self.editText.rander(item.data(Qt.ItemDataRole.UserRole))
        else:
            self.clear_edit_text()

    @QtCore.Slot()
    def delete_item(self):
        if self.list.selectedItems():
            item: QtWidgets.QListWidgetItem = self.list.selectedItems()[0]
            id = item.data(Qt.ItemDataRole.UserRole)["id"]
            contents = self.read_contents(self.get_path())
            index = -1
            for i in range(len(contents)):
                if contents[i]["id"] == id:
                    index = i
                    break
            if index >= 0:
                del contents[index]
                writeFile(self.get_path(), json.dumps(contents))
                select = index
                if index == len(contents):
                    select = len(contents) - 1
                self.refresh_list(select)
        else:
            self.editText.rander({})


    @QtCore.Slot()
    def focus_edit(self):
        self.editText.setFocus()
        cursor = self.editText.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)  # 还可以有别的位置
        self.editText.setTextCursor(cursor)

    @QtCore.Slot()
    def next(self):
        next_row = self.list.currentRow()+1
        if next_row < self.list.count():
            self.list.setCurrentRow(next_row)
            self.focus_edit()

    @QtCore.Slot()
    def pre(self):
        pre_row = self.list.currentRow()-1
        if pre_row >= 0:
            self.list.setCurrentRow(pre_row)
            self.focus_edit()

    @QtCore.Slot()
    def clear_edit_text(self):
        self.editText.rander({})



class MyTextEdit(QtWidgets.QTextEdit):

    ctrlenter = Signal(QtWidgets.QTextEdit)
    ctrln = Signal(QtWidgets.QTextEdit)
    ctrldown = Signal(QtWidgets.QTextEdit)
    ctrlup = Signal(QtWidgets.QTextEdit)
    ctrldelete = Signal(QtWidgets.QTextEdit)
    
    def __init__(self):
        QtWidgets.QTextEdit.__init__(self)
        self.data = {}

    def getData(self):
        return self.data

    def rander(self,data):
        self.data = data
        if "value" in data:
            self.setText(data["value"])
        else:
            self.setText("")
    
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        QtWidgets.QTextEdit.keyPressEvent(self,event)
        if event.key() == Qt.Key_Return and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrlenter.emit(self)
        if event.key() == Qt.Key_N and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrln.emit(self)
        if event.key() == Qt.Key_Down and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrldown.emit(self)
        if event.key() == Qt.Key_Up and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrlup.emit(self)
        if event.key() == Qt.Key_Delete and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrldelete.emit(self)

class MyListWidget(QtWidgets.QListWidget):

    deleted = Signal(QtWidgets.QListWidget)
    entered = Signal(QtWidgets.QListWidget)

    def __init__(self):
        QtWidgets.QListWidget.__init__(self)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        QtWidgets.QListWidget.keyPressEvent(self, event)
        if event.key() == Qt.Key_Delete:
            self.deleted.emit(self)
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            self.entered.emit(self)


class MyListItemWidget(QtWidgets.QWidget):

    deleted = Signal(QtWidgets.QWidget)

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

    def getData(self):
        return self.data

    def rander(self, data):
        self.data = data
        self.label = QtWidgets.QLabel(self.data["value"])
        self.box = QtWidgets.QVBoxLayout()
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.addWidget(self.label)
        self.setLayout(self.box)

            
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = MyWidget()
    widget.resize(800, 600)
    widget.show()
    widget.clear_edit_text()
    sys.exit(app.exec())
