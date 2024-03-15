# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import os
import re
import sys
import shrinkwrap.utils.tty as tty


class Label:
	"""
	Container for a string. Intended to be used with LabelController to
	display labels (strings of text) on a terminal at a fixed location and
	be able to update them in place. Instantiate with desired text, and
	update the text by calling update(). Nothing actually changes on screen
	until the LabelController does an update().
	"""
	def __init__(self, text=''):
		self.text = text
		self._prev_text = ''
		self._lc = None

	def update(self, text=''):
		self.text = text
		if self._lc:
			self._lc._update_pending = True


class LabelController:
	"""
	Coordinates printing and updating a set of labels at a fixed location on
	a terminal. The controller manages a list of labels, which are provided
	at construction and are displayed one under the other on the terminal.
	update() can be periodically called to redraw the labels if their
	contents has changed. Only works as long as no other text is printed to
	the terminal while the labels are active. If the provided file is not
	backed by a terminal, overdrawing is not performed.
	"""
	def __init__(self, labels=[], overdraw=True):
		self._labels = labels
		self._overdraw = overdraw
		self._drawn = False
		self._cursor_col = 1
		self._separator = ''
		self._update_pending = True

		self._out = sys.stdout
		self._in = sys.stdin

		if overdraw and not self._term_cols():
			self._overdraw = False

		for label in self._labels:
			label._lc = self

	def _term_cols(self):
		try:
			term_sz = os.get_terminal_size(self._out.fileno())
			return term_sz.columns
		except OSError:
			return None

	def cursor_pos(self):
		orig = tty.configure(self._in)
		if orig:
			try:
				pos = ''
				self._out.write('\x1b[6n')
				self._out.flush()
				while not (pos := pos + self._in.read(1)).endswith('R'):
					pass
				res = re.match(r'.*\[(?P<y>\d*);(?P<x>\d*)R', pos)
			finally:
				tty.restore(self._in, orig)
			if(res):
				return (int(res.group("x")), int(res.group("y")))
		assert(False)

	def _move_up(self, line_count, column=1):
		assert(self._overdraw)
		self._out.write(f'\033[{line_count}F')
		if column > 1:
			self._out.write(f'\033[{column}G')

	def _line_count(self, text, term_cols):
		assert(self._overdraw)
		return (len(text) + term_cols - 1) // term_cols

	def update(self):
		if not self._update_pending:
			return
		if self._overdraw:
			term_cols = self._term_cols()
			if not self._drawn:
				self._cursor_col = self.cursor_pos()[0]
				if self._cursor_col > 1:
					self._out.write('\n')
				self._separator = '-' * term_cols
				self._out.write(self._separator)
				self._out.write('\n')
				for l in self._labels:
					self._out.write(l.text)
					self._out.write('\n')
					l._prev_text = l.text
			else:
				erase_lines = 0
				for l in self._labels:
					erase_lines += self._line_count(l._prev_text, term_cols)
				self._move_up(erase_lines)
				for l in self._labels:
					cc = len(l.text)
					pcc = len(l._prev_text)
					self._out.write(l.text)
					self._out.write(' ' * (pcc - cc))
					self._out.write('\n')
					l._prev_text = l.text
		else:
			for l in self._labels:
				if l.text != l._prev_text:
					self._out.write(l.text)
					self._out.write('\n')
					l._prev_text = l.text
		self._out.flush()
		self._drawn = True
		self._update_pending = False

	def erase(self):
		if not self._overdraw or not self._drawn:
			return

		term_cols = self._term_cols()

		erase_lines = self._line_count(self._separator, term_cols)
		for l in self._labels:
			erase_lines += self._line_count(l._prev_text, term_cols)

		self._move_up(erase_lines)

		self._out.write(' ' * len(self._separator))
		self._out.write('\n')

		for l in self._labels:
			pcc = len(l._prev_text)
			self._out.write(' ' * pcc)
			self._out.write('\n')

		if self._cursor_col > 1:
			erase_lines += 1
		self._move_up(erase_lines, self._cursor_col)

		self._out.flush()
		self._drawn = False
		self._update_pending = True
