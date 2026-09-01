..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

##############
ffa-optee.yaml
##############

Description
###########

Brings together a software stack to demonstrate Arm FF-A running on FVP. Includes TF-A in secure EL3 running SPMD(Secure Partition Manager Dispatcher), with secure EL2 disabled and SPMC(Secure Partition Manager Core) inside OPTEE at secure EL1 and Linux in Normal world.

Build-Time Variables
####################

============= ======= ==============
btvar         default options
============= ======= ==============
EDK2_BUILD    RELEASE DEBUG, RELEASE
TFA_BUILD     release debug, release
TFA_LOG_LEVEL 40      <required>
============= ======= ==============

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
KERNEL         <null>                                                          <required>
LOCAL_NET_PORT 8022                                                            <required>
ROOTFS         <empty>                                                         <required>
SHARE          <empty>                                                         <required>
============== =============================================================== ==========

Components
##########

============== ================================================================================== ========================================
component      repository                                                                         revision
============== ================================================================================== ========================================
acpica         https://github.com/acpica/acpica.git                                               20260408
dt             https://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git v7.1-rc7-dts
edk2           https://github.com/tianocore/edk2.git                                              edk2-stable202608
edk2-platforms https://github.com/tianocore/edk2-platforms.git                                    d672a812054e9d4fe5868a1ee65f438c10710535
optee          https://github.com/OP-TEE/optee_os.git                                             4.9.0
tfa            https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git                        v2.15.0
============== ================================================================================== ========================================

