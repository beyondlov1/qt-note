from logging import Formatter, handlers
from math import fabs
from posixpath import dirname
import sys
import zlib

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QSize, Qt, Signal
import os
import json
import uuid

from TimeNormalizer import TimeNormalizer
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.util import timedelta_seconds
import arrow  # 引入包
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime, timedelta
from Cryptodome.Cipher import AES
import operator                     # 导入 operator，用于比较原始数据与加解密后的数据
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import time



logging.basicConfig(format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s',
                    level=logging.INFO)
logger = logging.getLogger("qt-note")
handler = logging.FileHandler(filename=os.path.join(dirname(sys.argv[0]), "note.log"), mode="a")
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s'))
logger.addHandler(handler)

tn = TimeNormalizer()

def readFile(path):
    with open(path, encoding="utf-8") as f:
        contents = f.read()
        return contents


def breadFile(path):
    with open(path, mode="rb") as f:
        contents = f.read()
        return contents


def writeFile(path, content):
    with open(path, "w") as f:
        f.write(content)


def bwriteFile(path, content):
    with open(path, "wb") as f:
        f.write(content)

def get_config():
    configpath = os.path.join(dirname(sys.argv[0]), "config.json")
    if os.path.exists(configpath):
        configjson = readFile(configpath)
        configobj = json.loads(configjson)
        return configobj
    else:
        return {}

def get_or_none(obj,key):
    if key in obj:
        return obj[key]
    else:
        return None

def get_dispatch_base():
    return get_or_none(get_config(), "dispatch_dir")

def get_path():
    path = get_or_none(get_config(), "note_path")
    if path:
        return path
    return os.path.join(dirname(sys.argv[0]), "note.list")

def get_ibuf_path():
    return get_path()+".ibuf"

def get_dellog_path():
    path = get_or_none(get_config(), "delnote_path")
    if path:
        return path
    return os.path.join(dirname(sys.argv[0]), "note.dellog")


def get_git_dir():
    return get_or_none(get_config(), "git_dir")


def get_key():
    key = get_or_none(get_config(), "key")
    if key:
        return key.encode()
    else:
        return None

def get_pid_path():
    return os.path.join(dirname(sys.argv[0]), "qt-note.pid")


def getvaliddata():
    path = get_path()
    ctuple = read_all()
    deleteditems = read_dellog()
    removeallbyidandvalue(ctuple[0],deleteditems)
    removeallbyidandvalue(ctuple[1],deleteditems)
    removeallbyidandvalue(ctuple[2],deleteditems)
    return ctuple


def readlist(path):
    if os.path.exists(path):
        content = readFile(path)
        if content:
            contents = json.loads(content)
        else:
            contents = []
    else:
        contents = []
    
    return contents

def read_ibuf():
    return readlist(get_ibuf_path())

def read_contents():
    return readlist(get_path())

def adddellogitem(item):
    dellog = read_dellog()
    removebyidandvalue(dellog, item)
    item["mtime"] = arrow.now().timestamp()
    dellog.append(item)
    writeFile(get_dellog_path(), json.dumps(dellog))

def read_dellog():
    return readlist(get_dellog_path())

def read_ibuf_shadow():
    return readlist(get_ibuf_shadow_path())

def deleteibufshadow():
    os.path.exists(get_ibuf_shadow_path())

def writeibufshadow(ibufshadow):
    writeitems(get_ibuf_shadow_path(), ibufshadow )

def get_ibuf_shadow_path():
    return get_ibuf_path()+".shadow"

def sort_ctime(x):
    return x["ctime"]

def read_all():
    contents = readlist(get_path())
    contents.sort(key=sort_ctime)
    ibuf = read_ibuf()
    ibuf.sort(key=sort_ctime)
    all = []
    add_all(all, contents)
    add_all(all, ibuf)
    all.sort(key=sort_ctime)
    return (all, ibuf, contents)

def add_all(list, toaddlist):
    for toadd in toaddlist:
        list.append(toadd)


def parse_contents(contentstr):
        if contentstr:
            contents = json.loads(contentstr)
        else:
            contents = []
        return contents

