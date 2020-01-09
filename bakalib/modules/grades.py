"""
grades
======
"""

__all__ = ("GradesModule",)

from dataclasses import dataclass
from typing import List

from ..core.client import Client
from ..utils import BakalibError, _setup_logger
from ._generic import GenericModule


class GradesModule(GenericModule):
    """This is a class for accessing grades of a client
    
    :param client: Instance of Client, defaults to None
    :type client: Client, optional
    :param url: URL of the school server, defaults to None
    :type url: str, optional
    :param token: Access token of a client, defaults to None
    :type token: str, optional
    """

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
        grades: List["GradesModule.Grade"]

        def __len__(self):
            return len(self.grades)

    def __init__(self, client: Client = None, url: str = None, token: str = None):
        """Constructor method
        """
        super().__init__(client=client, url=url, token=token)
        self.logger = _setup_logger(f"[GRADES_{client.username}]")

    def subjects(self) -> List["GradesModule.Subject"]:
        """Fetches all subjects and grades
        
        :raises BakalibError: If no grades returned
        :return: Dataclass containing subjects list
        :rtype: GradesModule.Result
        """
        response = self.request(hx=self.token, pm="znamky")
        if response["predmety"] is None:
            raise BakalibError("Grades module returned None, no grades were found.")

        for index, subject in enumerate(response["predmety"]["predmet"]):
            if not isinstance(subject["znamky"]["znamka"], list):
                response["predmety"]["predmet"][index]["znamky"]["znamka"] = [
                    subject["znamky"]["znamka"]
                ]

        return [
            self.Subject(
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
                    self.Grade(
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
