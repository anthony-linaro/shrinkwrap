..
 # Copyright (c) 2025, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

###############
Release Process
###############

Shrinkwrap is released at least once every quarter as a tagged snapshot of a
branch. If critical bugs are discovered in the release, subsequent bugfix-only
releases may be made available.

This document describes the process and serves as a checklist for the maintainer
to make a shrinkwrap release.

~~~~~~~~~~~~~~~~
Release Contents
~~~~~~~~~~~~~~~~

Shrinkwrap consists of 3 parts:
  - Shrinkwrap Python Package
  - Shrinkwrap Container Images
  - Shrinkwrap Documentation

A release is a consistent snapshot of all 3 parts, with a defined set of
features that has been through a quality assurance process. The Python package
is tagged in the Gitlab repository, the contianer images are tagged in docker
hub, and the documentation is tagged in readthedocs. In future, the Python
package may additionally be uploaded to PyPI.

~~~~~~~~~~~~~~~~~
Versioning Scheme
~~~~~~~~~~~~~~~~~

Shrinkwrap uses a date-based versioning scheme that is compatible with PEP 440,
which is required by PyPI:

``<year>.<month>.<patch>[.dev0]``

=========== ===========
component   description
=========== ===========
``<year>``  Version year as 4 digit decimal integer.
``<month>`` Version month as 1 or 2 digit decimal integer (no trailing zero).
``<patch>`` Patch level: 0 for the primary release, then increments for each bugfix release.
``.dev0``   Used for in-development versions. A release snapshot never has this suffix.
=========== ===========

As an example, let's say we have just released version ``2025.12.0``. The
version in the main branch of the repository will be immediately bumped to
``2026.3.0.dev0`` to indicate that the branch now represents the in-development
version that will be released in March 2026. When development is complete and we
are ready for release (hopefully in March 2026), the version in the main branch
is updated to ``2026.3.0`` and the release is tagged. Then the version is
updated to ``2026.6.0.dev0`` and the cycle begins again.

~~~~~~~~~~~~~~~~
Bug Fix Releases
~~~~~~~~~~~~~~~~

If the ``<year>.<month>.0`` release is found to have a critical bug, the
decision may be taken to make a bugfix release which will increment the
``<patch>``. First a branch is created in Gitlab, from the ``<year>.<month>.0``
version tag. The version is incremented to ``<year>.<month>.1.dev0``, then fixes
are backported from main onto the branch. Finally the version is set to
``<year>.<month>.1`` and the release is done following the same process but
using the release branch.

~~~~~~~~~~~~~~~~~
Release Checklist
~~~~~~~~~~~~~~~~~

- Maintainer determines that ``main`` is ready to start the release process

  - All planned features have landed
  - The ``main`` CI pipeline passes
  - Discretionary manual testing has been performed and no issues found
  - Documentation has been reviewed and is up-to-date

- Maintainer writes and commits the release notes to ``main``
- Maintainer makes commit to remove ``.dev0`` from version
- Maintainer triggers "full" pipeline in Gitlab, running full set of tests

  - On failure, debug and fix then go back to start
  - On success, containers are automatically tagged with version number in
    docker hub

- Maintainer creates tag of the tested SHA in Gitlab
- Maintainer creates new version corresponding to tag in readthedocs
- Maintainer makes commit to set the next version for the newly started
  development cycle ``<year>.<month>.0.dev0``
- Maintainer and Project Manager fill out Arm-specific release forms
- Project Manager makes release announcement
