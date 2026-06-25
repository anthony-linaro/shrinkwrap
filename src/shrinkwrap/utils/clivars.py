# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

_defaults = {
	'jobs': 4,
}


def get(**kwargs):
	clivars = dict(_defaults)

	for k, v in kwargs.items():
		assert(k in clivars)
		clivars[k] = v

	return {k: str(v) for k, v in clivars.items()}