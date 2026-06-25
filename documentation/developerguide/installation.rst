..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#############################
Installation
#############################

If you are developing Shrinkwrap or contributing to the project, install it
in *editable* mode with development dependencies.

Clone the repository
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   git clone https://git.gitlab.arm.com/tooling/shrinkwrap.git
   cd shrinkwrap


All the following command are within an **active virtual environment**
(see :ref:`quickstart-virtualenv`).

Install in editable mode (development)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install --upgrade pip
   pip install -e ".[dev]"

This installs Shrinkwrap in editable mode along with additional dependencies
required for development, testing, and packaging.

Install documentation dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To build the documentation locally, install the documentation dependencies:

.. code-block:: bash

   pip install -e ".[docs]"

If you are both developing the code *and* building documentation, install both
extras together:

.. code-block:: bash

   pip install -e ".[dev,docs]"

.. note::

   Editable installs reflect changes in the source tree immediately.
   There is no need to reinstall after modifying the code or documentation.

To build and generate the documentation in html format, run (inside the virtual environment):

.. code-block:: shell

    sphinx-build -b html -a -W documentation public

To render and explore the documentation, simply open `public/index.html` in a
web browser.
