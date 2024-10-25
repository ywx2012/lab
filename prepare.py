#!/usr/bin/env python3

import os
import sys
from shutil import copy
from utils import Config, download, extractall
from subprocess import check_output, check_call, Popen, PIPE
from graphlib import TopologicalSorter

def install(self, dstdir, dldir=None):
    dirname = os.path.join(dstdir, self.name)
    filename = os.path.join(dldir or dstdir, f"{self.name}{self.ext}")

    if not os.path.exists(dirname):
        download(self.url, filename)
        extractall(filename, dstdir, self.mkdir)

class Install:
    mkdir = False

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
    keep = {"dynamic", "dylib", "menu", "configfile", "zlib", "ozone", "opengl", "opengl_core", "egl", "glsl", "wayland", "pulse", "udev", "kms", "tinyalsa"}

    def install(self, cfg):
        super().install(cfg)
        dirname = os.path.join(cfg.srcdir, self.name)
        if not os.path.exists(os.path.join(dirname, "config.mk")):
            options = [
                line.strip().split()[0].decode()
                for line in check_output(
                    ["toolbox", "run", "./configure", "--help"],
                    cwd=dirname).splitlines()
                if line.strip().startswith(b"--disable-") ]
            argv = [
                "toolbox", "run", "./configure",
                f"--prefix={cfg.usrdir}"] + [
                o for o in options
                if o[10:] not in self.keep ]
            check_call(argv, cwd=dirname)

        if not os.path.exists(os.path.join(cfg.usrdir, "bin/retroarch")):
            check_call(["toolbox", "run", "make", "install"], cwd=dirname)

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

class virtiofsd(Install):
    name = "virtiofsd"
    ext = ".zip"
    url = "https://gitlab.com/virtio-fs/virtiofsd/-/jobs/artifacts/main/download?job=publish"
    mkdir = True

    def install(self, cfg):
        super().install(cfg)

        src = os.path.join(cfg.srcdir, self.name, "target/x86_64-unknown-linux-musl/release/virtiofsd")
        dst = os.path.join(cfg.usrdir, "bin/virtiofsd")
        if not os.path.exists(dst):
            os.chmod(src, 0o555)
            copy(src, dst)

def modinfo_depends(mod):
    line = check_output(["modinfo", "-F", "depends", mod], text=True).strip()
    if line:
        return line.split(",")
    return []

def modinfo_filename(mod):
    return check_output(["modinfo", "-n", mod], text=True).strip()

def resolve_dependencies(items, get_depends):
    graph = {}
    visited = set(items)
    queue = list(items)
    while queue:
        item = queue.pop(0)
        depends = get_depends(item)

        graph[item] = set(depends)
        for d in depends:
            if d not in visited:
                queue.append(d)
                visited.add(d)

    ts = TopologicalSorter(graph)
    return ts.static_order()

def copy_modules(cfg, mods):
    modules = []
    for mod in resolve_dependencies(mods, modinfo_depends):
        src = modinfo_filename(mod)
        basename = os.path.basename(src)
        dst = os.path.join(cfg.bootdir, "modules", basename)
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            copy(src, dst)
        modules.append(basename)
    return modules

def install_initrd(cfg):
    modules = copy_modules(cfg, ["virtiofs"])

    init = os.path.join(cfg.bootdir, "init")
    if not os.path.exists(init):
        with open(init, "w") as f:
            f.write("""#!/busybox sh

/busybox mkdir /bin
/busybox --install /bin
""" + '\n'.join(f'insmod /modules/{m}' for m in modules) + """
mkdir /proc
mount -t devtmpfs none /dev
mount -t proc none /proc
mkdir /sysroot
mount -t virtiofs -o ro sysroot /sysroot
cd /sysroot
mount -t sysfs none sys
mount -t proc none proc
mount -t devtmpfs none dev
mkdir dev/shm
mount -t tmpfs none dev/shm
mount -t tmpfs none tmp
mount -t tmpfs none run
mount -t tmpfs none var
mkdir -p var/home
mkdir -p var/roothome
mkdir -p var/mnt
mkdir -p var/opt
mkdir -p var/srv
mount -t virtiofs -o ro workspace var/mnt
export PATH="/sbin:/bin"
export XDG_CONFIG_HOME=/mnt/workspace
export HOME=/var/roothome
export LANG=C.utf8
exec setsid cttyhack switch_root -c /dev/console /sysroot /bin/bash -c "on_exit() { poweroff -f; }; trap on_exit EXIT; cd /mnt; $1"
""")
        os.chmod(init, 0o755)

    initrd = os.path.join(cfg.bootdir, "initrd")
    if os.path.exists(initrd):
        return

    filenames = ''.join(f'{p}\n' for p in (['busybox', 'init', 'modules'] + [f'modules/{m}' for m in modules])).encode()

    p1 = Popen(["cpio", "--dereference", "-ov", "--format=newc"], stdin=PIPE, stdout=PIPE, cwd=cfg.bootdir)
    p2 = Popen(["xz", "--format=lzma", "--compress", "--stdout"], stdin=p1.stdout, stdout=PIPE)
    p1.stdout.close()
    p1.stdin.write(filenames)
    p1.stdin.flush()
    p1.stdin.close()
    output = p2.communicate()[0]
    assert p1.wait() == 0
    assert p2.wait() == 0

    with open(initrd, "wb") as f:
        f.write(output)


def main():
    cfg = Config()
    Zig().install(cfg)
    RetroArch().install(cfg)
    install_vmlinuz(cfg)
    BusyBox().install(cfg)
    # install_init(cfg)
    virtiofsd().install(cfg)
    install_initrd(cfg)

if __name__ == '__main__':
    container = os.environ.get('container')
    if (container == "flatpak") or (container == 'oci' and os.environ.get('TOOLBOX_PATH')):
        check_call(["flatpak-spawn", "--host", "--watch-bus", "--env=TERM="+os.environ.get('TERM',''), "--", "python3"] + sys.argv)
    else:
        main()
