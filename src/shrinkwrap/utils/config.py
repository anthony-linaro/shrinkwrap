# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import graphlib
import io
import json
import os
import re
import textwrap
import yaml
from shrinkwrap import __version__
import shrinkwrap.utils.clivars as uclivars
import shrinkwrap.utils.workspace as workspace
from urllib.parse import urlparse

_default_image = 'docker.io/shrinkwraptool/base-slim'


def _looks_like_abbreviated_git_sha(revision):
	"""
	Detect abbreviated/full object ids that are likely commit hashes rather than
	ref names. Git servers generally cannot resolve these with
	`git fetch origin <sha>`, but a regular clone/fetch followed by
	`git checkout <sha>` works once the object is present locally.
	"""
	return isinstance(revision, str) and re.fullmatch(r'(?i)(?=.*[a-f])[0-9a-f]{7,40}', revision) is not None

def _get_image(configs, args):
	"""
	Determine the image to use
	"""
	if args.image is not None:
		# An image was specified on the command line, just use it !
		return args.image
	else:
		# No image forced on the command line, use one required by one of the configs,
		# but make sure that if multiple config require an image, this is the same.
		image = None
		for c in configs:
			if c['image'] is not None:
				if image is None:
					image = c['image']
				elif c['image'] == image:
					pass
				else:
					raise Exception('Unsupported case of different images requested.')
		# No image required in the configs or from the command line, use the default one
		return image if image else _default_image


def get_image(configs, args):
	image = _get_image(configs, args)
	parts = image.split(":")
	if len(parts) not in [1, 2]:
		raise Exception('Invalid image path.')
	image = parts[0]
	tag = parts[1] if len(parts) == 2 else __version__
	return f"{image}:{tag}"


def _component_normalize(component, name):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	component.setdefault('repo', {})

	if len(component['repo']) > 0 and \
		all(not isinstance(v, dict) for v in component['repo'].values()):
		component['repo'] = {'.': component['repo']}

	for repo in component['repo'].values():
		repo.setdefault('remote', None)
		repo.setdefault('revision', None)
		repo.setdefault('project', None)

	component.setdefault('sourcedir', None)
	component.setdefault('builddir', None)
	component.setdefault('toolchain', None)
	component.setdefault('stderrfilt', None)
	component.setdefault('prebuild', [])
	component.setdefault('build', [])
	component.setdefault('postbuild', [])
	component.setdefault('params', {})
	component.setdefault('sync', None)
	if component['sync'] == False:
		component['sync'] = 'false'
	elif component['sync'] == True:
		component['sync'] = 'true'

	component['artifacts'] = { key:
		{ 'path': val, 'base': None, 'export': True } if isinstance(val, str) else
		{ 'path': val['path'], 'base': val.get('rename'),
		  'export': val.get('export', True) } if isinstance(val, dict) else
		val for key, val in component.get('artifacts', {}).items() }

	return component


def _build_normalize(build):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	if len(build) == 0:
		build['__dummy'] = {}

	for name, component in build.items():
		_component_normalize(component, name)


def _vars_normalize(vars):
	for k, p in vars.items():
		assert(isinstance(p, dict))

		v = p.setdefault('value', None)
		if v is not None:
			p['value'] = str(v)

		o = p.get('options')
		if o is None:
			o = set()
		elif isinstance(o, list):
			o = { v if v is None else str(v) for v in o }
		elif isinstance(o, set):
			pass
		else:
			o = { str(o) }

		if None in o:
			raise ValueError(f"Options for variable '{k}' must not include 'null'")
		p['options'] = o

def _var_validate(v):
	return len(v['options']) == 0 or v['value'] in v['options']


class JSONdump(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, set):
			return list(obj)
		return super().default(obj)

def _var_options(v):
	return json.dumps(v['options'], cls=JSONdump)


def _buildex_normalize(buildex):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	_vars_normalize(buildex.setdefault('btvars', {}))

	for build in buildex.setdefault('runners', {}).values():
		for name, component in build.items():
			_component_normalize(component, name)

def _runners_normalize(runners):
	for runner in runners.values():
		runner.setdefault('name', None)
		runner.setdefault('rtvars', {})
		runner.setdefault('params', [])
		runner.setdefault('prerun', [])
		runner.setdefault('run', [])
		runner.setdefault('terminals', {})

def _run_normalize(run):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	run.setdefault('name', None)
	_vars_normalize(run.setdefault('rtvars', {}))
	run.setdefault('params', {})
	run.setdefault('prerun', [])
	run.setdefault('run', [])
	run.setdefault('terminals', {})
	run.setdefault('runner', None)
	run.setdefault('runners', {})
	_runners_normalize(run['runners'])


def _config_normalize(config):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	config.setdefault('name', None)
	config.setdefault('fullname', None)
	config.setdefault('description', None)
	config.setdefault('image', None)
	config.setdefault('concrete', False)
	config.setdefault('layers', [])
	config.setdefault('graph', {})
	config.setdefault('build', {})
	config.setdefault('buildex', {})

	_build_normalize(config['build'])
	_buildex_normalize(config['buildex'])

	config.setdefault('artifacts', {})
	config.setdefault('run', {})

	_run_normalize(config['run'])

	return config

