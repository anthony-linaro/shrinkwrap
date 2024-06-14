#!/bin/sh
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

set -e

usage()
{
cat << EOF
Builds and optionally publishes shrinkwrap docker images for the architecture
of the host system. (x86_64 and aarch64 are currently supported).

Usage:
$(basename $0) [--driver docker|kaniko] [--registry <url>] [--arch <arch>] --version <tag>

Where:
  --driver determines how the image will be built:
    docker: (default) and will use "docker build" and "docker push".
            This is usually what you want when running locally.
    kaniko: Uses kaniko, which does not require access to the docker daemon.
            Useful on CI systems where running inside a container. Must be
            running inside the kaniko container.

  --arch optionally provides a target arch label that overrides the default
  `uname -m`. Must be either "aarch64" or "x86_64". Unless `--version none`,
  must match the arch of the machine used to run the script. For
  `--version none` can be set to any supported arch to download that arch's
  package cache.

  <url> is the registry to publish to (defaults to docker.io/shrinkwraptool).
  <tag> is something like "latest" or "v1.0.0".

The user is responsible for having already configured the driver connection to
the registry.

If <tag> is "local" and --driver is "docker", the resulting image is NOT pushed
to the remote repository but instead kept locally by docker.

If <tag> is "none", the package cache is synced but no image is built.
EOF
}

DRIVER="docker"
REGISTRY="docker.io/shrinkwraptool"
VERSION=
ARCH=$(uname -m)

# Parse command line.
while [ $# -gt 0 ]; do
	case $1 in
	--version)
		VERSION="$2"
		shift # past argument
		shift # past value
		;;
	--registry)
		REGISTRY="$2"
		shift # past argument
		shift # past value
		;;
	--driver)
		DRIVER="$2"
		shift # past argument
		shift # past value
		;;
	--arch)
		ARCH="$2"
		shift # past argument
		shift # past value
		;;
	-h|--help)
		usage
		exit 0
		;;
	-*|--*)
		echo "error: unexpected named argument! ($1)"
		usage
		exit 1
		;;
	*)
		echo "error: unexpected positional argument! ($1)"
		usage
		exit 1
		;;
	esac
done

if [ -z ${VERSION} ]; then
	echo "error: no version provided!"
	usage
	exit 1
fi

if [ "${DRIVER}" != "docker" ] && [ "${DRIVER}" != "kaniko" ]; then
	echo "error: invalid driver provided! (${DRIVER})"
	usage
	exit 1
fi

# Configure the arch-specific variables which are passed to the Dockerfile.
if [ "${ARCH}" = "x86_64" ]; then
	TCH_PKG_URL_AARCH64=https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel
	TCH_PKG_NAME_AARCH64=arm-gnu-toolchain-13.2.rel1-x86_64-aarch64-none-elf.tar.xz
	TCH_PATH_AARCH64=arm-gnu-toolchain-13.2.Rel1-x86_64-aarch64-none-elf/bin
	TCH_LLVM_PKG_URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-15.0.6
	TCH_LLVM_PKG_NAME=clang+llvm-15.0.6-x86_64-linux-gnu-ubuntu-18.04.tar.xz
	TCH_LLVM_PATH=clang+llvm-15.0.6-x86_64-linux-gnu-ubuntu-18.04/bin
	TCH_PKG_URL_AARCH32=https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel
	TCH_PKG_NAME_AARCH32=arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-eabi.tar.xz
	TCH_PATH_AARCH32=arm-gnu-toolchain-13.2.Rel1-x86_64-arm-none-eabi/bin
	FVP_PKG_URL=https://developer.arm.com/-/media/Files/downloads/ecosystem-models
	FVP_PKG_NAME=FVP_Base_RevC-2xAEMvA_11.24_11_Linux64.tgz
	FVP_MODEL_DIR=Base_RevC_AEMvA_pkg/models/Linux64_GCC-9.3
	FVP_PLUGIN_DIR=Base_RevC_AEMvA_pkg/plugins/Linux64_GCC-9.3
