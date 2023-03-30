# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import os
import shrinkwrap.utils.config as config
import shrinkwrap.utils.rtvars as rtvars


cmd_name = os.path.splitext(os.path.basename(__file__))[0]


def add_parser(parser, formatter):
	"""
	Part of the command interface expected by shrinkwrap.py. Adds the
	subcommand to the parser, along with all options and documentation.
	Returns the subcommand name.
	"""
	cmdp = parser.add_parser(cmd_name,
		formatter_class=formatter,
		help="""Outputs to stdout the result of either merging down the
		     config layers, or resolving macros within the merged
		     config.""",
		epilog="""Custom config store(s) can be defined at at
		     <SHRINKWRAP_CONFIG> as a colon-separated list of
		     directories. Shrinkwrap will always search its default
		     config store even if <SHRINKWRAP_CONFIG> is not
		     defined.""")

	cmdp.add_argument('config',
		metavar='config',
		help="""Config to process. If the config exists relative to the
		     current directory that config is used. Else if the config
		     exists relative to the config store then it is used.""")

	cmdp.add_argument('-a', '--action',
		metavar='action', required=True,
		choices=['merge', 'resolveb', 'resolver'],
		help="""Action to take. Either "merge" (merge down the config
		     layers), "resolveb" (resolve build-time macros within the
		     merged config) or "resolver" (resolve run-time macros
		     within the build-time resolved config).""")

	cmdp.add_argument('-o', '--overlay',
		metavar='cfgfile', required=False, default=[],
		action='append',
		help="""Optional config file overlay to override run-time and
		     build-time settings. Only entries within the "build" and
		     "run" sections are used. Can be specified multiple times;
		     left-most overlay is the first overlay applied.""")

	cmdp.add_argument('-r', '--rtvar',
		metavar='key=value', required=False, default=[],
		action='append',
		help="""Override value for a single runtime variable defined by
		     the config. Specify option multiple times for multiple
		     variables. Overrides for variables that have a default
		     specified by the config are optional. Only used if action
		     is "resolver".""")

	return cmd_name


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	overlays = []
	for overlayname in args.overlay:
		overlay = config.filename(overlayname)
		overlay = config.load(overlay)
		overlay = {'build': overlay['build'], 'run': overlay['run']}
		overlays.append(overlay)

	filename = config.filename(args.config)
	merged = config.load(filename, overlays)

	if args.action == 'merge':
		print(config.dumps(merged))
	else:
		resolveb = config.resolveb(merged)

		if args.action == 'resolveb':
			print(config.dumps(resolveb))
		else:
			rtvars_dict = rtvars.parse(args.rtvar)
			resolver = config.resolver(resolveb, rtvars_dict)

			if args.action == 'resolver':
				print(config.dumps(resolver))