def _component_validate(component):
	sync = component.get('sync')
	if sync not in (None, 'true', 'false', 'force'):
		raise Exception(f'invalid "sync" value "{sync}"')

def _build_validate(build):
	for component in build.values():
		_component_validate(component)

def _config_validate(config):
	"""
	Ensures the config conforms to the schema. Throws exception if any
	issues are found.
	"""
	# TODO:

	if 'build' in config:
		_build_validate(config['build'])


def _component_sort(component):
	"""
	Sort the component so that the keys are in a canonical order. This
	improves readability by humans.
	"""
	lut = ['repo', 'sync', 'sourcedir', 'builddir', 'toolchain', 'stderrfilt',
			'params', 'prebuild', 'build', 'postbuild', 'artifacts']
	lut = {k: i for i, k in enumerate(lut)}
	return dict(sorted(component.items(), key=lambda x: lut[x[0]]))


def _build_sort(build):
	"""
	Sort the build section so that the keys are in a canonical order. This
	improves readability by humans.
	"""
	for name in build:
		build[name] = _component_sort(build[name])
	return dict(sorted(build.items()))


def _run_sort(run):
	"""
	Sort the run section so that the keys are in a canonical order. This
	improves readability by humans.
	"""
	lut = ['name', 'rtvars', 'params', 'prerun', 'run', 'terminals', 'runners', 'runner']
	lut = {k: i for i, k in enumerate(lut)}
	return dict(sorted(run.items(), key=lambda x: lut[x[0]]))


def _config_sort(config):
	"""
	Sort the config so that the keys are in a canonical order. This improves
	readability by humans.
	"""
	config['build'] = _build_sort(config['build'])
	config['run'] = _run_sort(config['run'])

	lut = ['name', 'fullname', 'description', 'image', 'concrete', 'layers',
			'graph', 'build', 'buildex', 'artifacts', 'run']
	lut = {k: i for i, k in enumerate(lut)}
	return dict(sorted(config.items(), key=lambda x: lut[x[0]]))


def _config_merge(base, new):
	"""
	Merges new config into the base config.
	"""
	_config_validate(base)
	_config_validate(new)

	def _merge(base, new, level=0):
		if new is None:
			return base

		if isinstance(base, list) and isinstance(new, list):
			return base + new

		if isinstance(base, set) and isinstance(new, set):
			return base | new

		elif isinstance(base, dict) and isinstance(new, dict):
			d = {}
			for k in list(set(list(base.keys()) + list(new.keys()))):
				d[k] = _merge(base.get(k), new.get(k), level+1)
			return d

		elif isinstance(base, str) and isinstance(new, str):
			return new

		return new

	config = _merge(base, new)

	# We add a dummy component if there are no others. After merging, if
	# there other components, remove it.
	if '__dummy' in config['build'] and len(config['build']) > 1:
		del config['build']['__dummy']

	return config


def _string_tokenize(string, escape=True):
	"""
	Returns ordered list of tokens, where each token has a 'type' and
	'value'. If 'type' is 'literal', 'value' is the literal string. If
	'type' is 'macro', 'value' is a dict defining 'type' and 'name'.
	"""
	regex = r'\$(?:' \
			r'(?P<escape>\$)|' \
			r'(?:\{' \
				r'(?P<type>[_a-zA-Z][_a-zA-Z0-9]*):' \
				r'(?P<name>[_a-zA-Z][_a-zA-Z0-9]*)?' \
			r'\})|' \
			r'(?P<invalid>)' \
		r')'
	pattern = re.compile(regex)
	tokens = []
	lit_start = 0

	m = pattern.search(string)
	while m:
		lit_end = m.span()[0]

		if lit_end > lit_start:
			tokens.append({
				'type': 'literal',
				'value': string[lit_start:lit_end],
			})

		lit_start = m.span()[1]

		if m['invalid'] is not None:
			raise Exception(f"Macro at col {lit_end}" \
					f" in '{string}' is invalid.")
		if m['escape'] is not None:
			assert(m['escape'] == '$')
			tokens.append({
				'type': 'literal',
				'value': '$' if escape else '$$',
			})
		if m['type'] is not None:
			tokens.append({
				'type': 'macro',
				'value': {
					'type': m['type'],
					'name': m['name'],
				},
			})

		m = pattern.search(string, pos=lit_start)

	tokens.append({
		'type': 'literal',
		'value': string[lit_start:],
	})

	return tokens


