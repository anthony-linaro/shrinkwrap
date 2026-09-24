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

============== =============================== ==============
btvar          default                         options
============== =============================== ==============
EDK2_BUILD     RELEASE                         DEBUG, RELEASE
GUEST_CMDLINE  root=/dev/vda2 acpi=force ip=on <required>
GUEST_ROOTFS   <empty>                         <required>
RMM_BASE       0xFDC00000                      <required>
RMM_BUILD      Release                         Debug, Release
RMM_LOG_LEVEL  40                              <required>
TFA_BUILD      release                         debug, release
TFA_LOG_LEVEL  40                              <required>
TFTF_BUILD     release                         debug, release
TFTF_LOG_LEVEL 40                              <required>
TFTF_SUITE     standard                        <required>
============== =============================== ==============

Run-Time Variables
##################

============== =============================================================== ==========
rtvar          default                                                         options
============== =============================================================== ==========
BL1            ${artifact:BL1}                                                 <required>
CMDLINE        console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp <required>
DTB            ${artifact:DTB}                                                 <required>
EDK2FLASH      <empty>                                                         <required>
FIP            ${artifact:FIP}                                                 <required>
KERNEL         ${artifact:KERNEL}                                              <required>
LOCAL_NET_PORT 8022                                                            <required>
ROOTFS         <empty>                                                         <required>
SHARE          <empty>                                                         <required>
============== =============================================================== ==========

Components
##########

================= ================================================================================== ========================================
component         repository                                                                         revision
================= ================================================================================== ========================================
acpica            https://github.com/acpica/acpica.git                                               20260408
dt                https://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git v7.1-rc7-dts
edk2              https://git.gitlab.arm.com/linux-arm/edk2-cca.git                                  3223_arm_cca_v4
edk2-cca-guest    https://git.gitlab.arm.com/linux-arm/edk2-cca.git                                  3223_arm_cca_v4
edk2-platforms    https://git.gitlab.arm.com/linux-arm/edk2-platforms-cca.git                        3223_arm_cca_v4
hafnium           https://git.trustedfirmware.org/hafnium/hafnium.git                                v2.15.0
kvm-unit-tests    https://gitlab.arm.com/linux-arm/kvm-unit-tests-cca                                cca/rmm-v1.0-rel0
kvmtool (dtc)     https://git.kernel.org/pub/scm/utils/dtc/dtc.git                                   v1.7.2
kvmtool (kvmtool) https://gitlab.arm.com/linux-arm/kvmtool-cca                                       cca/v11
linux             https://git.gitlab.arm.com/linux-arm/linux-cca.git                                 cca-host/v13
rmm               https://git.trustedfirmware.org/TF-RMM/tf-rmm.git                                  tf-rmm-v0.9.0
tfa               https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git                        5c33fafcddc09543dbfff97cac991847e8e4fda9
tftf              https://git.trustedfirmware.org/TF-A/tf-a-tests.git                                v2.15.0
================= ================================================================================== ========================================

