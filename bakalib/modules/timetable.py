"""
timetable
=========
"""

__all__ = ("Timetable",)

import datetime
import html
from concurrent.futures.thread import ThreadPoolExecutor
from dataclasses import dataclass

from ..core.client import Client
from ..utils import _setup_logger, cache, request
from ._generic import Generic


class Timetable(Generic):
    """
    Obtains information from the "rozvrh" module of Bakaláři.
    >>> timetable = Timetable(url, token)
    >>> timetable = Timetable(client) # <- You can also use a `Client` instance
    Methods:
        prev_week(prune: bool): Decrements self.date by 7 days and points to self.date_week.
        this_week(prune: bool): Points to date_week() with current date.
        next_week(prune: bool): Increments self.date by 7 days and points to self.date_week.
        date_week(date: datetime.date, prune: bool): Obtains timetable data about the week of the provided date.
        clear_cache(): Clears cache.
    """

    def __init__(
        self,
        client: Client = None,
        url: str = None,
        token: str = None,
        date: datetime.date = datetime.date.today(),
    ):
        super().__init__(client=client, url=url, token=token)
        self.date = date
        self.logger = _setup_logger(f"timetable_{client.username}")

        self.threadpool = ThreadPoolExecutor(max_workers=8)
        self.logger.info("TIMETABLE THREADPOOL CREATED")
        self.threadpool.submit(self._date_week, self.date)
        self.logger.info("TASK SUBMITTED")

    # ----------------------------------------------------

    def prev_week(self, prune: bool = True) -> "Timetable._date_week.Result":
        self.date = self.date - datetime.timedelta(7)
        return self.date_week(self.date, prune=prune)

    def this_week(self, prune: bool = True) -> "Timetable._date_week.Result":
        self.date = datetime.date.today()
        return self.date_week(self.date, prune=prune)

    def next_week(self, prune: bool = True) -> "Timetable._date_week.Result":
        self.date = self.date + datetime.timedelta(7)
        return self.date_week(self.date, prune=prune)

    # ----------------------------------------------------

    def date_week(
        self, date: datetime.date = None, prune: bool = True
    ) -> "Timetable._date_week.Result":
        """
        Obtains all timetable data about the week of the provided date.
        >>> this_week = timetable.date_week(datetime.date.today())
        >>> this_week = timetable.date_week(datetime.date.today(), prune=False) # <- Use this if you want to preserve empty lessons.
        >>> for header in this_week.headers:
        >>>     header.caption
        >>> for day in this_week.days:
        >>>     day.abbr
        >>>     for lesson in day.lessons:
        >>>         lesson.name
        >>>         lesson.teacher
        """
        self.date = date if date else self.date
        date_str = "{:04}{:02}{:02}".format(
            self.date.year, self.date.month, self.date.day
        )

        if not (self.url, self.token, "rozvrh", date_str) in cache:
            self.threadpool.shutdown(wait=True)
            self.logger.info("STOPPED, CREATING NEW THREADPOOL")
            self.threadpool = ThreadPoolExecutor(max_workers=8)
            self.logger.info("NEW THREADPOOL CREATED")

        self.threadpool.submit(self._date_week, self.date - datetime.timedelta(7))
        self.threadpool.submit(self._date_week, self.date + datetime.timedelta(7))
        self.logger.info("NEW TASKS SUBMITTED")

        return self._date_week(self.date, prune=prune)

    def _date_week(
        self, date: datetime.date, prune: bool = True
    ) -> "Timetable._date_week.Result":
        date_str = "{:04}{:02}{:02}".format(date.year, date.month, date.day)

        response = request(url=self.url, hx=self.token, pm="rozvrh", pmd=date_str)

        @dataclass(frozen=True)
        class Result:
            headers: list
            days: list
            cycle_name: str

            def __len__(self):
                return len(self.days)

        @dataclass(frozen=True)
        class Header:
            caption: str
            time_begin: str
            time_end: str

        @dataclass(frozen=True)
        class Day:
            abbr: str
            date: str
            lessons: list

            def __len__(self):
                return len(self.lessons)

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
            Header(header["caption"], header["begintime"], header["endtime"])
            for header in response["rozvrh"]["hodiny"]["hod"]
        ]
        days = [
            Day(
                day["zkratka"],
                day["datum"],
                [
                    Lesson(
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
                Header(lesson.caption, lesson.time_begin, lesson.time_end)
                for lesson in (
                    longest_day.lessons if longest_day else max(days, key=len)
                )
            ]

            for day in days:
                while len(day.lessons) < max(lengths):
                    day.lessons.append(placeholder_lesson)

        return Result(headers, days, response["rozvrh"]["nazevcyklu"])

    def clear_cache(self) -> None:
        """
        Clears all entries related to the "rozvrh" module from global cache.
        >>> timetable.clear_cache()
        """
        for entry in cache:
            if "rozvrh" in entry:
                cache.pop(entry)
