# qt-note

### build

```
pip3 install cx_Freeze
sudo apt-get install patchelf
# https://cx-freeze.readthedocs.io/en/latest/installation.html

pip3 install pyside6
# https://doc.qt.io/qtforpython/gettingstarted.html

git clone git@github.com:beyondlov1/Time_NLP.git
cd Time_NLP
python3 setup.py install

cxfreeze qt-note.py --zip-include=${VIRTUAL_ENV}/lib/python3.8/site-packages/TimeConverter-1.1.0-py3.8.egg/resource/ --include-files=${VIRTUAL_ENV}/lib/python3.8/site-packages/TimeConverter-1.1.0-py3.8.egg/resource/
```

### fix
build和直接运行时 Time_NLP这个包的resource文件夹可能读不到, 所以为了让python直接运行时可以启动,这里把Time_NLP的resource直接拷贝到了这里