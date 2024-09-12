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

Concrete
########

True

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
LOCAL_NET_PORT 8022
BL1            ${artifact:BL1}
FIP            ${artifact:FIP}
DTB            ${artifact:DTB}
CMDLINE        console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp
KERNEL         <null>
ROOTFS         <empty>
SHARE          <empty>
EDK2FLASH      <empty>
============== ===============================================================

