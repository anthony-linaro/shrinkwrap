..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

################
bootwrapper.yaml
################

Description
###########

Best choice for: I have a linux-system.axf boot-wrapper and want to run it.

This config does not build any components (although shrinkwrap still requires you to build it before running). Instead the user is expected to provide a boot-wrapper executable (usually called linux-system.axf) as the BOOTWRAPPER rtvar, which will be executed in the FVP. A ROOTFS can be optionally provided. If present it is loaded into the virtio block device (/dev/vda).

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

============== =======
rtvar          default
============== =======
LOCAL_NET_PORT 8022   
BOOTWRAPPER    <null> 
ROOTFS         <empty>
============== =======

