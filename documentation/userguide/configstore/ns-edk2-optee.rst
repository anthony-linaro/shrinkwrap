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
EDK2FLASH      ${artifact:EDK2FLASH}
============== ===============================================================

