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

============= ======= ==============
btvar         default options
============= ======= ==============
TFA_BUILD     release debug, release
TFA_LOG_LEVEL 40      <required>
============= ======= ==============

Run-Time Variables
##################

============== =============== ==========
rtvar          default         options
============== =============== ==========
BL1            ${artifact:BL1} <required>
FIP            ${artifact:FIP} <required>
LOCAL_NET_PORT 8022            <required>
============== =============== ==========

Components
##########

========= =========================================================== ========================================
component repository                                                  revision
========= =========================================================== ========================================
rfa       https://git.trustedfirmware.org/RF-A/rusted-firmware-a      v0.2.0
tfa       https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git 5c33fafcddc09543dbfff97cac991847e8e4fda9
========= =========================================================== ========================================

