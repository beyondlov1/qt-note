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

cxfreeze qt-note.py --zip-include=${VIRTUAL_PYTHON_PATH}/lib/python3.8/site-packages/TimeConverter-1.1.0-py3.8.egg/resource/ --include-files=${VIRTUAL_PYTHON_PATH}/lib/python3.8/site-packages/TimeConverter-1.1.0-py3.8.egg/resource/
```