def _string_substitute(string, lut, final=True):
	"""
	Takes a string containg macros and returns a string with the macros
	substituted for the values found in the lut. If final is False, any
	macro that does not have a value in the lut will be left as a macro in
	the returned string. If final is True, any macro that does not have a
	value in the lut will cause an exception. Final also controls unescaping
	on $. If False, $$ is left as is, otherwise they are replaced with $.
	"""
	# Skip substitution if not a string or is empty
	if not isinstance(string, str) or not string:
		return string

	calls = []
	frags = []
	frag = ''
	tokens = _string_tokenize(string, final)

	for t in tokens:
		if t['type'] == 'literal':
			frag += t['value']
		elif t['type'] == 'macro':
			m = t['value']
			try:
				lu = lut[m['type']][m['name']]
				if callable(lu):
					calls.append(lu)
					frags.append(frag)
					frag = ''
				else:
					frag += lu
			except Exception:
				macro = f"${{{m['type']}:{m['name']}}}"
				frag += macro
		else:
			assert(False)

	frags.append(frag)
	assert(len(calls) + 1 == len(frags))

	final = frags[0]

	# Any callable macros expect to be called with anything that immediately
	# follows them to the next whitespace, so do that now and assemble the
	# final string.
	for call, frag in zip(calls, frags[1:]):
		final += call(frag.split(' ')[0])
		final += frag

	return final


def _string_has_macros(string):
	tokens = _string_tokenize(string)
	return any([True for t in tokens if t['type'] == 'macro'])


def _mk_params(params, separator):
	pairs = [f'{k}' if v is None else f'{k}{separator}{v}'
						for k, v in params.items()]
	return ' '.join(sorted(pairs))


def filename(name, rel=os.getcwd()):
	"""
	Given a config name, finds the path to the config on disk. If the config
	name exists relative to rel, we return that since it is a user config.
	Else, if the config name exists relative to the config store then we
	return that. If neither exist, then we return name unmodified, since
	that will generate the most useful error.
	"""
	fpath = os.path.abspath(os.path.join(rel, name))
	cpath = workspace.config(name)

	if os.path.exists(fpath):
		return fpath
	elif cpath:
		return os.path.abspath(os.path.join(cpath, name))
	else:
		return name


def load(file_name, overlays=[], friendly=None):
	"""
	Load a config from disk and return it as a dictionary. The config is
	fully normalized, validated and merged. If file_name starts with '{' it
	is treated as a json config instead of a file name and is parsed
	directly. This allows passing json config snippets as overlays on the
	command line.
	"""
	def _config_load(file_name):
		if file_name[0] == '{':
			config = json.loads(file_name)
			config_dir = os.getcwd()
		else:
			with open(file_name) as file:
				config = yaml.safe_load(file)
			config_dir = os.path.dirname(file_name)

		config = _config_normalize(config)
		_config_validate(config)

		# Recursively load and merge the layers.
		master = _config_normalize({})
		for layer in config['layers']:
			layer = _config_load(filename(layer, config_dir))
			master = _config_merge(master, layer)

		master = _config_merge(master, config)

		return master

	config = _config_load(file_name)

	for overlay in overlays:
		config = _config_merge(config, overlay)

	# Now that the config is fully merged, we don't need the layers
	# property. Its also useful to store the name.
	del config['layers']
	config['fullname'] = os.path.basename(file_name)
	config['name'] = os.path.splitext(config['fullname'])[0]
	if friendly:
		config['fullname'] = friendly

	return _config_sort(config)


def dumps(config):
	return dump(config, None)


def dump(config, fileobj):
	return yaml.safe_dump(config,
			      fileobj,
			      explicit_start=True,
			      sort_keys=False,
			      version=(1, 2))


def _string_extract_artifacts(artifacts, strings):
	for s in strings:
		for t in _string_tokenize(str(s)):
			if t['type'] != 'macro':
				continue
			m = t['value']
			if m['type'] != 'artifact':
				continue
			if m['name'] is None:
				raise KeyError('name')
			artifacts.add(m['name'])


