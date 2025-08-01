..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#############################
Compile Documentation Locally
#############################

To build the docs locally, the following packages need to be installed on the
host:

.. code-block:: shell

    sudo apt-get install python3-pip
    pip3 install -U -r documentation/requirements.txt

To build and generate the documentation in html format, run:

.. code-block:: shell

    sphinx-build -b html -a -W documentation public

To render and explore the documentation, simply open `public/index.html` in a
web browser.
