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