def resolveb(config, btvars={}, clivars={}):
	"""
	Resolves the build-time macros (params, artifacts, etc) and fixes up the
	config. Based on the artifact dependencies, the component build graph is
	determined and placed into the config along with the global artifact
	map. Expects a config that was previously loaded with load().
	btvars=None implies that it is OK not to resolve btvars whose default
	value is None. isinstance(btvars, dict) implies btvars values must all be
	resolved.
	"""
	def _resolve_build_graph(config):
		def _exporters_update(exporters, name, component):
			new = {a: name for a in component['artifacts'].keys()}
			clash = set(exporters.keys()).intersection(new.keys())

			if len(clash) > 0:
				a = clash.pop()
				raise Exception(f"Duplicate artifact '{a}' exported by '{exporters[a]}' and '{new[a]}'.")

			exporters.update(new)

		def _importers_update(importers, name, component):
			artifacts = set()

			def _find_artifacts(strings):
				try:
					return _string_extract_artifacts(artifacts, strings)
				except KeyError as e:
					if e.args[0] != 'name': raise
					raise Exception(f"'{name}' uses unnamed 'artifact' macro. 'artifact' macros must be named.")

			_find_artifacts(component['params'].values())
			_find_artifacts(component['prebuild'])
			_find_artifacts(component['build'])
			_find_artifacts(component['postbuild'])
			_find_artifacts(component['artifacts'].values())

			importers[name] = sorted(list(artifacts))

		artifacts_exp = {}
		artifacts_imp = {}
		for name, desc in config['build'].items():
			_exporters_update(artifacts_exp, name, desc)
			_importers_update(artifacts_imp, name, desc)

		graph = {}
		for depender, deps in artifacts_imp.items():
			graph[depender] = []
			for dep in deps:
				if dep not in artifacts_exp:
					raise Exception(f"Imported artifact '{dep}' not exported by any component.")
				dependee = artifacts_exp[dep]
				if depender != dependee:
					graph[depender].append(dependee)

		return graph

	def _resolve_artifact_map(config):
		def _combine(config):
			return { 'artifact': { k: v['path']
				for desc in config['build'].values()
				for k, v in desc['artifacts'].items() } }

		def _normalize_basename(path):
			return os.path.basename(os.path.normpath(path))

		def _combine_full(config):
			artifact_map = {}
			for name, desc in config['build'].items():
				locs = {key: {
					'src': os.path.normpath(val['path']),
					'dst': os.path.join(config['name'], _normalize_basename(val['base'] or val['path']))
						if val['export'] == True else None,
					'component': name,
				} for key, val in desc['artifacts'].items()}
				artifact_map.update(locs)
			return artifact_map

		# ${artifact:*} macros could refer to other ${artifact:*}
		# macros, so iteratively substitute the maximum number of times,
		# which would be once per entry in the pathalogical case.

		artifact_lut = _combine(config)
		artifact_nr = len(artifact_lut['artifact'])

		while artifact_nr > 0:
			artifact_nr -= 1

			for desc in config['build'].values():
				for v in desc['artifacts'].values():
					v['path'] = _string_substitute(v['path'], artifact_lut, False)

			if artifact_nr > 0:
				artifact_lut = _combine(config)

		return _combine_full(config)

	def _substitute_macros(config, lut, final):
		for desc in config['build'].values():
			desc['sourcedir'] = _string_substitute(desc['sourcedir'], lut, final)
			desc['builddir'] = _string_substitute(desc['builddir'], lut, final)

			lut['param']['sourcedir'] = desc['sourcedir']
			lut['param']['builddir'] = desc['builddir']

			desc['params'] = { k: _string_substitute(v, lut, final) for k, v in desc['params'].items() }

			lut['param']['join_equal'] = _mk_params(desc['params'], '=')
			lut['param']['join_space'] = _mk_params(desc['params'], ' ')

			for r in desc['repo'].values():
				r['remote'] = _string_substitute(r['remote'], lut, final)
				r['revision'] = _string_substitute(r['revision'], lut, final)

			desc['toolchain'] = _string_substitute(desc['toolchain'], lut, final)

			for k in ( 'prebuild', 'build', 'postbuild', ):
				desc[k] = [ _string_substitute(s, lut, final) for s in desc[k] ]

			for v in desc['artifacts'].values():
				v['path'] = _string_substitute(v['path'], lut, False)
				v['base'] = _string_substitute(v['base'], lut, False)

		for v in config['buildex']['btvars'].values():
			v['value'] = _string_substitute(v['value'], lut, final)
			v['options'] = { _string_substitute(o, lut, final) for o in v['options'] }

	# If the runner is different from the default, override some of the
	# components by those defined in buildex for this runner.
	runner = config['run']['runner']
	build_components_override = config['buildex']['runners'].get(runner, {})

	for name, component in build_components_override.items():
		config['build'][name] = component

	# Compute the source and build directories for each component. If they
	# are already present, then don't override. This allows users to supply
	# their own source and build tree locations.
	for name, desc in config['build'].items():
		comp_dir = os.path.join(config['name'], name)
		if desc['sourcedir'] is None:
			desc['sourcedir'] = os.path.join(workspace.build,
							 'source',
							 comp_dir)
		if desc['builddir'] is None:
			desc['builddir'] = os.path.join(workspace.build,
							'build',
							comp_dir)
		if desc['sync'] is None:
			desc['sync'] = 'true'

	macro_lut = {
		'param': {
			**uclivars.get(**clivars),
			'configdir': lambda x: workspace.config(x, False),
		},
	}

	# Override the btvars with any values supplied by the user and check
	# that all btvars are defined.
	final_btvars = config['buildex']['btvars']

	for k, v in final_btvars.items():
		if btvars is not None:
			if k in btvars:
				v['value'] = btvars[k]
			if v['value'] is None:
				raise Exception(f'{k} build-time variable ' \
						'not set by user and no ' \
						'default available.')

		if v['type'] == 'path' and \
			v['value'] and \
			not _string_has_macros(v['value']):
			v['value'] = os.path.expanduser(v['value'])
			v['value'] = os.path.abspath(v['value'])

	macro_lut['btvar'] = {k: v['value'] for k, v in final_btvars.items()}

	# Do a first partial substitution, to resolve all macros except
	# ${artifact:*}. These macros must remain in place in order to resolve
	# the build graph. But its possible that btvars resolve to ${artifact:*}
	# so we need to do the first pass prior to resolving the build graph.
	# btvars are external to the component so they can't be used directly to
	# build the graph.
	_substitute_macros(config, macro_lut, False)

	# Now resolve the build graph, which finds ${artifact:*} users.
	graph = _resolve_build_graph(config)

	# At this point we should only have ${artifacts:*} macros remaining to
	# resolve. But there may be some cases where ${artifacts:*} resolve to
	# other ${artifacts:*}. So we need to iteratively resolve the
	# artifact_map.
	artifact_map = _resolve_artifact_map(config)
	artifact_src_map = {k: v['src'] for k, v in artifact_map.items()}
	macro_lut['artifact'] = artifact_src_map

	# Final check to ensure everything is resolved and to fix escaped $.
	_substitute_macros(config, macro_lut, True)

	for k, v in ({} if btvars is None else config['buildex']['btvars']).items():
		if not _var_validate(v):
			raise ValueError(f"{k} build-time variable " \
				f"must take one of the following values: { _var_options(v) }")

	config['graph'] = graph
	config['artifacts'] = artifact_map

	return _config_sort(config)

