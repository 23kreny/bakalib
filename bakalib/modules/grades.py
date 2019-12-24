"""
grades
======
"""

__all__ = ("Grades",)

from dataclasses import dataclass
from threading import Thread

from ..core.client import Client
from ..utils import BakalibError, _setup_logger, cache, request
from ._generic import Generic


class Grades(Generic):
    """
    Obtains information from the "znamky" module of Bakaláři.
    >>> grades = Grades(url, token)
    >>> grades = Grades(client) # <- You can also use a `Client` instance
    >>> for subject in grades.grades().subjects:
    >>>     for grade in subject.grades:
    >>>         print(grade.subject)
    >>>         print(grade.caption)
    >>>         print(grade.grade)
    Methods:
        grades(): Retrieves all grades.
        clear_cache(): Clears cache.
    """

    def __init__(self, client: Client = None, url: str = None, token: str = None):
        super().__init__(client=client, url=url, token=token)
        self.logger = _setup_logger(f"grades_{client.username}")

        self.thread = Thread(target=self._grades)
        self.thread.start()
        self.logger.info(f"GRADES THREAD STARTED")

    def grades(self) -> "Grades._grades.Result":
        """
        Retrieves all grades.
        >>> for subject in grades.grades().subjects:
        >>>     subject.name
        >>>     for grade in subject.grades:
        >>>         grade.caption
        >>>         grade.grade
        """
        if self.thread.is_alive():
            self.logger.info("GRADES THREAD RUNNING")
            self.thread.join()
            self.logger.info("GRADES THREAD FINISHED")
        return self._grades()

    def _grades(self) -> "Grades._grades.Result":
        response = request(url=self.url, hx=self.token, pm="znamky")
        if response["predmety"] is None:
            raise BakalibError("Grades module returned None, no grades were found.")

        for index, subject in enumerate(response["predmety"]["predmet"]):
            if not isinstance(subject["znamky"]["znamka"], list):
                response["predmety"]["predmet"][index]["znamky"]["znamka"] = [
                    subject["znamky"]["znamka"]
                ]

        @dataclass(frozen=True)
        class Result:
            subjects: list

            def __len__(self):
                return len(self.subjects)

        @dataclass(frozen=True)
        class Subject:
            name: str
            abbr: str
            average_round: str
            average: str
            recalculation: str
            points_to_grade: str
            quarter: str
            note: str
            glob_note: str
            grades: list

            def __len__(self):
                return len(self.grades)

        @dataclass(frozen=True)
        class Grade:
            subject: str
            max_points: str
            grade: str
            gr: str
            points: str
            date: str
            date_granted: str
            weight: str
            caption: str
            note: str
            type: str
            description: str

        subjects = [
            Subject(
                subject["nazev"],
                subject["zkratka"],
                subject["prumer"],
                subject["numprumer"],
                subject["prepocet"],
                subject["bodytoznm"],
                subject["ctvrt"],
                subject["pozn"],
                subject["globpozn"],
                [
                    Grade(
                        grade.get("pred"),
                        grade.get("maxb"),
                        grade.get("znamka"),
                        grade.get("zn"),
                        grade.get("bd"),
                        grade.get("datum"),
                        grade.get("udeleno"),
                        grade.get("vaha"),
                        grade.get("caption"),
                        grade.get("poznamka"),
                        grade.get("typ"),
                        grade.get("ozn"),
                    )
                    for grade in subject["znamky"]["znamka"]
                ],
            )
            for subject in response["predmety"]["predmet"]
        ]
        return Result(subjects)

    def clear_cache(self) -> None:
        """
        Clear all entries related to the "znamky" module from global cache.
        >>> grades.clear_cache()
        """
        for entry in cache:
            if "znamky" in entry:
                cache.pop(entry)
