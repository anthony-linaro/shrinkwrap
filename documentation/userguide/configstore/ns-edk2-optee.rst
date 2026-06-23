..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

##################
ns-edk2-optee.yaml
##################

Description
###########

Brings together a software stack to demonstrate OPTEE in secure EL1 with TF-A in secure EL3 but without FF-A and secure EL2(Hafnium). Secure partition dispatcher exists inside OPTEE.

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
edk2           https://github.com/tianocore/edk2.git                                              edk2-stable202605
edk2-platforms https://github.com/tianocore/edk2-platforms.git                                    ae058185e12591a9a49e5895e90ca52936851973
optee          https://github.com/OP-TEE/optee_os.git                                             4.9.0
tfa            https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git                        v2.15.0
============== ================================================================================== ========================================

