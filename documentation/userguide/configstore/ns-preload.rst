..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

###############
ns-preload.yaml
###############

Description
###########

Best choice for: I just want to run Linux on FVP.

A simple, non-secure-only configuration where all components are preloaded into memory (TF-A's BL31, DTB and kernel). The system resets directly to BL31. Allows easy specification of a custom command line at build-time (via build.dt.params dictionary) and specification of the device tree, kernel image and rootfs at run-time (see rtvars).

By default (if not overriding the rtvars), the upstream kernel device tree is used along with a sensible command line that will set up the console for logging and attempt to mount the rootfs image from the FVP's virtio block device. However the default rootfs image is empty, so the kernel will panic when attempting to mount; the user must supply a rootfs if it is required that the kernel completes its boot. No default kernel image is supplied and the config will refuse to run unless it is explicitly specified.  Note: If specifying a custom dtb at runtime, this will also override any command line specified at build time, since the command line is added to the chosen node of the default dtb.

A directory can optionally be shared from the host system into the Linux environment running in the FVP. To do so, set the SHARE rtvar to the desired directory, then mount the share inside the FVP with the following (or automate it in fstab):

.. code-block:: shell

  # mkdir /share
  # mount -t 9p -o trans=virtio,version=9p2000.L FM /share

Build-Time Variables
####################

===== =======
btvar default
===== =======
===== =======

Run-Time Variables
##################

============== ================
rtvar          default
============== ================
BL31           ${artifact:BL31}
DTB            ${artifact:DTB}
KERNEL         <null>
LOCAL_NET_PORT 8022
ROOTFS         <empty>
SHARE          <empty>
============== ================

Components
##########

========= ================================================================================== =========
component repository                                                                         revision
========= ================================================================================== =========
dt        https://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git v6.17-dts
tfa       https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git                        v2.13.0
========= ================================================================================== =========

