..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

###############
cca-4world.yaml
###############

Description
###########

Builds on cca-3world.yaml, but adds support for running Hafnium along with some secure partitions in Secure World.

Concrete
########

True

Build-Time Variables
####################

============ =======
btvar        default
============ =======
GUEST_ROOTFS <empty>
============ =======

Run-Time Variables
##################

============== ======================================================================
rtvar          default                                                               
============== ======================================================================
LOCAL_NET_PORT 8022                                                                  
BL1            ${artifact:BL1}                                                       
FIP            ${artifact:FIP}                                                       
DTB            ${artifact:DTB}                                                       
CMDLINE        mem=1G console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp
KERNEL         ${artifact:KERNEL}                                                    
ROOTFS         <empty>                                                               
EDK2FLASH      ${artifact:EDK2FLASH}                                                 
============== ======================================================================

