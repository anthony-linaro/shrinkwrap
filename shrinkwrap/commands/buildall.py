# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import os
import yaml
import shrinkwrap.utils.config as config
import shrinkwrap.utils.graph as ugraph
import shrinkwrap.utils.runtime as runtime
import shrinkwrap.utils.workspace as workspace


cmd_name = os.path.splitext(os.path.basename(__file__))[0]


def dflt_jobs():
	return min(os.cpu_count() // 2, 32)


def add_parser(parser, formatter):
	"""
	Part of the command interface expected by shrinkwrap.py. Adds the
	subcommand to the parser, along with all options and documentation.
	Returns the subcommand name.
	"""
	cmdp = parser.add_parser(cmd_name,
		formatter_class=formatter,
		help="""Builds either all concrete standard configs or an
		     explicitly specified set of configs and packages them ready
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

	cmdp.add_argument('configs',
		metavar='yamlfile',
		help="""A yaml file containing all the configs to be built. The
		     top level dictionary contains a 'configs' key, whose value
		     is a list of dictionaries, each with a 'config' key, whose
		     value is a config filename.""")

	add_common_args(cmdp)

	return cmd_name


def add_common_args(cmdp):
	"""
	Common args shared between build and buildmulti.
	"""
	cmdp.add_argument('-o', '--overlay',
		metavar='cfgfile', required=False, default=[],
		action='append',
		help="""Optional config file overlay to override run-time and
		     build-time settings. Only entries within the "build",
		     "buildex" and "run" sections are used. Applied to all
		     configs being built. Can be specified multiple times;
		     left-most overlay is the first overlay applied.""")

	cmdp.add_argument('-t', '--tasks',
		required=False, default=dflt_jobs(), metavar='count', type=int,
		help="""Maximum number of "high-level" tasks that will be
		     performed in parallel by Shrinkwrap. Tasks include syncing
		     git repositories, building components and copying
		     artifacts. Default={}""".format(dflt_jobs()))

	cmdp.add_argument('-j', '--jobs',
		required=False, default=dflt_jobs(), metavar='count', type=int,
		help="""Maximum number of low-level jobs that will be
		     performed in parallel by each component build task.
		     Default={}""".format(dflt_jobs()))

	cmdp.add_argument('-v', '--verbose',
		required=False, default=False, action='store_true',
		help="""If specified, the output from all executed commands will
		     be displayed. It is advisable to set tasks to 1 when
		     this option is selected.""")

	cmdp.add_argument('-n', '--dry-run',
		required=False, default=False, action='store_true',
		help="""If specified, <SHRINKWRAP_BUILD> and
		     <SHRINKWRAP_PACKAGE> will not be touched and none of the
		     build commands will be executed. Instead the set of
		     commands that would have been executed are output to stdout
		     as a bash script.""")

	cmdp.add_argument('-c', '--no-color',
		required=False, default=False, action='store_true',
		help="""If specified, logs will not be colorized.""")


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	with open(args.configs) as file:
		cfgs = yaml.safe_load(file)

	configs = [c['config'] for c in cfgs['configs']]
	btvarss = [c['btvars'] for c in cfgs['configs']]
	build(configs, btvarss, [], args)


def build(configs, btvarss, nosync, args):
	"""
	Concurrently builds a list of configs. Intended to be called as a common
	handler for the build and buildmulti commands.
	"""
	clivars = {'jobs': args.jobs}
	configs = config.load_resolveb_all(configs, args.overlay, clivars, btvarss)
	graph = config.build_graph(configs, args.verbose, nosync)

	if args.dry_run:
		script = ugraph.make_script(graph)
		print(script)
	else:
		if args.verbose:
			workspace.dump()

		# Run under a runtime environment, which may just run commands
		# natively on the host or may execute commands in a container,
		# depending on what the user specified.
		with runtime.Runtime(args.runtime, args.image) as rt:
			def add_volume(path, levels_up=0):
				while levels_up:
					path = os.path.dirname(path)
					levels_up -= 1
				os.makedirs(path, exist_ok=True)
				rt.add_volume(path)

			add_volume(workspace.build)
			add_volume(workspace.package)
			for c in workspace.configs():
				add_volume(c)

			for conf in configs:
				for comp in conf['build'].values():
					add_volume(comp['sourcedir'], 1)
					add_volume(comp['builddir'])

				for btvar in conf['buildex']['btvars'].values():
					if btvar['type'] == 'path':
						rt.add_volume(btvar['value'])

			rt.start()

			ugraph.execute(graph,
				       args.tasks,
				       args.verbose,
				       not args.no_color)

		for c in configs:
			# Dump the config.
			cfg_name = os.path.join(workspace.package,
						f'{c["name"]}.yaml')
			with open(cfg_name, 'w') as cfg:
				config.dump(c, cfg)

			# Dump the script to build the config.
			graph = config.build_graph([c], args.verbose, nosync)
			script = ugraph.make_script(graph)
			build_name = os.path.join(workspace.package,
						  c['name'],
						  'build.sh')
			with open(build_name, 'w') as build:
				build.write(script)
