# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

from termios import *
import copy

IFLAG = 0
OFLAG = 1
CFLAG = 2
LFLAG = 3
ISPEED = 4
OSPEED = 5
CC = 6

def configure(fd, when=TCSAFLUSH):
	try:
		orig = tcgetattr(fd)
		mode = copy.deepcopy(orig)

		# Don't remove/convert line feeds to new lines on input. EDK2
		# can't handle only receiving newlines.
		mode[IFLAG] = mode[IFLAG] & ~(INLCR | IGNCR | ICRNL)

		# Disable input echo and use non-canonical input mode (no
		# buffering).
		mode[LFLAG] = mode[LFLAG] & ~(ECHO | ICANON)
		mode[CC][VMIN] = 1
		mode[CC][VTIME] = 0

		# Use ^] as the interrupt (instead of ^C), and remove key
		# bindings for quit and suspend signals. This means the usual
		# key bindings are passed through to the child.
		mode[CC][VINTR] = b'\x1d'
		mode[CC][VQUIT] = b'\x00'
		mode[CC][VSUSP] = b'\x00'

		tcsetattr(fd, when, mode)
		return orig

	except error as e:
		# Expect failure if we are not connected to a tty. Non-fatal.
		pass

def restore(fd, mode, when=TCSAFLUSH):
	if mode:
		tcsetattr(fd, when, mode)
