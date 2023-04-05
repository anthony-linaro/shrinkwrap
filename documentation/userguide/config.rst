..
 # Copyright (c) 2022, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#######
Configs
#######

A config is a yaml file that defines everything about a given configuration.
This includes:

- meta data (e.g. its name, description, etc)
- the components that should be built
- how those components are built
- dependencies between components
- what artifacts are produced
- how to configure the fvp
- how to load and run the artifacts on the fvp

A config is declarative; the user declares how things relate and how things
should be done, and the tool extracts the information to decide exactly what
should be done and in what order in order to complete a task. All the data is
contained within the config and drives the tool. This way, shrinkwrap is highly
extensible. The user specifies the config(s) that should be used when invoking
shrinkwrap.


***************
Merging Configs
***************

A config is laid out as a hierarchical data structure, using nested dictionaries.
This suits it very well to being split into partial configs that are merged
together into a single, final config. This allows maximal reuse of the config
fragments and improves maintainability. Each config can optionally define a set
of foundational ``layers`` which it then builds upon. Furthermore, the user can
optionally specify a custom ``overlay`` config on the command line. Layers are
merged in order according to the following rules:

For each leaf key in the union of the hierarchical dictionaries:

- If the upper value is null or not present, then the lower value is taken

- If both the upper and lower values are lists, then the final value is the
  lower list with the upper list appended to its end.

- In all other cases the upper value is taken

You can use the ``process`` command to merge configs and see the resulting
output to get a better feel for how it works. See
:ref:`userguide/commands:Commands`.

---------------
Merging Example
---------------

.. code-block:: yaml
	:caption: lower config

	people:
	  Iris:
	    age: 2
	    likes:
	      - Peppa Pig
	      - Bananas

.. code-block:: yaml
	:caption: upper config

	people:
	  Iris:
	    age: 3
	    likes:
	      - Peas
	  James:
	    age: 6
	    likes:
	      - FIFA

.. code-block:: yaml
	:caption: merged result

	people:
	  Iris:
	    age: 3
	    likes:
	      - Peppa Pig
	      - Bananas
	      - Peas
	  James:
	    age: 6
	    likes:
	      - FIFA


******
Macros
******

Macros are placeholders that can be specified in various parts of a config yaml
file, which are substituted ("resolved") with information that is only known at
build-time or run-time. There are specific rules about which macros can be used
in which parts of the config, and about the order in which they get substituted.

Macros take the following form:

  ``${<type>:[<name>]}``

where:

  - ``type`` is a required namespace for the macro family
  - ``name`` is an optional name for the macro within its namespace. For some
    macro types, there are a fixed set of names. For others, the names are
    defined by the config itself.

You can use the ``process`` command to resolve macros and see the resulting
output to get a better feel for how they work. See
:ref:`userguide/commands:Commands`.

--------------
Defined Macros
--------------

======================= ========================================================================= ====
macro                   scope                                                                     description
======================= ========================================================================= ====
``${param:sourcedir}``  build.<component>.{params, prebuild, build, postbuild, clean, artifacts}  Directory in which the component's source code is located.
``${param:builddir}``   build.<component>.{params, prebuild, build, postbuild, clean, artifacts}  Directory in which the component should be built, if the component's build system supports separation of source and build trees.
``${param:configdir}``  build.<component>.{params, prebuild, build, postbuild, clean, artifacts}  Directory containing the config store. This MUST only be used for resolving files that already exist in the store.
``${param:jobs}``       build.<component>.{params, prebuild, build, postbuild, clean}             Maximum number of low level parallel jobs specified on the command line. To be passed to (e.g.) make as ``-j${param:jobs}``.
``${param:join_equal}`` build.<component>.{prebuild, build, postbuild, clean}                     String  containing all of the component's parameters (from its params dictionary), concatenated as ``key=value`` pairs.
``${param:join_space}`` build.<component>.{prebuild, build, postbuild, clean}                     String  containing all of the component's parameters (from its params dictionary), concatenated as ``key value`` pairs.
``${artifact:<name>}``  build.<component>.{params, prebuild, build, postbuild, clean}             Build path of an artifact declared by another component. Usage of these macros determine the component build dependency graph.
``${artifact:<name>}``  run.rtvars                                                                Package path of an artifact.
``${rtvar:<name>}``     run.params                                                                Run-time variables. The variable names, along with default values are declared in run.rtvars, and the user may override the value on the command line.
======================= ========================================================================= ====

******
Schema
******

--------------
Top-Level keys
--------------

The following is the set of top-level public keys that should be defined by a
config. There are some additional private keys that the tool will add (and make
visible as part of the ``process`` command), but these are subject to change and
not documented.

