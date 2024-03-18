..
 # Copyright (c) 2022, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

##################
Shrinkwrap Recipes
##################

This page contains an unordered list of Shrinkwrap usage examples intended to
demonstrate how Shrinkwrap can solve various problems.

******************************************
Override Component Version and/or Location
******************************************

You can change many, many configuration options by overlaying a config on top of
an existing config. Here we modify the revision and remote repository of the
TF-A component from its default (defined in tfa-base.yaml). You could also
specify the revision as a SHA or branch.

Create a file called ``my-overlay.yaml``:

.. code-block:: yaml

  build:
    tfa:
      repo:
	remote: https://github.com/ARM-software/arm-trusted-firmware.git
        revision: v2.9

Optionally, you can view the final, merged config as follows:

.. code-block:: shell

  shrinkwrap process --action=merge --overlay=my-overlay.yaml ns-preload.yaml

Now do a build, passing in the overlay:

.. code-block:: shell

  shrinkwrap build --overlay=my-overlay.yaml ns-preload.yaml

Finally, boot the config:

.. code-block:: shell

  shrinkwrap run --rtvar=KERNEL=path/to/Image ns-preload.yaml

***************************************
Reuse Existing Local Repo for Component
***************************************

By default, shrinkwrap will sync the git repos for all required components to a
private location (``<SHRINKWRAP_BUILD>/source/<config_name>/<component_name>``)
the first time you build a given config. However, sometimes you want shrinkwrap
to reuse a repo that already exists on your local system. In this case,
Shrinkwrap will build this source into its own private build tree, leaving the
source tree unmodified.

.. warning::

  Components support building in a tree separate from the source to differing
  degrees. For example, TF-A will always build fiptool in the source tree,
  although it will build all the FW components in the correct build tree. So
  depending on the component you are sharing source for, you may see some build
  artifacts appear.

Create a file called ``my-overlay.yaml``:

.. code-block:: yaml

  build:
    tfa:
      sourcedir: /path/to/my/tfa/git/repo

Now do a build, passing in the overlay:

.. code-block:: shell

  shrinkwrap build --overlay=my-overlay.yaml ns-preload.yaml

*******************************************
Changing Between Arm Architecture Revisions
*******************************************

Shrinkwrap comes with a set of configs that can be overlaid onto the primary
config in order to modify the targeted Arm architecture revision. These overlays
provide all the required modifications for the TF-A build configuration and the
FVP run configuration. Each architecture revision includes all mandatory
features associated with that extension as well as a selection of
sensible/common optional features.

``Armv8.0`` - ``Armv8.8`` and ``Armv9.0`` - ``Armv9.3`` are currently supported.
The yaml files are in the ``arch`` subdirectory of the config store. (You can
see them by running the ``inspect`` command with the ``--all`` option).

The below will build the ``ns-edk2`` config for Armv8.8 and run it on the FVP
configured for the same revision.

.. code-block:: shell

  shrinkwrap build ns-edk2.yaml --overlay=arch/v8.8.yaml
  shrinkwrap run ns-edk2.yaml --rtvar=KERNEL=path/to/Image

.. warning::

  Some components (notably TF-A) fail to incrementally build when changing their
  make parameters. Therefore, if you want to change the architecture revision
  for a config that has already been built, you must first clean tfa. See
  :ref:`userguide/recipes:Workaround for TF-A not Noticing Modified Build
  Params`.

**************************************
Explicitly Clean a Config or Component
**************************************

If the ``build`` command is invoked multiple times, Shrinkwrap will always
attempt to do an incremental build. This enables a developer to modify the
source and easily rebuild and run the result. However, sometimes it is useful to
explicitly clean a component (or all the components within a config) to force it
to be rebuilt from scratch. Shrinkwrap includes a ``clean`` command for this.

Clean an entire config (all components in config):

.. code-block:: shell

  shrinkwrap clean ns-edk2.yaml

Clean a specific set of components from a config (in this case, clean the tfa
and dt components):

.. code-block:: shell

  shrinkwrap clean ns-edk2.yaml --filter=tfa --filter=dt

Then rebuild the config and the cleaned components are rebuilt from scratch:

.. code-block:: shell

  shrinkwrap build ns-edk2.yaml

******************************************************
Workaround for TF-A not Noticing Modified Build Params
******************************************************

TF-A is not good at noticing when its build parameters change. If you have
already built TF-A, then attempt to do an incremental build with different
parameters, you rarely get what you expect. This happens a lot when using the
arch/vX.Y.yaml overlays, because different architecture revisions need to
specify different TF-A build parameters.

