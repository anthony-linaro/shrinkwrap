#!/bin/bash
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

# Exit on error and echo commands.
set -e

SOURCE_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export SHRINKWRAP_BUILD=${SOURCE_DIR}/build
export SHRINKWRAP_PACKAGE=${SOURCE_DIR}
export SHRINKWRAP_CONFIG=${SOURCE_DIR}/config
export PATH=${PATH}:${SOURCE_DIR}/../shrinkwrap

USAGE="$(basename "$0") - A build script to generate test assets/builds
The following parameters are valid:
    -h Show this help
    -R <shrinkwrap runtime> Specify the choice for shrinkwrap runtime. Defaults to 'docker'
    -n Dryrun mode for shrinkwrap build
    -v Versbose mode for shrinkwrap build
"

RUNTIME=docker

while getopts hnvR: option
do
case "${option}"
in
n) DRYRUN="--dry-run";;
v) VERBOSE="--verbose";;
R) RUNTIME=${OPTARG};;
h) echo "$USAGE"
   exit 0;;
*) echo "$USAGE"
   exit 0;;
esac
done

BUILD_USER=`whoami`
# Certain packages can't be configured when running as a root.
# However the check can be bypassed by setting FORCE_UNSAFE_CONFIGURE
if [ "${BUILD_USER}" == "root" ]; then
	echo -e "You are building as a root, you are being warned"
	echo -e "Setting FORCE_UNSAFE_CONFIGURE=1 for build to succeed"
	export FORCE_UNSAFE_CONFIGURE=1
fi
shrinkwrap -R ${RUNTIME} build ${VERBOSE} ${DRYRUN} assets.yaml
# Remove the generated config as it may picked up by default
rm -fr ${SHRINKWRAP_PACKAGE}/assets.yaml
