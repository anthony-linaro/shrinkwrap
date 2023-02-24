# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import graphlib
import io
import os
import re
import yaml
import shrinkwrap.utils.clivars as uclivars
import shrinkwrap.utils.workspace as workspace


def _component_normalize(component, name):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	if 'repo' not in component:
		component['repo'] = {}

	if len(component['repo']) > 0 and \
		all(type(v) != dict for v in component['repo'].values()):
		component['repo'] = {'.': component['repo']}

	for repo in component['repo'].values():
		if 'remote' not in repo:
			repo['remote'] = None

		if 'revision' not in repo:
			repo['revision'] = None

	if 'sourcedir' not in component:
		component['sourcedir'] = None

	if 'builddir' not in component:
		component['builddir'] = None

	if 'toolchain' not in component:
		component['toolchain'] = None

	if 'prebuild' not in component:
		component['prebuild'] = []

	if 'build' not in component:
		component['build'] = []

	if 'postbuild' not in component:
		component['postbuild'] = []

	if 'clean' not in component:
		component['clean'] = []

	if 'params' not in component:
		component['params'] = {}

	if 'artifacts' not in component:
		component['artifacts'] = {}

	return component


def _build_normalize(build):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	if len(build) == 0:
		build['__dummy'] = {}

	for name, component in build.items():
		_component_normalize(component, name)


def _run_normalize(run):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	if 'name' not in run:
		run['name'] = None

	if 'rtvars' not in run:
		run['rtvars'] = {}

	if 'params' not in run:
		run['params'] = {}

	if 'prerun' not in run:
		run['prerun'] = []

	if 'run' not in run:
		run['run'] = []

	if 'terminals' not in run:
		run['terminals'] = {}


def _config_normalize(config):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	if 'name' not in config:
		config['name'] = None

	if 'fullname' not in config:
		config['fullname'] = None

	if 'description' not in config:
		config['description'] = None

	if 'concrete' not in config:
		config['concrete'] = False

	if 'layers' not in config:
		config['layers'] = []

	if 'graph' not in config:
		config['graph'] = {}

	if 'build' not in config:
		config['build'] = {}

	_build_normalize(config['build'])

	if 'artifacts' not in config:
		config['artifacts'] = {}

	if 'run' not in config:
		config['run'] = {}

	_run_normalize(config['run'])

	return config


def _config_validate(config):
	"""
	Ensures the config conforms to the schema. Throws exception if any
	issues are found.
	"""
	# TODO:


def _component_sort(component):
	"""
	Sort the component so that the keys are in a canonical order. This
	improves readability by humans.
	"""
	lut = ['repo', 'sourcedir', 'builddir', 'toolchain', 'params',
			'prebuild', 'build', 'postbuild', 'clean', 'artifacts']
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
	lut = ['name', 'rtvars', 'params', 'prerun', 'run', 'terminals']
	lut = {k: i for i, k in enumerate(lut)}
	return dict(sorted(run.items(), key=lambda x: lut[x[0]]))


def _config_sort(config):
	"""
	Sort the config so that the keys are in a canonical order. This improves
	readability by humans.
	"""
	config['build'] = _build_sort(config['build'])
	config['run'] = _run_sort(config['run'])

	lut = ['name', 'fullname', 'description', 'concrete', 'layers',
			'graph', 'build', 'artifacts', 'run']
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

		if type(base) is list and type(new) is list:
			return base + new

		if type(base) is dict and type(new) is dict:
			d = {}
			for k in list(base.keys()) + list(new.keys()):
				d[k] = _merge(base.get(k), new.get(k), level+1)
			return d

		if type(base) is str and type(new) is str:
			return new

		return new

	config = _merge(base, new)

	# We add a dummy component if there are no others. After merging, if
	# there other components, remove it.
	if '__dummy' in config['build'] and len(config['build']) > 1:
		del config['build']['__dummy']

	return config


