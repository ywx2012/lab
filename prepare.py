#!/usr/bin/env python3

import os
from utils import Config, download, extractall

def install_zig(version, cfg):
    name = f"zig-linux-x86_64-{version}"
    dirname = os.path.join(cfg.srcdir, name)
    filename = os.path.join(cfg.srcdir, f"{name}.tar.xz")

    if not os.path.exists(dirname):
        download(f"https://ziglang.org/download/{version}/{name}.tar.xz", filename)
        extractall(filename, cfg.srcdir)

def main():
    cfg = Config()
    install_zig("0.13.0", cfg)

if __name__ == '__main__':
    main()
