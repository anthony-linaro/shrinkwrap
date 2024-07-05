# Shrinkwrap

Shrinkwrap is a tool to simplify the process of building and running firmware on
Arm Fixed Virtual Platforms (FVP). Users simply invoke the tool to build the
required config, then pass their own kernel and rootfs to the tool to boot the
full system on FVP.

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
  sudo pip3 install pyyaml termcolor tuxmake
  git clone https://git.gitlab.arm.com/tooling/shrinkwrap.git
  export PATH=$PWD/shrinkwrap/shrinkwrap:$PATH
```

```
  shrinkwrap --help
```
