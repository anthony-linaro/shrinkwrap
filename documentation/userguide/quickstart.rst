..
 # Copyright (c) 2022, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#################
Quick Start Guide
#################

******************
Install Shrinkwrap
******************

Packages don't yet exist, so currently the only way to install Shrinkwrap is to
install its dependencies and clone the git repository.

Shrinkwrap is tested on **Ubuntu 20.04** although other Linux distributions are
likely to JustWork (TM). macOS is also known to work when using the docker
runtime as long as Docker Desktop has first been installed.

Shrinkwrap requires **at least Python 3.6.9**. Older versions may work, but are
not tested.

.. code-block:: shell

  sudo apt-get install git netcat-openbsd python3 python3-pip telnet
  sudo pip3 install pyyaml termcolor tuxmake
  git clone https://git.gitlab.arm.com/tooling/shrinkwrap.git
  export PATH=$PWD/shrinkwrap/shrinkwrap:$PATH

If using a Python version older than 3.9, you will also need to install the
``graphlib-backport`` pip package:

.. code-block:: shell

  sudo pip3 install graphlib-backport

-------------------------------
If using Docker Runtime Backend
-------------------------------

If Docker was not previously set up on your system, you will need to install the
package, create a 'docker' group and add your user to it. This allows shrinkwrap
to interact with docker without needing sudo. For more information see `docker
linux-postinstall <https://docs.docker.com/engine/install/linux-postinstall/>`_.

.. code-block:: shell

  sudo apt-get install docker.io
  sudo groupadd docker
  sudo usermod -aG docker $USER
  # Log out/log in for change to take effect

-------------------------------
If using Podman Runtime Backend
-------------------------------

.. note::

  Podman is only available within Ubuntu repositories from Ubuntu 20.10 and
  newer. See `podman installation instructions
  <https://podman.io/getting-started/installation>`_ for installation methods
  for other distributions.

.. code-block:: shell

  sudo apt-get install podman

------------------------------
Optional Environment Variables
------------------------------

Shrinkwrap consumes the following set of optional environment variables:

================== ===================== ====
name               default               description
================== ===================== ====
SHRINKWRAP_CONFIG  <None>                Colon-separated list of paths to config stores. Configs are searched for relative to the current directory as well as relative to these paths.
SHRINKWRAP_BUILD   ~/.shrinkwrap/build   Location where config builds are performed. Each config has its own subdirectory, with further subdirectories for each of its components.
SHRINKWRAP_PACKAGE ~/.shrinkwrap/package Location where config builds are packaged to. When running a config, it is done from the package location.
================== ===================== ====

***************************************************
Guided Tour: Configure a platform and boot a kernel
***************************************************

This section provides a guided tour of Shrinkwrap, using a common use case of
building required platform FW and configuring the FVP for Armv9.3 and booting a
kernel. This example uses EDK2 (UEFI) but many other options are available.

.. note::

  By default, the below commands will use the docker runtime and automatically
  download and use the appropriate container image from Docker Hub.
  Alternatively, you can choose to run with the ``null`` runtime by providing
  ``--runtime=null`` (between ``shrinkwrap`` and the sub-command). This will
  cause all commands to be executed on the native system. Users are responsible
  for setting up the environment in this case. Or if you have chosen to use
  Podman as the runtime backend, add ``--runtime=podman``.

First invoke the tool to view help:

.. code-block:: shell

  shrinkwrap --help
  shrinkwrap <command> --help

Now, inspect the available configs:

.. code-block:: shell

  shrinkwrap inspect

This will show all of the (concrete) configs in the config store. The below
output shows a sample. Notice that each config lists its runtime variables
("rtvars") along with their default values. ``None`` means there is no default
and the user must provide a value when running the config. (A "concrete" config
is one that is deemed ready-to-use out-of-the-box. Whereas a config "fragment"
is a piece of config that is usually composed with others and configured into a
concrete config. You can view non-concrete fragments by providing extra args).

.. raw:: html

  <p>
  <details>
  <summary><a>Expand</a></summary>

