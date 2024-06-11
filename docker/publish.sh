#!/bin/sh
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

set -e

usage()
{
cat << EOF
Creates a manifest list for a multiarch docker image and publishes it so that
users can pull an image using a generic name and the variant for their machine
architecture is automatically selected.

Usage:
$(basename $0) [--driver docker|manifest-tool] [--user <user> --password <password>] [--registry <url>] --version <tag>

Where:
  --driver determines how the image will be published:
    docker:        (default) and will use "docker manifest". This is usually
                   what you want when running locally.
    manifest-tool: Uses manifest-tool, which does not require access to the
                   docker daemon. Useful on CI systems where running inside a
		   container.

  <user> is required by manifest-tool to access the registry
  <password> is required by manifest-tool to access the registry
  <url> is the registry to publish to (defaults to docker.io/shrinkwraptool).
  <tag> is something like "latest" or "v1.0.0".

An image for each of the supported architectures must have already been built
and published with <tag>.

The user is responsible for having already configured the driver connection to
the registry.
EOF
}

DRIVER="docker"
USER=
PASSWORD=
REGISTRY="docker.io/shrinkwraptool"
VERSION=

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
	--user)
		USER="$2"
		shift # past argument
		shift # past value
		;;
	--password)
		PASSWORD="$2"
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

if [ "${DRIVER}" != "docker" ] && [ "${DRIVER}" != "manifest-tool" ]; then
	echo "error: invalid driver provided! (${DRIVER})"
	usage
	exit 1
fi

if [ "${DRIVER}" = "manifest-tool" ]; then
	if [ -z ${USER} ] || [ -z ${PASSWORD} ]; then
		echo "error: --user and --password are required when using manifest-tool!"
		usage
		exit 1
	fi
fi

echo "Publishing multiarch image with driver=${DRIVER},registry=${REGISTRY},version=${VERSION}..."

# Do everything relative to this script's directory.
ROOT=$( dirname $( readlink -f "$0" ) )
cd ${ROOT}

if [ "${DRIVER}" = "docker" ]; then
	# base-slim-nofvp
	docker manifest create ${REGISTRY}/base-slim-nofvp:${VERSION} \
		${REGISTRY}/base-slim-nofvp:${VERSION}-aarch64 \
		${REGISTRY}/base-slim-nofvp:${VERSION}-x86_64
	docker manifest push ${REGISTRY}/base-slim-nofvp:${VERSION}
	docker manifest rm ${REGISTRY}/base-slim-nofvp:${VERSION}

	# base-slim
	docker manifest create ${REGISTRY}/base-slim:${VERSION} \
		${REGISTRY}/base-slim:${VERSION}-aarch64 \
		${REGISTRY}/base-slim:${VERSION}-x86_64
	docker manifest push ${REGISTRY}/base-slim:${VERSION}
	docker manifest rm ${REGISTRY}/base-slim:${VERSION}

	# base-full-nofvp
	docker manifest create ${REGISTRY}/base-full-nofvp:${VERSION} \
		${REGISTRY}/base-full-nofvp:${VERSION}-aarch64 \
		${REGISTRY}/base-full-nofvp:${VERSION}-x86_64
	docker manifest push ${REGISTRY}/base-full-nofvp:${VERSION}
	docker manifest rm ${REGISTRY}/base-full-nofvp:${VERSION}

	# base-full
	docker manifest create ${REGISTRY}/base-full:${VERSION} \
		${REGISTRY}/base-full:${VERSION}-aarch64 \
		${REGISTRY}/base-full:${VERSION}-x86_64
	docker manifest push ${REGISTRY}/base-full:${VERSION}
	docker manifest rm ${REGISTRY}/base-full:${VERSION}
elif [ "${DRIVER}" = "manifest-tool" ]; then
	manifest_publish()
	{
		NAME=$1
		MANIFEST=$(mktemp)

		cat << EOF > ${MANIFEST}
image: ${REGISTRY}/${NAME}:${VERSION}
manifests:
  - image: ${REGISTRY}/${NAME}:${VERSION}-aarch64
    platform:
      architecture: arm64
      os: linux
  - image: ${REGISTRY}/${NAME}:${VERSION}-x86_64
    platform:
      architecture: amd64
      os: linux
EOF

		manifest-tool-linux-amd64 --username ${USER} --password ${PASSWORD} push from-spec ${MANIFEST}
		rm -rf ${MANIFEST}
	}

	manifest_publish "base-slim-nofvp"
	manifest_publish "base-slim"
	manifest_publish "base-full-nofvp"
	manifest_publish "base-full"
else
	echo "Driver ${DRIVER} not supported"
	exit 1
fi
