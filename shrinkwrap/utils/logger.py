# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import sys
from collections import namedtuple
import re
termcolor = None


def _import_termcolor():
	global termcolor
	import termcolor as tc
	termcolor = tc


_ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
_colors = ['blue', 'cyan', 'green', 'yellow', 'magenta']
Data = namedtuple("Data", "id tag color noesc escbuf")


class MatchBuf:
	def __init__(self, match):
		self._match = match
		self._buf = ''

	def match(self, data):
		self._buf += data
		found = self._buf.find(self._match) >= 0
		self._buf = self._buf[1 - len(self._match):]
		return found


def splitlines(string):
	"""
	Like str.splitlines(True) but preserves '\r'.
	"""
	lines = string.split('\n')
	keepends = [l + '\n' for l in lines[:-1]]
	if lines[-1] != '':
		keepends.append(lines[-1])
	return keepends


class Logger:
	def __init__(self, tag_size):
		self._tag_size = tag_size
		self._id_next = 0
		self._color_next = 0
		self._prev_id = None
		self._prev_char = '\n'

	def alloc_data(self, tag, colorize, no_escapes=False):
		"""
		Returns the object that should be stashed in proc.data[0] when
		log() is called. Includes the tag for the process and an
		allocated colour.
		"""
		if colorize:
			_import_termcolor()
			color = self._color_next
			self._color_next += 1
			color = _colors[color % len(_colors)]
		else:
			color = None

		id = self._id_next
		self._id_next += 1

		if type(no_escapes) == str:
			noesc = True
			escbuf = MatchBuf(no_escapes)
		else:
			noesc = no_escapes
			escbuf = None

		return Data(id, tag, color, [noesc], escbuf)

	def free_data(self, data):
		pass

	def log(self, pm, proc, data, streamid):
		"""
		Logs text data from one of the processes (FVP or one of its uart
		terminals) to the terminal. Text is colored and a tag is added
		on the left to identify the originating process.
		"""
		id = proc.data[0].id
		tag = proc.data[0].tag
		color = proc.data[0].color
		noesc = proc.data[0].noesc
		escbuf = proc.data[0].escbuf

		# Remove any ansi escape sequences if requested.
		if noesc[0]:
			if escbuf and escbuf.match(data):
				noesc[0] = False
			else:
				data = _ansi_escape.sub('', data)
				if len(data) == 0:
					return

		# Make the tag.
		if len(tag) > self._tag_size:
			tag = tag[:self._tag_size-3] + '...'
		if len(tag):
			tag = f'{{:>{self._tag_size}}}'.format(tag)

		lines = splitlines(data)
		start = 0

		# If the cursor is not at the start of a new line, then if the
		# new log is for the same proc that owns the first part of the
		# line, just continue from there without adding a new tag. If
		# the first part of the line has a different owner, insert a
		# newline and add a tag for the new owner.
		if self._prev_char != '\n':
			if self._prev_id == id:
				self.print(lines[0], tag, True, color, end='')
				start = 1
			else:
				self.print('\n', tag, True, color, end='')

		for line in lines[start:]:
			self.print(line, tag, False, color, end='')

		self._prev_id = id
		self._prev_char = lines[-1][-1]

		sys.stdout.flush()

	def print(self, text, tag, cont, color=None, on_color=None, attrs=None, **kwargs):
		# Ensure that any '\r's only rewind to the end of the tag.
		if len(tag):
			tag = f'[ {tag} ] '
		text = text.replace('\r', f'\r{tag}')

		if not cont:
			self._print(tag, color, on_color, attrs, end='')

		self._print(text, color, on_color, attrs, **kwargs)

	def _print(self, text, color=None, on_color=None, attrs=None, **kwargs):
		if color:
			text = termcolor.colored(text, color, on_color, attrs)
		print(text, **kwargs)
