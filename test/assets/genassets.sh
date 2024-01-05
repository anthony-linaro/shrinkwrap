#!/bin/bash
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

# This script builds the assets required to run the test script.
# - rootfs that automatically invokes `poweroff -f`
# - Linux kernel image
# - bootwrapper image
# TODO: Build all of this using shrinkwrap.

# Exit on error and echo commands.
set -ex

ASSETS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
BUILD_DIR=${ASSETS_DIR}/build
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-

# Delete any previous build directory and start from scratch.
rm -rf ${BUILD_DIR} &> /dev/null
mkdir -p ${BUILD_DIR}
pushd ${BUILD_DIR}

# Prepare the init script that will immediately power off the system.
mkdir -p buildroot_overlay/etc/init.d
cat <<EOF > buildroot_overlay/etc/init.d/S10poweroff
#!/bin/sh
case "\$1" in
        start|stop|restart|reload)
                poweroff -f;;
        *)
                echo "Usage: \$0 {start|stop|restart|reload}"
                exit 1
esac
EOF
chmod +x buildroot_overlay/etc/init.d/S10poweroff

# Clone and build a very simple buildroot with the above overlay.
git clone https://github.com/buildroot/buildroot.git
cd buildroot
git checkout 2022.05.3
cp ${ASSETS_DIR}/buildroot.config .config
./utils/config --set-val BR2_ROOTFS_OVERLAY "\"${BUILD_DIR}/buildroot_overlay\""
make olddefconfig
make BR2_JLEVEL=`nproc`
cp output/images/rootfs.ext4 ${ASSETS_DIR}/.
cd -

# Build Linux defconfig.
git clone https://github.com/torvalds/linux.git
cd linux
git checkout v6.6
make defconfig
make -j`nproc` Image arm/fvp-base-revc.dtb
cp arch/arm64/boot/Image ${ASSETS_DIR}/.
cd -

# Build a bootwrapper axf.
git clone git://git.kernel.org/pub/scm/linux/kernel/git/mark/boot-wrapper-aarch64.git
cd boot-wrapper-aarch64
autoreconf -i
./configure \
	--host=aarch64-linux-gnu \
	--with-kernel-dir=${BUILD_DIR}/linux \
	--with-cmdline="console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp" \
	--enable-gicv3
make
cp linux-system.axf ${ASSETS_DIR}/.
cd -

popd
rm -rf ${BUILD_DIR} &> /dev/null
