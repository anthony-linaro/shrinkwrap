Troubleshooting
===============

This page lists common issues encountered when installing or running Shrinkwrap
and how to resolve them.

pip installs but ``shrinkwrap`` command not found
-------------------------------------------------

Ensure that:

* A virtual environment is activated

Verify:

.. code-block:: bash

   which python
   which pip
   which shrinkwrap
   pip show shrinkwraptool

If ``shrinkwrap`` is not on ``PATH``, reinstall inside the active environment.

Wrong Python version
--------------------

Shrinkwrap requires **Python 3.9.0 or newer**.

Check the active Python version:

.. code-block:: bash

   python -V

If the version is too old, create a new virtual environment using ``pyenv`` or
``venv`` and reinstall Shrinkwrap.

If the issue persists, reinstall Shrinkwrap:

.. code-block:: bash

   python -m pip install --force-reinstall shrinkwraptool

pip installs old versions
-------------------------

Force pip to upgrade and ignore cached wheels:

.. code-block:: bash

   python -m pip install --upgrade --no-cache-dir shrinkwraptool

Editable install not picking up changes
---------------------------------------

Ensure Shrinkwrap was installed in editable mode:

.. code-block:: bash

   python -m pip install -e ".[dev]"

Verify the source location:

.. code-block:: bash

   python -c "import shrinkwrap; print(shrinkwrap.__file__)"

PEP 668: Externally Managed Environment with pyenv
--------------------------------------------------

**Symptom**

``pip install`` fails even inside an activated pyenv virtualenv:

.. code-block:: console

   error: externally-managed-environment

The message may reference ``/usr/share/doc/python**/README.venv``.

**Cause**

The shell is still using the system Python instead of the pyenv
virtualenv. On Debian/Ubuntu, the system Python is marked as
*externally managed* (PEP 668), which blocks ``pip``.

**Fix**

Re-initialize pyenv and re-activate the environment:

.. code-block:: console

   export PATH="$HOME/.pyenv/bin:$PATH"
   eval "$(pyenv init -)"
   eval "$(pyenv virtualenv-init -)"
   hash -r
   pyenv activate shrinkwrap-env

Verify that ``which python`` and ``which pip`` point inside
``~/.pyenv/versions``.

**Fallback**

Force the correct interpreter:

.. code-block:: console

   pyenv exec python -m pip install <package>

pyenv install: missing optional modules (_bz2, _ssl, readline, curses, ctypes)
------------------------------------------------------------------------------

**Symptom**

``pyenv install <version>`` fails (or succeeds with warnings) and reports missing
modules such as ``_bz2``, ``_ssl``, ``readline``, ``_curses`` or ``_ctypes``:

.. code-block:: console

   ModuleNotFoundError: No module named '_bz2'
   WARNING: The Python bz2 extension was not compiled. Missing the bzip2 lib?
   ...
   ModuleNotFoundError: No module named '_ssl'
   ERROR: The Python ssl extension was not compiled. Missing the OpenSSL lib?

**Cause**

Python was built without required development headers/libraries (bzip2, OpenSSL,
readline, ncurses, libffi, zlib, etc.). pyenv compiles Python from source, so it
needs these *-dev* packages installed first.

**Fix (Ubuntu/Debian)**

Install build dependencies, then reinstall the Python version:

.. code-block:: console

   sudo apt update
   sudo apt install -y \
     build-essential curl git ca-certificates \
     libssl-dev zlib1g-dev \
     libbz2-dev libreadline-dev libsqlite3-dev \
     libncurses-dev libncursesw5-dev \
     xz-utils tk-dev libffi-dev liblzma-dev \
     uuid-dev

   pyenv uninstall -f <version>
   pyenv install <version>

**Verify**

After install, confirm the modules import correctly:

.. code-block:: console

   pyenv shell <version>
   python -c "import ssl,bz2,readline,curses,ctypes; print('ok')"