def check_and_notify():
    path = get_path()
    ctuple = read_all()
    all = ctuple[0]
    ibuf = ctuple[1]
    contents = ctuple[2]
    ibufchanged = False
    contentschanged = False
    for content in all:
        obj = to_obj(content["value"])
        if "due" in obj and obj["due"].timestamp() < arrow.now().timestamp() and not obj["reminded"]:
            emit_notify_event(obj["value"])
            obj["reminded"] = True
            content["value"] = to_str(obj)
            ibufchanged = content in ibuf
            contentschanged = content in contents
    if contentschanged:
        writeFile(path, json.dumps(ctuple[2]))
    if ibufchanged:
        writeFile(get_ibuf_path(), json.dumps(ctuple[1]))

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



def saferemove(list, item):
    if item in list:
        list.remove(item)


def getitembyid(notelist, id):
    i = 0
    for noteitem in notelist:
        if noteitem["id"] == id:
            return (i,noteitem)
        i = i+1
    return None

def getallitembyid(notelist, id):
    r = []
    i = 0
    for noteitem in notelist:
        if noteitem["id"] == id:
            r.append((i,noteitem))
        i = i+1
    return r

def getitembyidandvalue(notelist, item):
    i = 0
    for noteitem in notelist:
        if noteitem["id"] == item["id"] and noteitem["value"] == item["value"]:
            return (i,noteitem)
        i = i+1
    return None
    
def replaceallbyid(contents, targets):
    replacemapping = {}
    i = 0
    for content in contents:
        found = getitembyid(targets, content["id"])
        if found:
            replacemapping[str(i)] = found[1]
        i=i+1
    for item in replacemapping.items():
        contents[int(item[0])] = item[1]


def removeallbyid(contents:list, targets):
    for target in targets:
        found = getitembyid(contents, target["id"])
        if found:
            contents.remove(found[1])

def removeallbyidandvalue(contents:list, targets):
    for target in targets:
        found = getitembyid(contents, target["id"])
        if found and found[1]['value'] == target['value']:
            contents.remove(found[1])

def removebyidandvalue(contents:list, target):
    found = getitembyidandvalue(contents, target)
    if found:
        contents.remove(found[1])

def removebyid(targets:list, id):
    i = 0
    for target in targets:
        if target["id"] == id:
            break
        i=i+1
    del targets[i]
    return i

def removebyindex(targets:list, index):
    del targets[index]


def writeitems(path,items):
    writeFile(path, json.dumps(items))


def writecontents(items):
    writeitems(get_path(), items)

def writeibuf(items):
    writeitems(get_ibuf_path(), items)

def writedellog(items):
    writeitems(get_dellog_path(), items)

def trylock(path):
    r = {}
    synclckpath = path + ".lck"
    try:
        os.symlink(path, synclckpath)
        r["state"] = True
    except FileExistsError:
        ctime = os.path.getctime(synclckpath)
        if arrow.now().timestamp() - ctime > 60:
            os.remove(synclckpath)
            os.symlink(path, synclckpath)
            r["state"] = True
        else:
            r["state"] = False
            r["lockpath"] = synclckpath
    return r

def unlock(path):
    synclckpath = path + ".lck"
    os.remove(synclckpath)

def save(id:str, value:str, mtime = arrow.now().timestamp()):
    while(not trylock(get_ibuf_path())["state"]):
        time.sleep(0.1)
    
    if not "|" in value:
        parsed_obj = json.loads(tn.parse(value, timeBase = arrow.now()))
        print(parsed_obj)
        if "type" in parsed_obj and parsed_obj["type"] == "timestamp":
            value = value+"|"+parsed_obj["timestamp"]
        if "type" in parsed_obj and parsed_obj["type"] == "timedelta":
            delta = parsed_obj["timedelta"]
            arw = arrow.now().shift(years=delta["year"], months=delta["month"], days=delta["day"],
                                    hours=delta["hour"], minutes=delta["minute"], seconds=delta["second"])
            value = value+"|"+arw.format("YYYY-MM-DD HH:mm:ss")
    
    result = {}
    ctuple = read_all()
    ibuf = ctuple[1]
    if id:
        foundinibuf = getitembyid(ibuf, id)
        if foundinibuf:
            foundinibuf[1]["value"] = value
            foundinibuf[1]["mtime"] = mtime
            result = foundinibuf[1]
        else:
            newitem = {"id": id, "value": value, "ctime":mtime, "mtime": mtime}
            ibuf.append(newitem)
            result = newitem 
    else:
        newitem = {"id": str(uuid.uuid4()), "value": value, "ctime":mtime, "mtime": mtime}
        ibuf.append(newitem)
        result = newitem
    writeibuf(ibuf)
    unlock(get_ibuf_path())
    return result

