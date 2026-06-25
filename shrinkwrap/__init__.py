import os

__version__ = "2026.9.0.dev0"

_src_package_dir = os.path.realpath(
	os.path.join(os.path.dirname(__file__), '..', 'src', 'shrinkwrap')
)

if os.path.isdir(_src_package_dir) and _src_package_dir not in __path__:
	# Keep the legacy package entry point working while commands/utils live
	# under src/shrinkwrap.
	__path__.append(_src_package_dir)
