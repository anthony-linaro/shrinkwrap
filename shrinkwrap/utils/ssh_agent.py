# Copyright (c) 2024, Arm Limited.
# SPDX-License-Identifier: MIT

import atexit
import os
import re
import subprocess
from typing import Optional

import shrinkwrap.utils.logger as logger


_logger = logger.Logger(27)
"""Logger used within this module."""


def _log(msg):
        """Print a message to the console."""
        _logger.print(msg, tag='ssh-agent', cont=False)


_proc = None
"""ssh-agent process started by this module."""


def _start():
        """Start an ssh-agent process."""
        global _proc

        assert _proc is None
        _proc = subprocess.run(
                ['ssh-agent', '-s'], stdout=subprocess.PIPE, text=True)

        # Extract socket path and PID from ssh-agent output
        output = _proc.stdout
        match = re.search(
                r'SSH_AUTH_SOCK=(?P<sock>[^;]+).*SSH_AGENT_PID=(?P<pid>[^;]+)',
                output,
                re.DOTALL | re.MULTILINE)

        if not match:
                raise Exception(f'Failed to parse ssh-agent output: {output}')

        values = match.groupdict()

        os.environ['SSH_AUTH_SOCK'] = values['sock']
        os.environ['SSH_AGENT_PID'] = values['pid']

        _log(f'Started ssh-agent pid {values["pid"]}')

        # Register a handler to kill the ssh-agent process
        atexit.register(_stop)


def _stop():
        """Stop the ssh-agent process."""
        global _proc

        assert _proc is not None

        _log('Stopping ssh-agent')

        subprocess.check_call(['ssh-agent', '-k'], stdout=subprocess.DEVNULL)

        del os.environ['SSH_AUTH_SOCK']
        del os.environ['SSH_AGENT_PID']

        _proc = None


def socket() -> Optional[str]:
        """Return path to socket."""
        return os.environ.get('SSH_AUTH_SOCK')


def add(key: Optional[str]=None) -> None:
        """
        Add specified key, or add default keys if key is None.

        If no ssh-agent process is running, one is started.
        """
        if socket() is None:
                _start()
        else:
                global _proc
                if _proc is None:
                        raise Exception('Adding a key to an ssh-agent not owned by shrinkwrap is not supported.')

        if key is None:
                _log('Adding default keys')
        else:
                _log(f'Adding key {key}')

        args = ['ssh-add']
        if key is not None:
                args.append(key)

        subprocess.check_call(args)