def delete(id):
    r = None
    ctuple = read_all()
    all = ctuple[0]
    found = getitembyid(all, id)
    if found and not getitembyidandvalue(read_dellog(),found[1]):
        adddellogitem(found[1])
        r = found[1]
    return r
    

def dispatch():
    git_sync()
    ctuple = read_all()
    contents = ctuple[2]
    ibuf = ctuple[1]
    changed = False
    for content in ctuple[0]:
        if "delete_stage" in content:
            if content["delete_stage"] == 1:
                dispatchOne(get_dispatch_base(),
                            content["tag"], content["value_without_tag"])
                content["delete_stage"] = 2
                delete(content["id"])
                changed = True
            if content["delete_stage"] == 2:
                delete(content["id"])
                changed = True
    for content in ctuple[0]:
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
                delete(content["id"])
                changed = True
    if changed:
        logger.info("dispatch save start")
        widget.ct.refresh()
        git_sync()
        logger.info("dispatch save end")


def dispatchOne(base, name, value):
    if not name.endswith(".md"):
        name = name + ".md"
    target_path = os.path.join(base, name)
    if not os.path.exists(dirname(target_path)):
        os.makedirs(dirname(target_path))
    elif os.path.exists(target_path):
        # 防止重复添加
        content = readFile(target_path)
        if content.strip().endswith(value):
            return
    with open(target_path, mode="a", encoding="utf-8") as f:
        f.write("\n\n")
        f.write(value)
        f.write("\n")


def list_name_items(dirpath):
    file_items = []
    names = os.listdir(dirpath)
    for filename in names:
        path = os.path.join(dirpath, filename)
        if os.path.isfile(path):
            file_items.append({"name": filename, "path": path})
        if os.path.isdir(path):
            continue
    return file_items


AES_BLOCK_SIZE = AES.block_size     # AES 加密数据块大小, 只能是16
AES_KEY_SIZE = 16

# 待加密文本补齐到 block size 的整数倍
def padContent(bytes):
    while len(bytes) % AES_BLOCK_SIZE != 0:     # 循环直到补齐 AES_BLOCK_SIZE 的倍数
        bytes += ' '.encode()                   # 通过补空格（不影响源文件的可读）来补齐
    return bytes                                # 返回补齐后的字节列表

# 待加密的密钥补齐到对应的位数
def padKey(key):
    if len(key) > AES_KEY_SIZE:                 # 如果密钥长度超过 AES_KEY_SIZE
        return key[:AES_KEY_SIZE]               # 截取前面部分作为密钥并返回
    while len(key) % AES_KEY_SIZE != 0:         # 不到 AES_KEY_SIZE 长度则补齐
        key += ' '.encode()                     # 补齐的字符可用任意字符代替
    return key                                  # 返回补齐后的密钥

# AES 加密
def encrypt(key, bytes):
    # 新建一个 AES 算法实例，使用 ECB（电子密码本）模式
    myCipher = AES.new(padKey(key), AES.MODE_ECB)
    encryptData = myCipher.encrypt(padContent(bytes))       # 调用加密方法，得到加密后的数据
    return encryptData                          # 返回加密数据

# AES 解密
def decrypt(key, encryptData):
    # 新建一个 AES 算法实例，使用 ECB（电子密码本）模式
    myCipher = AES.new(padKey(key), AES.MODE_ECB)
    bytes = myCipher.decrypt(encryptData)       # 调用解密方法，得到解密后的数据
    return bytes                                # 返回解密数据


def compress(bytes_message):
    compressed = zlib.compress(bytes_message, zlib.Z_BEST_COMPRESSION)
    return compressed

def decompress(compressed):
    return zlib.decompress(compressed)

def eqvalue(item1,item2):
    return item1["value"] == item2["value"]

def getnewer(item1,item2):
    if item1["mtime"] > item2["mtime"]:
        return item1
    elif item1["mtime"] < item2["mtime"]:
        return item2
    else:
        return None
    


