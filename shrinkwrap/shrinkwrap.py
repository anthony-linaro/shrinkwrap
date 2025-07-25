#!/usr/bin/env python3
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT


# Fixup PythonPath to avoid confusion between (this) module and package.
import sys
import os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if os.path.basename(p) != 'shrinkwrap']
sys.path = [root] + sys.path


import argparse
import shutil
from shrinkwrap import __version__


from shrinkwrap.commands import build
from shrinkwrap.commands import buildall
from shrinkwrap.commands import clean
from shrinkwrap.commands import inspect
from shrinkwrap.commands import process
from shrinkwrap.commands import run


VERBOSE = True


def config_verbose_flag(args):
	global VERBOSE
	# Not all commands (e.g. run) have --verbose. Choose not to change
	# behavior in that case.
	if 'verbose' in args:
		VERBOSE = args.verbose
	else:
		VERBOSE = False


def formatter(prog):
	width = shutil.get_terminal_size().columns
	width -= 2
	width = min(80, width)
	return argparse.HelpFormatter(prog, width=width)


def main():
	"""
	Main entry point. Parses command line and dispatches to appropriate
	command handler.
	"""

	def inner():
		tool_name = os.path.splitext(os.path.basename(__file__))[0]

		# Parse the arguments. The parser will raise an exception if the
		# required arguments are not present, which will tell the user what they
		# did wrong.

		parser = argparse.ArgumentParser(epilog='To file a bug report, contact '
							'<ryan.roberts@arm.com>.',
						 formatter_class=formatter)

		parser.add_argument('--version',
			action='version',
			version=f'{tool_name} v{__version__}')

		parser.add_argument('-R', '--runtime',
			metavar='engine', required=False, default='docker',
			choices=['null', 'docker', 'docker-local', 'podman', 'podman-local'],
			help="""Specifies the environment in which to execute build and
				 run commands. If 'null', executes natively on the host.
				 'docker' attempts to download the image from dockerhub and
				 execute the commands in a container. 'docker-local' is like
				 'docker' but will only look for the image locally. 'podman'
				 and 'podman-local' are like 'docker' and 'docker-local'
				 except podman is used as the runtime instead of docker.
				 Defaults to 'docker'.""")

		parser.add_argument('-I', '--image',
			metavar='name',
			required=False,
			type=str,
			default=None,
			help="""If using a container runtime, specifies the name of the
				 image to use. Defaults to the official shrinkwrap image,
				 unless a specific image is required in the config file.""")

		parser.add_argument('--ssh-agent',
			default=False,
			action='store_true',
			required=False,
			help="""Start ssh-agent and add default keys.""")

		parser.add_argument('--ssh-agent-key',
			dest='ssh_agent_keys',
			default=[],
			metavar='key',
			action='append',
			type=str,
			required=False,
			help="""Start ssh-agent and add specified key.""")

		subparsers = parser.add_subparsers(dest='command',
						   metavar='<command>',
						   title=f'Supported commands (run '
							 f'"{tool_name} <command> '
							 f'--help" for more info)')

		# Register all the commands.
		cmds = {}
		cmds[build.add_parser(subparsers, formatter)] = build
		cmds[buildall.add_parser(subparsers, formatter)] = buildall
		cmds[clean.add_parser(subparsers, formatter)] = clean
		cmds[inspect.add_parser(subparsers, formatter)] = inspect
		cmds[process.add_parser(subparsers, formatter)] = process
		cmds[run.add_parser(subparsers, formatter)] = run

		# Parse the arguments.
		args = parser.parse_args()
		config_verbose_flag(args)

		if args.ssh_agent:
			args.ssh_agent_keys.append(None)

		# Dispatch to the correct command.
		if args.command in cmds:
			cmds[args.command].dispatch(args)
		else:
			print(f'Unknown command {args.command}')
			parser.print_help()

	try:
		inner()
	except SystemExit as e:
		raise
	except BaseException as e:
		if VERBOSE:
			raise
		print(f'{e.__class__.__name__}: {e}')
		exit(1)

if __name__ == "__main__":
	main()