=========== ========== ===========
key         type       description
=========== ========== ===========
description string     A human-readable description of what the config contains and does. Displayed by the ``inspect`` command.
concrete    boolean    true if the config is intended to be directly built and run, or false if it is intended as a fragment to be included in other configs.
build       dictionary Contains all the components to be built. The key is the component name and the value is a dictionary.
run         dictionary Contains all the information about how to run the built artifacts on the FVP.
=========== ========== ===========

-------------
build section
-------------

The build section, contains a dictionary of components that must be built. The
keys are the component names and the values are themselves dictionaries, each
containing the component meta data.

~~~~~~~~~~~~~~~~~
component section
~~~~~~~~~~~~~~~~~

=========== =========== ===========
key         type        description
=========== =========== ===========
repo        dictionary  Specifies information about the git repo(s) that must be cloned and checked out. Shrinkwrap will only sync the git repo if it does not already exist. If it exists, it leaves it in whatever state the user left it in and attempts to build it. Not required if ``sourcedir`` is provided.
sourcedir   string      If specified, points to the path on disk where the source repo can be found. Useful for developer use cases where a local repo already exists.
builddir    string      If specified, the location where the component will be built. If not specified, shrinkwrap allocates its own location based on SHRINKWRAP_BUILD.
toolchain   string      Defines the toolchain to be used for compilation. Value is set as CROSS_COMPILE environment variable before invoking any prebuild/build/postbuild/clean commands. When using the standard image with a container runtime, the options are: ``aarch64-none-elf-``, ``arm-none-eabi-``, ``aarch64-linux-gnu-``, or ``arm-linux-gnueabihf-``.
params      dictionary  Optional set of key:value pairs. When building most components, they require a set of parameters to be passed. By setting them out as a dictionary, it is easy to override and add to them in higher layers. See ``${param:join_*}`` macros.
prebuild    list        List of shell commands to be executed during component build before the ``build`` list.
build       list        List of shell commands to be executed during component build.
postbuild   list        List of shell commands to be executed during component build after the ``build`` list.
clean       list        List of shell commands to be executed during component clean.
artifacts   dictionary  Set of artifacts (files and/or directories) that the component exports. Key is artifact name and value is path to built artifact. Other components can reference them with the ``${artifact:<name>}`` macros. Used to determine build dependencies.
=========== =========== ===========

-----------
run section
-----------

=========== =========== ===========
key         type        description
=========== =========== ===========
name        string      Name of the FVP binary, which must be in $PATH.
rtvars      dictionary  Run-Time variables. Keys are the variable names and values are a dictionary with keys 'type' (which must be one of 'path' and 'string') and 'value' (which takes the default value). Run-Time variables can be overridden by the user at the command line.
params      dictionary  Dictionary of parameters to be passed to the FVP. Similar to the component's params, laying these out in a dictionary makes it easy for higher layers to override and add parameters.
prerun      list        List of shell commands to be executed before the FVP is started.
terminals   dictionary  Describes the set of UART terminals available for the FVP. key is the terminal parameter name known to the FVP (e.g. ``bp.terminal_0``) See below for format of the value.
=========== =========== ===========

~~~~~~~~~~~~~~~~
terminal section
~~~~~~~~~~~~~~~~

=========== =========== ===========
key         type        description
=========== =========== ===========
friendly    string      Label to display against the terminal when muxing to stdout. An empty string disables the prefix for the output.
port_regex  string      Regex to use to find the TCP port of the terminal when parsing the FVP stdout. Must have single capture group.
type        enum-string Terminal type. See below for options.
no_color    boolean     Optional (defaults to false, only applies to ['stdout', 'stdinout'] types): If true, output from this terminal is not color-coded. If this terminal carries the interactive shell, it is advised to set this to true to prevent interferring with the shell's escape sequences. --no-color command line option causes this to behave as if set to true.
no_escapes  bool/string Optional (defaults to false, only applies to ['stdout', 'stdinout'] types): If true, strips any escape sequences from the output stream before forwarding to the terminal. If a string, behaves as if true until the string is found in the output, which sets it to false. Useful to expunge escape sequences from EDK2 during boot.
=========== =========== ===========

Terminal types:

- **stdout**: Mux output to stdout. Do not supply any input.
- **stdinout**: Mux output to stdout. Forward stdin to its input. Max of 1 of these types allowed.
- **telnet**: Shrinkwrap will print out a telnet command to run in a separate terminal to get a unique interactive terminal.
- **xterm**: Shrinkwrap will automatically launch xterm to provide a unique interactive terminal. Only works when runtime=null.
