"""
Modules package

contents:

    generic
    grades
    timetable

"""
from ._generic import Generic as _Generic
from .grades import Grades
from .timetable import Timetable

__all__ = (
    "_Generic",
    "Grades",
    "Timetable",
)