def git_sync():
    # 只同步 note.list 文件
    path = get_path()
    r = trylock(path)
    if not r["state"]:
        logger.info("git sync locked, abort.(rm %s)", r["lockpath"])
        return
    try: 
        ctuple = read_all()
        contents = ctuple[2]
        oldlenc = len(contents)

        # 防止文件中还含有dellog
        dellogitems = read_dellog()
        removeallbyidandvalue(contents, dellogitems)
        fixed = False
        if len(contents) != oldlenc:
            writecontents(contents)
            fixed = True
        if fixed:
            ctuple = read_all()
            contents = ctuple[2]

        ibufshadow = read_ibuf_shadow()

        print("local:"+ json.dumps(contents))

        oldcontents = ctuple[0][:]
        os.system("cd "+get_git_dir()+"&& git pull")
        enotepath = os.path.join(get_git_dir(), "note.list.ze")
        enotebytes = b''
        newcontents = []
        if os.path.exists(enotepath):
            enotebytes = breadFile(enotepath)
            econtents = parse_contents(decompress(decrypt(get_key(), enotebytes)).decode("utf-8"))
            print("remote:"+json.dumps(econtents))
            remoteadded = []
            remoteremoved = []
            remotechanged = []
            for econtent in econtents:
                foundinlocal = getitembyid(contents, econtent["id"])
                if foundinlocal:
                    # 本地找到了, 看看是否修改过
                    if not eqvalue(foundinlocal[1], econtent):
                        newer = getnewer(foundinlocal[1], econtent)
                        if newer and  newer == econtent:
                            remotechanged.append(newer)
                    else:
                        # no changed
                        pass
                else:
                    # 在本地没找到, 是否本地删除
                    dellog = read_dellog()
                    dellogitem = getitembyidandvalue(dellog, econtent)
                    if not dellogitem:
                        # 本地没删除, remote添加的, 或者远程把值改了
                        remoteadded.append(econtent)
                    else:
                        # 本地删除了, remote没删除, 值相同, 需要判断删除时间和remote修改时间大小
                        if dellogitem[1]["mtime"] >= econtent["mtime"]:
                            # 后删除的
                            remoteremoved.append(econtent)
                        else:
                            # 远程又将其恢复了
                            remoteadded.append(econtent)
            for content in contents:
                foundinremote = getitembyid(econtents, content["id"])
                if not foundinremote:
                    if not getitembyid(ibufshadow, content["id"]):
                        remoteremoved.append(content)
            add_all(contents, remoteadded)
            replaceallbyid(contents, remotechanged)
            removeallbyid(contents, remoteremoved)
            
            for content in contents:
                newcontents.append(content)
            newcontents.sort(key=sort_ctime)
        else:
            newcontents = contents
    
        newcontentsstr = json.dumps(newcontents)
        writeFile(get_path(),newcontentsstr)
        deleteibufshadow()
        newenotebytes = encrypt(get_key(),compress(breadFile(get_path())))
        needpush = not operator.eq(enotebytes, newenotebytes)
        if needpush:
            bwriteFile(enotepath, newenotebytes)
            print("need push")
            os.system("cd "+get_git_dir()+"&& git add . && git commit -m auto && git push")
        if not operator.eq(newcontents, oldcontents):
            widget.ct.refresh()
    finally:
        unlock(path)


    # 将 ibuf 合并到 contents
    ibufpath = get_ibuf_path()
    r = trylock(get_ibuf_path())
    if not r["state"]:
        logger.info("git sync locked, abort.(rm %s)", r["lockpath"])
        return
    try:
        ibuf = read_ibuf()
        dellogitems = read_dellog()
        removeallbyidandvalue(ibuf, dellogitems)
        fixed = False
        if len(ibuf) != oldlenc:
            writeibuf(ibuf)
            fixed = True
        if fixed:
            ibuf = read_ibuf()

        writeibufshadow(ibuf)

        refresh = False
        contents = read_contents()
        for item in ibuf:
            found = getitembyid(contents, item["id"])
            if found:
                if found[1]["mtime"] < item["mtime"]:
                    found[1] = item
                    refresh = True
            else:
                contents.append(item)
                refresh = True
        writecontents(contents)
        if os.path.exists(ibufpath):
            os.remove(ibufpath)
        if refresh:
            widget.ct.refresh()
    finally:
        unlock(ibufpath)



