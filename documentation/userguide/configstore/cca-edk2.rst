..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#############
cca-edk2.yaml
#############

Description
###########

Brings together TF-A, TF-RMM and EDK2 to provide a 3 world environment running on FVP. In this config TF-A is in Root World, TF-RMM is in Realm EL2 and EDK2 and Linux form the non-secure EL2. Allows easy specification of the kernel image and command line, and rootfs at runtime (see rtvars). ACPI is provided by UEFI. DT is enabled by default. Use 'acpi=force' command line option to enable ACPI boot.

By default (if not overriding the rtvars) a sensible command line is used that will set up the console for logging and attempt to mount the rootfs image from the FVP's virtio block device. However the default rootfs image is empty, so the kernel will panic when attempting to mount; the user must supply a rootfs if it is required that the kernel completes its boot. No default kernel image is supplied and the config will refuse to run unless it is explicitly specified.

Note that by default, UEFI variables are build time configured directing EDK2 to boot to the shell. This will cause startup.nsh to be executed and will start the kernel boot. This way everything is automatic. By default, all EDK2 output is muxed to stdout. If you prefer booting UEFI to its UI, override the the build pcd parameter `PcdUefiShellDefaultBootEnable` using the overlay and override terminals 'bp.terminal_0'.type to 'telnet'.

.. code-block:: shell

  $ shrinkwrap build cca-edk2.yaml


.. code-block:: shell

  $ shrinkwrap run cca-edk2.yaml --rtvar KERNEL=path/to/Image --rtvar ROOTFS=path/to/rootfs.img


When booting with device tree, a directory can optionally be shared from the host system into the Linux environment running in the FVP. To do so, set the SHARE rtvar to the desired directory, then mount the share inside the FVP with the following (or automate it in fstab):

.. code-block:: shell

  # mkdir /share
  # mount -t 9p -o trans=virtio,version=9p2000.L FM /share

Build-Time Variables
####################

============= ========== ==============
btvar         default    options
============= ========== ==============
EDK2_BUILD    RELEASE    DEBUG, RELEASE
RMM_BASE      0xFDC00000 <required>
RMM_BUILD     Release    Debug, Release
RMM_LOG_LEVEL 40         <required>
TFA_BUILD     release    debug, release
TFA_LOG_LEVEL 40         <required>
============= ========== ==============

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

============== ================================================================================== ===============
component      repository                                                                         revision
============== ================================================================================== ===============
acpica         https://github.com/acpica/acpica.git                                               20251212
dt             https://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git v6.19-dts
edk2           https://git.gitlab.arm.com/linux-arm/edk2-cca.git                                  3223_arm_cca_v4
edk2-platforms https://git.gitlab.arm.com/linux-arm/edk2-platforms-cca.git                        3223_arm_cca_v4
rmm            https://git.trustedfirmware.org/TF-RMM/tf-rmm.git                                  tf-rmm-v0.9.0
tfa            https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git                        v2.15.0
============== ================================================================================== ===============

