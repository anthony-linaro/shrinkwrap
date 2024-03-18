# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import graphlib
import os
import shutil
import tempfile
import shrinkwrap.utils.logger as logger
import shrinkwrap.utils.label as label
import shrinkwrap.utils.process as process
import shrinkwrap.utils.workspace as workspace


def _mk_labels(graph):
	"""
	Returns a tuple of labels and mask. Each is a two level dictionary,
	where there is an entry for each config/component that we are building.
	Mask is initially set to true.
	"""
	labels = {}
	mask = {}

	ts = graphlib.TopologicalSorter(graph)
	ts.prepare()
	while ts.is_active():
		for frag in ts.get_ready():
			ts.done(frag)

			cfg = frag.config
			cmp = frag.component

			if cfg is None or cmp is None:
				continue

			if cfg not in labels:
				labels[cfg] = {}
				mask[cfg] = {}
			if cmp not in labels[cfg]:
				labels[cfg][cmp] = label.Label()
				mask[cfg][cmp] = True

	return labels, mask


def _mk_label_controller(labels, overdraw):
	"""
	Makes a label controller for all the labels in the labels two-level
	dictionary.
	"""
	label_list = []
	for sl in labels.values():
		for l in sl.values():
			label_list.append(l)
	return label.LabelController(label_list, overdraw=overdraw)


def _mk_tag(config, component):
	"""
	Makes a fixed-width tag string for a config and component.
	"""
	def _clamp(text, max):
		if len(text) > max:
			text = text[:max-3] + '...'
		return text

	config = '' if config is None else config
	component = '' if component is None else component
	config = _clamp(config, 10)
	component = _clamp(component, 14)
	return '[ {:>10} : {:14} ]'.format(config, component)


def _update_labels(labels, mask, config, component, summary):
	"""
	Updates all the labels whose mask is True and which match config and
	component (if specified, then only update for that config/component. If
	None, then update all configs/components). summary provides the text to
	update the labels with.
	"""
	def iter(labels, mask, key):
		if key is None:
			for key in labels:
				yield key, labels[key], mask[key]
		else:
			yield key, labels[key], mask[key]

	for cfg, l0, m0 in iter(labels, mask, config):
		for cmp, l1, m1 in iter(l0, m0, component):
			if m1:
				l1.update(_mk_tag(cfg, cmp) + ' ' + summary)


def _run_script(pm, data, script):
	# Write the script out to a file in a temp directory, and wrap the
	# directory name and command to run in a Process. Add the Process to the
	# ProcessManager. On completion, the caller must destroy the directory.

	tmpdir = tempfile.mkdtemp(dir=workspace.build)
	tmpfilename = os.path.join(tmpdir, 'script.sh')
	with open(tmpfilename, 'w') as tmpfile:
		tmpfile.write(script.commands())

	# Start the process asynchronously.
	pm.add(process.Process(f'bash {tmpfilename}',
			       False,
			       (*data, script, tmpdir),
			       True))


def execute(graph, tasks, verbose=False, colorize=True):
	labels, mask = _mk_labels(graph)
	lc = _mk_label_controller(labels, not verbose)

	queue = []
	active = 0
	log = logger.Logger(27)
	ts = graphlib.TopologicalSorter(graph)

	def _pump(pm):
		nonlocal queue
		nonlocal active
		nonlocal log
		while len(queue) > 0 and active < tasks:
			frag = queue.pop()
			logname = None
			if frag.config and frag.component:
				logname = os.path.join(workspace.build,
						'log',
						frag.config,
						f'{frag.component}.log')
				os.makedirs(os.path.dirname(logname), exist_ok=True)
			_update_labels(labels,
				       mask,
				       frag.config,
				       frag.component,
				       frag.summary + '...')
			data = (log.alloc_data(str(frag), colorize, False, logname), [])
			_run_script(pm, data, frag)
			active += 1

	def _should_log(proc, data, streamid):
		if verbose or \
		   (streamid == process.STDERR and \
		   (not proc.data[2].stderrfilt or \
		   'warning' in data or 'error' in data)):
			return True
		return False

	def _log(pm, proc, data, streamid):
		logstd = _should_log(proc, data, streamid)
		if not verbose:
			proc.data[1].append(data)
		if logstd:
			lc.erase()
		log.log(pm, proc, data, streamid, logstd)
		if logstd:
			lc.update()

	def _complete(pm, proc, retcode):
		nonlocal queue
		nonlocal active
		nonlocal ts

		data = proc.data[0]
		err = proc.data[1]
		frag = proc.data[2]
		tmpdir = proc.data[3]

		log.free_data(data)
		shutil.rmtree(tmpdir)

		if retcode is None:
			# Forcibly terminated due to errors elsewhere. No need
			# to do anything further.
			return

		if retcode:
			if not verbose:
				print('\n== error start ' + ('=' * 65))
				print(''.join(err))
				print('== error end ' + ('=' * 67) + '\n')
			raise Exception(f"Failed to execute '{frag}'")

		state = 'Done' if frag.final else 'Waiting...'
		_update_labels(labels,
			       mask,
			       frag.config,
			       frag.component,
			       state)
		if frag.final:
			mask[frag.config][frag.component] = False

		ts.done(frag)
		active -= 1
		queue.extend(ts.get_ready())
		_pump(pm)

		lc.update()

	# Initially set all labels to waiting. They will be updated as the
	# fragments execute.
	_update_labels(labels, mask, None, None, 'Waiting...')

	# The process manager will run all added processes in the background and
	# give callbacks whenever there is output available and when each
	# process terminates. _pump() adds processes to the set.
	pm = process.ProcessManager(_log, _complete)

	# Fill the queue with all the initial script fragments which do not have
	# start dependencies.
	ts.prepare()
	queue.extend(ts.get_ready())

	# Call _pump() initially to start as many tasks as are allowed.
	# Then enter the pm.
	_pump(pm)
	lc.update()
	pm.run()

	# Mark all components as done. This should be a nop since the script
	# should have indicated if it was the last step for a given
	# config/component and we would have already set it to done. But this
	# catches anything that might have slipped through.
	_update_labels(labels, mask, None, None, 'Done')
	lc.update()


def make_script(graph):
	# Start the script with the preamble from the first script fragment in
	# the graph. The preamble for each script is identical and we only need
	# it once since we are concatenating the fragments together.
	script = '' + list(graph.keys())[0].preamble() + '\n'

	# Walk the graph, adding each script fragment to the final script
	# (without its preamble).
	ts = graphlib.TopologicalSorter(graph)
	ts.prepare()
	while ts.is_active():
		for frag in ts.get_ready():
			script += frag.commands(False) + '\n'
			ts.done(frag)

	return script
