import base64
import datetime
import hashlib
import json
import pathlib
import re
from concurrent.futures.thread import ThreadPoolExecutor
import dataclasses
from threading import Thread

import cachetools
import requests
import urllib3
import xmltodict

name = "bakalib"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BakalibError(Exception):
    pass


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
            build(): Builds the local database from 'https://sluzby.bakalari.cz/api/v1/municipality'.
                     Library comes prepackaged with the database json.
                     Use only when needed.
    """

    data_dir = pathlib.Path(__file__).parent.joinpath("data")
    db_file = data_dir.joinpath("municipality.json")

    @dataclasses.dataclass(frozen=True)
    class Result:
        cities: list

    @dataclasses.dataclass(frozen=True)
    class City:
        name: str
        school_count: str
        schools: list

    @dataclasses.dataclass(frozen=True)
    class School:
        id: str
        name: str
        domain: str

    def __init__(self):
        super().__init__()

        self.thread = Thread(target=self._municipality)
        self.thread.start()

    def municipality(self):
        if self.thread.is_alive():
            self.thread.join()
        return self._municipality()

    def _municipality(self):
        if not self.data_dir.is_dir():
            self.data_dir.mkdir()
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
                                url + requests.utils.quote(municInfo.find("name").text),
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
        self.db_file.write_text(
            json.dumps(dataclasses.asdict(result), indent=4, sort_keys=True),
            encoding="utf-8",
        )
        return result


cache = cachetools.TTLCache(32, 300)


@cachetools.cached(cache)
def request(url: str, token: str, *args) -> dict:
    """
    Make a GET request to school URL.\n
    Module names are available at `https://github.com/bakalari-api/bakalari-api/tree/master/moduly`.
    """
    if not args or len(args) > 2:
        raise BakalibError("Bad arguments")
    params = {"hx": token, "pm": args[0]}
    if len(args) > 1:
        params.update({"pmd": args[1]})
    r = requests.get(url=url, params=params, verify=False)
    response = xmltodict.parse(r.content)
    try:
        if not response["results"]["result"] == "01":
            raise BakalibError("Received response is invalid")
    except KeyError:
        raise BakalibError("Wrong request/buggy xml")
    return response["results"]


class Client:
    """
    Creates an instance with access to basic information of the user.\n
    Check for validity runs only
    >>> user = Client(username="User12345", domain="domain.example.com/bakaweb", password="1234abcd")
    >>> user = Client(username="User12345", domain="domain.example.com/bakaweb", perm_token="*login*User12345*pwd*abcdefgh12345678+jklm==*sgn*ANDR")
    >>> user.info()
    Methods:
        info(): Obtains basic information about the user.
        add_modules(*args): Extends the functionality with another module/s.
    """

    def __init__(
        self,
        username: str,
        password: str = None,
        domain: str = None,
        perm_token: str = None,
        check_validity: bool = True,
    ):
        super().__init__()
        self.username = username
        self.domain = domain
        self.url = f"https://{self.domain}/login.aspx"

        if perm_token:
            self.perm_token = perm_token
            token = self._token(self.perm_token)
        elif password:
            self.perm_token = self._permanent_token(username, password)
            token = self._token(self.perm_token)
        else:
            raise BakalibError("Incorrect arguments")

        if check_validity:
            if self._is_token_valid(token):
                self.token = token
            else:
                raise BakalibError("Token is invalid: Invalid password/perm_token")
        else:
            self.token = token

        self.thread = Thread(target=request, args=(self.url, self.token, "login"))
        self.thread.start()

    def _permanent_token(self, user: str, password: str) -> str:
        """
        Generates a permanent access token with securely hashed password.
        """
        r = requests.get(url=self.url, params={"gethx": user}, verify=False)
        xml = xmltodict.parse(r.content)
        if not xml["results"]["res"] == "01":
            raise BakalibError("Invalid username")
        salt = xml["results"]["salt"]
        ikod = xml["results"]["ikod"]
        typ = xml["results"]["typ"]
        salted_password = (salt + ikod + typ + password).encode("utf-8")
        hashed_password = base64.b64encode(hashlib.sha512(salted_password).digest())
        perm_token = (
            "*login*" + user + "*pwd*" + hashed_password.decode("utf8") + "*sgn*ANDR"
        )
        return perm_token

    def _token(self, perm_token: str) -> str:
        """
        Generates an access token using current time.
        """
        today = datetime.date.today()
        datecode = "{:04}{:02}{:02}".format(today.year, today.month, today.day)
        hash = hashlib.sha512((perm_token + datecode).encode("utf-8")).digest()
        token = base64.urlsafe_b64encode(hash).decode("utf-8")
        return token

    def _is_token_valid(self, token: str) -> bool:
        """
        Checks for token validity.
        """
        try:
            request(self.url, token, "login")
            return True
        except BakalibError:
            return False

    def add_modules(self, *modules) -> None:
        """
        Extends the functionality of the Client class with another module(s).\n
        Supported modules: timetable, grades\n
        WIP: absence
        >>> user.add_modules("timetable", "grades")
        >>> user.timetable.this_week()
        >>> user.grades.grades()
        """
        if modules:
            for module in modules:
                if module == "timetable":
                    self.timetable = Timetable(self)
                elif module == "grades":
                    self.grades = Grades(self)
                else:
                    raise BakalibError("Bad module name was provided")
        else:
            raise BakalibError("No modules were provided")

    def info(self) -> "Client.info.Result":
        """
        Obtains basic information about the user into a NamedTuple.
        >>> user.info().name
        >>> user.info().class_ # <-- due to class being a reserved keyword.
        >>> user.info().school
        """
        if self.thread.is_alive():
            self.thread.join()

        @dataclasses.dataclass(frozen=True)
        class Result:
            version: str
            name: str
            type_abbr: str
            type: str
            school: str
            school_type: str
            class_: str
            year: str
            modules: str
            newmarkdays: str

        response = request(self.url, self.token, "login")
        result = Result(
            *[
                response.get(element).get("newmarkdays")
                if element == "params"
                else response.get(element)
                for element in response
                if not element == "result"
            ]
        )
        return result


class GenericModule:
    """
    Generic module boilerplate, takes either `Client` object or url and token strings.
    >>> client = Client(username="user123", password="abcdefgh", domain="domain.example.com/bakaweb")
    >>> module = GenericModule(client=client)
    >>> module = GenericModule(url="domain.example.com/bakaweb", token="abcdefgh12345678")
    """

    def __init__(
        self, client: Client = None, url: str = None, token: str = None
    ) -> None:
        if client:
            self.url = client.url
            self.token = client.token
        elif url and token:
            self.url = url
            self.token = token
        else:
            raise BakalibError("Invalid arguments provided to module.")


class Timetable(GenericModule):
    """
    Obtains information from the "rozvrh" module of Bakaláři.
    >>> timetable = Timetable(url, token)
    >>> timetable = Timetable(client) # <- You can also use a `Client` instance
    Methods:
        prev_week(prune: bool): Decrements self.date by 7 days and points to self.date_week.
        this_week(prune: bool): Points to date_week() with current date.
        next_week(prune: bool): Increments self.date by 7 days and points to self.date_week.
        date_week(date: datetime.date, prune: bool): Obtains timetable data about the week of the provided date.
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

        self.threadpool = ThreadPoolExecutor(max_workers=8)
        self.threadpool.submit(self._date_week, self.date)

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
        global cache

        self.date = date if date else self.date
        date_str = "{:04}{:02}{:02}".format(
            self.date.year, self.date.month, self.date.day
        )

        if not (self.url, self.token, "rozvrh", date_str) in cache:
            self.threadpool.shutdown(wait=True)
            self.threadpool = ThreadPoolExecutor(max_workers=8)

        self.threadpool.submit(self._date_week, self.date - datetime.timedelta(7))
        self.threadpool.submit(self._date_week, self.date + datetime.timedelta(7))
        return self._date_week(self.date, prune=prune)

    def clear_cache(self) -> None:
        """
        Clears all entries related to the "rozvrh" module from global cache.
        >>> timetable.clear_cache()
        """
        global cache

        for entry in cache:
            if "rozvrh" in entry:
                cache.pop(entry)

    def _date_week(
        self, date: datetime.date, prune: bool = True
    ) -> "Timetable._date_week.Result":
        date_str = "{:04}{:02}{:02}".format(date.year, date.month, date.day)

        response = request(self.url, self.token, "rozvrh", date_str)

        @dataclasses.dataclass(frozen=True)
        class Result:
            headers: list
            days: list
            cycle_name: str

            def __len__(self):
                return len(days)

        @dataclasses.dataclass(frozen=True)
        class Header:
            caption: str
            time_begin: str
            time_end: str

        @dataclasses.dataclass(frozen=True)
        class Day:
            abbr: str
            date: str
            lessons: list

            def __len__(self):
                return len(self.lessons)

        @dataclasses.dataclass(frozen=True)
        class Lesson:
            id_code: str
            type: str
            holiday: str
            abbr: str
            name: str
            name_alt: str
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
                        lesson.get("zkratka"),
                        lesson.get("zkrpr"),
                        lesson.get("pr"),
                        lesson.get("nazev"),
                        lesson.get("zkruc"),
                        lesson.get("uc"),
                        lesson.get("zkrmist"),
                        lesson.get("mist"),
                        lesson.get("zkrabs"),
                        lesson.get("abs"),
                        lesson.get("tema"),
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
                        lesson.type == "X"
                        and not lesson.holiday
                        and not lesson.name_alt
                        and not lesson.change_description
                    ):
                        day.lessons.pop(0)
                    else:
                        break
                for lesson in reversed(day.lessons):
                    if (
                        lesson.type == "X"
                        and not lesson.holiday
                        and not lesson.name_alt
                        and not lesson.change_description
                    ):
                        day.lessons.pop()
                        placeholder_lesson = lesson
                    else:
                        break
                lengths.append(len(day))

            for day in days:
                while len(day.lessons) < max(lengths):
                    day.lessons.append(placeholder_lesson)

            headers = [
                Header(lesson.caption, lesson.time_begin, lesson.time_end)
                for lesson in max(days, key=len).lessons
            ]

        return Result(headers, days, response["rozvrh"]["nazevcyklu"])


class Grades(GenericModule):
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
    """

    def __init__(self, client: Client = None, url: str = None, token: str = None):
        super().__init__(client=client, url=url, token=token)

        self.thread = Thread(target=self._grades)
        self.thread.start()

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
            self.thread.join()
        return self._grades()

    def clear_cache(self) -> None:
        """
        Clear all entries related to the "znamky" module from global cache.
        >>> grades.clear_cache()
        """
        global cache

        for entry in cache:
            if "znamky" in entry:
                cache.pop(entry)

    def _grades(self) -> "Grades._grades.Result":
        response = request(self.url, self.token, "znamky")
        if response["predmety"] is None:
            raise BakalibError("Grades module returned None, no grades were found.")

        for index, subject in enumerate(response["predmety"]["predmet"]):
            if not isinstance(subject["znamky"]["znamka"], list):
                response["predmety"]["predmet"][index]["znamky"]["znamka"] = [
                    subject["znamky"]["znamka"]
                ]

        @dataclasses.dataclass(frozen=True)
        class Result:
            subjects: list

        @dataclasses.dataclass(frozen=True)
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

        @dataclasses.dataclass(frozen=True)
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
