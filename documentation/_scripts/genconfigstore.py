#!/usr/bin/env python3
# Copyright (c) 2023, Arm Limited.
# SPDX-License-Identifier: MIT


# Uses `shrinkwrap inspect --json` to determine all the standard concrete
# configs, and generates rst pages for each one. To be run whenever configs are
# added or updated.


import json
import os
import subprocess


def make_rst_table(headers, data):
	colwidths = []
	for i, header in enumerate(headers):
		colwidth = len(str(header))
		for row in data:
			colwidth = max(colwidth, len(str(row[i])))
		colwidths.append(colwidth)

	def track_str(colwidths):
		return ' '.join(['=' * w for w in colwidths]) + '\n'

	def row_str(colwidths, data):
		return ' '.join([f'{d:{w}}' for d, w in zip(data, colwidths)]) + '\n'

	table = ''
	table += track_str(colwidths)
	table += row_str(colwidths, headers)
	table += track_str(colwidths)
	for row in data:
		table += row_str(colwidths, row)
	table += track_str(colwidths)

	return table


def make_rst_table_from_dict(headers, data):
	return make_rst_table(headers, [(k, v) for k, v in data.items()])


index = """..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

############
Config Store
############

Shrinkwrap ships with the following standard set of configs for use
out-of-the-box:

.. toctree::
   :titlesonly:
   :maxdepth: 1

"""

template = """..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

{}
{}
{}

Description
###########

{}

Concrete
########

{}

Build-Time Variables
####################

{}
Run-Time Variables
##################

{}
"""

cfgs_raw = subprocess.run('shrinkwrap inspect --json',
                          capture_output=True,
            		  text=True,
            		  shell=True,
            		  check=True).stdout

cfgs = json.loads(cfgs_raw)

docsdir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
docsdir = os.path.join(docsdir, 'userguide', 'configstore')

with open(os.path.join(docsdir, 'index.rst'), 'w') as indexf:
	indexf.write(index)

	for c in cfgs:
		rstbase = os.path.splitext(os.path.basename(c['name']))[0]+'.rst'
		rst = os.path.join(docsdir, rstbase)

		indexf.write(f'   {rstbase}\n')

		page = template.format(
			'#' * len(c['name']),
			c['name'],
			'#' * len(c['name']),
			c['description'].replace('\n', '\n\n'),
			c['concrete'],
			make_rst_table_from_dict(('btvar', 'default'), c['btvars']),
			make_rst_table_from_dict(('rtvar', 'default'), c['rtvars']))

		with open(rst, 'w') as rstf:
			rstf.write(page)

