# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import json
import io
import os
import re
import textwrap
import shrinkwrap.utils.config as config


cmd_name = os.path.splitext(os.path.basename(__file__))[0]


def add_parser(parser, formatter):
	"""
	Part of the command interface expected by shrinkwrap.py. Adds the
	subcommand to the parser, along with all options and documentation.
	Returns the subcommand name.
	"""
	cmdp = parser.add_parser(cmd_name,
		formatter_class=formatter,
		help="""Outputs to stdout info about either all concrete
		     standard configs or an explicitly specified set of configs.
		     Info includes name, description and runtime variables with
		     their default values.""",
		epilog="""Custom config store(s) can be defined at at
		     <SHRINKWRAP_CONFIG> as a colon-separated list of
		     directories. Shrinkwrap will always search its default
		     config store even if <SHRINKWRAP_CONFIG> is not
		     defined.""")

	cmdp.add_argument('configs',
		metavar='config', nargs='*',
		help="""0 or more configs to inspect. If a config exists
		     relative to the current directory that config is used. Else
		     if a config exists relative to the config store then it is
		     used. If no configs are provided, all concrete configs
		     in the config store are built.""")

	cmdp.add_argument('-a', '--all',
		required=False, default=False, action='store_true',
		help="""If specified, and no configs were explicitly provided,
		     lists all standard configs rather than just the concrete
		     ones.""")

	cmdp.add_argument('-j', '--json',
		required=False, default=False, action='store_true',
		help="""If specified, output is in json.""")

	return cmd_name


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	configs = config.load_all(args.configs)

	cfgs = []
	for c in sorted(configs, key=lambda c: c['fullname']):
		if len(args.configs) == 0 and not args.all and not c['concrete']:
			continue

		cfgs.append({
			'name': c['fullname'],
			'description': c['description'],
			'image': c['image'] if c['image'] is not None else '<none>',
			'concrete': c['concrete'],
			'btvars': c['buildex']['btvars'],
			'rtvars': c['run']['rtvars'],
			'components': _comp_revisions(c['build']),
		})

	if args.json:
		print(json.dumps(cfgs, indent=4, cls=config.JSONdump))
		return

	width = 80
	indent = 21
	vindent = 24

	descs = []
	for c in cfgs:
		buf = io.StringIO()

		buf.write(_text_wrap('name',
				     c['name'],
				     width=width,
				     indent=indent,
				     paraspace=1))
		buf.write('\n')
		buf.write(_text_wrap('description',
				     c['description'],
				     width=width,
				     indent=indent,
				     paraspace=1))
		buf.write('\n')
		buf.write(_text_wrap('image',
				     c['image'],
				     width=width,
				     indent=indent,
				     paraspace=1))
		buf.write('\n')
		buf.write(_text_wrap('concrete',
				     c['concrete'],
				     width=width,
				     indent=indent,
				     paraspace=1))
		buf.write('\n')
		buf.write(_vars_wrap('build-time vars',
				     c['btvars'],
				     width=width,
				     kindent=indent,
				     vindent=vindent))
		buf.write('\n')
		buf.write(_vars_wrap('run-time vars',
				     c['rtvars'],
				     width=width,
				     kindent=indent,
				     vindent=vindent))
		buf.write('\n')
		buf.write(_repo_wrap('components',
				     c['components'],
				     width=width,
				     kindent=indent,
				     vindent=vindent))

		descs.append(buf.getvalue())

	separator = '\n' + ('-' * width) + '\n\n'
	all = separator.join(descs)
	print(all)


def _var_value(value):
	if value is None:
		return '<null>'
	if value == '':
		return '<empty>'
	return str(value)


def _comp_revisions(components):
	revs = {}
	for comp in sorted(components.keys()):
		for repo in sorted(components[comp]['repo'].keys()):
			name = comp if repo == '.' else f"{comp} ({repo})"
			revision = components[comp]['repo'][repo]['revision']
			remote = components[comp]['repo'][repo]['remote']
			revs[name] = {
				'repository': remote,
				'revision': revision,
			}
	return revs


def _text_wrap(tag, text, width=80, indent=0, paraspace=1, end='\n'):
	text = str(text)
	tag = str(tag)
	indent_pattern = ' ' * indent

	lines = [textwrap.fill(l,
			       width=width,
			       initial_indent=indent_pattern,
			       subsequent_indent=indent_pattern)
		for l in text.splitlines() if l]

	wrapped = ('\n' * (paraspace + 1)).join(lines)

	if tag:
		if len(tag) > indent - 2:
			wrapped = f'{tag}:\n' + wrapped
		else:
			wrapped = f'{tag}:' + wrapped[len(tag) + 1:]

	return wrapped + end


def _dict_wrap(tag, dictionary, width=80, kindent=0, vindent=0, end='\n'):
	if len(dictionary) == 0:
		lines = [str(None)]
	else:
		dwidth = width - kindent
		lines = []

		for k, v in dictionary.items():
			line = _text_wrap(k,
					  v,
					  width=dwidth,
					  indent=vindent,
					  paraspace=0,
					  end='')
			lines.append(line)

	dtext = '\n'.join(lines)

	return _text_wrap(tag,
			  dtext,
			  width=width,
			  indent=kindent,
			  paraspace=0,
			  end=end)


def _var_options(_opt):
	if len(_opt) == 0:
		return "<required>"
	else:
		return list(map(_var_value, _opt))

def _vars_wrap(tag, vars, width=80, kindent=0, vindent=0, end='\n'):
	vars_indent = 0
	for var in vars.values():
		vars_indent = max(vars_indent, len(var['value']))
	vars_indent += 2

	dictionary = {
		k:	f"{ _var_value(v['value']) }"
			f"{ ' ' * (vars_indent - len(v['value'])) }"
			f"{ _var_options(v['options']) }"
		for k, v in vars.items() }

	return _dict_wrap(tag, dictionary, 10000, kindent, vindent, end)


def _repo_wrap(tag, components, width=80, kindent=0, vindent=0, end='\n'):
	def is_git_sha(s):
		return bool(re.fullmatch(r"[0-9a-f]{40}", s))

	repo_indent = 0
	for info in components.values():
		rev = info['revision']
		if is_git_sha(rev):
			rev = rev[:12]
		repo_indent = max(repo_indent, len(rev))
	repo_indent += 2

	dictionary = {}
	for comp, info in components.items():
		repo = info['repository']
		rev = info['revision']
		if is_git_sha(rev):
			rev = rev[:12]
		value = f"{rev}{' ' * (repo_indent - len(rev))}{repo}"
		dictionary[comp] = value

	return _dict_wrap(tag, dictionary, 10000, kindent, vindent, end)
