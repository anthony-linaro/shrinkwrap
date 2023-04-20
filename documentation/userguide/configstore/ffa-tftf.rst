..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#############
ffa-tftf.yaml
#############

Description
###########

Brings together a software stack to demonstrate Arm FF-A running on FVP. Includes TF-A in secure EL3, Hafnium in secure EL2 and some demo TF-A test secure partitions.

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
EDK2FLASH      ${artifact:EDK2FLASH}                                          
============== ===============================================================

