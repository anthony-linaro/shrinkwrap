# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import os
import subprocess
import sys
import tuxmake.runtime
import types
import shrinkwrap.utils.ssh_agent as ssh_agent_lib

_SSH_AUTH_SOCK = '/run/host-services/ssh-auth.sock'
"""Path to ssh-agent socket."""


_instance = None


def get_null_user_opts(self):
	return []


class Runtime:
	"""
	Wraps tuxmake.runtime to provide an interface for executing commands in
	an abstracted runtime. Multiple runtimes are supported, identified by a
	`name`. The 'null' runtime simply executes the commands on the native
	host. The 'docker', 'docker-local', 'podman' and 'podman-local' runtimes
	execute the commands in a container.
	"""
	def __init__(self, *, name, image=None, ssh_agent_keys=None):
		self._rt = None
		self._mountpoints = set()

		self._rt = tuxmake.runtime.Runtime.get(name)
		self._rt.set_image(image)

		is_mac = sys.platform.startswith('darwin')
		is_docker = name.startswith('docker')

		# MacOS uses GIDs that overlap with already defined GIDs in the
		# container so we can't just bind the macos host UID/GID to the
		# shrinkwrap user in the container. This concept doesn't really
		# work anyway, because on MacOS the container is running on a
		# completely separate (linux) kernel in a VM. Fortunately docker
		# maps the VM to the current MacOS user when touching mapped
		# volumes so it all works out. So on MacOS run as root.
		# Unfortunately, tuxmake tries to be too clever (it assumes a
		# linux host) and tries to map the in-container user to the host
		# UID/GID. This fails when the in-container user is root. So we
		# have this ugly workaround to override the user-opts with
		# nothing. By passing nothing, we implicitly run as root and
		# tuxmake doesn't try to run usermod.
		if is_mac and is_docker:
			self._rt.get_user_opts = \
				types.MethodType(get_null_user_opts, self._rt)
		else:
			self._rt.set_user('shrinkwrap')
			self._rt.set_group('shrinkwrap')

		for key in ssh_agent_keys:
			ssh_agent_lib.add(key)

		socket = ssh_agent_lib.socket()

		if name != 'null' and socket is not None:
			if is_mac:
				socket = _SSH_AUTH_SOCK

			self._rt.add_volume(socket, _SSH_AUTH_SOCK)

	def start(self):
		for mp in self._mountpoints:
			self._rt.add_volume(mp)

		self._rt.prepare()

	def add_volume(self, src):
		# Podman can't deal with duplicate mount points, so filter out
		# duplicates here, including mount-points that are children of
		# other mount points. Then defer registering the actual final
		# volumes until start() time.

		if not src:
			return

		mountpoints = set()

		for mp in self._mountpoints:
			common = os.path.commonpath([src, mp])
			if common == mp:
				# mp is parent (or duplicate) of src, so src
				# already covered.
				return
			elif common != src:
				# src is not a parent of mp. So include mp in
				# filtered set of mount points.
				mountpoints.add(mp)

		# If we got here, then src is a unique mountpoint. Add it, and
		# commit the filtered set.
		mountpoints.add(src)
		self._mountpoints = mountpoints

	def mkcmd(self, cmd, interactive=False):
		return self._rt.get_command_line(cmd, interactive, False)

	def ip_address(self):
		"""
		Returns the primary ip address of the runtime.
		"""

		script = """
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(0)
try:
	s.connect(('10.254.254.254', 1))
	ip = s.getsockname()[0]
except Exception:
	ip = '127.0.0.1'
finally:
	s.close()
print(ip)
""".replace('\n', '\\n').replace('\t', '\\t')

		cmd = ['python3', '-c', f'exec("{script}")']
		res = subprocess.run(self.mkcmd(cmd),
				     universal_newlines=True,
				     stdout=subprocess.PIPE,
				     stderr=subprocess.PIPE)
		if res.returncode == 0:
			return res.stdout.strip()
		return '127.0.0.1'
	
	def __enter__(self):
		global _instance
		assert _instance is None
		_instance = self
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		global _instance
		assert _instance == self
		_instance = None


def get():
	"""
	Returns the current Runtime instance.
	"""
	global _instance
	assert _instance is not None
	return _instance


def mkcmd(cmd, interactive=False):
	"""
	Shorthand for get().mkcmd().
	"""
	return get().mkcmd(cmd, interactive)
