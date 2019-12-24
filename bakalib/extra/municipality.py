"""
municipality
============
"""

__all__ = ("Municipality",)

import dataclasses
import json
import re
from threading import Thread

import requests

from ..utils import BakalibError, _setup_logger, data_dir


class Municipality:
    """
    Provides info about all schools that use the Bakaláři system.\n
        >>> m = Municipality()
        >>> for city in m.municipality().cities:
        >>>     print(city.name)
        >>>     for school in city.schools:
        >>>         print(school.name)
        >>>         print(school.domain)
    Methods:\n
            municipality(): Returns your local database as a NamedTuple
            build(): Builds the local database from 'https://sluzby.bakalari.cz/api/v1/municipality'.
                     Library comes prepackaged with a database json. Use only when needed.
    """

    db_file = data_dir.joinpath("municipality", "db.json")

    @dataclasses.dataclass(frozen=True)
    class Result:
        cities: list

        def __len__(self):
            return len(self.cities)

    @dataclasses.dataclass(frozen=True)
    class City:
        name: str
        school_count: str
        schools: list

        def __len__(self):
            return len(self.schools)

    @dataclasses.dataclass(frozen=True)
    class School:
        id: str
        name: str
        domain: str

    def __init__(self):
        self.logger = _setup_logger("municipality")

        self.thread = Thread(target=self._municipality)
        self.thread.start()
        self.logger.info("MUNICIPALITY THREAD STARTED")

    def municipality(self):
        if self.thread.is_alive():
            self.logger.info("MUNICIPALITY THREAD RUNNING")
            self.thread.join()
            self.logger.info("MUNICIPALITY THREAD FINISHED")
        return self._municipality()

    def _municipality(self):
        if not data_dir.is_dir():
            data_dir.mkdir()
        if self.db_file.is_file():
            db = json.loads(self.db_file.read_text(encoding="utf-8"), encoding="utf-8")
            result = self.Result(
                [
                    self.City(
                        name=city["name"],
                        school_count=city["school_count"],
                        schools=[
                            self.School(
                                id=school["id"],
                                name=school["name"],
                                domain=school["domain"],
                            )
                            for school in city["schools"]
                        ],
                    )
                    for city in db["cities"]
                ]
            )
            return result
        else:
            return self.build()

    def build(self):
        import lxml.etree as ET

        url = "https://sluzby.bakalari.cz/api/v1/municipality/"
        parser = ET.XMLParser(recover=True)

        try:
            result = self.Result(
                [
                    self.City(
                        municInfo.find("name").text,
                        municInfo.find("schoolCount").text,
                        [
                            self.School(
                                school.find("id").text,
                                school.find("name").text,
                                re.sub(
                                    "((/)?login.aspx(/)?)?",
                                    "",
                                    re.sub(
                                        "http(s)?://(www.)?",
                                        "",
                                        school.find("schoolUrl").text,
                                    ),
                                ).rstrip("/"),
                            )
                            for school in ET.fromstring(
                                requests.get(
                                    url
                                    + requests.utils.quote(municInfo.find("name").text),
                                    stream=True,
                                ).content,
                                parser=parser,
                            ).iter("schoolInfo")
                            if school.find("name").text
                        ],
                    )
                    for municInfo in ET.fromstring(
                        requests.get(url, stream=True).content, parser=parser
                    ).iter("municipalityInfo")
                    if municInfo.find("name").text
                ]
            )
        except Exception as e:
            self.logger.error(f"{type(e)}: {e}")
            raise BakalibError("Municipality failed to generate")

        self.db_file.write_text(
            json.dumps(dataclasses.asdict(result), indent=4, sort_keys=True),
            encoding="utf-8",
        )
        return result
