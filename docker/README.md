# Shrinkwrap

Shrinkwrap is a tool to simplify the process of building and running firmware on
Arm Fixed Virtual Platforms (FVP) and QEMU. Users simply invoke the tool to build
the required config, then pass their own kernel and rootfs to the tool to boot the
full system on FVP or QEMU.

- Documentation is available at: [ReadTheDocs](https://shrinkwrap.docs.arm.com)
- Source Code is available at: [GitLab](https://gitlab.arm.com/tooling/shrinkwrap)
- Shrinkwrap Container Images are available at: [DockerHub](https://hub.docker.com/u/shrinkwraptool)

These Docker images are used by the shrinkwrap tool as a backend runtime.

# License

All shrinkwrap images are based on Debian. See
[DockerHub](https://hub.docker.com/_/debian) for Debian licensing information.

As with all Docker images, these likely also contain other software which may be
under other licenses (such as Bash, etc from the base distribution, along with
any direct or indirect dependencies of the primary software being contained).

For images that contain a Fixed Virtual Platfom (FVP), use of the FVP is subject
to the "END USER LICENSE AGREEMENT FOR ARM ECOSYSTEM MODELS", which is available
at /tools/Base_RevC_AEMvA_pkg/license_terms/license_agreement.txt within the
image.

As for any pre-built image usage, it is the image user's responsibility to
ensure that any use of this image complies with any relevant licenses for all
software contained within.