class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        names = []
        for item in list_name_items(get_dispatch_base()):
            names.append(item['name'])
        
        self.lineEdit = QtWidgets.QLineEdit()
        cp = QtWidgets.QCompleter(names)
        cp.setCompletionMode(QtWidgets.QCompleter.CompletionMode.InlineCompletion)
        self.lineEdit.setCompleter(cp)
        self.lineEdit.returnPressed.connect(self.insert_filename)
        
        
        self.editText = MyTextEdit()
        self.editText.ctrlenter.connect(self.write_to_list)
        self.editText.ctrln.connect(self.clear_edit_text)
        self.editText.ctrldown.connect(self.next)
        self.editText.ctrlj.connect(self.next)
        self.editText.ctrlup.connect(self.pre)
        self.editText.ctrlk.connect(self.pre)
        self.editText.ctrldelete.connect(self.delete_item)
        self.editText.ctrle.connect(self.show_list_item)
        self.editText.at.connect(self.focus_line_edit)
        self.list = MyListWidget()
        self.list.deleted.connect(self.delete_item)
        self.list.entered.connect(self.focus_edit)
        self.list.itemSelectionChanged.connect(self.show_list_item)
        self.refresh_list()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.editText)
        self.layout.addWidget(self.lineEdit)
        self.layout.addWidget(self.list)

        self.ct = Notifier()
        self.ct.notified.connect(self.notify)
        self.ct.refreshed.connect(self.refresh_list)

    @QtCore.Slot()
    def focus_line_edit(self):
        self.lineEdit.setFocus()

    @QtCore.Slot()
    def insert_filename(self):
        text = self.lineEdit.text()
        self.editText.insertPlainText(text)
        self.lineEdit.clear()
        self.editText.setFocus()
        self.write_to_list()

    @QtCore.Slot(str)
    def notify(self, msg):
        self.dialog = CustomDialog(msg, parent=self)
        self.dialog.show()
        self.refresh_list()

    def init_list(self,qlist:QtWidgets.QListWidget, data):
        for datum in data:
            item = QtWidgets.QListWidgetItem(qlist)
            item.setData(Qt.ItemDataRole.UserRole,datum)
            widget = MyListItemWidget()
            widget.rander(datum)
            item.setSizeHint(widget.sizeHint())
            qlist.setItemWidget(item, widget)
            qlist.addItem(item)
            
    @QtCore.Slot()
    def write_to_list(self):
        value = self.editText.toPlainText()
        id = None
        if self.editText.getData() and self.editText.getData()["id"]:
            id = self.editText.getData()["id"]
        result = save(id,value)
        i = 0
        for item in getvaliddata()[0]:
            if item["id"] == result["id"]:
                break
            i=i+1
        self.refresh_list(i)
        self.clear_edit_text()

    def refresh_list(self, select=0):
        self.list.clear()
        tuple = getvaliddata()
        distinctlist = []
        itemmap = {}
        for item in tuple[0]:
            if item["id"] not in itemmap:
                distinctlist.append(item)
            else:
                distinctlist.remove(itemmap[item["id"]])
                distinctlist.append(item)
            itemmap[item["id"]] = item       
            
        self.init_list(self.list, distinctlist)
        if distinctlist:
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
            dr = delete(id)
            if dr:
                select = self.list.currentIndex().row() -1
                if select < 0:
                    select  = 0
                vall = getvaliddata()[0]
                if select >= len(vall):
                    select = len(vall) - 1
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
    ctrlj = Signal(QtWidgets.QTextEdit)
    ctrlup = Signal(QtWidgets.QTextEdit)
    ctrlk = Signal(QtWidgets.QTextEdit)
    ctrldelete = Signal(QtWidgets.QTextEdit)
    ctrle = Signal(QtWidgets.QTextEdit)
    at = Signal(QtWidgets.QTextEdit)
    
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
        if event.key() == Qt.Key_At:
            self.at.emit(self)
        if event.key() == Qt.Key_Return and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrlenter.emit(self)
        if event.key() == Qt.Key_N and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrln.emit(self)
        if event.key() == Qt.Key_Down and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrldown.emit(self)
        if event.key() == Qt.Key_J and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrlj.emit(self)
        if event.key() == Qt.Key_Up and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrlup.emit(self)
        if event.key() == Qt.Key_K and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrlk.emit(self)
        if event.key() == Qt.Key_Delete and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrldelete.emit(self)
        if event.key() == Qt.Key_E and event.keyCombination().keyboardModifiers() == Qt.ControlModifier:
            self.ctrle.emit(self)
    
    def focusInEvent(self, QFocusEvent):
        self.setStyleSheet(
            "border-width:1;border-color:red;border-style:outset")

    def focusOutEvent(self, QFocusEvent):
        self.setStyleSheet(
            "border-width:1;border-color:grey;border-style:outset")

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



