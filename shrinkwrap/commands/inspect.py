# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import io
import os
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

	return cmd_name


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	configs = config.load_resolveb_all(args.configs)

	width = 80
	indent = 21
	vindent = 24

	descs = []
	for c in sorted(configs, key=lambda c: c['fullname']):
		if len(args.configs) == 0 and not args.all and not c['concrete']:
			continue

		buf = io.StringIO()

		buf.write(_text_wrap('name',
				     c['fullname'],
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
		buf.write(_text_wrap('concrete',
				     c['concrete'],
				     width=width,
				     indent=indent,
				     paraspace=1))
		buf.write('\n')
		rtvars = {k: _var_value(v['value'])
	    				for k,v in c['run']['rtvars'].items()}
		buf.write(_dict_wrap('run-time variables',
				     rtvars,
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
