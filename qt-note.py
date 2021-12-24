from posixpath import dirname
import sys
import random
import threading
from typing import Deque
from unicodedata import name 
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QSize, Qt, Signal
import os
import json
import uuid

from TimeNormalizer import TimeNormalizer
from apscheduler.schedulers.blocking import BlockingScheduler
import arrow  # 引入包
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger


tn = TimeNormalizer()


def readFile(path):
    with open(path, encoding="utf-8") as f:
        contents = f.read()
        return contents


def writeFile(path, content):
    with open(path, "w") as f:
        f.write(content)


def get_path():
    return os.path.join(dirname(sys.argv[0]), "note.list")


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.editText = MyTextEdit()
        self.editText.ctrlenter.connect(self.write_to_list)
        self.editText.ctrln.connect(self.clear_edit_text)
        self.editText.ctrldown.connect(self.next)
        self.editText.ctrlup.connect(self.pre)
        self.editText.ctrldelete.connect(self.delete_item)
        self.editText.ctrle.connect(self.show_list_item)
        self.list = MyListWidget()
        self.list.deleted.connect(self.delete_item)
        self.list.entered.connect(self.focus_edit)
        self.list.itemSelectionChanged.connect(self.show_list_item)
        self.refresh_list()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.editText)
        self.layout.addWidget(self.list)

        self.ct = Notifier()
        self.ct.notified.connect(self.notify)
        self.ct.refreshed.connect(self.refresh_list)

    @QtCore.Slot(str)
    def notify(self, msg):
        self.dialog = CustomDialog(msg, parent=self)
        self.dialog.show()
        self.refresh_list()

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
        if not "|" in value:
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
        path = get_path()
        contents = read_contents(path)
        if self.editText.getData() and self.editText.getData()["id"]:
            id = self.editText.getData()["id"]
            for content in contents:
                if content["id"] == id:
                    content["value"] = value
                    break
                next_select += 1
        else:
            contents.append(    
                {"id": str(uuid.uuid4()), "value": value, "ctime":arrow.now().timestamp()})
            next_select = len(contents) - 1
        writeFile(path, json.dumps(contents))
        self.refresh_list(next_select)
        self.clear_edit_text()

    def refresh_list(self, select=0):
        self.list.clear()
        path = get_path()
        contents = read_contents(path)
        self.init_list(self.list, contents)
        if contents:
            self.list.setCurrentRow(select)
        else:
            self.focus_edit()

    @QtCore.Slot()
    def show_list_item(self):
        if self.list.selectedItems():
            item: QtWidgets.QListWidgetItem = self.list.selectedItems()[0]
            self.editText.rander(item.data(Qt.ItemDataRole.UserRole))
            cursor = self.editText.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)  # 还可以有别的位置
            self.editText.setTextCursor(cursor)
        else:
            self.clear_edit_text()

    @QtCore.Slot()
    def delete_item(self):
        if self.list.selectedItems():
            item: QtWidgets.QListWidgetItem = self.list.selectedItems()[0]
            id = item.data(Qt.ItemDataRole.UserRole)["id"]
            contents = read_contents(get_path())
            index = -1
            for i in range(len(contents)):
                if contents[i]["id"] == id:
                    index = i
                    break
            if index >= 0:
                del contents[index]
                writeFile(get_path(), json.dumps(contents))
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
    ctrle = Signal(QtWidgets.QTextEdit)
    
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
        if event.key() == Qt.Key_E and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrle.emit(self)
            

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
        content = self.data["value"]
        end = len(content)
        line_end_index = content.find("\n", 20)
        if line_end_index > 0:
            end = line_end_index + 1
        self.label = QtWidgets.QLabel(content[:end].strip())
        self.box = QtWidgets.QVBoxLayout()
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.addWidget(self.label)
        self.setLayout(self.box)


def read_contents(path):
    if os.path.exists(path):
        content = readFile(path)
        if content:
            contents = json.loads(content)
        else:
            contents = []
    else:
        contents = []
    return contents

def check_and_notify(path:str=get_path()):
    contents = read_contents(path)
    for content in contents:
        obj = to_obj(content["value"])
        if "due" in obj and obj["due"].timestamp() < arrow.now().timestamp() and not obj["reminded"]:
            emit_notify_event(obj["value"])
            obj["reminded"] = True
            content["value"] = to_str(obj)
    writeFile(path, json.dumps(contents))