def _string_tokenize(string):
	"""
	Returns ordered list of tokens, where each token has a 'type' and
	'value'. If 'type' is 'literal', 'value' is the literal string. If
	'type' is 'macro', 'value' is a dict defining 'type' and 'name'.
	"""
	regex = '\$(?:' \
			'(?P<escape>\$)|' \
			'(?:\{' \
				'(?P<type>[_a-zA-Z][_a-zA-Z0-9]*):' \
				'(?P<name>[_a-zA-Z][_a-zA-Z0-9]*)?' \
			'\})|' \
			'(?P<invalid>)' \
		')'
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
			tokens.append({
				'type': 'literal',
				'value': m['escape'],
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


def _string_substitute(string, lut, partial=False):
	"""
	Takes a string containg macros and returns a string with the macros
	substituted for the values found in the lut. If partial is True, any
	macro that does not have a value in the lut will be left as a macro in
	the returned string. If partial is False, any macro that does not have a
	value in the lut will cause an interrupt.
	"""
	calls = []
	frags = []
	frag = ''
	tokens = _string_tokenize(string)

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
			except KeyError:
				if partial:
					frag += f"${{{m['type']}:{m['name']}}}"
				else:
					raise

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


def _mk_params(params, separator):
	pairs = [f'{k}' if v is None else f'{k}{separator}{v}'
						for k, v in params.items()]
	return ' '.join(pairs)


def filename(name, rel=os.getcwd()):
	"""
	Given a config name, finds the path to the config on disk. If the config
	name exists relative to rel, we return that since it is a user config.
	Else, if the config name exists relative to the config store then we
	return that. If neither exist, then we return the filepath option, since
	that will generate the most useful error.
	"""
	fpath = os.path.abspath(os.path.join(rel, name))
	cpath = workspace.config(name)

	if os.path.exists(fpath):
		return fpath
	elif cpath:
		return os.path.abspath(os.path.join(cpath, name))
	else:
		return fpath


def load(file_name, overlay=None, friendly=None):
	"""
	Load a config from disk and return it as a dictionary. The config is
	fully normalized, validated and merged.
	"""
	def _config_load(file_name):
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

	if overlay:
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


def resolveb(config, clivars={}):
	"""
	Resolves the build-time macros (params, artifacts, etc) and fixes up the
	config. Based on the artifact dependencies, the component build graph is
	determined and placed into the config along with the global artifact
	map. Expects a config that was previously loaded with load().
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
			macros = []

			for s in component['params'].values():
				tokens = _string_tokenize(str(s))
				macros += [t['value'] for t in tokens if t['type'] == 'macro']

			for m in macros:
				if m['type'] != 'artifact':
					raise Exception(f"'{name}' uses macro of type '{m['type']}'. Components must only use 'artifact' macros.")
				if m['name'] is None:
					raise Exception(f"'{name}' uses unnamed 'artifact' macro. 'artifact' macros must be named.")
				artifacts.add(m['name'])

			for scope in ['prebuild', 'build', 'postbuild', 'clean']:
				for s in component[scope]:
					for t in _string_tokenize(str(s)):
						if t['type'] != 'macro':
							continue
						m = t['value']
						if m['type'] != 'artifact':
							continue
						if m['name'] is None:
							raise Exception(f"'{name}' uses unnamed 'artifact' macro. 'artifact' macros must be named.")
						artifacts.add(m['name'])

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
				dependee = artifacts_exp[dep]
				graph[depender].append(dependee)

		return graph

	def _resolve_artifact_map(config):

		artifact_map = {}

		for desc in config['build'].values():
			lut = {
				'param': {
					'sourcedir': desc['sourcedir'],
					'builddir': desc['builddir'],
					'configdir': lambda x: workspace.config(x, False),
				},
			}

			for key, val in desc['artifacts'].items():
				desc['artifacts'][key] = _string_substitute(val, lut)

			locs = {key: {
				'src': val,
				'dst': os.path.join(config['name'], os.path.basename(val)),
			} for key, val in desc['artifacts'].items()}

			artifact_map.update(locs)

		return artifact_map

	def _substitute_macros(config, artifacts, clivars):
		for desc in config['build'].values():
			lut = {
				'artifact': artifacts,
				'param': {
					**clivars,
					'sourcedir': desc['sourcedir'],
					'builddir': desc['builddir'],
					'configdir': lambda x: workspace.config(x, False),
				},
			}

			for k in desc['params']:
				v = desc['params'][k]
				if v:
					desc['params'][k] = _string_substitute(str(v), lut)

			lut['param']['join_equal'] = _mk_params(desc['params'], '=')
			lut['param']['join_space'] = _mk_params(desc['params'], ' ')

			for i, s in enumerate(desc['prebuild']):
				desc['prebuild'][i] = _string_substitute(s, lut)
			for i, s in enumerate(desc['build']):
				desc['build'][i] = _string_substitute(s, lut)
			for i, s in enumerate(desc['postbuild']):
				desc['postbuild'][i] = _string_substitute(s, lut)
			for i, s in enumerate(desc['clean']):
				desc['clean'][i] = _string_substitute(s, lut)

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

	graph = _resolve_build_graph(config)
	artifact_map = _resolve_artifact_map(config)
	artifact_src_map = {k: v['src'] for k, v in artifact_map.items()}
	clivars = uclivars.get(**clivars)
	_substitute_macros(config, artifact_src_map, clivars)

	config['graph'] = graph
	config['artifacts'] = artifact_map

	return _config_sort(config)


def resolver(config, rtvars={}, clivars={}):
	"""
	Resolves the run-time macros (artifacts, rtvars, etc) and fixes up the
	config. Expects a config that was previously resolved with resolveb().
	"""
	clivars = uclivars.get(**clivars)
	run = config['run']

	#Override the rtvars with any values supplied by the user and check that
	#all rtvars are defined.
	for k in run['rtvars']:
		if k in rtvars:
			run['rtvars'][k]['value'] = rtvars[k]
	for k, v in run['rtvars'].items():
		if v['value'] is None:
			raise Exception(f'{k} run-time variable not ' \
					'set by user and no default available.')

	# Update the artifacts so that the destination now points to an absolute
	# path rather than one that is implictly relative to SHRINKWRAP_PACKAGE.
	# We can't do this at build-time because we don't know where the package
	# will be located at run-time.
	for k in config['artifacts']:
		v = config['artifacts'][k]
		v['dst'] = os.path.join(workspace.package, v['dst'])

	# Create a lookup table with all the artifacts in their package
	# locations, then do substitution to fully resolve the rtvars. An
	# exception will be thrown if there are any macros that we don't have
	# values for.
	lut = {
		'param': {
			**dict(clivars),
		},
		'artifact': {k: v['dst']
				for k, v in config['artifacts'].items()},
	}
	for k in run['rtvars']:
		v = run['rtvars'][k]
		v['value'] = _string_substitute(str(v['value']), lut)
		if v['type'] == 'path' and v['value']:
			v['value'] = os.path.expanduser(v['value'])
			v['value'] = os.path.abspath(v['value'])

	# Now create a lookup table with all the rtvars and resolve all the
	# parameters. An exception will be thrown if there are any macros that
	# we don't have values for.
	lut['rtvar'] = {k: v['value'] for k, v in run['rtvars'].items()}

	for k in run['params']:
		v = run['params'][k]
		if v:
			run['params'][k] = _string_substitute(str(v), lut)

	# Assemble the final runtime command and stuff it into the config.
	params = _mk_params(run['params'], '=')

	terms = []
	for param, terminal in run['terminals'].items():
		if terminal['type'] in ['stdout']:
			terms.append(f'-C {param}.start_telnet=0')
			terms.append(f'-C {param}.mode=raw')
		if terminal['type'] in ['xterm']:
			terms.append(f'-C {param}.start_telnet=1')
			terms.append(f'-C {param}.mode=telnet')
		if terminal['type'] in ['telnet', 'stdinout']:
			terms.append(f'-C {param}.start_telnet=0')
			terms.append(f'-C {param}.mode=telnet')
	terms = ' '.join(terms)

	if run["name"]:
		run['run'] = [' '.join([run["name"], params, terms])]

	for i, s in enumerate(run['prerun']):
		run['prerun'][i] = _string_substitute(s, lut)

	return _config_sort(config)


def load_resolveb_all(names, overlayname=None, clivars={}):
	"""
	Takes a list of config names and returns a corresponding list of
	resolved configs. If the input list is None or empty, all standard
	configs are loaded and resolved.
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

	overlay = None
	if overlayname:
		overlay = filename(overlayname)
		overlay = load(overlay)
		overlay = {'build': overlay['build'], 'run': overlay['run']}

	for name in names:
		try:
			file = filename(name)
			merged = load(file, overlay, name)
			resolved = resolveb(merged, clivars)
			configs.append(resolved)
		except Exception:
			if explicit:
				raise

	return configs


class Script:
	def __init__(self,
		     summary,
		     config=None,
		     component=None,
		     preamble=None,
		     final=False):
		self.summary = summary
		self.config = config
		self.component = component
		self.final = final
		self._cmds = ''
		self._sealed = False
		self._preamble = preamble

	def append(self, *args, **kwargs):
		assert(not self._sealed)

		buf = io.StringIO()
		print(*args, **kwargs, file=buf)

		self._cmds += buf.getvalue()

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


def build_graph(configs, echo):
	"""
	Returns a graph of scripts where the edges represent dependencies. The
	scripts should be executed according to the graph in order to correctly
	build all the configs.
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
			dst = os.path.join(workspace.package, artifact['dst'])
			dir = os.path.dirname(dst)
			if dir not in dirs:
				gl2.append(f'mkdir -p {dir}')
				dirs.add(dir)
	gl2.seal()
	graph[gl2] = [gl1]

	for config in configs:
		build_scripts = {}

		ts = graphlib.TopologicalSorter(config['graph'])
		ts.prepare()
		while ts.is_active():
			for name in ts.get_ready():
				component = config['build'][name]

				g = Script('Syncing git repo', config["name"], name, preamble=pre)
				if len(component['repo']) > 0:
					g.append(f'# Sync git repo for config={config["name"]} component={name}.')
					g.append(f'pushd {os.path.dirname(component["sourcedir"])}')

					for gitlocal, repo in component['repo'].items():
						parent = os.path.basename(component["sourcedir"])
						gitlocal = os.path.normpath(os.path.join(parent, gitlocal))
						gitremote = repo['remote']
						gitrev = repo['revision']
						basedir = os.path.normpath(os.path.join(gitlocal, '..'))
						sync = os.path.join(basedir, f'.{os.path.basename(gitlocal)}_sync')

						g.append(f'if [ ! -d "{gitlocal}/.git" ] || [ -f "{sync}" ]; then')
						g.append(f'\trm -rf {gitlocal} > /dev/null 2>&1 || true')
						g.append(f'\tmkdir -p {basedir}')
						g.append(f'\ttouch {sync}')
						g.append(f'\tgit clone {gitargs}{gitremote} {gitlocal}')
						g.append(f'\tpushd {gitlocal}')
						g.append(f'\tgit checkout {gitargs}--force {gitrev}')
						g.append(f'\tgit submodule {gitargs}update --init --checkout --recursive --force')
						g.append(f'\tpopd')
						g.append(f'\trm {sync}')
						g.append(f'fi')

					g.append(f'popd')
				g.seal()
				graph[g] = [gl2]

				b = Script('Building', config["name"], name, preamble=pre)
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

		a = Script('Copying artifacts', config["name"], preamble=pre, final=True)
		if len(config['artifacts']) > 0:
			a.append(f'# Copy artifacts for config={config["name"]}.')
			for artifact in config['artifacts'].values():
				src = artifact['src']
				dst = os.path.join(workspace.package, artifact['dst'])
				a.append(f'cp {src} {dst}')
		a.seal()
		graph[a] = [gl2] + [s for s in build_scripts.values()]

	return graph


def clean_graph(configs, echo, clean_repo):
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

				c = Script('Cleaning', config["name"], name, preamble=pre)
				c.append(f'# Clean for config={config["name"]} component={name}.')
				if len(component['clean']) > 0:
					c.append(f'export CROSS_COMPILE={component["toolchain"] if component["toolchain"] else ""}')
					c.append(f'if [ -d "{component["sourcedir"]}" ]; then')
					c.append(f'\tpushd {component["sourcedir"]}')
					for cmd in component['clean']:
						c.append(f'\t{cmd}')
					c.append(f'\tpopd')
					c.append(f'fi')
				c.append(f'rm -rf {component["builddir"]} > /dev/null 2>&1 || true')
				c.seal()
				graph[c] = [gl1]

				if clean_repo:
					g = Script('Cleaning git repo', config["name"], name, preamble=pre)
					if len(component['repo']) > 0:
						g.append(f'# Clean git repo for config={config["name"]} component={name}.')
						g.append(f'if [ -d "{os.path.dirname(component["sourcedir"])}" ]; then')
						g.append(f'\tpushd {os.path.dirname(component["sourcedir"])}')

						for gitlocal, repo in component['repo'].items():
							parent = os.path.basename(component["sourcedir"])
							gitlocal = os.path.normpath(os.path.join(parent, gitlocal))
							basedir = os.path.normpath(os.path.join(gitlocal, '..'))
							sync = os.path.join(basedir, f'.{os.path.basename(gitlocal)}_sync')

							g.append(f'\tif [ -d "{gitlocal}/.git" ] && [ ! -f "{sync}" ]; then')
							g.append(f'\t\tpushd {gitlocal}')
							g.append(f'\t\tgit clean {gitargs}-xdff')
							g.append(f'\t\tgit reset {gitargs}--hard')
							g.append(f'\t\tpopd')
							g.append(f'\tfi')

						g.append(f'\tpopd')
						g.append(f'fi')
					g.seal()
					graph[g] = [c]

				ts.done(name)

	return graph
