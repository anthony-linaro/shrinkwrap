# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import os
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
		help="""Cleans either all concrete standard configs or an
		     explicitly specified set of configs, ready to be rebuilt
		     from scratch.""")

	cmdp.add_argument('configs',
		metavar='config', nargs='*',
		help="""0 or more configs to clean. If a config exists relative
		     to the current directory that config is used. Else if a
		     config exists relative to the config store then it is used.
		     If no configs are provided, all concrete configs in the
		     config store are cleaned.""")

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
		     performed in parallel by Shrinkwrap. Tasks include cleaning
		     components. Default={}""".format(dflt_jobs()))

	cmdp.add_argument('-j', '--jobs',
		required=False, default=dflt_jobs(), metavar='count', type=int,
		help="""Maximum number of low-level jobs that will be
		     performed in parallel by each component clean task.
		     Default={}""".format(dflt_jobs()))

	cmdp.add_argument('-v', '--verbose',
		required=False, default=False, action='store_true',
		help="""If specified, the output from all executed commands will
		     be displayed. It is advisable to set tasks to 1 when
		     this option is selected.""")

	cmdp.add_argument('-n', '--dry-run',
		required=False, default=False, action='store_true',
		help="""If specified, none of the clean commands will be
		     executed. Instead the set of commands that would have been
		     executed are output to stdout as a bash script.""")

	cmdp.add_argument('-c', '--no-color',
		required=False, default=False, action='store_true',
		help="""If specified, logs will not be colorized.""")

	cmdp.add_argument('-f', '--filter',
		metavar='[config.]component', required=False, default=[],
		action='append',
		help="""Optionally specify the components to clean. Option can
		     be specified multiple times to clean multiple components.
		     If not specified, all components are cleaned. If 'config.'
		     is omitted, component is cleaned for all configs being
		     cleaned (component must exist in all configs being
		     cleaned).""")

	return cmd_name


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	clivars = {'jobs': args.jobs}
	configs = config.load_resolveb_all(args.configs, args.overlay, clivars)
	if len(args.configs) == 0:
		configs = [c for c in configs if c['concrete']]
	for conf in configs:
		conf['graph'] = _filter(conf['name'],
					conf['graph'],
					args.filter)

	graph = config.clean_graph(configs, args.verbose)

	if args.dry_run:
		script = ugraph.make_script(graph)
		print(script)
	else:
		if args.verbose:
			workspace.dump()

		# Run under a runtime environment, which may just run commands
		# natively on the host or may execute commands in a container,
		# depending on what the user specified.
		with runtime.Runtime(name=args.runtime, image=args.image,
		       			ssh_agent_keys=args.ssh_agent_keys) as rt:
			def add_volume(path, levels_up=0):
				while levels_up:
					path = os.path.dirname(path)
					levels_up -= 1
				os.makedirs(path, exist_ok=True)
				rt.add_volume(path)

			add_volume(workspace.build)
			add_volume(workspace.package)

			for conf in configs:
				for comp in conf['build'].values():
					add_volume(comp['sourcedir'], 1)
					add_volume(comp['builddir'], 1)

			rt.start()

			ugraph.execute(graph,
				       args.tasks,
				       args.verbose,
				       not args.no_color)


def _filter(name, graph, args):
	components = []
	pruned = {}

	for arg in args:
		try:
			conf, comp = arg.split('.', maxsplit=1)
			if conf == name:
				components.append(comp)
		except ValueError:
			components.append(arg)

	if len(components) == 0:
		return graph

	for c in components:
		if c not in graph:
			raise Exception(f'Bad filter: {c} not a '
					f'component of {name}')
		pruned[c] = []

	return pruned