.. code-block:: none

  name:                bootwrapper.yaml

  description:         Best choice for: I have a linux-system.axf boot-wrapper and
                       want to run it.

                       This config does not build any components (although
                       shrinkwrap still requires you to build it before running).
                       Instead the user is expected to provide a boot-wrapper
                       executable (usually called linux-system.axf) as the
                       BOOTWRAPPER rtvar, which will be executed in the FVP. A
                       ROOTFS can be optionally provided. If present it is loaded
                       into the virtio block device (/dev/vda).

  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BOOTWRAPPER:            None
                       ROOTFS:

  --------------------------------------------------------------------------------

  name:                cca-3world.yaml

  description:         Brings together a software stack to demonstrate Arm CCA
                       running on FVP in a three-world configuration. Includes
                       TF-A in root world, RMM in realm world, and Linux in Normal
                       world.

                       In order to launch realm VMs, the user must bring their own
                       rootfs that contains a realm-aware kvmtool and an RSI-aware
                       guest kernel image.

  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BL1:                    ${artifact:BL1}
                       FIP:                    ${artifact:FIP}
                       KERNEL:                 ${artifact:KERNEL}
                       ROOTFS:

  --------------------------------------------------------------------------------

  name:                cca-4world.yaml

  description:         Brings together a software stack to demonstrate Arm CCA
                       running on FVP in a four-world configuration. Includes TF-A
                       in root world, Hafnium and some demo secure partitions in
                       secure world, RMM in realm world, and Linux in Normal
                       world.

                       In order to launch realm VMs, the user must bring their own
                       rootfs that contains a realm-aware kvmtool and an RSI-aware
                       guest kernel image.

  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BL1:                    ${artifact:BL1}
                       FIP:                    ${artifact:FIP}
                       KERNEL:                 ${artifact:KERNEL}
                       ROOTFS:

  --------------------------------------------------------------------------------

  name:                ffa-tftf.yaml

  description:         Brings together a software stack to demonstrate Arm FF-A
                       running on FVP. Includes TF-A in secure EL3, Hafnium in
                       secure EL2 and some demo TF-A test secure partitions.

  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BL1:                    ${artifact:BL1}
                       FIP:                    ${artifact:FIP}
                       DTB:                    ${artifact:DTB}
                       CMDLINE:                console=ttyAMA0
                                               earlycon=pl011,0x1c090000
                                               root=/dev/vda ip=dhcp
                       KERNEL:                 None
                       ROOTFS:
                       EDK2FLASH:

  --------------------------------------------------------------------------------

  name:                ns-edk2.yaml

  description:         Best choice for: I want to run Linux on FVP, booting with
                       ACPI/DT, and have easy control over its command line.

                       Brings together TF-A and EDK2 to provide a simple non-
                       secure world environment running on FVP. Allows easy
                       specification of the kernel image and command line, and
                       rootfs at runtime (see rtvars). ACPI is provided by UEFI.

                       An extra rtvar is added (DTB) which allows specification of
                       a custom device tree. By default (if not overriding the
                       rtvar), the upstream kernel device tree is used. DT is
                       enabled by default. Use 'acpi=force' to enable ACPI boot.

                       By default (if not overriding the rtvars) a sensible
                       command line is used that will set up the console for
                       logging and attempt to mount the rootfs image from the
                       FVP's virtio block device. However the default rootfs image
                       is empty, so the kernel will panic when attempting to
                       mount; the user must supply a rootfs if it is required that
                       the kernel completes its boot. No default kernel image is
                       supplied and the config will refuse to run unless it is
                       explicitly specified.

                       Note that by default, UEFI variables are build time
                       configured directing EDK2 to boot to the shell. This will
                       cause startup.nsh to be executed and will start the kernel
                       boot. This way everything is automatic. By default, all
                       EDK2 output is muxed to stdout. If you prefer booting UEFI
                       to its UI, override the the build pcd parameter
                       `PcdUefiShellDefaultBootEnable` using the overlay and
                       override terminals 'bp.terminal_0'.type to 'telnet'.
  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BL1:                    ${artifact:BL1}
                       FIP:                    ${artifact:FIP}
                       DTB:                    ${artifact:DTB}
                       CMDLINE:                console=ttyAMA0
                                               earlycon=pl011,0x1c090000
                                               root=/dev/vda ip=dhcp
                       KERNEL:                 None
                       ROOTFS:
                       EDK2FLASH:

  --------------------------------------------------------------------------------

  name:                ns-preload.yaml

  description:         Best choice for: I just want to run Linux on FVP.

                       A simple, non-secure-only configuration where all
                       components are preloaded into memory (TF-A's BL31, DTB and
                       kernel). The system resets directly to BL31. Allows easy
                       specification of a custom command line at build-time (via
                       build.dt.params dictionary) and specification of the device
                       tree, kernel image and rootfs at run-time (see rtvars).

                       By default (if not overriding the rtvars), the upstream
                       kernel device tree is used along with a sensible command
                       line that will set up the console for logging and attempt
                       to mount the rootfs image from the FVP's virtio block
                       device. However the default rootfs image is empty, so the
                       kernel will panic when attempting to mount; the user must
                       supply a rootfs if it is required that the kernel completes
                       its boot. No default kernel image is supplied and the
                       config will refuse to run unless it is explicitly
                       specified.  Note: If specifying a custom dtb at runtime,
                       this will also override any command line specified at build
                       time, since the command line is added to the chosen node of
                       the default dtb.

  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BL31:                   ${artifact:BL31}
                       DTB:                    ${artifact:DTB}
                       KERNEL:                 None
                       ROOTFS:

.. raw:: html

  </details>
  </p>

Now build the ``ns-edk2.yaml`` config. This allows booting a kernel on FVP,
using edk2 as the bootloader (it uses DT by default, but can be made to use ACPI
by passing ``acpi=force`` at runtime). (optionally add ``--verbose`` to see all
the output from the component build systems).

.. code-block:: shell

  shrinkwrap build --overlay=arch/v9.3.yaml ns-edk2.yaml

This will sync all the required repos, build the components and package the
artifacts.

.. warning::

  By default, Shrinkwrap will sync all component repos to the revision specified
  in the config on every build invocation. If you have made changes in the
  working directory, your CHANGES WILL BE LOST! You can override this behaviour
  so that Shrinkwrap just builds whatever is in the working directory by adding
  ``--no-sync <component>`` or ``--no-sync-all`` to the command line.

Alternatively, pass ``--dry-run`` to view the shell script that would have been
run:

.. code-block:: shell

  shrinkwrap build --overlay=arch/v9.3.yaml --dry-run ns-edk2.yaml

.. raw:: html

  <p>
  <details>
  <summary><a>Expand</a></summary>

