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

Build to wrap a provided kernel with boot-wrapper EL3 FW into linux-system.axf. Provide the kernel image via the KERNEL btvar, and optionally override the kernel command line by providing the CMDLINE btvar.

Then run the boot-wrapper (or pass a separately created one as the BOOTWRAPPER rtvar) in the FVP. A ROOTFS can be optionally provided. If present it is loaded into the virtio block device (/dev/vda).

Build-Time Variables
####################

======= =============================================================== ==========
btvar   default                                                         options
======= =============================================================== ==========
CMDLINE console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp <required>
DTB     ${artifact:DTB}                                                 <required>
KERNEL  <null>                                                          <required>
======= =============================================================== ==========

Run-Time Variables
##################

============== ======================= ==========
rtvar          default                 options
============== ======================= ==========
BOOTWRAPPER    ${artifact:BOOTWRAPPER} <required>
LOCAL_NET_PORT 8022                    <required>
ROOTFS         <empty>                 <required>
============== ======================= ==========

Components
##########

=========== ================================================================================== =========
component   repository                                                                         revision
=========== ================================================================================== =========
bootwrapper https://git.kernel.org/pub/scm/linux/kernel/git/mark/boot-wrapper-aarch64.git      master
dt          https://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git v6.19-dts
=========== ================================================================================== =========

