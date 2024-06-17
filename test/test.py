#!/usr/bin/env python3
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT


import argparse
import json
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


ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
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
		'arch': {'start': 'v8.5', 'end': 'v8.7'}, # BL2 freezes from v8.8. Haven't traced root cause yet.
	},
	{
		'config': 'bootwrapper.yaml',
		'btvars': {},
		'rtvars': {
			'default': {'BOOTWRAPPER': BOOTWRAPPER, 'ROOTFS': ROOTFS},
		},
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

	print(f'pass: {nr_pass}, fail: {len(results) - nr_pass}')

	return nr_pass == len(results)


def run(cmd, timeout=None, expect=0, capture=False):
	print(f'+ {cmd}')
	ret = subprocess.run(cmd, timeout=timeout, shell=True,
		stdout=subprocess.PIPE if capture else None,
		stderr=subprocess.STDOUT if capture else None)
	if ret.returncode != expect:
		raise subprocess.CalledProcessError(ret.returncode, ret.args,
					output=ret.stdout, stderr=ret.stderr)
	return ret.stdout


def build_configs(configs, overlay=None, btvarss=None):

	status = 'pass'
	error = None

	rt = f'-R {RUNTIME} -I {IMAGE}'
	cleanargs = f'{" ".join(configs)} {f"-o {overlay}" if overlay else ""}'

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
		buildargs = f'{tmpfilename} {f"-o {overlay}" if overlay else ""}'

		try:
			run(f'shrinkwrap {rt} clean {cleanargs}', None)
			run(f'shrinkwrap {rt} buildall {buildargs}', None)
		except Exception as e:
			status = 'fail'
			error = str(e)

	global results
	results += [{
		'type': 'build',
		'status': status,
		'error': error,
		'config': config,
		'overlay': overlay,
		'btvars': btvars,
	} for config, btvars in zip(configs, btvarss)]


def run_config(config, overlay, rtvars, tag, capture):

	def make_rtcmds(rtvars):
		return ' '.join([f'-r {k}={v}' for k, v in rtvars.items()])

	runargs = make_rtcmds(rtvars)

	result = {
		'type': 'run',
		'status': 'fail',
		'error': None,
		'config': config,
		'overlay': overlay,
		'rtvars': rtvars,
		'tag': tag,
	}

	rt = f'-R {RUNTIME} -I {IMAGE}'
	overlay = f'-o {overlay}' if overlay else ''
	args = f'{config} {overlay} {runargs}'

	try:
		stdout = run(f'shrinkwrap {rt} run {args}',
	       			timeout=600, capture=capture)
		result['status'] = 'pass'
	except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
		stdout = e.stdout
		result['error'] = str(e)
	except Exception as e:
		stdout = None
		result['error'] = str(e)

	return result, stdout


def run_configs(configs, overlay=None, rtvarss=None):

	if rtvarss is None:
		rtvarss = [{'default': {}}] * len(configs)

	params = []
	for config, _rtvars in zip(configs, rtvarss):
		for tag, rtvars in _rtvars.items():
			params.append((config, overlay, rtvars, tag, FVPJOBS > 1))

	with mp.Pool(processes=FVPJOBS) as pool:
		for result, stdout in pool.starmap(run_config, params):
			results.append(result)
			if stdout:
				sys.stdout.write(stdout.decode())


def do_main(args):
	if args.smoke_test:
		arches = set([c['arch']['end'] for c in CONFIGS])
	else:
		arches = list(arch_range('v8.0', ARCH_LATEST))

	for arch in arches:
		configs = [c['config'] for c in CONFIGS if arch_in_range(arch, c['arch']['end'] if args.smoke_test else c['arch']['start'], c['arch']['end'])]
		btvarss = [c['btvars'] for c in CONFIGS if arch_in_range(arch, c['arch']['end'] if args.smoke_test else c['arch']['start'], c['arch']['end'])]
		rtvarss = [c['rtvars'] for c in CONFIGS if arch_in_range(arch, c['arch']['end'] if args.smoke_test else c['arch']['start'], c['arch']['end'])]
		if len(configs) == 0:
			continue
		build_configs(configs, f'arch/{arch}.yaml', btvarss=btvarss)
		run_configs(configs, f'arch/{arch}.yaml', rtvarss=rtvarss)

	# Special-case configs that don't support arch overrides.
	build_configs(['cca-3world.yaml', 'cca-4world.yaml'],
	       			btvarss=[
					{'GUEST_ROOTFS': ROOTFS},
					{'GUEST_ROOTFS': ROOTFS}
				])
	run_configs(['cca-3world.yaml', 'cca-4world.yaml'], None,
	     			rtvarss=[
					{'default': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS}},
					{'default': {'KERNEL': KERNEL, 'ROOTFS': ROOTFS}},
				])

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

	parser.add_argument('-j', '--junit',
		metavar='file', required=False, default=None,
		help="""Optionally output results in junit format to specified file.""")

	parser.add_argument('-f', '--fvpjobs',
		metavar='count', required=False, default=1, type=int,
		help="""Maximum number of FVPs to run in parallel.""")

	parser.add_argument('-s', '--smoke-test',
		required=False, default=False, action='store_true',
		help="""If specified, run a smaller selection of tests.""")

	args = parser.parse_args()

	global RUNTIME
	global IMAGE
	global FVPJOBS
	RUNTIME = args.runtime
	IMAGE = args.image
	FVPJOBS = args.fvpjobs

	do_main(args)


if __name__ == "__main__":
	main()
