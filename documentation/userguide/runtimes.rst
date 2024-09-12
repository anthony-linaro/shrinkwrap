..
 # Copyright (c) 2022, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#########
Run-Times
#########

Shrinkwrap uses a "runtime" to execute all of its shell commands and allows the
user to choose which runtime to use. Both the design and implementation of this
is borrowed from `Tuxmake <https://tuxmake.org>`_.

Shrinkwrap supports the following set of runtimes:

============ ====
runtime      description
============ ====
null         Shell commands are executed natively on the user's system. The user is responsible for ensuring the the required toolchain, environment variables and any other dependencies are set up.
docker       (default). Shell commands are executed in a docker container. By default, the official shrinkwrap image will be pulled and used, which contains all dependencies already setup.
docker-local Like docker, but will only look for the container image on the local system. Will not attempt to pull over the network.
podman       Shell commands are executed in a podman container. By default, the official shrinkwrap image will be pulled and used, which contains all dependencies already setup.
podman-local Like podman, but will only look for the container image on the local system. Will not attempt to pull over the network.
============ ====

The desired runtime can be specified using the ``--runtime`` option, which is a
top-level argument (must come before the command):

.. code-block:: shell

  shrinkwrap --runtime=<name> ...

If using a container runtime (anything other than null), a custom image can
optionally be specified. If omitted, the official shrinkwrap image is used:

.. code-block:: shell

  shrinkwrap --runtime=<name> --image=<name> ...

************************
Container Image Variants
************************

Shrinkwrap runs on both x86_64 and aarch64 architectures, and provides multiarch
container images so that the correct variant is automatically selected for your
platform. Images are automatically downloaded by shrinkwrap when the ``docker``
or ``podman`` runtime is selected. Images are available on Docker Hub and can be
freely downloaded without the need for an account.

=============================================== ====
image name                                      description
=============================================== ====
docker.io/shrinkwraptool/base-slim-nofvp:latest Contains all toolchains and other dependencies required to build all standard configs. Can be used as a base to create an image with a custom FVP.
docker.io/shrinkwraptool/base-slim:latest       (default). As per ``shrinkwraptool/base-slim-nofvp:latest`` but also contains the Base_RevC-2xAEMvA FVP. This is sufficient for most use cases and is much smaller than the ``full`` variant.
docker.io/shrinkwraptool/base-full-nofvp:latest Builds upon ``shrinkwraptool/base-slim:latest``, adding aarch32 toolchains (both arm-none-eabi and arm-linux-gnueabihf). These are not needed for standard configs, but will be required if creating a custom config that includes (e.g.) SCP FW. Separated out due to big size increase.
docker.io/shrinkwraptool/base-full:latest       As per ``shrinkwraptool/base-full-nofvp:latest`` but also contains the Base_RevC-2xAEMvA FVP.
=============================================== ====

********************
Runtime Requirements
********************

The best way to understand the requirements for the packages available within
the runtime is to look at the dockerfiles for the official shrinkwrap images.
These are available at ``docker/Dockerfile.*``.

*****************************
Build Container Image Locally
*****************************

If you have a need to build the shrinkwrap container images on your local system,
you can do it as follows:

.. code-block:: shell

  cd docker
  ./build.sh --version local

This will build a set of images called:

- ``shrinkwraptool/base-slim:local-<ARCH>``
- ``shrinkwraptool/base-slim-nofvp:local-<ARCH>``
- ``shrinkwraptool/base-full:local-<ARCH>``
- ``shrinkwraptool/base-full-nofvp:local-<ARCH>``

To use a locally built image, call shrinkwrap as follows if running on an x86_64
system:

.. code-block:: shell

  shrinkwrap --runtime=<name>-local --image=shrinkwraptool/base-slim:local-x86_64 ...

Or like this if running on an aarch64 system:

.. code-block:: shell

  shrinkwrap --runtime=<name>-local --image=shrinkwraptool/base-slim:local-aarch64 ...

where <name> is either docker or podman. Note that because the image is not on
Docker Hub, the <name>-local runtime is required to prevent Shrinkwrap from
erroneously trying to download an update.