# ARCH is "aarch64" on Ubuntu, or "arm64" on Mac OS
elif [ "${ARCH}" = "aarch64" ] || [ "${ARCH}" = "arm64" ]; then
	TCH_PKG_URL_AARCH64=https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel
	TCH_PKG_NAME_AARCH64=arm-gnu-toolchain-13.2.rel1-aarch64-aarch64-none-elf.tar.xz
	TCH_PATH_AARCH64=arm-gnu-toolchain-13.2.Rel1-aarch64-aarch64-none-elf/bin
	TCH_LLVM_PKG_URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-15.0.6
	TCH_LLVM_PKG_NAME=clang+llvm-15.0.6-aarch64-linux-gnu.tar.xz
	TCH_LLVM_PATH=clang+llvm-15.0.6-aarch64-linux-gnu/bin
	TCH_PKG_URL_AARCH32=https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel
	TCH_PKG_NAME_AARCH32=arm-gnu-toolchain-13.2.rel1-aarch64-arm-none-eabi.tar.xz
	TCH_PATH_AARCH32=arm-gnu-toolchain-13.2.Rel1-aarch64-arm-none-eabi/bin
	FVP_PKG_URL=https://developer.arm.com/-/media/Files/downloads/ecosystem-models
	FVP_PKG_NAME=FVP_Base_RevC-2xAEMvA_11.24_11_Linux64_armv8l.tgz
	FVP_MODEL_DIR=Base_RevC_AEMvA_pkg/models/Linux64_armv8l_GCC-9.3
	FVP_PLUGIN_DIR=Base_RevC_AEMvA_pkg/plugins/Linux64_armv8l_GCC-9.3
else
	echo "Host architecture ${ARCH} not supported"
	usage
	exit 1
fi

echo "Building image for ${ARCH} with driver=${DRIVER},registry=${REGISTRY},version=${VERSION}..."

wget_or_cache()
{
	FILE=$1
	URL=$2

	if [ ! -f ${FILE} ]; then
		wget -q -O ${FILE} ${URL}
	fi
}

# Do everything relative to this script's directory.
ROOT=$( dirname $( readlink -f "$0" ) )
cd ${ROOT}

# Grab the pre-built packages.
mkdir -p assets
wget_or_cache assets/${TCH_PKG_NAME_AARCH64} ${TCH_PKG_URL_AARCH64}/${TCH_PKG_NAME_AARCH64}
wget_or_cache assets/${TCH_LLVM_PKG_NAME} ${TCH_LLVM_PKG_URL}/${TCH_LLVM_PKG_NAME}
wget_or_cache assets/${TCH_PKG_NAME_AARCH32} ${TCH_PKG_URL_AARCH32}/${TCH_PKG_NAME_AARCH32}
wget_or_cache assets/${FVP_PKG_NAME} ${FVP_PKG_URL}/${FVP_PKG_NAME}

# Short circuit building the images if requested.
if [ "${VERSION}" = "none" ]; then
	exit
fi

# Build the images.
if [ "${DRIVER}" = "docker" ]; then
	docker build \
		--build-arg=BASE=registry.gitlab.arm.com/tooling/shrinkwrap/bookworm-slim \
		--build-arg=TCH_PKG_NAME_AARCH64=${TCH_PKG_NAME_AARCH64} \
		--build-arg=TCH_PATH_AARCH64=${TCH_PATH_AARCH64} \
		--file=Dockerfile.slim \
		--tag=${REGISTRY}/base-slim-nofvp:${VERSION}-${ARCH} \
		.
	docker build \
		--build-arg=BASE=${REGISTRY}/base-slim-nofvp:${VERSION}-${ARCH} \
		--build-arg=FVP_PKG_NAME=${FVP_PKG_NAME} \
		--build-arg=FVP_MODEL_DIR=${FVP_MODEL_DIR} \
		--build-arg=FVP_PLUGIN_DIR=${FVP_PLUGIN_DIR} \
		--file=Dockerfile.fvp \
		--tag=${REGISTRY}/base-slim:${VERSION}-${ARCH} \
		.
	docker build \
		--build-arg=BASE=${REGISTRY}/base-slim-nofvp:${VERSION}-${ARCH} \
		--build-arg=TCH_PKG_NAME_AARCH32=${TCH_PKG_NAME_AARCH32} \
		--build-arg=TCH_PATH_AARCH32=${TCH_PATH_AARCH32} \
		--build-arg=TCH_LLVM_PKG_NAME=${TCH_LLVM_PKG_NAME} \
		--build-arg=TCH_LLVM_PATH=${TCH_LLVM_PATH} \
		--file=Dockerfile.full \
		--tag=${REGISTRY}/base-full-nofvp:${VERSION}-${ARCH} \
		.
	docker build \
		--build-arg=BASE=${REGISTRY}/base-full-nofvp:${VERSION}-${ARCH} \
		--build-arg=FVP_PKG_NAME=${FVP_PKG_NAME} \
		--build-arg=FVP_MODEL_DIR=${FVP_MODEL_DIR} \
		--build-arg=FVP_PLUGIN_DIR=${FVP_PLUGIN_DIR} \
		--file=Dockerfile.fvp \
		--tag=${REGISTRY}/base-full:${VERSION}-${ARCH} \
		.

	# If not a local version, publish the image.
	if [ "${VERSION}" != "local" ]; then
		docker push ${REGISTRY}/base-slim-nofvp:${VERSION}-${ARCH}
		docker push ${REGISTRY}/base-slim:${VERSION}-${ARCH}
		docker push ${REGISTRY}/base-full-nofvp:${VERSION}-${ARCH}
		docker push ${REGISTRY}/base-full:${VERSION}-${ARCH}
	fi