def _resolve_run(run, lut):
	# Now create a lookup table with all the rtvars and resolve all the
	# parameters. An exception will be thrown if there are any macros that
	# we don't have values for.
	lut['rtvar'] = {k: v['value'] for k, v in run['rtvars'].items()}

	for i, s, in enumerate(run['run']):
		run['run'][i] = _string_substitute(s, lut)

	for i, s in enumerate(run['prerun']):
		run['prerun'][i] = _string_substitute(s, lut)

def resolver(config, rtvars={}, clivars={}):
	"""
	Resolves the run-time macros (artifacts, rtvars, etc) and fixes up the
	config. Expects a config that was previously resolved with resolveb().
	"""
	clivars = uclivars.get(**clivars)
	run = config['run']

	artifacts_imp = set()
	all_runners = [run] + list(run['runners'].values())

	for runner in all_runners:
		params = runner['params'].values() if type(runner['params']) == dict else runner['params']
		# Find the list of imported artifacts before any processing passes
		_string_extract_artifacts(artifacts_imp, params)
		_string_extract_artifacts(artifacts_imp, runner['prerun'])
		_string_extract_artifacts(artifacts_imp, runner['run'])
		_string_extract_artifacts(artifacts_imp, runner['rtvars'].values())

		# Override the rtvars with any values supplied by the user and check
		# that all rtvars are defined.
		for k, v in runner['rtvars'].items():
			if k in rtvars:
				v['value'] = rtvars[k]
			if v['value'] is None:
				raise Exception(f'{k} run-time variable not ' \
						'set by user and no default available.')

	# Update the artifacts so that the destination now points to an absolute
	# path rather than one that is implictly relative to SHRINKWRAP_PACKAGE.
	# We can't do this at build-time because we don't know where the package
	# will be located at run-time.
	for k, v in config['artifacts'].items():
		if v['dst'] is None:
			if k not in artifacts_imp:
				continue
			raise Exception(f"Artifact '{k}' is required at run-time but not exported by any component")
		v['dst'] = os.path.join(workspace.package, v['dst'])

	# Create a lookup table with all the artifacts in their package
	# locations, then do substitution to fully resolve the rtvars. An
	# exception will be thrown if there are any macros that we don't have
	# values for.
	lut = {
		'param': {
			'packagedir': os.path.join(workspace.package, config['name']),
			**dict(clivars),
		},
		'artifact': {k: v['dst']
				for k, v in config['artifacts'].items()},
		'btvar': {k: v['value']
				for k, v in config['buildex']['btvars'].items()},
	}
	for runner in all_runners:
		for v in runner['rtvars'].values():
			v['value'] = _string_substitute(str(v['value']), lut)
			if v['type'] == 'path' and v['value']:
				v['value'] = os.path.expanduser(v['value'])
				v['value'] = os.path.abspath(v['value'])

			# Also check that the rtvar is well formed
			t = v.get('type')
			if t not in ('path', 'string'):
				raise Exception(f'invalid type `{t}` for run-time variable {k}')

	if run['runner'] is None:
		run['runner'] = 'FVP'
 
	# Assemble the final runtime commands and stuff them into the config.
	# For backward compatibility, run['run'] will contain the FVP command-line,
	# and run['runners'][r]['run'] contain the command-line of each of the
	# other runners.
	if run["name"]:
		terms = []
		params = _mk_params(run['params'], '=')
		for param, terminal in run['terminals'].items():
			# port_regex is deprecated; when not provided, we add an echo to
			# terminal_command then construct the regex to find it. This is
			# guarranteed to be a unique string, whereas the string output
			# by the FVP may be ambiguous for some models that have lots of
			# terminals.
			if 'port_regex' not in terminal or terminal['port_regex'] is None:
				terminal['port_regex'] = f'{param}: port (\\d+)'
				terms.append(f'-C {param}.start_telnet=1')

				cmd = f'-C {param}.terminal_command="echo {param}: port %port"'
				if terminal['type'] == 'xterm':
					cmd += '; xterm -e telnet localhost %port'
				terms.append(cmd)

				if terminal['type'] in ['telnet', 'stdinout', 'xterm']:
					terms.append(f'-C {param}.mode=telnet')
				else:
					terms.append(f'-C {param}.mode=raw')
				continue

		run['run'] = [' '.join([run["name"], params] + terms)]
	_resolve_run(run, lut)

	# Additional runners use a list of params rather than a dict
	for runner in run['runners'].values():
		if runner['name']:
			params = ' '.join(runner['params'])
			runner['run'] = [' '.join([runner['name'], params])]
		_resolve_run(runner, lut)

	return _config_sort(config)


