..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

############
ns-edk2.yaml
############

Description
###########

Best choice for: I want to run Linux on FVP, booting with ACPI/DT, and have easy control over its command line.

Brings together TF-A and EDK2 to provide a simple non-secure world environment running on FVP. Allows easy specification of the kernel image and command line, and rootfs at runtime (see rtvars). ACPI is provided by UEFI.

An extra rtvar is added (DTB) which allows specification of a custom device tree. By default (if not overriding the rtvar), the upstream kernel device tree is used. DT is enabled by default. Use 'acpi=force' to enable ACPI boot.

By default (if not overriding the rtvars) a sensible command line is used that will set up the console for logging and attempt to mount the rootfs image from the FVP's virtio block device. However the default rootfs image is empty, so the kernel will panic when attempting to mount; the user must supply a rootfs if it is required that the kernel completes its boot. No default kernel image is supplied and the config will refuse to run unless it is explicitly specified.

Note that by default, UEFI variables are build time configured directing EDK2 to boot to the shell. This will cause startup.nsh to be executed and will start the kernel boot. This way everything is automatic. By default, all EDK2 output is muxed to stdout. If you prefer booting UEFI to its UI, override the the build pcd parameter `PcdUefiShellDefaultBootEnable` using the overlay and override terminals 'bp.terminal_0'.type to 'telnet'.

When booting with device tree, a directory can optionally be shared from the host system into the Linux environment running in the FVP. To do so, set the SHARE rtvar to the desired directory, then mount the share inside the FVP with the following (or automate it in fstab):

.. code-block:: shell

  # mkdir /share
  # mount -t 9p -o trans=virtio,version=9p2000.L FM /share

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
acpica         https://github.com/acpica/acpica.git                                               20251212
dt             https://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git v6.19-dts
edk2           https://github.com/tianocore/edk2.git                                              edk2-stable202511
edk2-platforms https://github.com/tianocore/edk2-platforms.git                                    0f527ebcef4e111586bf7a62b0f24a7f6c7dc2a4
tfa            https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git                        v2.14.0
============== ================================================================================== ========================================