elif [ "${DRIVER}" = "kaniko" ]; then
	# Build the images.
	/kaniko/executor \
		--cleanup \
		--cache=true --cache-copy-layers --cache-run-layers \
		--build-arg=BASE=registry.gitlab.arm.com/tooling/shrinkwrap/bookworm-slim \
		--build-arg=TCH_PKG_NAME_AARCH64=${TCH_PKG_NAME_AARCH64} \
		--build-arg=TCH_PATH_AARCH64=${TCH_PATH_AARCH64} \
		--dockerfile=Dockerfile.slim \
		--destination=${REGISTRY}/base-slim-nofvp:${VERSION}-${ARCH} \
		--context=.
	/kaniko/executor \
		--cleanup \
		--cache=true --cache-copy-layers --cache-run-layers \
		--build-arg=BASE=${REGISTRY}/base-slim-nofvp:${VERSION}-${ARCH} \
		--build-arg=FVP_PKG_NAME=${FVP_PKG_NAME} \
		--build-arg=FVP_MODEL_DIR=${FVP_MODEL_DIR} \
		--build-arg=FVP_PLUGIN_DIR=${FVP_PLUGIN_DIR} \
		--dockerfile=Dockerfile.fvp \
		--destination=${REGISTRY}/base-slim:${VERSION}-${ARCH} \
		--context=.
	/kaniko/executor \
		--cleanup \
		--cache=true --cache-copy-layers --cache-run-layers \
		--build-arg=BASE=${REGISTRY}/base-slim-nofvp:${VERSION}-${ARCH} \
		--build-arg=TCH_PKG_NAME_AARCH32=${TCH_PKG_NAME_AARCH32} \
		--build-arg=TCH_PATH_AARCH32=${TCH_PATH_AARCH32} \
		--build-arg=TCH_LLVM_PKG_NAME=${TCH_LLVM_PKG_NAME} \
		--build-arg=TCH_LLVM_PATH=${TCH_LLVM_PATH} \
		--dockerfile=Dockerfile.full \
		--destination=${REGISTRY}/base-full-nofvp:${VERSION}-${ARCH} \
		--context=.
	/kaniko/executor \
		--cleanup \
		--cache=true --cache-copy-layers --cache-run-layers \
		--build-arg=BASE=${REGISTRY}/base-full-nofvp:${VERSION}-${ARCH} \
		--build-arg=FVP_PKG_NAME=${FVP_PKG_NAME} \
		--build-arg=FVP_MODEL_DIR=${FVP_MODEL_DIR} \
		--build-arg=FVP_PLUGIN_DIR=${FVP_PLUGIN_DIR} \
		--dockerfile=Dockerfile.fvp \
		--destination=${REGISTRY}/base-full:${VERSION}-${ARCH} \
		--context=.
else
	echo "Driver ${DRIVER} not supported"
	exit 1
fi
