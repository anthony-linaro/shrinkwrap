# Shrinkwrap

Shrinkwrap is a tool to simplify the process of building and running firmware on
Arm Fixed Virtual Platforms (FVP) and QEMU. Users simply invoke the tool to build
the required config, then pass their own kernel and rootfs to the tool to boot the
full system on FVP or QEMU.

- Documentation is available at: [ReadTheDocs](https://shrinkwrap.docs.arm.com)
- Source Code is available at: [GitLab](https://gitlab.arm.com/tooling/shrinkwrap)
- Shrinkwrap Container Images are available at: [DockerHub](https://hub.docker.com/u/shrinkwraptool)

The documentation (linked above) contains a
[QuickStart](https://shrinkwrap.docs.arm.com/en/latest/userguide/quickstart.html)
section, which details how to install and use the tool. However, if you are in a
hurry, here are the minimal steps:

> **NOTE:** This assumes you have Python >=3.9.0 and docker installed. If this
> is not the case, please refer to the documentation.

```
  sudo apt-get install git netcat-openbsd python3 python3-pip telnet
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install shrinkwraptool
```

```
  shrinkwrap --help
```
