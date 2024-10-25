#!/usr/bin/env python3

import os
import argparse
from subprocess import run, check_output, Popen
import json

HOST_RUN = ["flatpak-spawn", "--host", "--watch-bus"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', type=int, default=2048)
    parser.add_argument('config', nargs='*')

    args = parser.parse_args()

    names = args.config or ['base']
    if len(names) == 1:
        name = names[0]
        cfg = CONFIGS[name]()
    else:
        name = '+'.join(sorted(names))
        configs = tuple(resolve_dependencies([CONFIGS[name] for name in names], lambda x: x.__bases__))
        cfg = Meta.__new__(Meta, name, configs[::-1], {})()

    modprobe = ''.join(f'modprobe {m}; ' for m in cfg.modprobe())
    qemu_argv = list(cfg.qemu_argv())

    init_script = f"{modprobe}sh"

    sysroot = "/sysroot/ostree/deploy/{osname}/deploy/{checksum}.{serial}".format(**json.loads(check_output(HOST_RUN+["rpm-ostree", "status", "-b", "--json"]))["deployments"][0])
    sysrootd = Popen(HOST_RUN+["workspace/usr/bin/virtiofsd", "--sandbox=none", "--socket-path=/tmp/sysroot.sock", "-o", f"source={sysroot}"])

    workspaced = Popen(HOST_RUN+["workspace/usr/bin/virtiofsd", "--sandbox=none", "--socket-path=/tmp/workspace.sock", "-o", "source="+os.getcwd()])

    env = os.environ.copy()
    env['LANG'] = 'C.utf8'

    try:
        run(["qemu-system-x86_64",
             "-boot", "reboot-timeout=0", "-action", "reboot=shutdown",
             "-nodefaults", "-no-user-config", "-nographic",
             "-machine", "q35,accel=kvm", "-cpu", "host",
             "-m", f"{args.m}",
             "-object", f"memory-backend-memfd,id=mem,size={args.m}M,share=on",
            "-numa", "node,memdev=mem",
             "-chardev", "stdio,mux=on,id=char0",
             "-serial", "chardev:char0",
             "-mon", "chardev=char0,mode=readline",

             "-chardev", "socket,id=char1,path=/tmp/sysroot.sock",
             "-device", "vhost-user-fs-pci,chardev=char1,tag=sysroot",

             "-chardev", "socket,id=char2,path=/tmp/workspace.sock",
             "-device", "vhost-user-fs-pci,chardev=char2,tag=workspace",

             "-kernel", "workspace/boot/vmlinuz",
             "-initrd", "workspace/boot/initrd",
             "-append", f'console=ttyS0 panic=-1 quiet -- "{init_script}"'
             ] + qemu_argv,
            env=env,
            check=True)
    finally:
        try:
            workspaced.terminate()
            workspaced.wait()
        finally:
            sysrootd.terminate()
            sysrootd.wait()

CONFIGS = {}

class Meta(type):

    def __new__(self, name, bases, attrs):
        t = type.__new__(self, name, bases, attrs)
        CONFIGS[name] = t
        return t

class base(metaclass=Meta):

    def qemu_argv(self):
        return []

    def modprobe(self):
        return []

class gpu(base):

    def qemu_argv(self):
        yield from super().qemu_argv()
        yield from ('-display', 'gtk,gl=on,show-cursor=on,zoom-to-fit=off', '-device', 'virtio-gpu-gl')

class gl(gpu):

    def modprobe(self):
        yield from super().modprobe()
        yield 'virtio-gpu'


if __name__ == '__main__':
    main()
