# Copyright (c) 2026, Arm Limited.
# SPDX-License-Identifier: MIT

import subprocess
import sys
from pathlib import Path


def run_shrinkwrap(*args):
    repo_root = Path(__file__).resolve().parents[1]

    return subprocess.run(
        [sys.executable, "shrinkwrap/shrinkwrap.py", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
