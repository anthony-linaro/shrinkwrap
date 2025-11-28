#!/usr/bin/env python3

# (C) COPYRIGHT 2022 ARM Limited or its affiliates.
# ALL RIGHTS RESERVED


import re
import requests
import slugify
import time
import argparse


parser = argparse.ArgumentParser(description='Build documentation using readthedocs.')
parser.add_argument('--domain',  default='https://readthedocs.com',
				 help='readthedocs url (default=https://readthedocs.com)')
parser.add_argument('--token', 	 required=True,
				 help='readthedocs authentication token')
parser.add_argument('--project', required=True,
				 help='readthedocs project slug')
parser.add_argument('--branch',  required=True, help='git branch to build')
parser.add_argument('--timeout', default=240, type=int,
				 help='timeout in seconds (default=240)')
parser.add_argument('--state',	 default='inactive', choices=['inactive', 'active', 'hidden'],
				 help='target documentation state')


args = parser.parse_args()


def git_branch_to_rtd_version(branch):
    # Follows the same approach as RTD's implementation.
    normalized = re.sub("[/%!?]", "-", branch)
    allowed = "-._"
    return slugify.slugify(
        normalized,
        only_ascii=True,
        spaces=False,
        lower=True,
        ok=allowed,
        space_replacement="-",
    ).lstrip(allowed)


def build_readthedocs(domain, token, project, version='latest', timeout=240):
	"""
	Requests that the readthedocs server builds the specified version of the specified project,
	and waits for the build to complete.

	The following error codes may be returned:
		0: Docs built successfully
		1: Docs failed to build
		2: General error (domain incorrect, project/version unknown, timeout, etc)
	"""
	try:
		headers = {'Authorization': f'token {token}'}

		print(f'INFO: setting state for {project}/{version} to {args.state}')

		update_version_url = f'{domain}/api/v3/projects/{project}/versions/{version}/'
		state = {
			"active": args.state in ['active', 'hidden'],
			"hidden": args.state == 'hidden',
			"privacy_level": "public",
		}
		rsp = requests.patch(update_version_url, headers=headers, json=state)
		if not rsp.ok:
			print(f'ERROR: project/version unknown ({project}, {version})')
			return 2

		print(f'INFO: building docs for {project}/{version}')

		start_build_url = f'{domain}/api/v3/projects/{project}/versions/{version}/builds/'
		rsp = requests.post(start_build_url, headers=headers)
		if not rsp.ok:
			print(f'ERROR: project/version unknown ({project}, {version})')
			return 2

		build_id = rsp.json()["build"]["id"]
		query_build_url = f'{domain}/api/v3/projects/{project}/builds/{build_id}/'

		start = time.perf_counter()
		success = None
		while success is None and time.perf_counter() - start < timeout:
			rsp = requests.get(query_build_url, headers=headers).json()
			success = rsp['success']
			if success is None:
				time.sleep(5)

		if success is True:
			print(f'INFO: docs built successfully for {project}, {version}')
			return 0
		elif success is False:
			print(f'INFO: docs failed to build for {project}, {version}')
			return 1
		else:
			raise TimeoutError('timeout')

	except Exception as err:
		print(f'ERROR: server unresponsive: {err}')
		return 2


exit(build_readthedocs(args.domain,
		       args.token,
		       args.project,
		       git_branch_to_rtd_version(args.branch),
		       args.timeout))
