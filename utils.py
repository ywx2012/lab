import os
from urllib.request import urlretrieve
from shutil import move
import tarfile
from zipfile import ZipFile

class Config:

    def __init__(self, rootdir="workspace"):
        self.rootdir = os.path.abspath(rootdir)
        self.srcdir = os.path.join(self.rootdir, "src")
        self.usrdir = os.path.join(self.rootdir, "usr")

def download(url, filename):
    if os.path.exists(filename):
        return
    assert False
    fp, _ = urlretrieve(url)
    os.chmod(fp, 0o555)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    move(fp, filename)

def extractall(filename, path):
    os.makedirs(path, exist_ok=True)
    if filename.endswith(".zip"):
        with ZipFile(filename) as fp:
            fp.extractall(path)
    else:
        with tarfile.open(filename) as fp:
            fp.extractall(path, filter='data')
