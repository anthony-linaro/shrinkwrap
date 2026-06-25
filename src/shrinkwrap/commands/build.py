# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import os
import shrinkwrap.commands.buildall as buildall
import shrinkwrap.utils.vars as vars


cmd_name = os.path.splitext(os.path.basename(__file__))[0]


def add_parser(parser, formatter):
	"""
	Part of the command interface expected by shrinkwrap.py. Adds the
	subcommand to the parser, along with all options and documentation.
	Returns the subcommand name.
	"""
	cmdp = parser.add_parser(cmd_name,
		formatter_class=formatter,
		help="""Builds a specified config and packages it ready
		     to run.""",
		epilog="""Custom config store(s) can be defined at at
		     <SHRINKWRAP_CONFIG> as a colon-separated list of
		     directories. Building is done at <SHRINKWRAP_BUILD> and
		     output is saved to <SHRINKWRAP_PACKAGE>. The package
		     includes all FW binaries, a manifest and a build.sh script
		     containing all the commands that were executed per config.
		     Any pre-existing config package directory is first deleted.
		     Shrinkwrap will always search its default config store even
		     if <SHRINKWRAP_CONFIG> is not defined. <SHRINKWRAP_BUILD>
		     and <SHRINKWRAP_PACKAGE> default to '~/.shrinkwrap/build'
		     and '~/.shrinkwrap/package'. The user can override them by
		     setting the environment variables.""")

	cmdp.add_argument('config',
		metavar='config',
		help="""Config to build. If the config exists relative to the
		     current directory that config is used. Else if the config
		     exists relative to the config store then it is used.""")

	cmdp.add_argument('-b', '--btvar',
		metavar='key=value', required=False, default=[],
		action='append',
		help="""Override value for a single build-time variable defined
		     by the config. Specify option multiple times for multiple
		     variables. Overrides for variables that have a default
		     specified by the config are optional.""")

	cmdp.add_argument('-s', '--no-sync',
		metavar='component', required=False, default=[],
		action='append',
		help="""Optionally specify any components whose git repos should
		     not be synced. For all other components, Shrinkwrap ensures
		     that all repos are clean and checked out at the correct
		     revision. Option can be specified multiple times.""")

	cmdp.add_argument('--no-sync-all',
		required=False, default=False, action='store_true',
		help="""Do not sync repos for any component, as if --no-sync was
		     specified for every component in the config.""")

	cmdp.add_argument('--force-sync',
		metavar='component', required=False, default=[], action='append',
		help="""Synchronize the repo of the given component even if the local
		     source directory contains unsaved changes. YOUR CHANGES WILL BE
		     LOST! In addition, download updates from remote branches.""")

	cmdp.add_argument('--force-sync-all',
		required=False, default=False, action='store_true',
		help="""Synchronize all components even if the local source directories
		     contain unsaved changes. YOUR CHANGES WILL BE LOST! In addition,
		     download all remote branch updates. Note that this will override
		     any 'sync: false' config option.""")

	buildall.add_common_args(cmdp)

	return cmd_name


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	btvars = vars.parse(args.btvar, type='bt')
	if args.no_sync_all:
		args.no_sync = True
	if args.force_sync_all:
		args.force_sync = True
	buildall.build([args.config], [btvars], args.no_sync, args.force_sync, args)
