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


Once built, the user must get some of the generated artifacts into the FVP environment. This can either be done by copying them to the host's rootfs or by sharing them into the FVP using 9p.

For the time being, there is an issue in the linux kernel's handling of 9p which does not share correctly the guest image to the guest EFI, preventing the guest to boot. Copying the artifacts into the host's rootfs is the way to go. Something like the following example should work. For simplicity, this example reuses the guest filesystem generated with buildroot as the host's rootfs, after resizing it so that there is room for the guest's rootfs:

.. code-block:: shell

  $ cd ~/.shrinkwrap/package/cca-3world
  $ e2fsck -fp rootfs.ext2
  $ resize2fs rootfs.ext2 256M
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
  # ./lkvm run --realm --disable-sve --irqchip=gicv3-its --firmware KVMTOOL_EFI.fd -c 1 -m 512 --no-pvtime --force-pci --disk guest-disk.img --measurement-algo=sha256


Be patient while this boots to the UEFI shell. Navigate to "Boot Manager", then "UEFI Shell" and wait for the startup.nsh script to execute, which will launch the kernel. Continue to be patient, and eventually you will land at a login prompt. Login as "root" (no password).

This config also builds kvm-unit-tests, which can be run in the realm instead of Linux. It is also possible to launch Linux without using EDK2 as the guest FW.

When the linux kernel 9p issue will be fixed, the shared directory approach can be used. Simply boot the host with the SHARE rtvar. This only works for DT-based environments though:

.. code-block:: shell

  $ cd ~/.shrinkwrap/package/cca-3world
  $ shrinkwrap run cca-3world.yaml --rtvar ROOTFS=rootfs.ext2 --rtvar SHARE=.


Then, once the host has booted, log in as "root" (no password) and mount the shared folder to "/cca" and change dir to it. The realm guest can then be launched as previously:

.. code-block:: shell

  # mkdir /cca
  # mount -t 9p -o trans=virtio,version=9p2000.L FM /cca
  # cd /cca
  # ./lkvm run --realm --disable-sve --irqchip=gicv3-its --firmware KVMTOOL_EFI.fd -c 1 -m 512 --no-pvtime --force-pci --disk guest-disk.img --measurement-algo=sha256

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

============== ===============================================================
rtvar          default
============== ===============================================================
LOCAL_NET_PORT 8022
BL1            ${artifact:BL1}
FIP            ${artifact:FIP}
DTB            ${artifact:DTB}
CMDLINE        console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp
KERNEL         ${artifact:KERNEL}
ROOTFS         <empty>
SHARE          <empty>
EDK2FLASH      <empty>
============== ===============================================================

