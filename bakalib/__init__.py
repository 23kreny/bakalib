"""
Bakalib - library for accessing the Bakaláři school system easily!
core:
    client - authentication and info about the user
extra:
    municipality - list of cities and schools
modules:
    generic - boilerplate module
    grades
    timetable

"""

from . import core, extra, modules
from ._version import version

__all__ = (
    "core",
    "extra",
    "modules",
    "version",
)
