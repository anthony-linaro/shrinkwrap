..
 # Copyright (c) 2023, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

##############
buildroot.yaml
##############

Description
###########

Generates a very simple rootfs as an ext2/4 image. Higher layers can modify the buildroot config by adding commands to prebuild.

Build-Time Variables
####################

===== =======
btvar default
===== =======
===== =======

Run-Time Variables
##################

===== =======
rtvar default
===== =======
===== =======

Components
##########

========= ========================================== =========
component repository                                 revision
========= ========================================== =========
buildroot https://github.com/buildroot/buildroot.git 2025.08.1
========= ========================================== =========

