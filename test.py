

import json
import pickle
from posixpath import dirname
from sys import maxsize

import sys
import os

import zlib
# import requests

from Cryptodome.Cipher import AES

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


def dispatch(value):
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
        print(tag)



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




 
# zlib.compress 用来压缩字符串的bytes类型
def str_zlib():
    bytes_message =  breadFile("/home/beyond/github/enote-data/note.list.ze")
    compressed = zlib.compress(bytes_message, zlib.Z_BEST_COMPRESSION)
    decompressed = zlib.decompress(compressed)      # str、repr的区别
    print("original string:", len(bytes_message))
    print("original bytes:",  len(bytes_message))
    print("compressed:",  len(compressed))
    print("decompressed:",  len(decompressed))
 
# zlib.compressobj 用来压缩数据流，用于文件传输
def file_compress(beginFile, zlibFile, level):
    infile = open(beginFile, "rb")
    zfile = open(zlibFile, "wb")
    compressobj = zlib.compressobj(level)   # 压缩对象
    data = infile.read(1024)                # 1024为读取的size参数
    while data:
        zfile.write(compressobj.compress(data))     # 写入压缩数据
        data = infile.read(1024)        # 继续读取文件中的下一个size的内容
    zfile.write(compressobj.flush())    # compressobj.flush()包含剩余压缩输出的字节对象，将剩余的字节内容写入到目标文件中
 
def file_decompress(zlibFile, endFile):
    zlibFile = open(zlibFile, "rb")
    endFile = open(endFile, "wb")
    decompressobj = zlib.decompressobj()
    data = zlibFile.read(1024)
    while data:
        endFile.write(decompressobj.decompress(data))
        data = zlibFile.read(1024)
    endFile.write(decompressobj.flush())

AES_BLOCK_SIZE = AES.block_size     # AES 加密数据块大小, 只能是16
AES_KEY_SIZE = 16

# 待加密的密钥补齐到对应的位数
def padKey(key):
    if len(key) > AES_KEY_SIZE:                 # 如果密钥长度超过 AES_KEY_SIZE
        return key[:AES_KEY_SIZE]               # 截取前面部分作为密钥并返回
    while len(key) % AES_KEY_SIZE != 0:         # 不到 AES_KEY_SIZE 长度则补齐
        key += ' '.encode()                     # 补齐的字符可用任意字符代替
    return key                                  # 返回补齐后的密钥

# AES 解密
def decrypt(key, encryptData):
    # 新建一个 AES 算法实例，使用 ECB（电子密码本）模式
    myCipher = AES.new(padKey(key), AES.MODE_ECB)
    bytes = myCipher.decrypt(encryptData)       # 调用解密方法，得到解密后的数据
    return bytes                                # 返回解密数据


# print("ssssssssssss\n".strip())
list1 = [{"a":"bb"}]
d = {"a":"22"}
print(list1.index(d))

# 测试字符串的压缩与解压
# str_zlib()

# # # 测试数据流压缩
# beginFile = "./note.list"
# zlibFile = "./notez.list"
# level = 1
# file_compress(beginFile, zlibFile, level)

# # 测试数据流解压
# zlibFile = "./notez.list"
# endFile = "./note.list"
# file_decompress(zlibFile, endFile)


# a = pickle.dumps(json.loads(readFile("./note.list")))
# bwriteFile("./note.list.p", a)
# beginFile = "./note.list.p"
# zlibFile = "./notezp.list"
# level = 9
# file_compress(beginFile, zlibFile, level)
