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
        self.bootdir = os.path.join(self.rootdir, "boot")

def download(url, filename):
    if os.path.exists(filename):
        return
    assert False
    fp, _ = urlretrieve(url)
    os.chmod(fp, 0o555)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    move(fp, filename)

def extractall(filename, path, create=False):
    if filename.endswith(".zip"):
        if create:
            path = os.path.join(path, filename[:-4])
        os.makedirs(path, exist_ok=True)
        with ZipFile(filename) as fp:
            fp.extractall(path)
    elif any(filename.endswith(f".tar{ext}") for ext in ("", ".gz", ".bz2", "xz")):
        if create:
            base, ext = os.path.splitext(filename)
            if ext != ".tar":
                base, ext = os.path.splitext(base)
            path = os.path.join(path, base)
        with tarfile.open(filename) as fp:
            fp.extractall(path, filter='data')
