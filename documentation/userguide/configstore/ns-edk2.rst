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

Note that by default, a pre-canned flash image is loaded into the model, which contains UEFI variables directing EDK2 to boot to the shell. This will cause startup.nsh to be executed and will start the kernel boot. This way everything is automatic. By default, all EDK2 output is muxed to stdout. If you prefer booting UEFI to its UI, override the EDK2FLASH rtvar with an empty string and override terminals.'bp.terminal_0'.type to 'telnet'.

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