def emit_notify_event(msg:str):
    widget.ct.send(msg)

def to_obj(value:str):
    result = {}
    split = value.split("|")
    result["value"] = split[0]
    if len(split) == 2:
        result["due"] = arrow.get(
            split[1], "YYYY-MM-DD HH:mm:ss", tzinfo="local")
        result["reminded"] = False
    if len(split) == 3:
        result["due"] = arrow.get(
            split[1], "YYYY-MM-DD HH:mm:ss", tzinfo="local")
        result["reminded"] = bool(split[2])
    return result

def to_str(obj):
    return obj["value"]+"|"+obj["due"].format("YYYY-MM-DD HH:mm:ss")+"|"+str(obj["reminded"]).lower()


class CustomDialog(QtWidgets.QDialog):
    def __init__(self, msg,parent=None):
        super().__init__(parent)

        self.setWindowTitle("HELLO!")

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        message = QtWidgets.QLabel(msg)
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class Notifier(QtCore.QObject):

    notified = Signal(str)
    refreshed = Signal()

    def __init__(self) -> None:
        QtCore.QObject.__init__(self)

    def send(self, msg):
        self.notified.emit(msg)
    
    def refresh(self):
        self.refreshed.emit()


def get_dispatch_base():
    configpath = os.path.join(dirname(sys.argv[0]), "config.json")
    if os.path.exists(configpath):
        configjson = readFile(configpath)
        configobj = json.loads(configjson)
        if "dispatch_dir" in configobj:
            return configobj["dispatch_dir"]
    return None


def dispatch():
    contents = read_contents(get_path())
    changed = False
    for content in contents[:]:
        if "delete_stage" in content:
            if content["delete_stage"] == 1:
                dispatchOne(get_dispatch_base(),
                            content["tag"], content["value_without_tag"])
                content["delete_stage"] = 2
                contents.remove(content)
                changed = True
            if content["delete_stage"] == 2:
                contents.remove(content)
                changed = True
    for content in contents[:]:
        value = content["value"]
        if "@" in value:
            tag_start_index = value.index("@")
            space_index = value.find(" ", tag_start_index)
            newline_index = value.find("\n", tag_start_index)
            if newline_index == -1:
                newline_index = sys.maxsize
            if space_index == -1:
                space_index = sys.maxsize
            tag_end_index = min(space_index, newline_index)
            tag = value[tag_start_index+1:tag_end_index]
            if tag and ("due" not in content or not content["due"]):
                if arrow.now().timestamp() - content["ctime"] < interval_sec:
                    continue
                content["delete_stage"] = 1
                content["tag"] = tag
                content["value_without_tag"] = value[:tag_start_index]
                dispatchOne(get_dispatch_base(), tag, value[:tag_start_index])
                content["delete_stage"] = 2
                contents.remove(content)
                changed = True
    if changed:
        writeFile(get_path(), json.dumps(contents))
        widget.ct.refresh()


def dispatchOne(base, name, value):
    if not name.endswith(".md"):
        name = name + ".md"
    target_path = os.path.join(base, name)
    if not os.path.exists(dirname(target_path)):
        os.makedirs(dirname(target_path))
    with open(target_path, mode="a", encoding="utf-8") as f:
        f.write("\n\n")
        f.write(value)
        f.write("\n")


def list_names(dirpath):
    file_items = []
    names = os.listdir(dirpath)
    for filename in names:
        path = os.path.join(dirpath, filename)
        if os.path.isfile(path):
            file_items.append({"name": filename, "path": path})
        if os.path.isdir(path):
            continue
    return file_items


if __name__ == "__main__":
    interval_sec = 60

    app = QtWidgets.QApplication([])
    widget = MyWidget()
    widget.resize(800, 600)
    widget.show()
    widget.clear_edit_text()

    bs = BackgroundScheduler()
    # 这里能直接add_job(job,"interval", seconds=30),cx_freeze打包会报错 https://www.cnblogs.com/ljbguanli/p/7218026.html
    trigger = IntervalTrigger(seconds=30)
    bs.add_job(check_and_notify, trigger)
    bs.start()

    if get_dispatch_base():    
        dispatch_bs = BackgroundScheduler()
        dispatch_trigger = IntervalTrigger(seconds=interval_sec)
        dispatch_bs.add_job(dispatch, dispatch_trigger)
        dispatch_bs.start()

    sys.exit(app.exec())
