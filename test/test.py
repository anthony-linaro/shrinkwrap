#!/usr/bin/env python3
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT


import argparse
import io
import multiprocessing as mp
import os
import re
import subprocess
import sys
import tempfile
from xml.sax.saxutils import escape, quoteattr
import yaml


RUNTIME = None
IMAGE = None
FVPJOBS = None
DRY_RUN = False


SCRIPTDIR = os.path.dirname(os.path.abspath(__file__))
SYNCTEST = os.path.join(SCRIPTDIR, 'test-sync.sh')
ASSETS = os.path.join(SCRIPTDIR, 'assets')
KERNEL = os.path.join(ASSETS, 'Image')
BOOTWRAPPER = os.path.join(ASSETS, 'linux-system.axf')
ROOTFS = os.path.join(ASSETS, 'rootfs.ext4')


ARCH_LATEST = 'v9.5'
CONFIGS = [
	{
		'config': 'ns-preload.yaml',
		'btvars': {},
		'rtvars': {
			'default': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
		},
		'arch': {'start': 'v8.0', 'end': ARCH_LATEST},
	},
	{
		'config': 'ns-edk2.yaml',
		'btvars': {},
		'rtvars': {
			'dt': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
			'acpi': {
				'KERNEL': KERNEL,
				'ROOTFS': ROOTFS,
				'CMDLINE': '\"console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp acpi=force\"'
			},
		},
		'arch': {'start': 'v8.0', 'end': ARCH_LATEST},
	},
	{
		'config': 'ns-edk2-optee.yaml',
		'btvars': {},
		'rtvars': {
			'default': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
		},
		'arch': {'start': 'v8.0', 'end': ARCH_LATEST},
	},
	{
		'config': 'ffa-optee.yaml',
		'btvars': {},
		'rtvars': {
			'dt': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
			'acpi': {
				'KERNEL': KERNEL,
				'ROOTFS': ROOTFS,
				'CMDLINE': '\"console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp acpi=force\"'
			},
		},
		'arch': {'start': 'v8.0', 'end': ARCH_LATEST},
	},
	{
		'config': 'ffa-hafnium-optee.yaml',
		'btvars': {},
		'rtvars': {
			'dt': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
			'acpi': {
				'KERNEL': KERNEL,
				'ROOTFS': ROOTFS,
				'CMDLINE': '\"console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp acpi=force\"'
			},
		},
		'arch': {'start': 'v8.5', 'end': ARCH_LATEST},
	},
	{
		'config': 'ffa-tftf.yaml',
		'btvars': {},
		'rtvars': {
			'dt': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
			'acpi': {
				'KERNEL': KERNEL,
				'ROOTFS': ROOTFS,
				'CMDLINE': '\"console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp acpi=force\"'
			},
		},
		'arch': {'start': 'v8.5', 'end': ARCH_LATEST},
	},
	{
		'config': 'bootwrapper.yaml',
		'btvars': {},
		'rtvars': {
			'default': {'BOOTWRAPPER': BOOTWRAPPER, 'ROOTFS': ROOTFS},
		},
		# Temporary workaround: bootwrapper doesn't disable the GCS EL3
		# traps so the kernel traps to EL3 when trying to configure it.
		# GCS is enabled at arch/v9.4.yaml so stop testing at v9.3 as
		# temporary workaround. (See PDSWLINUX-4668).
		'arch': {'start': 'v8.0', 'end': 'v9.3'},
	},
	{
		'config': 'cca-3world.yaml',
		'btvars': {'GUEST_ROOTFS': ROOTFS},
		'rtvars': {'default': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS}},
	},
	{
		'config': 'cca-3world.yaml',
		'btvars': {},
		'rtvars': {'realm': {}},
		'overlays': ['buildroot-cca.yaml', 'test/cca.yaml'],
		# Building the whole userspace and booting multiple guests takes a while!
		# 30min timeout should be enough.
		'timeout': 1800,
	},
	{
		'config': 'cca-4world.yaml',
		'btvars': {'GUEST_ROOTFS': ROOTFS},
		'rtvars': {'default': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS}},
	},
	{
		'config': 'cca-edk2.yaml',
		'btvars': {},
		'rtvars': {
			'dt': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
			'acpi': {
				'KERNEL': KERNEL,
				'ROOTFS': ROOTFS,
				'CMDLINE': '\"console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp acpi=force\"'
			},
		},
	},
]


results = []
arch_regex = re.compile(r"^v(\d+\.\d)$")


def arch_range(start, end):
	"""
	Given a start and end version string (in format "vX.Y"), yields all
	version strings between start and end, inclusive of both start and end.
	"""
	match_s = arch_regex.match(start)
	match_e = arch_regex.match(end)

	start = int(float(match_s.group(1)) * 10)
	end = int(float(match_e.group(1)) * 10)

	for version in range(start, end + 1):
		major = version // 10
		minor = version - major * 10
		yield f'v{major}.{minor}'