.. code-block:: none

  #!/bin/bash
  # SHRINKWRAP AUTOGENERATED SCRIPT.

  # Exit on error.
  set -e

  # Remove old package.
  rm -rf /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2.yaml > /dev/null 2>&1 || true
  rm -rf /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2 > /dev/null 2>&1 || true

  # Create directory structure.
  mkdir -p /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2/dt
  mkdir -p /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2/edk2
  mkdir -p /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2/tfa
  mkdir -p /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2

  # Sync git repo for config=ns-edk2 component=dt.
  pushd /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2
  if [ ! -d "dt/.git" ] || [ -f "./.dt_sync" ]; then
  	rm -rf dt > /dev/null 2>&1 || true
  	mkdir -p .
  	touch ./.dt_sync
  	git clone --quiet git://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git dt
  	pushd dt
  	git checkout --quiet --force v6.1-dts
  	git submodule --quiet update --init --checkout --recursive --force
  	popd
  	rm ./.dt_sync
  fi
  popd

  # Sync git repo for config=ns-edk2 component=edk2.
  pushd /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2
  if [ ! -d "edk2/edk2/.git" ] || [ -f "edk2/.edk2_sync" ]; then
  	rm -rf edk2/edk2 > /dev/null 2>&1 || true
  	mkdir -p edk2
  	touch edk2/.edk2_sync
  	git clone --quiet https://github.com/tianocore/edk2.git edk2/edk2
  	pushd edk2/edk2
  	git checkout --quiet --force edk2-stable202211
  	git submodule --quiet update --init --checkout --recursive --force
  	popd
  	rm edk2/.edk2_sync
  fi
  if [ ! -d "edk2/edk2-platforms/.git" ] || [ -f "edk2/.edk2-platforms_sync" ]; then
  	rm -rf edk2/edk2-platforms > /dev/null 2>&1 || true
  	mkdir -p edk2
  	touch edk2/.edk2-platforms_sync
  	git clone --quiet https://github.com/tianocore/edk2-platforms.git edk2/edk2-platforms
  	pushd edk2/edk2-platforms
  	git checkout --quiet --force 20e07099d8f11889d101dd710ca85001be20e179
  	git submodule --quiet update --init --checkout --recursive --force
  	popd
  	rm edk2/.edk2-platforms_sync
  fi
  if [ ! -d "edk2/acpica/.git" ] || [ -f "edk2/.acpica_sync" ]; then
  	rm -rf edk2/acpica > /dev/null 2>&1 || true
  	mkdir -p edk2
  	touch edk2/.acpica_sync
  	git clone --quiet https://github.com/acpica/acpica.git edk2/acpica
  	pushd edk2/acpica
  	git checkout --quiet --force R10_20_22
  	git submodule --quiet update --init --checkout --recursive --force
  	popd
  	rm edk2/.acpica_sync
  fi
  popd


  # Sync git repo for config=ns-edk2 component=tfa.
  pushd /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2
  if [ ! -d "tfa/.git" ] || [ -f "./.tfa_sync" ]; then
  	rm -rf tfa > /dev/null 2>&1 || true
  	mkdir -p .
  	touch ./.tfa_sync
  	git clone --quiet https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git tfa
  	pushd tfa
  	git checkout --quiet --force v2.8.0
  	git submodule --quiet update --init --checkout --recursive --force
  	popd
  	rm ./.tfa_sync
  fi
  popd

  # Build for config=ns-edk2 component=dt.
  export CROSS_COMPILE=aarch64-none-elf-
  pushd /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2/dt
  DTS=fvp-base-revc.dts
  INITRD_START=
  INITRD_END=
  DT_BASENAME=$(basename ${DTS} .dts)
  DTB_INTER=src/arm64/arm/${DT_BASENAME}.dtb
  DTB_FINAL=/data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/dt/dt_bootargs.dtb
  make CPP=${CROSS_COMPILE}cpp -j28 ${DTB_INTER}
  CHOSEN=
  if [ ! -z "" ]; then
  CHOSEN="${CHOSEN}bootargs = \"\";\n"
  fi
  if [ ! -z "${INITRD_START}" ] && [ ! -z "${INITRD_END}" ]; then
  INITRD_START_HI=$(((${INITRD_START} >> 32) & 0xffffffff))
  INITRD_START_LO=$((${INITRD_START} & 0xffffffff))
  INITRD_END_HI=$(((${INITRD_END} >> 32) & 0xffffffff))
  INITRD_END_LO=$((${INITRD_END} & 0xffffffff))
  CHOSEN="${CHOSEN}linux,initrd-start = <${INITRD_START_HI} ${INITRD_START_LO}>;\n"
  CHOSEN="${CHOSEN}linux,initrd-end = <${INITRD_END_HI} ${INITRD_END_LO}>;\n"
  fi
  if [ -z "${CHOSEN}" ]; then
  cp ${DTB_INTER} ${DTB_FINAL}
  else
  ( dtc -q -O dts -I dtb ${DTB_INTER} ; echo -e "/ { chosen { ${CHOSEN} }; };" ) | dtc -q -O dtb -o ${DTB_FINAL}
  fi
  if [ "${DTS}" = "fvp-base-revc.dts" ]; then
  OVERLAY="/ {
    reserved-memory {
      fw: fw@7C000000 {
        reg = <0x00000000 0xFC000000 0 0x04000000>;
        no-map;
      };
    };
    timer {
      clock-frequency = <100000000>;
    };
    psci {
      compatible = \"arm,psci-1.0\", \"arm,psci-0.2\";
      max-pwr-lvl = <2>;
    };
    cpus {
      cpu-map {
        cluster0 {
          core0 { cpu = <&{/cpus/cpu@0}>; };
          core1 { cpu = <&{/cpus/cpu@100}>; };
          core2 { cpu = <&{/cpus/cpu@200}>; };
          core3 { cpu = <&{/cpus/cpu@300}>; };
        };
        cluster1 {
          core0 { cpu = <&{/cpus/cpu@10000}>; };
          core1 { cpu = <&{/cpus/cpu@10100}>; };
          core2 { cpu = <&{/cpus/cpu@10200}>; };
          core3 { cpu = <&{/cpus/cpu@10300}>; };
        };
      };
    };
    bus@8000000 {
      motherboard-bus@8000000 {
        iofpga-bus@300000000 {
          virtio@200000 {
            status = \"okay\";
          };
        };
      };
    };
  };"
  ( dtc -q -O dts -I dtb ${DTB_FINAL} ; echo -e "${OVERLAY}" ) | dtc -q -O dtb -o ${DTB_FINAL}
  fi
  popd

  # Build for config=ns-edk2 component=edk2.
  export CROSS_COMPILE=aarch64-none-elf-
  pushd /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2/edk2
  export WORKSPACE=/data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2/edk2
  export GCC5_AARCH64_PREFIX=$CROSS_COMPILE
  export PACKAGES_PATH=$WORKSPACE/edk2:$WORKSPACE/edk2-platforms
  export IASL_PREFIX=$WORKSPACE/acpica/generate/unix/bin/
  export PYTHON_COMMAND=/usr/bin/python3
  make -j28 -C acpica
  source edk2/edksetup.sh
  make -j28 -C edk2/BaseTools
  build -n 28 -D EDK2_OUT_DIR=/data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/edk2 -a AARCH64 -t GCC5 -p Platform/ARM/VExpressPkg/ArmVExpress-FVP-AArch64.dsc -b RELEASE
  popd


  # Build for config=ns-edk2 component=tfa.
  export CROSS_COMPILE=aarch64-none-elf-
  pushd /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/source/ns-edk2/tfa
  make BUILD_BASE=/data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/tfa PLAT=fvp DEBUG=0 LOG_LEVEL=40 ARM_DISABLE_TRUSTED_WDOG=1 FVP_HW_CONFIG_DTS=fdts/fvp-base-gicv3-psci-1t.dts BL33=/data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/edk2/RELEASE_GCC5/FV/FVP_AARCH64_EFI.fd ARM_ARCH_MINOR=5 ENABLE_SVE_FOR_NS=1 ENABLE_SVE_FOR_SWD=1 CTX_INCLUDE_PAUTH_REGS=1 BRANCH_PROTECTION=1 CTX_INCLUDE_MTE_REGS=1 ENABLE_FEAT_HCX=1 CTX_INCLUDE_AARCH32_REGS=0 ENABLE_SME_FOR_NS=1 ENABLE_SME_FOR_SWD=1 all fip
  popd

  # Copy artifacts for config=ns-edk2.
  cp /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/dt/dt_bootargs.dtb /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2/dt_bootargs.dtb
  cp /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/edk2/RELEASE_GCC5/FV/FVP_AARCH64_EFI.fd /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2/FVP_AARCH64_EFI.fd
  cp /data_nvme0n1/ryarob01/shrinkwrap_demo/shrinkwrap/config/edk2-flash.img /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2/edk2-flash.img
  cp /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/tfa/fvp/release/bl1.bin /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2/bl1.bin
  cp /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/tfa/fvp/release/bl2.bin /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2/bl2.bin
  cp /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/tfa/fvp/release/bl31.bin /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2/bl31.bin
  cp /data_nvme0n1/ryarob01/shrinkwrap_demo/live/build/build/ns-edk2/tfa/fvp/release/fip.bin /data_nvme0n1/ryarob01/shrinkwrap_demo/live/package/ns-edk2/fip.bin

