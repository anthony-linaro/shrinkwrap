..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

###############
cca-3world.yaml
###############

Description
###########

Brings together a software stack to demonstrate Arm CCA running on FVP in a three-world configuration. Includes TF-A in root world, RMM in realm world, and EDK2 and Linux in Normal world on the host. Guests can be launched in-realm in a number of configurations using kvmtool. EDK2 can be optionally used as guest FW.

If the user provides an ext2/4 filesystem image via the GUEST_ROOTFS btvar, a guest disk image is created that includes a FAT16 partition containing the guest kernel (to be loaded by the guest EDK2 FW), and the provided filesystem as the rootfs. The user can provide their own filesystem image, or alternatively use a simple buildroot image created with buildroot.yaml:

.. code-block:: shell

  $ shrinkwrap build cca-3world.yaml --overlay buildroot.yaml --btvar GUEST_ROOTFS='${artifact:BUILDROOT}'


The user can also control the guest kernel command line parameters used on the guest disk image via the GUEST_CMDLINE btvar.

Once built, the user must get some of the generated artifacts into the FVP environment. This can either be done by copying them to the host's rootfs or by sharing them into the FVP using 9p.

For the time being, there is an issue in the linux kernel's handling of 9p which does not share correctly the guest image to the guest EFI, preventing the guest to boot. Copying the artifacts into the host's rootfs is the way to go. Something like the following example should work. For simplicity, this example reuses the guest filesystem generated with buildroot as the host's rootfs, after resizing it so that there is room for the guest's rootfs:

.. code-block:: shell

  $ cd ~/.shrinkwrap/package/cca-3world
  $ TOOLS_PATH=~/.shrinkwrap/build/build/cca-3world/buildroot/host/sbin
  $ $TOOLS_PATH/e2fsck -fp rootfs.ext2
  $ $TOOLS_PATH/resize2fs rootfs.ext2 256M
  $ sudo su
  # mkdir mnt
  # mount rootfs.ext2 mnt
  # mkdir mnt/cca
  # cp guest-disk.img KVMTOOL_EFI.fd lkvm mnt/cca/.
  # umount mnt
  # rm -rf mnt
  # exit


Now you can boot the host, using the rootfs we just modified, either using DT:

.. code-block:: shell

  $ shrinkwrap run cca-3world.yaml --rtvar ROOTFS=rootfs.ext2


Or alternatively, using ACPI:

.. code-block:: shell

  $ shrinkwrap run cca-3world.yaml -r ROOTFS=rootfs.ext2 --rtvar CMDLINE="mem=1G earlycon root=/dev/vda ip=dhcp acpi=force"


Finally, once the host has booted, log in as "root" (no password), and launch a realm using kvmtool from the /cca directory (that was created above):

.. code-block:: shell

  # cd /cca
  # ./lkvm run --realm --disable-sve --irqchip=gicv3-its --firmware KVMTOOL_EFI.fd -c 1 -m 512 --no-pvtime --force-pci --disk guest-disk.img --measurement-algo=sha256 --restricted_mem


Be patient while this boots to the UEFI shell. Navigate to "Boot Manager", then "UEFI Shell" and wait for the startup.nsh script to execute, which will launch the kernel. Continue to be patient, and eventually you will land at a login prompt. Login as "root" (no password).

When the linux kernel 9p issue will be fixed, the shared directory approach can be used. Simply boot the host with the SHARE rtvar. This only works for DT-based environments though:

.. code-block:: shell

  $ cd ~/.shrinkwrap/package/cca-3world
  $ shrinkwrap run cca-3world.yaml --rtvar ROOTFS=rootfs.ext2 --rtvar SHARE=.


Then, once the host has booted, log in as "root" (no password) and mount the shared folder to "/cca" and change dir to it. The realm guest can then be launched as previously:

.. code-block:: shell

  # mkdir /cca
  # mount -t 9p -o trans=virtio,version=9p2000.L FM /cca
  # cd /cca
  # ./lkvm run --realm --disable-sve --irqchip=gicv3-its --firmware KVMTOOL_EFI.fd -c 1 -m 512 --no-pvtime --force-pci --disk guest-disk.img --measurement-algo=sha256 --restricted_mem


It is also possible to launch Linux without using EDK2 as the guest FW:

.. code-block:: shell

  # ./lkvm run --realm --disable-sve --irqchip=gicv3-its -c 1 -m 512 --no-pvtime --force-pci --console virtio --kernel Image --disk guest-disk.img -p "console=hvc0 root=/dev/vda2" --measurement-algo=sha256 --restricted_mem


This config also builds kvm-unit-tests, which can be run in the realm instead of Linux:

.. code-block:: shell

  # cd /cca/kvm-unit-tests/arm
  # export PATH=/cca:$PATH
  # ./run-realm-tests

Build-Time Variables
####################

============= =============================== ==============
btvar         default                         options
============= =============================== ==============
EDK2_BUILD    RELEASE                         DEBUG, RELEASE
GUEST_CMDLINE root=/dev/vda2 acpi=force ip=on <required>
GUEST_ROOTFS  <empty>                         <required>
RMM_BASE      0xFDC00000                      <required>
RMM_BUILD     Release                         Debug, Release
RMM_LOG_LEVEL 40                              <required>
TFA_BUILD     release                         debug, release
TFA_LOG_LEVEL 40                              <required>
============= =============================== ==============

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
KERNEL         ${artifact:KERNEL}                                              <required>
LOCAL_NET_PORT 8022                                                            <required>
ROOTFS         <empty>                                                         <required>
SHARE          <empty>                                                         <required>
============== =============================================================== ==========

Components
##########

================= ================================================================================== ========================================
component         repository                                                                         revision
================= ================================================================================== ========================================
acpica            https://github.com/acpica/acpica.git                                               20260408
dt                https://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git v7.1-rc7-dts
edk2              https://git.gitlab.arm.com/linux-arm/edk2-cca.git                                  3223_arm_cca_v4
edk2-cca-guest    https://git.gitlab.arm.com/linux-arm/edk2-cca.git                                  3223_arm_cca_v4
edk2-platforms    https://git.gitlab.arm.com/linux-arm/edk2-platforms-cca.git                        3223_arm_cca_v4
kvm-unit-tests    https://gitlab.arm.com/linux-arm/kvm-unit-tests-cca                                cca/rmm-v1.0-rel0
kvmtool (dtc)     https://git.kernel.org/pub/scm/utils/dtc/dtc.git                                   v1.7.2
kvmtool (kvmtool) https://gitlab.arm.com/linux-arm/kvmtool-cca                                       cca/v11
linux             https://git.gitlab.arm.com/linux-arm/linux-cca.git                                 cca-host/v13
rmm               https://git.trustedfirmware.org/TF-RMM/tf-rmm.git                                  tf-rmm-v0.9.0
tfa               https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git                        5c33fafcddc09543dbfff97cac991847e8e4fda9
================= ================================================================================== ========================================

