#!/usr/bin/env python3
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT


import argparse
import json
import os
import re
import subprocess
import tempfile
import yaml


RUNTIME = None
IMAGE = None


ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
KERNEL = os.path.join(ASSETS, 'Image')
BOOTWRAPPER = os.path.join(ASSETS, 'linux-system.axf')
ROOTFS = os.path.join(ASSETS, 'rootfs.ext4')


ARCH_LATEST = 'v9.5'
CONFIGS = [
	{
		'config': 'ns-preload.yaml',
		'btvars': {},
		'rtvars': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
		'arch': {'start': 'v8.0', 'end': ARCH_LATEST},
	},
	{
		'config': 'ns-edk2.yaml',
		'btvars': {},
		'rtvars': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
		'arch': {'start': 'v8.0', 'end': ARCH_LATEST},
	},
	{
		'config': 'ns-edk2.yaml',
		'btvars': {},
		'rtvars': {
			'KERNEL': KERNEL,
			'ROOTFS': ROOTFS,
			'CMDLINE': '\"console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp acpi=force\"'
		},
		'arch': {'start': 'v8.0', 'end': ARCH_LATEST},
	},
	{
		'config': 'ffa-tftf.yaml',
		'btvars': {},
		'rtvars': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS},
		'arch': {'start': 'v8.5', 'end': 'v8.7'}, # BL2 freezes from v8.8. Haven't traced root cause yet.
	},
	{
		'config': 'ffa-tftf.yaml',
		'btvars': {},
		'rtvars': {
			'KERNEL': KERNEL,
			'ROOTFS': ROOTFS,
			'CMDLINE': '\"console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp acpi=force\"'
		},
		'arch': {'start': 'v8.5', 'end': 'v8.7'}, # BL2 freezes from v8.8. Haven't traced root cause yet.
	},
	{
		'config': 'bootwrapper.yaml',
		'btvars': {},
		'rtvars': {'BOOTWRAPPER': BOOTWRAPPER, 'ROOTFS': ROOTFS},
		'arch': {'start': 'v8.0', 'end': ARCH_LATEST},
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


def print_result(r):
	def report(status, type, config, overlay):
		desc = f'{status.upper()}: {type}: {config},{overlay}'
		count = (1, 0) if status == 'pass' else (0, 1)
		return count[0], count[1], desc

	if r['type'] == 'build':
		configs = r['configs']
	elif r['type'] == 'run':
		configs = [r['config']]
	else:
		assert(False)

	nr_pass = 0
	nr_fail = 0
	for c in configs:
		p, f, desc = report(r['status'],
				      r['type'],
				      c,
				      r['overlay'])
		nr_pass += p
		nr_fail += f
		print(desc)

	return nr_pass, nr_fail


def print_results():
	print('TEST REPORT JSON')
	print(json.dumps(results, indent=4))

	nr_pass = 0
	nr_fail = 0
	print('TEST REPORT SUMMARY')
	for r in results:
		p, f = print_result(r)
		nr_pass += p
		nr_fail += f

	print(f'pass: {nr_pass}, fail: {nr_fail}')


class WrongExit(Exception):
	pass


def run(cmd, timeout=None, expect=0):
	print(f'+ {cmd}')
	ret = subprocess.run(cmd, timeout=timeout, shell=True)
	if ret.returncode != expect:
		raise WrongExit(ret)


def build_configs(configs, overlay=None, btvarss=None):
	result = {
		'type': 'build',
		'status': 'fail',
		'error': None,
		'configs': configs,
		'overlay': overlay,
		'btvarss': btvarss,
	}

	rt = f'-R {RUNTIME} -I {IMAGE}'
	overlay = f'-o {overlay}' if overlay else ''
	cleanargs = f'{" ".join(configs)} {overlay}'

	if btvarss is None:
		btvarss = [{}] * len(configs)

	assert(len(configs) == len(btvarss))

	cfgs = []
	for c, b in zip(configs, btvarss):
		cfgs.append({'config': c, 'btvars': b})

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
		buildargs = f'{tmpfilename} {overlay}'

		try:
			run(f'shrinkwrap {rt} clean {cleanargs} -d', None)
			run(f'shrinkwrap {rt} buildall {buildargs}', None)
			result['status'] = 'pass'
		except Exception as e:
			result['error'] = str(e)

	results.append(result)


def run_config(config, overlay=None, runargs=None, runtime=600):
	result = {
		'type': 'run',
		'status': 'fail',
		'error': None,
		'config': config,
		'overlay': overlay,
		'runargs': runargs,
		'runtime': runtime,
	}

	rt = f'-R {RUNTIME} -I {IMAGE}'
	overlay = f'-o {overlay}' if overlay else ''
	runargs = runargs if runargs else ''
	args = f'{config} {overlay} {runargs}'

	try:
		run(f'shrinkwrap {rt} run {args}', runtime)
		result['status'] = 'pass'
	except Exception as e:
		result['error'] = str(e)

	results.append(result)


def make_rtcmds(rtvars):
	return ' '.join([f'-r {k}={v}' for k, v in rtvars.items()])


def do_main(smoke_test):
	if smoke_test:
		arches = set([c['arch']['end'] for c in CONFIGS])
	else:
		arches = list(arch_range('v8.0', ARCH_LATEST))

	for arch in arches:
		configs = [c['config'] for c in CONFIGS if arch_in_range(arch, c['arch']['end'] if smoke_test else c['arch']['start'], c['arch']['end'])]
		btvarss = [c['btvars'] for c in CONFIGS if arch_in_range(arch, c['arch']['end'] if smoke_test else c['arch']['start'], c['arch']['end'])]
		rtvarss = [c['rtvars'] for c in CONFIGS if arch_in_range(arch, c['arch']['end'] if smoke_test else c['arch']['start'], c['arch']['end'])]
		if len(configs) == 0:
			continue
		build_configs(configs, f'arch/{arch}.yaml', btvarss=btvarss)
		for config, rtvars in zip(configs, rtvarss):
			run_config(config, f'arch/{arch}.yaml', make_rtcmds(rtvars))

	# Special-case configs that don't support arch overrides.
	build_configs(['cca-3world.yaml', 'cca-4world.yaml'],
	       			btvarss=[
					{'GUEST_ROOTFS': ROOTFS},
					{'GUEST_ROOTFS': ROOTFS}
				])
	run_config('cca-3world.yaml', None, make_rtcmds({'KERNEL': KERNEL, 'ROOTFS': ROOTFS}))
	run_config('cca-4world.yaml', None, make_rtcmds({'KERNEL': KERNEL, 'ROOTFS': ROOTFS}))

	print_results()


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

	parser.add_argument('-s', '--smoke-test',
		required=False, default=False, action='store_true',
		help="""If specified, run a smaller selection of tests.""")

	args = parser.parse_args()

	global RUNTIME
	global IMAGE
	RUNTIME = args.runtime
	IMAGE = args.image

	do_main(args.smoke_test)


if __name__ == "__main__":
	main()