def load_all(names, overlaynames=[]):
	"""
	Takes a list of config names and returns a corresponding list of
	loaded configs. If the input list is None or empty, all standard
	configs are loaded.
	"""
	explicit = names is not None and len(names) != 0
	configs = []

	if not explicit:
		names = []
		for p in workspace.configs():
			for root, dirs, files in os.walk(p):
				names += [os.path.relpath(
						os.path.join(root, f), p)
								for f in files]

	overlays = []
	for overlayname in overlaynames:
		overlay = filename(overlayname)
		overlay = load(overlay)
		overlay = {
			'build': overlay['build'],
			'buildex': overlay['buildex'],
			'run': overlay['run'],
		}
		overlays.append(overlay)

	for name in names:
		try:
			file = filename(name)
			merged = load(file, overlays, name)
			configs.append(merged)
		except Exception:
			if explicit:
				raise

	return configs


def load_resolveb_all(names, overlaynames=[], clivars={}, btvarss=None):
	"""
	Takes a list of config names and returns a corresponding list of
	resolved configs. If the input list is None or empty, all standard
	configs are loaded and resolved.
	"""
	configs_m = load_all(names, overlaynames)

	if btvarss is None:
		btvarss = [None] * len(configs_m)

	assert(len(configs_m) == len(btvarss))

	configs_r = []

	for merged, btvars in zip(configs_m, btvarss):
		resolved = resolveb(merged, btvars, clivars)
		configs_r.append(resolved)

	return configs_r


class Script:
	def __init__(self,
		     summary,
		     config=None,
		     component=None,
		     preamble=None,
		     final=False,
		     stderrfilt=None):
		self.summary = summary
		self.config = config
		self.component = component
		self.final = final
		self.stderrfilt = stderrfilt
		self._cmds = ''
		self._sealed = False
		self._preamble = preamble

	def append(self, *args, **kwargs):
		assert(not self._sealed)

		buf = io.StringIO()
		print(*args, **kwargs, file=buf)

		self._cmds += buf.getvalue()

	def append_multiline(self, text, *args, indent='', **kwargs):
		text = textwrap.indent(textwrap.dedent(text).strip(), indent)
		self.append(text, *args, **kwargs)

	def seal(self):
		assert(not self._sealed)
		self._sealed = True

	def preamble(self):
		return self._preamble

	def commands(self, inc_preamble=True):
		if inc_preamble:
			return self._preamble + '\n' + self._cmds
		else:
			return self._cmds

	def __eq__(self, other):
		return self.summary == other.summary and \
			self.config == other.config and \
			self.component == other.component and \
			self._cmds == other._cmds and \
			self._sealed == other._sealed

	def __hash__(self):
		assert(self._sealed)
		return hash((
			self.summary,
			self.config,
			self.component,
			self._cmds,
			self._sealed
		))

	def __repr__(self):
		return f'{self.config}:{self.component} {self.summary}'


def script_preamble(echo):
	pre = Script(None)
	pre.append(f'#!/bin/bash')
	pre.append(f'# SHRINKWRAP AUTOGENERATED SCRIPT.')
	pre.append()
	if echo:
		pre.append(f'# Exit on error and echo commands.')
		pre.append(f'set -ex')
	else:
		pre.append(f'# Exit on error.')
		pre.append(f'set -e')
	return pre.commands(False)


def script_build_preamble(echo):
	pre = Script(None)
	gitargs = '' if echo else '--quiet '
	pre.append_multiline(f'''
	# Function to update submodules without recursion
	update_submodules() {{
		local repo_path="$1"
		local reference_path="$2"

		local cwd=$(pwd)
		cd $repo_path
		# Check if .gitmodules file exists
		local gitmodules_file=".gitmodules"
		if [ -f "$gitmodules_file" ]; then
			# Extract submodule paths from .gitmodules
			git config --file "$gitmodules_file" --get-regexp path | while read -r path_key submodule_path; do
				local git_submodule_reference=""
				local submodule_reference="$reference_path/$submodule_path"

				# Check if the submodule exists in the project cache
				if [[ -n "$reference_path" && -e "$submodule_reference/.git" ]]; then
					git_submodule_reference="--reference $submodule_reference"
				fi

				if [ -d "$submodule_path" ]; then
					# Manually update nested submodules
					git submodule {gitargs} update --init --checkout --force $git_submodule_reference $submodule_path
					# Recursively process the submodule
					update_submodules "$submodule_path" "$submodule_reference"
				fi
			done
		fi
		cd $cwd
	}}''')
	return pre.commands(False)


