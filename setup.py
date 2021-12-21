from cx_Freeze import setup, Executable


options = {
    'build_exe':
        {
            'include_files': ['/usr/local/lib/python3.8/dist-packages/TimeConverter-1.1.0-py3.8.egg/resource/']  # 额外添加的文件 可以是文件夹
        }
}

setup(
    name="qt-note",
    version="1.0",
    description="note",
    author="beyond",
    options = options,
    executables=[Executable("qt-note.py")]
)
