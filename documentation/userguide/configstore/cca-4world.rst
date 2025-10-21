..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

###############
cca-4world.yaml
###############

Description
###########

Builds on cca-3world.yaml, and adds support for running Hafnium along with some secure partitions in Secure World. Build with:

.. code-block:: shell

  $ shrinkwrap build cca-4world.yaml --overlay buildroot.yaml --btvar GUEST_ROOTFS='${artifact:BUILDROOT}'


Then run the model with:

.. code-block:: shell

  $ cd ~/.shrinkwrap/package/cca-4world
  $ shrinkwrap run cca-4world.yaml --rtvar ROOTFS=rootfs.ext2 --rtvar SHARE=.


Once the host has booted, log in as "root" (no password).

Secure partitions can be enumerated by:

.. code-block:: shell

  # cat /sys/devices/arm-ffa-*/uuid
  b4b5671e-4a90-4fe1-b81f-fb13dae1dacb
  d1582309-f023-47b9-827c-4464f5578fc8
  79b55c73-1d8c-44b9-8593-61e1770ad8d2
  eaba83d8-baaf-4eaf-8144-f7fdcbe544a7


See cca-3worlds.yaml config :ref:`userguide/configstore/cca-3world:description` if willing to launch a realm using kvmtool.

Build-Time Variables
####################

============= ===============================
btvar         default
============= ===============================
GUEST_CMDLINE root=/dev/vda2 acpi=force ip=on
GUEST_ROOTFS  <empty>
============= ===============================

Run-Time Variables
##################

============== ===============================================================
rtvar          default
============== ===============================================================
BL1            ${artifact:BL1}
CMDLINE        console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp
DTB            ${artifact:DTB}
EDK2FLASH      <empty>
FIP            ${artifact:FIP}
KERNEL         ${artifact:KERNEL}
LOCAL_NET_PORT 8022
ROOTFS         <empty>
SHARE          <empty>
============== ===============================================================

Components
##########

===================== ================================================================================== =================
component             repository                                                                         revision
===================== ================================================================================== =================
acpica                https://github.com/acpica/acpica.git                                               R09_27_24
dt                    https://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git v6.14-dts
edk2 (edk2)           https://git.gitlab.arm.com/linux-arm/edk2-cca.git                                  3223_arm_cca_v4
edk2 (edk2-platforms) https://git.gitlab.arm.com/linux-arm/edk2-platforms-cca.git                        3223_arm_cca_v4
edk2-cca-guest (edk2) https://git.gitlab.arm.com/linux-arm/edk2-cca.git                                  3223_arm_cca_v4
hafnium               https://git.trustedfirmware.org/hafnium/hafnium.git                                v2.13.0
kvm-unit-tests        https://gitlab.arm.com/linux-arm/kvm-unit-tests-cca                                cca/rmm-v1.0-rel0
kvmtool (dtc)         https://git.kernel.org/pub/scm/utils/dtc/dtc.git                                   v1.6.1
kvmtool (kvmtool)     https://gitlab.arm.com/linux-arm/kvmtool-cca                                       cca/v6
linux                 https://git.gitlab.arm.com/linux-arm/linux-cca.git                                 cca-host/v8
rmm                   https://git.trustedfirmware.org/TF-RMM/tf-rmm.git                                  tf-rmm-v0.7.0
tfa                   https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git                        v2.13.0
tftf                  https://git.trustedfirmware.org/TF-A/tf-a-tests.git                                v2.13.0
===================== ================================================================================== =================