class Resquest(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/save":
            s=str(self.rfile.read(int(self.headers['content-length'])),'UTF-8')#先解码     
            print(s)
            item = json.loads(s)
            # print(urllib.parse.parse_qs(urllib.parse.unquote(s)))#解释参数
            if "id" in item and "body" in item:
                save(item["id"], item["body"], item["mtime"])
                widget.ct.refresh()
            elif "body" in item:
                save(None, item["body"], item["mtime"])
                widget.ct.refresh()
            else:
                pass
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"message":"ok"}).encode("utf-8"))
        if self.path == "/list":
            s=str(self.rfile.read(int(self.headers['content-length'])),'UTF-8')#先解码     
            print(s)
            params = json.loads(s)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(getvaliddata()[0]).encode("utf-8"))
        if self.path == "/one":
            s=str(self.rfile.read(int(self.headers['content-length'])),'UTF-8')#先解码     
            print(s)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            params = json.loads(s)
            if "id" not in params:
                self.wfile.write(json.dumps({}).encode("utf-8"))
            else:
                found = getitembyid(getvaliddata()[0],params["id"])
                if found:
                    self.wfile.write(json.dumps(found[1]).encode("utf-8"))
                else:
                    self.wfile.write(json.dumps({"id":params["id"], "value":"", "ctime":arrow.now().timestamp(), "mtime":arrow.now().timestamp()}).encode("utf-8"))
            

server = None
def startserver():
    server.serve_forever()


if __name__ == "__main__":
    try:
        if not os.path.exists(get_pid_path()):
            writeFile(get_pid_path(), str(os.getpid()))
        else:
            print("another process is running.")
            exit(1)
    except:
        os.remove(get_pid_path())
        exit(1)

    interval_sec = 60*60

    app = QtWidgets.QApplication([])
    widget = MyWidget()
    widget.resize(800, 600)
    widget.move(widget.width() * -2, 0)
    desktop = QtWidgets.QApplication.primaryScreen().availableVirtualGeometry()
    x = (desktop.width() - widget.frameSize().width())
    y = (desktop.height() - widget.frameSize().height()) 
    widget.move(x,y)
    widget.show()
    widget.clear_edit_text()

    bs = BackgroundScheduler()
    # 这里能直接add_job(job,"interval", seconds=30),cx_freeze打包会报错 https://www.cnblogs.com/ljbguanli/p/7218026.html
    trigger = IntervalTrigger(seconds=30)
    bs.add_job(check_and_notify, trigger)
    bs.start()

    dispatch_bs = BackgroundScheduler()
    if get_dispatch_base():    
        dispatch_trigger = IntervalTrigger(
            seconds=interval_sec, start_date=datetime.now()+timedelta(seconds=30))
        dispatch_bs.add_job(dispatch, dispatch_trigger)
        dispatch_bs.start()
    
    git_bs = BackgroundScheduler()
    if get_git_dir():
        git_trigger = IntervalTrigger(
            seconds=30, start_date=datetime.now()+timedelta(seconds=5))
        git_bs.add_job(git_sync, git_trigger)
        git_bs.start()

    port = 22901
    server = HTTPServer(('localhost', port), Resquest)
    print("Starting server, listen at: %s" % port)
    serverthread = Thread(target=startserver)
    serverthread.start()
    exitcode = app.exec()
    if server: server.shutdown()
    if bs: bs.shutdown()
    if dispatch_bs: dispatch_bs.shutdown()
    if git_bs: git_bs.shutdown()
    serverthread.join()
    os.remove(get_pid_path())
    sys.exit(exitcode)
