..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

######################
qemu/qemu-ns-edk2.yaml
######################

Description
###########

Best choice for: I want to run Linux on QEMU SBSA, booting with EDK2, and have easy control over its command line.

Brings together TF-A and EDK2 to provide a simple non-secure world environment running on QEMU. Allows easy specification of the kernel image and command line, and rootfs at runtime (see rtvars).

By default a sensible command line is used that will set up the console for logging and attempt to mount the rootfs image from QEMU's virtio block device. No default kernel image is supplied and the config will refuse to run unless it is explicitly specified.

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

===== ======= =======
rtvar default options
===== ======= =======
===== ======= =======

Components
##########

============== =========================================================== ========================================
component      repository                                                  revision
============== =========================================================== ========================================
acpica         https://github.com/acpica/acpica.git                        20260408
edk2           https://github.com/tianocore/edk2.git                       edk2-stable202608
edk2-platforms https://github.com/tianocore/edk2-platforms.git             d672a812054e9d4fe5868a1ee65f438c10710535
qemu           https://gitlab.com/qemu-project/qemu.git                    v11.0.3
tfa            https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git 5c33fafcddc09543dbfff97cac991847e8e4fda9
============== =========================================================== ========================================

