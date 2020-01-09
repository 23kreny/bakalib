"""
timetable
=========
"""

__all__ = ("TimetableModule",)

import datetime
import html
from dataclasses import dataclass
from typing import List
from cachetools import cached
from ..core.client import Client
from ..utils import _setup_logger, cache
from ._generic import GenericModule


class TimetableModule(GenericModule):
    """This is a class for accessing timetables of a client
    
    :param client: Instance of a client, defaults to None
    :type client: Client, optional
    :param url: URL of the school server, defaults to None
    :type url: str, optional
    :param token: Access token, defaults to None
    :type token: str, optional
    :param date: Initial date, defaults to datetime.date.today()
    :type date: datetime.date, optional
    """

    date: datetime.date

    @dataclass(frozen=True)
    class Header:
        caption: str
        time_begin: str
        time_end: str

    @dataclass(frozen=True)
    class Lesson:
        id_code: str
        type: str
        holiday: str
        abbr: str
        name: str
        teacher_abbr: str
        teacher: str
        room_abbr: str
        room: str
        absence_abbr: str
        absence: str
        theme: str
        group_abbr: str
        group: str
        cycle: str
        disengaged: str
        change_description: str
        notice: str
        caption: str
        time_begin: str
        time_end: str

    @dataclass(frozen=True)
    class Day:
        abbr: str
        date: str
        lessons: List["TimetableModule.Lesson"]

        def __len__(self):
            return len(self.lessons)

    @dataclass(frozen=True)
    class Result:
        headers: List["TimetableModule.Header"]
        days: List["TimetableModule.Day"]
        cycle_name: str

    def __init__(
        self,
        client: Client = None,
        url: str = None,
        token: str = None,
        date: datetime.date = datetime.date.today(),
    ):
        """Constructor method
        """
        super().__init__(client=client, url=url, token=token)
        self.date = date
        self.logger = _setup_logger(f"[TIMETABLE_{client.username}]")

    # ----------------------------------------------------

    def prev_week(self, prune: bool = True) -> "TimetableModule.Result":
        """Convenience method
        
        :param prune: Remove unnecessary empty lessons, defaults to True
        :type prune: bool, optional
        :return: Dataclass containing all days
        :rtype: TimetableModule.Result
        """
        self.date = self.date - datetime.timedelta(7)
        return self.date_week(self.date, prune)

    def this_week(self, prune: bool = True) -> "TimetableModule.Result":
        """Convenience method
        
        :param prune: Remove unnecessary empty lessons, defaults to True
        :type prune: bool, optional
        :return: Dataclass containing all days
        :rtype: TimetableModule.Result
        """
        self.date = datetime.date.today()
        return self.date_week(self.date, prune)

    def next_week(self, prune: bool = True) -> "TimetableModule.Result":
        """Convenience method
        
        :param prune: Remove unnecessary empty lessons, defaults to True
        :type prune: bool, optional
        :return: Dataclass containing all days
        :rtype: TimetableModule.Result
        """
        self.date = self.date + datetime.timedelta(7)
        return self.date_week(self.date, prune)

    # ----------------------------------------------------

    def date_week(
        self, date: datetime.date = None, prune: bool = True
    ) -> "TimetableModule.Result":
        """Fetches timetable data
        
        :param date: Date used to fetch the data, defaults to None
        :type date: datetime.date, optional
        :param prune: Remove unnecessary empty lessons, defaults to True
        :type prune: bool, optional
        :return: Dataclass containing all days
        :rtype: TimetableModule.Result
        """
        date_str = "{:04}{:02}{:02}".format(
            self.date.year, self.date.month, self.date.day
        )

        response = self.request(hx=self.token, pm="rozvrh", pmd=date_str)

        def holiday_check(obj: dict):
            zkratka = obj.get("zkratka")
            nazev = obj.get("nazev")
            if not zkratka:
                return nazev
            elif not nazev:
                return zkratka
            elif zkratka and nazev:
                return max([obj.get("zkratka"), obj.get("nazev")], key=len)
            else:
                return None

        headers = [
            self.Header(header["caption"], header["begintime"], header["endtime"])
            for header in response["rozvrh"]["hodiny"]["hod"]
        ]
        days = [
            self.Day(
                day["zkratka"],
                day["datum"],
                [
                    self.Lesson(
                        lesson.get("idcode"),
                        lesson.get("typ"),
                        holiday_check(lesson),
                        lesson.get("zkrpr"),
                        lesson.get("pr"),
                        lesson.get("zkruc"),
                        lesson.get("uc"),
                        lesson.get("zkrmist"),
                        lesson.get("mist"),
                        lesson.get("zkrabs"),
                        lesson.get("abs"),
                        html.unescape(lesson.get("tema"))
                        if lesson.get("tema")
                        else lesson.get("tema"),
                        lesson.get("zkrskup"),
                        lesson.get("skup"),
                        lesson.get("cycle"),
                        lesson.get("uvol"),
                        lesson.get("chng"),
                        lesson.get("notice"),
                        header.caption,
                        header.time_begin,
                        header.time_end,
                    )
                    for header, lesson in zip(headers, day["hodiny"]["hod"])
                ],
            )
            for day in response["rozvrh"]["dny"]["den"]
        ]

        if prune:
            lengths = []
            placeholder_lesson = None
            for day in days:
                for lesson in day.lessons:
                    if (
                        (lesson.type == "X" or lesson.type == "A")
                        and not lesson.holiday
                        and not lesson.change_description
                    ):
                        day.lessons.pop(0)
                    else:
                        break
                for lesson in reversed(day.lessons):
                    if (
                        (lesson.type == "X" or lesson.type == "A")
                        and not lesson.holiday
                        and not lesson.change_description
                    ):
                        day.lessons.pop()
                        placeholder_lesson = lesson
                    else:
                        break
                lengths.append(len(day))

            longest_day = None
            for day in sorted(days, key=len, reverse=True):
                if day.lessons[-1].type != "A" and day.lessons[-1].type != "X":
                    longest_day = day
                    break
            else:
                longest_day = max(days, key=len)

            headers = [
                self.Header(lesson.caption, lesson.time_begin, lesson.time_end)
                for lesson in (
                    longest_day.lessons if longest_day else max(days, key=len)
                )
            ]

            for day in days:
                while len(day.lessons) < max(lengths):
                    day.lessons.append(placeholder_lesson)

        return self.Result(headers, days, response["rozvrh"]["nazevcyklu"])

    def clear_cache(self) -> None:
        """Clears all entries related to timetable from cache
        """
        for entry in cache:
            if "rozvrh" in entry:
                cache.pop(entry)