.. raw:: html

  </details>
  </p>

Now start the FVP. We will pass our own kernel and rootfs disk image as runtime
variables. A config can define any number of runtime variables which may have
default values (see ``inspect`` command above). If a variable has no default
value, then the user must provide a value when invoking the ``run`` command. The
``ns-edk2.yaml`` config requires the user to provide a kernel, but the rootfs
is optional. If the rootfs was omitted, the kernel would boot to the point where
it attempts to mount the rootfs then panic (which is sufficient for some
development use cases!).

.. code-block:: shell

  shrinkwrap run --rtvar=KERNEL=path/to/Image --rtvar=ROOTFS=path/to/rootfs.img ns-edk2.yaml

This starts the FVP and multiplexes all the UART terminals to stdout and
forwards stdin to the ``tfa+linux`` uart terminal. This allows the user to
interact directly with the FVP in a terminal without the need for a GUI setup:

.. raw:: html

  <p>
  <details>
  <summary><a>Expand</a></summary>

.. code-block:: none

  [       fvp ] terminal_0: Listening for serial connection on port 5000
  [       fvp ] terminal_1: Listening for serial connection on port 5001
  [       fvp ] terminal_2: Listening for serial connection on port 5002
  [       fvp ] terminal_3: Listening for serial connection on port 5003
  [       fvp ]
  [       fvp ] Info: FVP_Base_RevC_2xAEMvA: FVP_Base_RevC_2xAEMvA.bp.flashloader0: FlashLoader: Loaded 100 kB from file '<root>/package/ns-preload/fip.bin'
  [       fvp ]
  [       fvp ] Info: FVP_Base_RevC_2xAEMvA: FVP_Base_RevC_2xAEMvA.bp.secureflashloader: FlashLoader: Loaded 30 kB from file '<root>/package/ns-preload/bl1.bin'
  [       fvp ]
  [       fvp ] libdbus-1.so.3: cannot open shared object file: No such file or directory
  [       fvp ] libdbus-1.so.3: cannot open shared object file: No such file or directory
  [ tfa+linux ] NOTICE:  BL31: v2.7(release):v2.7.0-391-g9dedc1ab2
  [ tfa+linux ] NOTICE:  BL31: Built : 09:41:20, Sep 15 2022
  [ tfa+linux ] INFO:    GICv3 with legacy support detected.
  [ tfa+linux ] INFO:    ARM GICv3 driver initialized in EL3
  [ tfa+linux ] INFO:    Maximum SPI INTID supported: 255
  [ tfa+linux ] INFO:    Configuring TrustZone Controller
  [ tfa+linux ] INFO:    Total 8 regions set.
  [ tfa+linux ] INFO:    BL31: Initializing runtime services
  [ tfa+linux ] INFO:    BL31: Preparing for EL3 exit to normal world
  [ tfa+linux ] INFO:    Entry point address = 0x84000000
  [ tfa+linux ] INFO:    SPSR = 0x3c9
  [ tfa+linux ] [    0.000000] Booting Linux on physical CPU 0x0000000000 [0x410fd0f0]
  [ tfa+linux ] [    0.000000] Linux version 5.15.0-rc2-gca9bfbea162d (ryarob01@e125769) (aarch64-none-linux-gnu-gcc (GNU Toolchain for the A-profile Architecture 9.2-2019.12 (arm-9.10)) 9.2.1 20191025, GNU ld (GNU Toolchain for the A-profile Architecture 9.2-2019.12 (arm-9.10)) 2.33.1.20191209) #1 SMP PREEMPT Thu Aug 4 11:31:55 BST 2022
  [ tfa+linux ] [    0.000000] Machine model: FVP Base RevC
  [ tfa+linux ] [    0.000000] earlycon: pl11 at MMIO 0x000000001c090000 (options '')
  [ tfa+linux ] [    0.000000] printk: bootconsole [pl11] enabled
  [ tfa+linux ] [    0.000000] efi: UEFI not found.
  [ tfa+linux ] [    0.000000] Reserved memory: created DMA memory pool at 0x0000000018000000, size 8 MiB
  [ tfa+linux ] [    0.000000] OF: reserved mem: initialized node vram@18000000, compatible id shared-dma-pool
  [ tfa+linux ] [    0.000000] NUMA: No NUMA configuration found
  [ tfa+linux ] [    0.000000] NUMA: Faking a node at [mem 0x0000000080000000-0x00000008ffffffff]
  [ tfa+linux ] [    0.000000] NUMA: NODE_DATA [mem 0x8ff7efc00-0x8ff7f1fff]
  [ tfa+linux ] [    0.000000] Zone ranges:
  [ tfa+linux ] [    0.000000]   DMA      [mem 0x0000000080000000-0x00000000ffffffff]
  [ tfa+linux ] [    0.000000]   DMA32    empty
  [ tfa+linux ] [    0.000000]   Normal   [mem 0x0000000100000000-0x00000008ffffffff]
  [ tfa+linux ] [    0.000000] Movable zone start for each node
  [ tfa+linux ] [    0.000000] Early memory node ranges
  [ tfa+linux ] [    0.000000]   node   0: [mem 0x0000000080000000-0x00000000ffffffff]
  [ tfa+linux ] [    0.000000]   node   0: [mem 0x0000000880000000-0x00000008ffffffff]
  [ tfa+linux ] [    0.000000] Initmem setup node 0 [mem 0x0000000080000000-0x00000008ffffffff]
  [ tfa+linux ] [    0.000000] cma: Reserved 32 MiB at 0x00000000fe000000
  [ tfa+linux ] [    0.000000] psci: probing for conduit method from DT.
  [ tfa+linux ] [    0.000000] psci: PSCIv1.1 detected in firmware.
  [ tfa+linux ] [    0.000000] psci: Using standard PSCI v0.2 function IDs
  [ tfa+linux ] [    0.000000] psci: MIGRATE_INFO_TYPE not supported.
  [ tfa+linux ] [    0.000000] psci: SMC Calling Convention v1.2
  ...