def arch_in_range(arch, start, end):
	"""
	Given an arch version and a start and end version string (all in format
	"vX.Y"), returns true if arch is within the range, inclusive of both
	start and end.
	"""
	match_a = arch_regex.match(arch)
	match_s = arch_regex.match(start)
	match_e = arch_regex.match(end)

	arch = float(match_a.group(1))
	start = float(match_s.group(1))
	end = float(match_e.group(1))

	return start <= arch and arch <= end


def test_name(r):
	def add_part(parts, result, name):
		if name in result and result[name]:
			if not (name == 'tag' and result[name] == 'default'):
				parts.append(result[name])

	parts = []
	add_part(parts, r, 'type')
	add_part(parts, r, 'config')
	add_part(parts, r, 'overlay')
	add_part(parts, r, 'tag')
	return ':'.join(parts)


def print_testcase(f, case):
	if case['status'] == 'pass':
		element = 'system-out'
		prop = ''
	if case['status'] == 'fail':
		element = 'failure'
		prop = ' type="failure"'
	if case['status'] == 'error':
		element = 'error'
		prop = ' type="error"'
	if case['status'] == 'skip':
		element = 'skipped'
		prop = ' type="skipped"'

	print(f'        <testcase classname={quoteattr(case["type"])} name={quoteattr(test_name(case))}>', file=f)
	if case['error'] == None:
		print(f'            <{element}{prop}/>', file=f)
	else:
		print(f'            <{element}{prop}>', file=f)
		print(escape(case['error']), file=f)
		print(f'            </{element}>', file=f)
	print('        </testcase>', file=f)


def print_testsuite(f, suitename, cases):
	print(f'    <testsuite name={quoteattr(suitename)}>', file=f)
	for case in cases:
		print_testcase(f, case)
	print('    </testsuite>', file=f)


def print_junit_results(f, suitename, cases):
	print('<?xml version="1.0" encoding="utf-8"?>', file=f)
	print('<testsuites>', file=f)
	print_testsuite(f, suitename, cases)
	print('</testsuites>', file=f)


def print_results(junit=None):
	if junit:
		with open(junit, 'w') as f:
			print_junit_results(f, 'selftest', results)

	nr_pass = 0
	print('TEST REPORT SUMMARY')
	for r in results:
		print(f'{r["status"].upper()}: {test_name(r)}')
		if r['status'] == 'pass':
			nr_pass += 1

	dry_run = "(dry run) " if DRY_RUN else ""
	print(f'{dry_run}pass: {nr_pass}, fail: {len(results) - nr_pass}')

	return nr_pass == len(results)


def run(cmd, timeout=None, expect=0, capture=False):
	output = io.StringIO() if capture else sys.stdout
	print(">> " + "-" * 77, file=output)
	print(f"+ {cmd}", file=output)

	def finalize():
		print("<< " + "-" * 77, file=output)
		return output.getvalue() if capture else None

	if DRY_RUN:
		print(f"+ DRY_RUN={DRY_RUN}", file=output)
		return finalize()

	try:
		# Ensure subprocess's output is ordered after ours.
		output.flush()
		ret = subprocess.run(cmd, timeout=timeout, shell=True,
			stdout=subprocess.PIPE if capture else None,
			stderr=subprocess.STDOUT if capture else None)
		if ret.stdout:
			output.write(ret.stdout.decode())
		print(f"+ returncode={ret.returncode}, expect={expect}", file=output)
		if ret.returncode != expect:
			raise subprocess.CalledProcessError(ret.returncode, ret.args,
						output=finalize(), stderr=None)
	except subprocess.TimeoutExpired as e:
		if e.stdout:
			output.write(e.stdout.decode())
		print(f"+ timeout={timeout}", file=output)
		e.stdout = finalize()
		raise

	return finalize()


def build_configs(configs, overlays):

	status = 'pass'
	error = None

	rt = f'-R {RUNTIME} -I {IMAGE}'
	cfg_files = [c['config'] for c in configs]
	overlay_args = ' '.join(f'-o {o}' for o in overlays)
	cleanargs = f'{" ".join(cfg_files)} {overlay_args}'

	cfgs = []
	for c in configs:
		cfgs.append({'config': c['config'], 'btvars': c['btvars']})

	with tempfile.TemporaryDirectory() as tmpdir:
		tmpfilename = os.path.join(tmpdir, 'configs.yaml')
		with open(tmpfilename, 'w') as tmpfile:
			yaml.safe_dump({'configs': cfgs},
					tmpfile,
					explicit_start=True,
					sort_keys=False,
					version=(1, 2))
		with open(tmpfilename, 'r') as tmpfile:
			print(tmpfile.read())
		buildargs = f'{tmpfilename} {overlay_args}'

		try:
			run(f'shrinkwrap {rt} clean {cleanargs}')
			run(f'shrinkwrap {rt} buildall {buildargs}')
		except Exception as e:
			status = 'fail'
			error = str(e)

	global results
	results += [{
		'type': 'build',
		'status': status,
		'error': error,
		'config': c['config'],
		'overlays': ",".join(overlays),
		'btvars': c['btvars'],
	} for c in configs]


