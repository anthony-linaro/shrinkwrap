..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

########
rfa.yaml
########

Description
###########

Rusted-Firmware-A. This configuration runs RF-A with the default features along with its normal-world and secure-world tests.

Build-Time Variables
####################

===== =======
btvar default
===== =======
===== =======

Run-Time Variables
##################

============== ===============
rtvar          default
============== ===============
BL1            ${artifact:BL1}
FIP            ${artifact:FIP}
LOCAL_NET_PORT 8022
============== ===============

Components
##########

========= =========================================================== ========================================
component repository                                                  revision
========= =========================================================== ========================================
rfa       https://git.trustedfirmware.org/RF-A/rusted-firmware-a      b0fec182669b59f16271ba695b4387cffcbc42a1
tfa       https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git v2.14.0
========= =========================================================== ========================================