.. raw:: html

  </details>
  </p>

Alternatively, you could have passed ``--dry-run`` to see the FVP invocation script:

.. code-block:: shell

  shrinkwrap run --rtvar=KERNEL=path/to/Image --rtvar=ROOTFS=path/to/rootfs.img --dry-run ns-edk2.yaml

.. raw:: html

  <p>
  <details>
  <summary><a>Expand</a></summary>

.. code-block:: none

  #!/bin/bash
  # SHRINKWRAP AUTOGENERATED SCRIPT.

  # Exit on error.
  set -e

  # Execute prerun commands.
  SEMIHOSTDIR=`mktemp -d`
  function finish { rm -rf $SEMIHOSTDIR; }
  trap finish EXIT
  cp ./path/to/Image ${SEMIHOSTDIR}/Image
  cp <root>/package/ns-edk2/fvp-base-revc_args.dtb ${SEMIHOSTDIR}/fdt.dtb
  cat <<EOF > ${SEMIHOSTDIR}/startup.nsh
  Image dtb=fdt.dtb console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp
  EOF

  # Run the model.
  FVP_Base_RevC-2xAEMvA \
      --plugin=$(which ScalableVectorExtension.so) \
      --stat \
      -C SVE.ScalableVectorExtension.has_sme2=1 \
      -C SVE.ScalableVectorExtension.has_sme=1 \
      -C SVE.ScalableVectorExtension.has_sve2=1 \
      -C bp.dram_metadata.is_enabled=1 \
      -C bp.dram_size=4 \
      -C bp.flashloader0.fname=<root>/package/ns-edk2/fip.bin \
      -C bp.flashloader1.fname=<root>/package/ns-edk2/edk2-flash.img \
      -C bp.hostbridge.userNetPorts=8022=22 \
      -C bp.hostbridge.userNetworking=1 \
      -C bp.refcounter.non_arch_start_at_default=1 \
      -C bp.refcounter.use_real_time=0 \
      -C bp.secure_memory=1 \
      -C bp.secureflashloader.fname=<root>/package/ns-edk2/bl1.bin \
      -C bp.smsc_91c111.enabled=1 \
      -C bp.terminal_0.mode=telnet \
      -C bp.terminal_0.start_telnet=0 \
      -C bp.terminal_1.mode=raw \
      -C bp.terminal_1.start_telnet=0 \
      -C bp.terminal_2.mode=raw \
      -C bp.terminal_2.start_telnet=0 \
      -C bp.terminal_3.mode=raw \
      -C bp.terminal_3.start_telnet=0 \
      -C bp.ve_sysregs.exit_on_shutdown=1 \
      -C bp.virtioblockdevice.image_path=./path/to/rootfs.img \
      -C bp.vis.disable_visualisation=1 \
      -C cache_state_modelled=0 \
      -C cluster0.NUM_CORES=4 \
      -C cluster0.PA_SIZE=48 \
      -C cluster0.check_memory_attributes=0 \
      -C cluster0.clear_reg_top_eret=2 \
      -C cluster0.cpu0.semihosting-cwd=${SEMIHOSTDIR} \
      -C cluster0.ecv_support_level=2 \
      -C cluster0.enhanced_pac2_level=3 \
      -C cluster0.gicv3.cpuintf-mmap-access-level=2 \
      -C cluster0.gicv3.without-DS-support=1 \
      -C cluster0.gicv4.mask-virtual-interrupt=1 \
      -C cluster0.has_16k_granule=1 \
      -C cluster0.has_amu=1 \
      -C cluster0.has_arm_v8-1=1 \
      -C cluster0.has_arm_v8-2=1 \
      -C cluster0.has_arm_v8-3=1 \
      -C cluster0.has_arm_v8-4=1 \
      -C cluster0.has_arm_v8-5=1 \
      -C cluster0.has_arm_v8-6=1 \
      -C cluster0.has_arm_v8-7=1 \
      -C cluster0.has_arm_v8-8=1 \
      -C cluster0.has_arm_v9-0=1 \
      -C cluster0.has_arm_v9-1=1 \
      -C cluster0.has_arm_v9-2=1 \
      -C cluster0.has_arm_v9-3=1 \
      -C cluster0.has_branch_target_exception=1 \
      -C cluster0.has_brbe=1 \
      -C cluster0.has_brbe_v1p1=1 \
      -C cluster0.has_const_pac=1 \
      -C cluster0.has_hpmn0=1 \
      -C cluster0.has_large_system_ext=1 \
      -C cluster0.has_large_va=1 \
      -C cluster0.has_rndr=1 \
      -C cluster0.max_32bit_el=0 \
      -C cluster0.memory_tagging_support_level=3 \
      -C cluster0.pmb_idr_external_abort=1 \
      -C cluster0.stage12_tlb_size=1024 \
      -C cluster1.NUM_CORES=4 \
      -C cluster1.PA_SIZE=48 \
      -C cluster1.check_memory_attributes=0 \
      -C cluster1.clear_reg_top_eret=2 \
      -C cluster1.ecv_support_level=2 \
      -C cluster1.enhanced_pac2_level=3 \
      -C cluster1.gicv3.cpuintf-mmap-access-level=2 \
      -C cluster1.gicv3.without-DS-support=1 \
      -C cluster1.gicv4.mask-virtual-interrupt=1 \
      -C cluster1.has_16k_granule=1 \
      -C cluster1.has_amu=1 \
      -C cluster1.has_arm_v8-1=1 \
      -C cluster1.has_arm_v8-2=1 \
      -C cluster1.has_arm_v8-3=1 \
      -C cluster1.has_arm_v8-4=1 \
      -C cluster1.has_arm_v8-5=1 \
      -C cluster1.has_arm_v8-6=1 \
      -C cluster1.has_arm_v8-7=1 \
      -C cluster1.has_arm_v8-8=1 \
      -C cluster1.has_arm_v9-0=1 \
      -C cluster1.has_arm_v9-1=1 \
      -C cluster1.has_arm_v9-2=1 \
      -C cluster1.has_arm_v9-3=1 \
      -C cluster1.has_branch_target_exception=1 \
      -C cluster1.has_brbe=1 \
      -C cluster1.has_brbe_v1p1=1 \
      -C cluster1.has_const_pac=1 \
      -C cluster1.has_hpmn0=1 \
      -C cluster1.has_large_system_ext=1 \
      -C cluster1.has_large_va=1 \
      -C cluster1.has_rndr=1 \
      -C cluster1.max_32bit_el=0 \
      -C cluster1.memory_tagging_support_level=3 \
      -C cluster1.pmb_idr_external_abort=1 \
      -C cluster1.stage12_tlb_size=1024 \
      -C pci.pci_smmuv3.mmu.SMMU_AIDR=2 \
      -C pci.pci_smmuv3.mmu.SMMU_IDR0=4592187 \
      -C pci.pci_smmuv3.mmu.SMMU_IDR1=6291458 \
      -C pci.pci_smmuv3.mmu.SMMU_IDR3=5908 \
      -C pci.pci_smmuv3.mmu.SMMU_IDR5=4294902901 \
      -C pci.pci_smmuv3.mmu.SMMU_ROOT_IDR0=3 \
      -C pci.pci_smmuv3.mmu.SMMU_ROOT_IIDR=1083 \
      -C pci.pci_smmuv3.mmu.SMMU_S_IDR1=2684354562 \
      -C pci.pci_smmuv3.mmu.SMMU_S_IDR2=0 \
      -C pci.pci_smmuv3.mmu.SMMU_S_IDR3=0 \
      -C pci.pci_smmuv3.mmu.root_register_page_offset=131072 \
      -C pctl.startup=0.0.0.0

