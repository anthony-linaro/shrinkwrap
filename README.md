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

> **NOTE:** This assumes you have Docker installed. If this is not the case,
> please refer to the documentation.

```shell
# On Debian derivatives (e.g. Ubuntu) [with uv, recommended]
curl -LsSf https://astral.sh/uv/install.sh | sh # Install uv first
sudo apt-get update && sudo apt-get install curl git netcat-openbsd telnet
uv tool install git+https://git.gitlab.arm.com/tooling/shrinkwrap.git

# On Debian derivatives (e.g. Ubuntu) [with pipx]
sudo apt-get update && sudo apt-get install curl git netcat-openbsd pipx python3-venv telnet
pipx install git+https://git.gitlab.arm.com/tooling/shrinkwrap.git

# On macOS (with Homebrew) [with uv, recommended]
brew install git telnet uv
uv tool install git+https://git.gitlab.arm.com/tooling/shrinkwrap.git

# On macOS (with Homebrew) [with pipx]
brew install git telnet pipx
pipx install git+https://git.gitlab.arm.com/tooling/shrinkwrap.git
```

```
  shrinkwrap --help
```
