

from sys import maxsize

import sys
import os


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


a = "helo @hello world"


def dispatchOne(base, name, value):
    target_path = base+os.path.sep + name
    with open(target_path, mode="a", encoding="utf-8") as f:
        f.write("\n\n")
        f.write(value)
        f.write("\n")

dispatchOne("/tmp","hello", "myworld")