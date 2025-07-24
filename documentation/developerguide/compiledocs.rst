..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#############################
Compile Documentation Locally
#############################

To build the docs locally, ensure that you have initialized a virtual
environment and installed Shrinkwrap's development dependencies within it:

.. code-block:: shell

    uv venv # Initialize a virtual environment in `${PWD}/.venv`
    uv sync # Install development dependencies from `pyproject.toml`

    # Note: `uv sync` will automatically run `uv venv`

Most IDEs will automatically identify and ask to set up this new virtual
environment but, if not, enter the environment with the following:

.. code-block:: shell

    . .venv/bin/activate

Once you are inside the virtual environment, generate the documentation with:

.. code-block:: shell

    sphinx-build -b html -a -W documentation public

Alternatively, you can run the following to generate the documentation
regardless of whether you are inside the virtual environment or not:

.. code-block:: shell

    uv run sphinx-build -b html -a -W documentation public

To render and explore the documentation, simply open `public/index.html` in a
web browser.