def run_config(config, overlays, rtvars, tag, capture, timeout):

	def make_rtcmds(rtvars):
		return ' '.join([f'-r {k}={v}' for k, v in rtvars.items()])

	runargs = make_rtcmds(rtvars)

	result = {
		'type': 'run',
		'status': 'fail',
		'error': None,
		'config': config,
		'overlays': ','.join(overlays),
		'rtvars': rtvars,
		'tag': tag,
	}

	rt = f'-R {RUNTIME} -I {IMAGE}'
	overlay_args = ' '.join(f"-o {o}" for o in overlays)
	args = f'{config} {overlay_args} {runargs}'

	try:
		stdout = run(f'shrinkwrap {rt} run {args}',
				timeout=timeout, capture=capture)
		result['status'] = 'pass'
	except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
		stdout = e.stdout
		result['error'] = str(e)
	except Exception as e:
		stdout = None
		result['error'] = str(e)

	return result, stdout


def run_configs(configs, overlays):
	params = []
	for c in configs:
		for tag, rtvars in c['rtvars'].items():
			timeout = c.get('timeout', 600)
			params.append((c['config'], overlays, rtvars, tag, FVPJOBS > 1, timeout))

	with mp.Pool(processes=FVPJOBS) as pool:
		for result, stdout in pool.starmap(run_config, params):
			results.append(result)
			if stdout:
				sys.stdout.write(stdout)


def run_repo_sync_test(args):
	# Cannot select synctest with `-c`, but it's easy to run manually
	if args.config is not None:
		return

	if DRY_RUN:
		ret = 0
		print(f"+ {SYNCTEST}")
	else:
		ret = subprocess.run(SYNCTEST).returncode
	results.append({
		'type': 'repo-sync-behaviours',
		'status': 'pass' if ret == 0 else 'fail',
		'error': None,
	})


def do_main(args):
	selected_configs = [c for c in CONFIGS
			            if args.config is None or args.config == c['config']]
	if not selected_configs:
		print(f"Unknown config {args.config}")
		exit(1)

	if args.smoke_test:
		# Assume tests with a special timeout are long-running ones
		selected_configs = [c for c in selected_configs if not 'timeout' in c]

	arch_configs = [c for c in selected_configs if 'arch' in c]
	noarch_configs = [c for c in selected_configs if 'arch' not in c]

	if args.smoke_test:
		arches = set([c['arch']['end'] for c in arch_configs])
	else:
		arches = list(arch_range('v8.0', ARCH_LATEST))

	# Gather configs that have the same overlays, and can be built together
	test_batches = {}

	# Configs that support an arch override.
	for arch in arches:
		for c in arch_configs:
			first_arch = c['arch']['end'] if args.smoke_test else c['arch']['start']
			if not arch_in_range(arch, first_arch, c['arch']['end']):
				continue

			overlays = (f'arch/{arch}.yaml',) + tuple(c.get('overlays', ()))
			test_batches.setdefault(overlays, []).append(c)

	# Configs that don't support an arch override.
	for c in noarch_configs:
		overlays = tuple(c.get('overlays', ()))
		test_batches.setdefault(overlays, []).append(c)

	for overlays, configs in test_batches.items():
		build_configs(configs, overlays)
		run_configs(configs, overlays)

	run_repo_sync_test(args)

	success = print_results(args.junit)
	exit(not success)


def main():
	parser = argparse.ArgumentParser()

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
		default='docker.io/shrinkwraptool/base-full:latest',
		help="""If using a container runtime, specifies the name of the
		     image to use. Defaults to the official shrinkwrap image.""")

	parser.add_argument('-c', '--config',
		metavar='name', required=False, default=None,
		help="""Only test the given config.""")

	parser.add_argument('-j', '--junit',
		metavar='file', required=False, default=None,
		help="""Optionally output results in junit format to specified file.""")

	parser.add_argument('-f', '--fvpjobs',
		metavar='count', required=False, default=1, type=int,
		help="""Maximum number of FVPs to run in parallel.""")

	parser.add_argument('-n', '--dry-run',
		required=False, default=False, action='store_true',
		help="""Do not build or run anything, only print what would be done.""")

	parser.add_argument('-s', '--smoke-test',
		required=False, default=False, action='store_true',
		help="""If specified, run a smaller selection of tests.""")

	args = parser.parse_args()

	global RUNTIME
	global IMAGE
	global FVPJOBS
	global DRY_RUN
	RUNTIME = args.runtime
	IMAGE = args.image
	FVPJOBS = args.fvpjobs
	DRY_RUN = args.dry_run

	do_main(args)


if __name__ == "__main__":
	main()
