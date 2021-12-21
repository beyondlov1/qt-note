from cx_Freeze import setup, Executable


options = {
    'build_exe':
        {
            'include_files': ['resource']  # 额外添加的文件 可以是文件夹
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