.. raw:: html

  </details>
  </p>

Overlays are an important concept for Shrinkwrap. An overlay is a config
fragment (either a yaml file or a json-encoded string) that can be passed
separately on the command line and forms the top layer of the config. In this
way, it can override or add any required configuration. You could achieve the
same effect by creating a new config and specifying the main config as a layer
in that new config, but with an overlay, you can apply a config fragment to many
different existing configs without the need to write a new config file each
time. You can see overlays being using in the above commands to target a
specific Arm architecture revision (v9.3 in the example). You can change the
targeted architecture just by changing the overlay. There are many other places
where overlays come in handy. See :ref:`userguide/recipes:Shrinkwrap Recipes`
for more examples.

You will notice in the examples above, that only ``build`` commands include the
overlay and ``run`` commands don't specify it. This is because the final config
used for building is packaged in the built package, so when running the package,
the presence of the overlay is implicit. However, a user could choose to provide
an extra overlay at ``run`` time, that affects only the runtime portion to
customize even further if desired.

For debug purposes, you can see a final, merged config by using the ``process``
command:

.. code-block:: shell

  shrinkwrap process --action=merge --overlay=arch/v9.3.yaml ns-edk2.yaml

.. raw:: html

  <p>
  <details>
  <summary><a>Expand</a></summary>