Work around this by explicitly cleaning TF-A when changing architecture
revisions:

.. code-block:: shell

  shrinkwrap build ns-edk2.yaml --overlay=arch/v8.7.yaml
  shrinkwrap clean ns-edk2.yaml --filter=tfa
  shrinkwrap build ns-edk2.yaml --overlay=arch/v9.3.yaml

************************
Use a Custom FVP Version
************************

By default, the ``run`` command will use the FVP that is bundled with the latest
published shrinkwrap docker image. Sometimes you might want to use a different
version though. In this case, the simplest approach is to install the FVP on
your system, ensuring that the required directories are in your PATH, and invoke
``shrinkwrap run`` with the ``null`` runtime.

Shrinkwrap expects both the FVP binary (e.g. FVP_Base_RevC-2xAEMvA) and its
plugins (e.g. ScalableVectorExtension.so) to be on your path. The example below
shows downloading and untaring the FVP and adding the required directories to
the PATH.

.. code-block:: shell

  wget -q -O FVP_Base_RevC-2xAEMvA_11.18_16_Linux64.tgz https://developer.arm.com/-/media/Files/downloads/ecosystem-models/FVP_Base_RevC-2xAEMvA_11.18_16_Linux64.tgz
  tar xf FVP_Base_RevC-2xAEMvA_11.18_16_Linux64.tgz
  export PATH=$PWD/Base_RevC_AEMvA_pkg/models/Linux64_GCC-9.3:$PWD/Base_RevC_AEMvA_pkg/plugins/Linux64_GCC-9.3:$PATH
  shrinkwrap build ns-edk2.yaml
  shrinkwrap --runtime=null run ns-edk2.yaml --rtvar=KERNEL=path/to/Image

******************************
Use an Alternative Device Tree
******************************

There are a couple of ways to use an alternative device tree:

All provided concrete configs that use a device tree, expose a DTB rtvar with a
default value. Users can override this value to provide an externally compiled
DTB at **run-time**.

Alternatively, the dt-base.yaml config fragment can be passed a parameter at
**build-time** that tells it to compile an alternative DTS file. dt-base.yaml
builds the device tree for the FVP_Base_RevC-2xAEMvA FVP by default and is used
by all the standard concrete configs that require a device tree and is available
for use in defining custom configs.

Add the following to a higher layer of the config:

.. code-block:: yaml

  build:
    dt:
      prebuild:
	- DTS=foundation-v8-gicv3-psci.dts

Note that dt-base.yaml only accepts names of dts files that already exist in the
device tree repo.

*******************************************************
Accessing the FVP over Network when using Docker/Podman
*******************************************************

When using the docker or podman runtimes, the FVP runs inside a container. This
has a different IP address to the host system. Shrinkwrap helpfully prints out
the runtime environment's IP address when starting the FVP. This is the IP
address you need to use to (e.g.) connect the debugger or to SSH into the hosted
Linux system.

********************
Boot Linux with ACPI
********************

``ns-edk2.yaml`` uses EDK2 to boot Linux, and defaults to using the Device Tree.
You can change the behaviour to boot with ACPI by passing ``acpi=force`` on the
comand line:

.. code-block:: shell

  shrinkwrap run ns-edk2.yaml --rtvar=KERNEL=path/to/Image --rtvar=CMDLINE="console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp acpi=force"

*************************************
Pass Overlay Directly on Command Line
*************************************

All of the previous examples that utilize overlays, put the overlay in a yaml
file and pass the file name on the command line. Here is an example that runs
the FVP as normal but saves all output from UART0 to uart0.log:

Create a file called ``my-overlay.yaml``:

.. code-block:: yaml

  run:
    params:
      -C bp.pl011_uart0.out_file: uart0.log

Now run the FVP, passing in the overlay:

.. code-block:: shell

  shrinkwrap run ns-edk2.yaml --rtvar=KERNEL=path/to/Image --overlay=my-overlay.yaml

However, it is also possible to pass an overlay, encoded as json, directly on
the command line, without the need for a file. This is useful when the overlay
is small. JSON allows the entire content to be encoded on a single line without
having to care about whitespace, so is suited to this purpose.

This is equivalent:

.. code-block:: shell

  shrinkwrap run ns-edk2.yaml --rtvar=KERNEL=path/to/Image --overlay='{"run":{"params":{"-C bp.pl011_uart0.out_file":"uart0.log"}}}'