def build_graph(configs, echo, nosync, force_sync):
	"""
	Returns a graph of scripts where the edges represent dependencies. The
	scripts should be executed according to the graph in order to correctly
	build all the configs.
	"""
	graph = {}
	gitargs = '' if echo else '--quiet '

	pre = script_preamble(echo)
	pre += script_build_preamble(echo)

	gl1 = Script('Removing old package', preamble=pre)
	gl1.append(f'# Remove old package.')
	for config in configs:
		gl1.append(f'rm -rf {workspace.package}/{config["name"]}.yaml > /dev/null 2>&1 || true')
		gl1.append(f'rm -rf {workspace.package}/{config["name"]} > /dev/null 2>&1 || true')
	gl1.seal()
	graph[gl1] = []

	gl2 = Script('Creating directory structure', preamble=pre)
	gl2.append(f'# Create directory structure.')
	for config in configs:
		dirs = set()
		for component in config['build'].values():
			dir = component["sourcedir"]
			if dir not in dirs:
				gl2.append(f'mkdir -p {dir}')
				dirs.add(dir)
		dirs = set()
		dir = os.path.join(workspace.package, config['name'])
		gl2.append(f'mkdir -p {dir}')
		dirs.add(dir)
		for artifact in config['artifacts'].values():
			if artifact['dst'] is None:
				continue
			dst = os.path.join(workspace.package, artifact['dst'])
			dir = os.path.dirname(dst)
			if dir not in dirs:
				gl2.append(f'mkdir -p {dir}')
				dirs.add(dir)
	gl2.seal()
	graph[gl2] = [gl1]

	force_sync_all = not isinstance(force_sync, list)
	sync_none = not isinstance(nosync, list)

	for config in configs:
		build_scripts = {}

		# Make copies of nosync and force_sync that we can modify below
		force_sync = set(config['build'].keys() if force_sync_all else force_sync)
		nosync = set(config['build'].keys() if sync_none else nosync)

		invalid_sync_cfg = force_sync.intersection(nosync)
		if invalid_sync_cfg:
			raise Exception(f'Conflicting sync configuration for {invalid_sync_cfg}')
		for name, component in config['build'].items():
			if component['sync'] == 'false' and name not in force_sync:
				nosync.add(name)
			elif component['sync'] == 'force' and name not in nosync:
				force_sync.add(name)

		ts = graphlib.TopologicalSorter(config['graph'])
		ts.prepare()
		while ts.is_active():
			for name in ts.get_ready():
				component = config['build'][name]

				if name not in nosync and len(component['repo']) > 0:
					g = Script('Syncing git repo', config["name"], name, preamble=pre)
					g.append(f'# Sync git repo for config={config["name"]} component={name}.')
					g.append(f'pushd {os.path.dirname(component["sourcedir"])}')

					for gitlocal, repo in component['repo'].items():
						parent = os.path.basename(component["sourcedir"])
						gitlocal = os.path.normpath(os.path.join(parent, gitlocal))
						gitremote = repo['remote']
						gitrev = repo['revision']
						git_project_cache = repo['project']
						basedir = os.path.normpath(os.path.join(gitlocal, '..'))
						sync = os.path.join(basedir, f'.{os.path.basename(gitlocal)}_sync')
						fetchrev = '' if _looks_like_abbreviated_git_sha(gitrev) else f' {gitrev}'

						project_cache_dir = workspace.project_cache
						git_local_reference=" "
						if project_cache_dir:
							if not git_project_cache:
								parsed_url  = urlparse(gitremote)
								git_project_cache = os.path.basename(parsed_url.path)

							# Lets start searching for non bare repo first
							git_project_cache = os.path.join(project_cache_dir, git_project_cache.removesuffix('.git'))
							# Search for non bare repo
							if os.path.isdir(os.path.join(git_project_cache, '.git')):
								git_local_reference = f"--reference-if-able {os.path.join(git_project_cache, '.git')} "
							# Search for a bare repo
							elif os.path.isdir(f"{git_project_cache}.git"):
								git_local_reference=f"--reference-if-able {git_project_cache}.git "
							else:
								git_project_cache = ""
						else:
							git_project_cache = ""

						if name in force_sync:
							# We don't update any submodule before `git submodule sync`,
							# to handle the case where a remote changes the submodule's URL.
							# `git checkout` handles most cases, but doesn't update a local
							# branch. So if gitrev is a branch, do a `git reset` as well.
							sync_cmd_when_exists = f'''
							git remote set-url origin {gitremote}
							git fetch {gitargs}--prune --prune-tags --force --recurse-submodules=off --tags origin{fetchrev}
							git checkout {gitargs}--force {gitrev}
							git show-ref -q --heads {gitrev} && git reset {gitargs}--hard origin/{gitrev}
							git submodule {gitargs}sync --recursive
							git submodule {gitargs}update --init --checkout --recursive --force
							'''.strip()
						else:
							sync_cmd_when_exists = f'''
							if ! git checkout {gitargs} {gitrev} > /dev/null 2>&1 &&
							   ! ( git remote set-url origin {gitremote} &&
							       git fetch {gitargs}--prune --tags origin{fetchrev} &&
							       git checkout {gitargs} {gitrev}) ||
							   ! git submodule {gitargs}update --init --checkout --recursive
							then
								echo "note: use --force-sync={name} to override any change"
								exit 1
							fi
							'''.strip()

						g.append_multiline(f'''
						if [ ! -e "{gitlocal}/.git" ] || [ -f "{sync}" ]; then
							rm -rf {gitlocal} > /dev/null 2>&1 || true
							mkdir -p {basedir}
							touch {sync}
							git clone {gitargs}{git_local_reference}{gitremote} --no-checkout {gitlocal}
							pushd {gitlocal}
							git fetch {gitargs} --tags origin{fetchrev}
							git checkout {gitargs}--force {gitrev}
							# run with --reference
							update_submodules "$(pwd)" "{git_project_cache}"
							popd
							rm {sync}
						else
							pushd {gitlocal}
							{sync_cmd_when_exists}
							popd
						fi''')
					g.append(f'popd')
					g.seal()
					graph[g] = [gl2]
				else:
					g = gl2

				b = Script('Building', config["name"], name, preamble=pre, stderrfilt=component['stderrfilt'])
				if len(component['prebuild']) + \
				   len(component['build']) + \
				   len(component['postbuild']) > 0:
					b.append(f'# Build for config={config["name"]} component={name}.')
					b.append(f'export CROSS_COMPILE={component["toolchain"] if component["toolchain"] else ""}')
					b.append(f'pushd {component["sourcedir"]}')
					for cmd in component['prebuild']:
						b.append(cmd)
					for cmd in component['build']:
						b.append(cmd)
					for cmd in component['postbuild']:
						b.append(cmd)
					b.append(f'popd')
				b.seal()
				graph[b] = [g] + [build_scripts[s] for s in config['graph'][name]]

				build_scripts[name] = b
				ts.done(name)

				a = Script('Copying artifacts', config["name"], name, preamble=pre, final=True)
				artifacts = {k: v for k, v in config['artifacts'].items() if v['component'] == name}
				if len(artifacts) > 0:
					a.append(f'# Copy artifacts for config={config["name"]} component={name}.')
					for artifact in artifacts.values():
						if artifact['dst'] is None:
							continue
						src = artifact['src']
						dst = os.path.join(workspace.package, artifact['dst'])
						# Disallow sparse copies to prevent possible file corruption when the host
						# volume is mounted into a docker container, particularly on macOS.
						a.append(f'cp -r --sparse=never {src} {dst}')
				a.seal()
				graph[a] = [b]

	return graph