.. code-block:: none

  %YAML 1.2
  ---
  name: ns-edk2
  fullname: ns-edk2.yaml
  description: 'Best choice for: I want to run Linux on FVP, booting with ACPI/DT, and
    have easy control over its command line.

    Brings together TF-A and EDK2 to provide a simple non-secure world environment running
    on FVP. Allows easy specification of the kernel image and command line, and rootfs
    at runtime (see rtvars). ACPI is provided by UEFI.

    An extra rtvar is added (DTB) which allows specification of a custom device tree.
    By default (if not overriding the rtvar), the upstream kernel device tree is used.
    DT is enabled by default. Use ''acpi=force'' to enable ACPI boot.

    By default (if not overriding the rtvars) a sensible command line is used that will
    set up the console for logging and attempt to mount the rootfs image from the FVP''s
    virtio block device. However the default rootfs image is empty, so the kernel will
    panic when attempting to mount; the user must supply a rootfs if it is required
    that the kernel completes its boot. No default kernel image is supplied and the
    config will refuse to run unless it is explicitly specified.

    Note that by default, UEFI variables are build time configured directing EDK2
    to boot to the shell. This will cause startup.nsh to be executed and will
    start the kernel boot. This way everything is automatic. By default, all EDK2
    output is muxed to stdout. If you prefer booting UEFI to its UI, override the
    the build pcd parameter `PcdUefiShellDefaultBootEnable` using the overlay
    and override terminals 'bp.terminal_0'.type to 'telnet'.
  concrete: true
  graph: {}
  build:
    dt:
      repo:
        .:
          remote: git://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git
          revision: v6.1-dts
      sourcedir: null
      builddir: null
      toolchain: aarch64-none-elf-
      params: {}
      prebuild:
      - DTS=fvp-base-revc.dts
      - INITRD_START=
      - INITRD_END=
      build:
      - DT_BASENAME=$$(basename $${DTS} .dts)
      - DTB_INTER=src/arm64/arm/$${DT_BASENAME}.dtb
      - DTB_FINAL=${param:builddir}/dt_bootargs.dtb
      - make CPP=$${CROSS_COMPILE}cpp -j${param:jobs} $${DTB_INTER}
      - CHOSEN=
      - if [ ! -z "${param:join_equal}" ]; then
      - CHOSEN="$${CHOSEN}bootargs = \"${param:join_equal}\";\n"
      - fi
      - if [ ! -z "$${INITRD_START}" ] && [ ! -z "$${INITRD_END}" ]; then
      - INITRD_START_HI=$$((($${INITRD_START} >> 32) & 0xffffffff))
      - INITRD_START_LO=$$(($${INITRD_START} & 0xffffffff))
      - INITRD_END_HI=$$((($${INITRD_END} >> 32) & 0xffffffff))
      - INITRD_END_LO=$$(($${INITRD_END} & 0xffffffff))
      - CHOSEN="$${CHOSEN}linux,initrd-start = <$${INITRD_START_HI} $${INITRD_START_LO}>;\n"
      - CHOSEN="$${CHOSEN}linux,initrd-end = <$${INITRD_END_HI} $${INITRD_END_LO}>;\n"
      - fi
      - if [ -z "$${CHOSEN}" ]; then
      - cp $${DTB_INTER} $${DTB_FINAL}
      - else
      - ( dtc -q -O dts -I dtb $${DTB_INTER} ; echo -e "/ { chosen { $${CHOSEN} }; };"
        ) | dtc -q -O dtb -o $${DTB_FINAL}
      - fi
      - if [ "$${DTS}" = "fvp-base-revc.dts" ]; then
      - "OVERLAY=\"/ {\n  reserved-memory {\n    fw: fw@7C000000 {\n      reg = <0x00000000\
        \ 0xFC000000 0 0x04000000>;\n      no-map;\n    };\n  };\n  timer {\n    clock-frequency\
        \ = <100000000>;\n  };\n  psci {\n    compatible = \\\"arm,psci-1.0\\\", \\\"\
        arm,psci-0.2\\\";\n    max-pwr-lvl = <2>;\n  };\n  cpus {\n    cpu-map {\n \
        \     cluster0 {\n        core0 { cpu = <&{/cpus/cpu@0}>; };\n        core1\
        \ { cpu = <&{/cpus/cpu@100}>; };\n        core2 { cpu = <&{/cpus/cpu@200}>;\
        \ };\n        core3 { cpu = <&{/cpus/cpu@300}>; };\n      };\n      cluster1\
        \ {\n        core0 { cpu = <&{/cpus/cpu@10000}>; };\n        core1 { cpu = <&{/cpus/cpu@10100}>;\
        \ };\n        core2 { cpu = <&{/cpus/cpu@10200}>; };\n        core3 { cpu =\
        \ <&{/cpus/cpu@10300}>; };\n      };\n    };\n  };\n  bus@8000000 {\n    motherboard-bus@8000000\
        \ {\n      iofpga-bus@300000000 {\n        virtio@200000 {\n          status\
        \ = \\\"okay\\\";\n        };\n      };\n    };\n  };\n};\""
      - ( dtc -q -O dts -I dtb $${DTB_FINAL} ; echo -e "$${OVERLAY}" ) | dtc -q -O dtb
        -o $${DTB_FINAL}
      - fi
      postbuild: []
      artifacts:
        DTB: ${param:builddir}/dt_bootargs.dtb
    edk2:
      repo:
        edk2:
          remote: https://github.com/tianocore/edk2.git
          revision: edk2-stable202211
        edk2-platforms:
          remote: https://github.com/tianocore/edk2-platforms.git
          revision: 20e07099d8f11889d101dd710ca85001be20e179
        acpica:
          remote: https://github.com/acpica/acpica.git
          revision: R10_20_22
      sourcedir: null
      builddir: null
      toolchain: aarch64-none-elf-
      params:
        -a: AARCH64
        -t: GCC5
        -p: Platform/ARM/VExpressPkg/ArmVExpress-FVP-AArch64.dsc
        -b: RELEASE
        --pcd: PcdShellDefaultDelay=0
        ' --pcd': PcdUefiShellDefaultBootEnable=1
      prebuild:
      - export WORKSPACE=${param:sourcedir}
      - export GCC5_AARCH64_PREFIX=$$CROSS_COMPILE
      - export PACKAGES_PATH=$$WORKSPACE/edk2:$$WORKSPACE/edk2-platforms
      - export IASL_PREFIX=$$WORKSPACE/acpica/generate/unix/bin/
      - export PYTHON_COMMAND=/usr/bin/python3
      build:
      - make -j${param:jobs} -C acpica
      - source edk2/edksetup.sh
      - make -j${param:jobs} -C edk2/BaseTools
      - build -n ${param:jobs} -D EDK2_OUT_DIR=${param:builddir} ${param:join_space}
      postbuild: []
      artifacts:
        EDK2: ${param:builddir}/RELEASE_GCC5/FV/FVP_AARCH64_EFI.fd
    tfa:
      repo:
        .:
          remote: https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git
          revision: v2.8.0
      sourcedir: null
      builddir: null
      toolchain: aarch64-none-elf-
      params:
        PLAT: fvp
        DEBUG: 0
        LOG_LEVEL: 40
        ARM_DISABLE_TRUSTED_WDOG: 1
        FVP_HW_CONFIG_DTS: fdts/fvp-base-gicv3-psci-1t.dts
        BL33: ${artifact:EDK2}
        ARM_ARCH_MINOR: 5
        ENABLE_SVE_FOR_NS: 1
        ENABLE_SVE_FOR_SWD: 1
        CTX_INCLUDE_PAUTH_REGS: 1
        BRANCH_PROTECTION: 1
        CTX_INCLUDE_MTE_REGS: 1
        ENABLE_FEAT_HCX: 1
        CTX_INCLUDE_AARCH32_REGS: 0
        ENABLE_SME_FOR_NS: 1
        ENABLE_SME_FOR_SWD: 1
      prebuild: []
      build:
      - make BUILD_BASE=${param:builddir} ${param:join_equal} all fip
      postbuild: []
      artifacts:
        BL1: ${param:builddir}/fvp/release/bl1.bin
        BL2: ${param:builddir}/fvp/release/bl2.bin
        BL31: ${param:builddir}/fvp/release/bl31.bin
        FIP: ${param:builddir}/fvp/release/fip.bin
  artifacts: {}
  run:
    name: FVP_Base_RevC-2xAEMvA
    rtvars:
      LOCAL_NET_PORT:
        type: string
        value: 8022
      BL1:
        type: path
        value: ${artifact:BL1}
      FIP:
        type: path
        value: ${artifact:FIP}
      DTB:
        type: path
        value: ${artifact:DTB}
      CMDLINE:
        type: string
        value: console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp
      KERNEL:
        type: path
        value: null
      ROOTFS:
        type: path
        value: ''
      EDK2FLASH:
        type: path
        value: ''
    params:
      -C bp.dram_size: 4
      -C cluster0.NUM_CORES: 4
      -C cluster1.NUM_CORES: 4
      -C cluster0.PA_SIZE: 48
      -C cluster1.PA_SIZE: 48
      --stat: null
      -C bp.vis.disable_visualisation: 1
      -C bp.dram_metadata.is_enabled: 1
      -C bp.refcounter.non_arch_start_at_default: 1
      -C bp.refcounter.use_real_time: 0
      -C bp.secure_memory: 1
      -C bp.ve_sysregs.exit_on_shutdown: 1
      -C pctl.startup: 0.0.0.0
      -C cluster0.clear_reg_top_eret: 2
      -C cluster1.clear_reg_top_eret: 2
      -C bp.smsc_91c111.enabled: 1
      -C bp.hostbridge.userNetworking: 1
      -C bp.hostbridge.userNetPorts: ${rtvar:LOCAL_NET_PORT}=22
      -C cache_state_modelled: 0
      -C cluster0.stage12_tlb_size: 1024
      -C cluster1.stage12_tlb_size: 1024
      -C cluster0.check_memory_attributes: 0
      -C cluster1.check_memory_attributes: 0
      -C cluster0.gicv3.cpuintf-mmap-access-level: 2
      -C cluster1.gicv3.cpuintf-mmap-access-level: 2
      -C cluster0.gicv3.without-DS-support: 1
      -C cluster1.gicv3.without-DS-support: 1
      -C cluster0.gicv4.mask-virtual-interrupt: 1
      -C cluster1.gicv4.mask-virtual-interrupt: 1
      -C pci.pci_smmuv3.mmu.SMMU_AIDR: 2
      -C pci.pci_smmuv3.mmu.SMMU_IDR0: 4592187
      -C pci.pci_smmuv3.mmu.SMMU_IDR1: 6291458
      -C pci.pci_smmuv3.mmu.SMMU_IDR3: 5908
      -C pci.pci_smmuv3.mmu.SMMU_IDR5: 4294902901
      -C pci.pci_smmuv3.mmu.SMMU_S_IDR1: 2684354562
      -C pci.pci_smmuv3.mmu.SMMU_S_IDR2: 0
      -C pci.pci_smmuv3.mmu.SMMU_S_IDR3: 0
      -C bp.virtio_rng.enabled: 1
      -C bp.secureflashloader.fname: ${rtvar:BL1}
      -C bp.flashloader0.fname: ${rtvar:FIP}
      -C bp.virtioblockdevice.image_path: ${rtvar:ROOTFS}
      -C cluster0.cpu0.semihosting-cwd: $${SEMIHOSTDIR}
      -C bp.flashloader1.fname: ${rtvar:EDK2FLASH}
      -C cluster0.has_16k_granule: 1
      -C cluster1.has_16k_granule: 1
      -C cluster0.has_arm_v8-1: 1
      -C cluster1.has_arm_v8-1: 1
      -C cluster0.has_large_system_ext: 1
      -C cluster1.has_large_system_ext: 1
      -C cluster0.has_arm_v8-2: 1
      -C cluster1.has_arm_v8-2: 1
      -C cluster0.has_large_va: 1
      -C cluster1.has_large_va: 1
      --plugin: $$(which ScalableVectorExtension.so)
      -C cluster0.has_arm_v8-3: 1
      -C cluster1.has_arm_v8-3: 1
      -C cluster0.has_arm_v8-4: 1
      -C cluster1.has_arm_v8-4: 1
      -C cluster0.has_amu: 1
      -C cluster1.has_amu: 1
      -C cluster0.has_arm_v8-5: 1
      -C cluster1.has_arm_v8-5: 1
      -C cluster0.has_branch_target_exception: 1
      -C cluster1.has_branch_target_exception: 1
      -C cluster0.has_rndr: 1
      -C cluster1.has_rndr: 1
      -C cluster0.memory_tagging_support_level: 3
      -C cluster1.memory_tagging_support_level: 3
      -C cluster0.has_arm_v8-6: 1
      -C cluster1.has_arm_v8-6: 1
      -C cluster0.ecv_support_level: 2
      -C cluster1.ecv_support_level: 2
      -C cluster0.enhanced_pac2_level: 3
      -C cluster1.enhanced_pac2_level: 3
      -C cluster0.has_arm_v8-7: 1
      -C cluster1.has_arm_v8-7: 1
      -C cluster0.has_arm_v8-8: 1
      -C cluster1.has_arm_v8-8: 1
      -C cluster0.has_const_pac: 1
      -C cluster1.has_const_pac: 1
      -C cluster0.has_hpmn0: 1
      -C cluster1.has_hpmn0: 1
      -C cluster0.pmb_idr_external_abort: 1
      -C cluster1.pmb_idr_external_abort: 1
      -C cluster0.has_arm_v9-0: 1
      -C cluster1.has_arm_v9-0: 1
      -C cluster0.max_32bit_el: 0
      -C cluster1.max_32bit_el: 0
      -C SVE.ScalableVectorExtension.has_sve2: 1
      -C cluster0.has_arm_v9-1: 1
      -C cluster1.has_arm_v9-1: 1
      -C cluster0.has_arm_v9-2: 1
      -C cluster1.has_arm_v9-2: 1
      -C cluster0.has_brbe: 1
      -C cluster1.has_brbe: 1
      -C SVE.ScalableVectorExtension.has_sme: 1
      -C cluster0.has_arm_v9-3: 1
      -C cluster1.has_arm_v9-3: 1
      -C cluster0.has_brbe_v1p1: 1
      -C cluster1.has_brbe_v1p1: 1
    prerun:
    - SEMIHOSTDIR=`mktemp -d`
    - function finish { rm -rf $$SEMIHOSTDIR; }
    - trap finish EXIT
    - cp ${rtvar:KERNEL} $${SEMIHOSTDIR}/Image
    - cp ${rtvar:DTB} $${SEMIHOSTDIR}/fdt.dtb
    - cat <<EOF > $${SEMIHOSTDIR}/startup.nsh
    - Image dtb=fdt.dtb ${rtvar:CMDLINE}
    - EOF
    run: []
    terminals:
      bp.terminal_0:
        friendly: ''
        port_regex: 'terminal_0: Listening for serial connection on port (\d+)'
        type: stdinout
        no_color: true
        no_escapes: 'EFI stub: Booting Linux Kernel...'
      bp.terminal_1:
        friendly: edk2
        port_regex: 'terminal_1: Listening for serial connection on port (\d+)'
        type: stdout
      bp.terminal_2:
        friendly: term2
        port_regex: 'terminal_2: Listening for serial connection on port (\d+)'
        type: stdout
      bp.terminal_3:
        friendly: term3
        port_regex: 'terminal_3: Listening for serial connection on port (\d+)'
        type: stdout

.. raw:: html

  </details>
  </p>
