#!/usr/bin/env python3

import os
from shutil import copy
from utils import Config, download, extractall
from subprocess import check_output, check_call

def install(self, dstdir, dldir=None):
    dirname = os.path.join(dstdir, self.name)
    filename = os.path.join(dldir or dstdir, f"{self.name}{self.ext}")

    if not os.path.exists(dirname):
        download(self.url, filename)
        extractall(filename, dstdir)

class Install:

    def install(self, cfg):
        install(self, cfg.srcdir)

class Zig(Install):
    version = "0.13.0"
    name = f"zig-linux-x86_64-{version}"
    ext = ".tar.xz"
    url = f"https://ziglang.org/download/{version}/{name}{ext}"

class LibretroCoreInfo(Install):
    version = "1.19.0"
    name = f"libretro-core-info-{version}"
    ext = ".tar.gz"
    url = f"https://github.com/libretro/libretro-core-info/archive/refs/tags/v{version}{ext}"

class RetroArchCoreInfo:

    def __init__(self, info, name):
        self.info = info.name
        self.name = f"{name}_libretro.info"

    def install(self, cfg, dstdir):
        filename = os.path.join(dstdir, self.name)
        if not os.path.exists(filename):
            copy(os.path.join(cfg.srcdir, self.info, self.name), filename)

class RetroArchCore:
    ext = ".zip"

    def __init__(self, name):
        self.name = f"{name}_libretro.so"
        self.url = f"https://buildbot.libretro.com/nightly/linux/x86_64/latest/{self.name}{self.ext}"

    def install(self, dstdir):
        install(self, os.path.join(dstdir, 'cores'), os.path.join(dstdir, 'downloads'))

class RetroArch(Install):
    version = "1.19.1"
    name = f"RetroArch-{version}"
    ext = ".tar.gz"
    url = f"https://github.com/libretro/RetroArch/archive/refs/tags/v{version}{ext}"
    cores = ("2048", "craft")
    keep = {"dynamic", "dylib", "menu", "configfile", "zlib", "ozone", "opengl", "opengl_core", "egl", "glsl", "wayland", "pulse"}

    def install(self, cfg):
        super().install(cfg)
        dirname = os.path.join(cfg.srcdir, self.name)
        if not os.path.exists(os.path.join(dirname, "config.mk")):
            options = [
                line.strip().split()[0].decode()
                for line in check_output(
                    ["./configure", "--help"],
                    cwd=dirname).splitlines()
                if line.strip().startswith(b"--disable-") ]
            argv = [
                "./configure",
                f"--prefix={cfg.usrdir}"] + [
                o for o in options
                if o[10:] not in self.keep ]
            check_call(argv, cwd=dirname)

        if not os.path.exists(os.path.join(cfg.usrdir, "bin/retroarch")):
            check_call(["make", "install"], cwd=dirname)

        info = LibretroCoreInfo()
        info.install(cfg)

        cfgdir = os.path.join(cfg.rootdir, "retroarch")
        for core in self.cores:
            RetroArchCore(core).install(cfgdir)
            RetroArchCoreInfo(info, core).install(cfg, os.path.join(cfgdir, "cores"))

        cfgfile = os.path.join(cfgdir, "retroarch.cfg")

        if not os.path.exists(cfgfile):
            os.makedirs(os.path.dirname(cfgfile), exist_ok=True)
            with open(cfgfile, "w") as f:
                f.write('''pause_nonactive = "false"
config_save_on_exit = "false"
remap_save_on_exit = "false"
video_fullscreen = "true"
menu_timedate_enable = "false"
menu_battery_level_enable = "false"
''')

def install_vmlinuz(cfg):
    kernel_version = check_output(["uname", "-r"], text=True).strip()
    path = os.path.join(cfg.bootdir, 'vmlinuz')
    if not os.path.exists(path):
        os.makedirs(cfg.bootdir, exist_ok=True)
        copy(f"/lib/modules/{kernel_version}/vmlinuz", path)

class BusyBox(Install):
    version = "1.35.0"
    name = f"busybox"
    ext = ""
    url = f"https://www.busybox.net/downloads/binaries/{version}-x86_64-linux-musl/{name}"

    def install(self, cfg):
        super().install(cfg)

        path = os.path.join(cfg.bootdir, 'busybox')
        if not os.path.exists(path):
            os.makedirs(cfg.bootdir, exist_ok=True)
            copy(os.path.join(cfg.srcdir, self.name), path)

def install_init(cfg):
    path = os.path.join(cfg.bootdir, 'init')
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("""#!/busybox sh

/busybox mkdir /bin
/busybox --install /bin
mkdir /proc
mkdir /sys
mount -t devtmpfs none /dev
mount -t proc none /proc
mount -t sysfs none /sys
exec sh -c "on_exit() { poweroff -f; }; trap on_exit EXIT; $1"
""")
        os.chmod(path, 0o755)

def main():
    cfg = Config()
    Zig().install(cfg)
    RetroArch().install(cfg)
    install_vmlinuz(cfg)
    BusyBox().install(cfg)
    install_init(cfg)

if __name__ == '__main__':
    container = os.environ.get('container')
    if (container == "flatpak") or (container == 'oci' and os.environ.get('TOOLBOX_PATH')):
        check_call(["flatpak-spawn", "--host", "--watch-bus", "--env=TERM="+os.environ.get('TERM',''), "--", "python3"]+sys.argv)
    else:
        main()
