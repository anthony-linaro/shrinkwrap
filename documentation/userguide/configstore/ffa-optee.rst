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

===== =======
btvar default
===== =======
===== =======

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
KERNEL         <null>
LOCAL_NET_PORT 8022
ROOTFS         <empty>
SHARE          <empty>
============== ===============================================================

Components
##########

===================== ================================================================================== ========================================
component             repository                                                                         revision
===================== ================================================================================== ========================================
acpica                https://github.com/acpica/acpica.git                                               R09_27_24
dt                    https://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git v6.14-dts
edk2 (edk2)           https://github.com/tianocore/edk2.git                                              95d8a1c255cfb8e063d679930d08ca6426eb5701
edk2 (edk2-platforms) https://github.com/tianocore/edk2-platforms.git                                    5b5885ef3e30a2896f23afd6df3d2dae8d5e51b3
optee                 https://github.com/OP-TEE/optee_os.git                                             4.3.0
tfa                   https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git                        v2.13.0
===================== ================================================================================== ========================================

