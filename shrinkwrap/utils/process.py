# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import fcntl
import io
import os
import pty
import shlex
import selectors
import subprocess
import sys
import shrinkwrap.utils.runtime as runtime
import shrinkwrap.utils.tty as tty


STDOUT = 0
STDERR = 1


class Process:
	"""
	A wrapper to a process that should be managed by the ProcessManager.
	"""
	def __init__(self, args, interactive, data, run_to_end):
		self.args = shlex.split(args)
		self.interactive = interactive
		self.data = data
		self.run_to_end = run_to_end
		self._popen = None
		self._stdout = None
		self._stdin = None
		self._stderr = None
		self._active = 0


class ProcessManager:
	"""
	A ProcessManager can manage a set of processes running in parallel such
	that it can capture all their (stdout + stderr) output and pass it to a
	handler delegate.
	"""
	def __init__(self, handler=None, terminate_handler=None):
		self._handler = handler
		self._terminate_handler = terminate_handler
		self._procs = []
		self._active = 0
		self._sel = None

	def set_handler(self, handler):
		self._handler = handler

	def add(self, process):
		self._procs.append(process)
		if self._sel:
			self._proc_activate(process)

	def run(self, forward_stdin=False):
		try:
			self._sel = selectors.DefaultSelector()
			self._active = 0

			if forward_stdin:
				self._stdin_activate()

			for proc in self._procs:
				self._proc_activate(proc)

			while self._active > 0:
				for key, mask in self._sel.select():
					handler = key.data[0]
					handler(key, mask)
		finally:
			for proc in self._procs:
				try:
					self._proc_deactivate(proc, force=True)
				except:
					pass

			if forward_stdin:
				self._stdin_deactivate()

			self._sel.close()
			self._sel = None

	def _read_nonblock(self, fileobj):
		# If stdin and stdout are both connected to a tty, setting stdin
		# to nonblocking will also cause stdout to be set nonblocking
		# and can cause errors when printing to stdout the output buffer
		# is full. So work around that by only making fds nonblocking
		# while we do the read.
		fl = fcntl.fcntl(fileobj, fcntl.F_GETFL)
		fcntl.fcntl(fileobj, fcntl.F_SETFL, fl | os.O_NONBLOCK)
		data = fileobj.read()
		fcntl.fcntl(fileobj, fcntl.F_SETFL, fl)
		return data

	def _proc_handle(self, key, mask):
		proc = key.data[1]
		streamid = key.data[2]
		data = self._read_nonblock(key.fileobj)

		if data == '':
			self._proc_stream_deactivate(proc, key.fileobj, streamid)
		elif self._handler:
			self._handler(self, proc, data, streamid)

	def _proc_activate(self, proc):
		cmd = runtime.mkcmd(proc.args, proc.interactive)

		if proc.interactive:
			master, slave = pty.openpty()

			proc._popen = subprocess.Popen(cmd,
						       stdin=slave,
						       stdout=slave,
						       stderr=slave)

			proc._stdin = io.open(master, 'wb', buffering=0)
			proc._stdout = io.open(master, 'rb', -1, closefd=False)
			# Don't attempt to translate newlines. We need the '\r's
			# to correctly return the carriage for interactive
			# terminals. Telnet sometimes gives '\r\r\n' too, which
			# would be incorrectly translated to '\n\n'.
			proc._stdout = io.TextIOWrapper(proc._stdout,
							newline='',
							errors='replace')
			# stdout and stderr get merged into pty, so can't tell
			# them apart. This isn't a problem for the emit build
			# warnings use case.
			proc._stderr = None
			proc._active = 1
		else:
			proc._popen = subprocess.Popen(cmd,
						       stdin=subprocess.DEVNULL,
						       stdout=subprocess.PIPE,
						       stderr=subprocess.PIPE,
						       universal_newlines=True,
						       errors='replace')

			proc._stdin = None
			proc._stdout = proc._popen.stdout
			proc._stderr = proc._popen.stderr
			proc._active = 2

		if proc._stdout:
			self._sel.register(proc._stdout,
					   selectors.EVENT_READ,
					   (self._proc_handle, proc, STDOUT))

		if proc._stderr:
			self._sel.register(proc._stderr,
					   selectors.EVENT_READ,
					   (self._proc_handle, proc, STDERR))

		if proc.run_to_end:
			self._active += 1

	def _proc_stream_deactivate(self, proc, stream, streamid, force=False):
		if not stream:
			return

		self._sel.unregister(stream)

		if streamid == STDOUT:
			proc._stdout = None
		if streamid == STDERR:
			proc._stderr = None

		assert(proc._active > 0)
		proc._active -= 1

		if not force and proc._active == 0:
			self._proc_deactivate(proc, force)

	def _proc_deactivate(self, proc, force):
		if not proc._popen:
			return

		if proc.run_to_end:
			self._active -= 1

		proc._stdin = None
		self._proc_stream_deactivate(proc, proc._stdout, STDOUT, force)
		self._proc_stream_deactivate(proc, proc._stderr, STDERR, force)

		proc._popen.kill()
		try:
			proc._popen.communicate()
		except:
			pass
		retcode = None if force else proc._popen.poll()
		proc._popen = None

		if self._terminate_handler:
			self._terminate_handler(self, proc, retcode)

	def _stdin_handle(self, key, mask):
		data = self._read_nonblock(key.fileobj)
		for proc in self._procs:
			if proc._stdin:
				proc._stdin.write(data)

	def _stdin_activate(self):
		# Replace stdin with unbuffered binary stream so we can pass
		# input to the ptys without any modification.
		self._stdin_orig = sys.stdin
		sys.stdin = io.open(self._stdin_orig.fileno(),
				    'rb',
				    buffering=0,
				    closefd=False)

		# Set the terminal to raw input mode.
		self._tty_orig = tty.configure(sys.stdin)

		# Register stdin so we get notified when there is data.
		self._sel.register(sys.stdin,
				   selectors.EVENT_READ,
				   (self._stdin_handle,))

	def _stdin_deactivate(self):
		# Unregister for notifications.
		self._sel.unregister(sys.stdin)

		# Restore terminal mode.
		tty.restore(sys.stdin, self._tty_orig)

		# Restore stdin to being buffered text.
		sys.stdin.close()
		sys.stdin = self._stdin_orig
		self._stdin_orig = None
