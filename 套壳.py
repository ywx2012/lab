#!/usr/bin/env python3

print("""Traceback (most recent call last)
  File "segfault.c", line 7, in main
  File "segfault.c", line 6, in h
  File "segfault.c", line 5, in g
  File "segfault.c", line 3, in f
Error: SIGSEGV while accessing 0x0000000000000000""")
