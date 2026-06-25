# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

def parse(args, type):
	vars = {}

	for pair in args:
		try:
			key, value = pair.split('=', maxsplit=1)
			vars[key] = value
		except ValueError:
			raise Exception(f'Invalid {type}var {pair}')

	return vars