def clean_graph(configs, echo):
	"""
	Returns a graph of scripts where the edges represent dependencies. The
	scripts should be executed according to the graph in order to correctly
	clean all the configs.
	"""
	graph = {}
	gitargs = '' if echo else '--quiet '

	pre = script_preamble(echo)

	gl1 = Script('Removing old package', preamble=pre)
	gl1.append(f'# Remove old package.')
	for config in configs:
		gl1.append(f'rm -rf {workspace.package}/{config["name"]}.yaml > /dev/null 2>&1 || true')
		gl1.append(f'rm -rf {workspace.package}/{config["name"]} > /dev/null 2>&1 || true')
	gl1.seal()
	graph[gl1] = []

	for config in configs:
		ts = graphlib.TopologicalSorter(config['graph'])
		ts.prepare()
		while ts.is_active():
			for name in ts.get_ready():
				component = config['build'][name]

				c = Script('Cleaning', config["name"], name, preamble=pre, final=True)
				c.append(f'# Clean for config={config["name"]} component={name}.')
				c.append(f'rm -rf {component["builddir"]} > /dev/null 2>&1 || true')
				if len(component['repo']) > 0:
					c.append(f'if [ -d "{os.path.dirname(component["sourcedir"])}" ]; then')
					c.append(f'\tpushd {os.path.dirname(component["sourcedir"])}')

					for gitlocal, repo in component['repo'].items():
						parent = os.path.basename(component["sourcedir"])
						gitlocal = os.path.normpath(os.path.join(parent, gitlocal))
						basedir = os.path.normpath(os.path.join(gitlocal, '..'))
						sync = os.path.join(basedir, f'.{os.path.basename(gitlocal)}_sync')

						c.append_multiline(f'''
						if [ -d "{gitlocal}/.git" ] && [ ! -f "{sync}" ]; then
							pushd {gitlocal}
							git clean {gitargs}-xdff
							popd
						else
							rm -rf {gitlocal} {sync} > /dev/null 2>&1 || true
						fi''', indent='\t')

					c.append(f'\tpopd')
					c.append(f'fi')
				c.seal()
				graph[c] = [gl1]

				ts.done(name)

	return graph
