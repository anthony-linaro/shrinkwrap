# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import os

_code_root = os.path.dirname(os.path.dirname(__file__))
_data_root = os.path.expanduser('~/.shrinkwrap')

def _get_loc(var, default=None):
	path = os.environ.get(var, default)
	if not path:
		return None
	path = os.path.abspath(path)
	os.makedirs(path, exist_ok=True)
	return path

build = _get_loc('SHRINKWRAP_BUILD', os.path.join(_data_root, 'build'))
package = _get_loc('SHRINKWRAP_PACKAGE', os.path.join(_data_root, 'package'))
project_cache = _get_loc("SHRINKWRAP_PROJECT_CACHE")

_configs = None

def configs():
	global _configs

	if _configs is None:
		value = os.environ.get('SHRINKWRAP_CONFIG')

		# Set of paths that we will search for configs in, in priority
		# order. Prefer any user-supplied paths, then fall back to
		# ~/.shrinkwrap/config (which is the "installed" location of the
		# standard config store), then fall back to the in-repo location
		# for the uninstalled case. Then filter out any paths that don't
		# exist.
		paths = value.split(':') if value else []
		paths += [os.path.realpath(os.path.join(_data_root, 'config'))]
		paths += [os.path.realpath(os.path.join(_code_root, 'config'))]
		_configs = [p for p in paths if os.path.exists(p)]

	return _configs

def config(path, join=True):
	for config in configs():
		p = os.path.join(config, path) if join else f'{config}{path}'
		if os.path.exists(p):
			return config
	return None

def dump():
	print(f'workspace.project_cache:')
	print(f'  {project_cache}')
	print(f'workspace.build:')
	print(f'  {build}')
	print(f'workspace.package:')
	print(f'  {package}')
	print(f'workspace.config:')
	for path in configs():
		print(f'  {path}')
