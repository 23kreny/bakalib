import base64
import datetime
import hashlib
import json
import pathlib
import re
from typing import NamedTuple

import cachetools
import requests
import urllib3
import xmltodict

name = "bakalib"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BakalibError(Exception):
    pass


class Municipality:
    '''
    Provides info about all schools that use the Bakaláři system.\n
        >>> m = Municipality()
        >>> for city in m.cities:
        >>>     print(city.name)
        >>>     for school in city.schools:
        >>>         print(school.name)
        >>>         print(school.domain)
    Methods:\n
            build(): Builds the local database from 'https://sluzby.bakalari.cz/api/v1/municipality'.
                     Library comes prepackaged with the database json.
                     Use only when needed.
    '''
    conf_dir = pathlib.Path(__file__).parent.joinpath("data")
    db_file = conf_dir.joinpath("municipality.json")

    class City(NamedTuple):
        name: str
        school_count: str
        schools: list

    class School(NamedTuple):
        id: str
        name: str
        domain: str

    def __init__(self):
        super().__init__()
        if not self.conf_dir.is_dir():
            self.conf_dir.mkdir()
        if self.db_file.is_file():
            self.cities = [
                self.City(
                    city[0],
                    city[1],
                    [
                        self.School(
                            school[0],
                            school[1],
                            school[2]
                        ) for school in city[2]
                    ]
                ) for city in json.loads(self.db_file.read_text(encoding='utf-8'), encoding='utf-8')
            ]
        else:
            self.cities = self.build()

    def build(self) -> dict:
        import lxml.etree as ET
        url = "https://sluzby.bakalari.cz/api/v1/municipality/"
        parser = ET.XMLParser(recover=True)

        cities = [
            self.City(
                municInfo.find("name").text,
                municInfo.find("schoolCount").text,
                [
                    self.School(
                        school.find("id").text,
                        school.find("name").text,
                        re.sub("((/)?login.aspx(/)?)?", "", re.sub("http(s)?://(www.)?",
                                                                   "", school.find("schoolUrl").text)).rstrip("/")
                    ) for school in ET.fromstring(requests.get(url + requests.utils.quote(municInfo.find("name").text), stream=True).content, parser=parser).iter("schoolInfo") if school.find("name").text
                ]
            ) for municInfo in ET.fromstring(requests.get(url, stream=True).content, parser=parser).iter("municipalityInfo") if municInfo.find("name").text
        ]
        self.db_file.write_text(json.dumps(
            cities, indent=4, sort_keys=True), encoding='utf-8')
        return cities


def request(url: str, token: str, *args) -> dict:
    '''
    Make a GET request to school URL.\n
    Module names are available at `https://github.com/bakalari-api/bakalari-api/tree/master/moduly`.
    '''
    if args is None or len(args) > 2:
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
        raise BakalibError("Wrong request")
    return response["results"]


class Client(object):
    '''
    Creates an instance with access to basic information of the user.
    >>> user = Client(username="Username12345", domain="domain.example.com", password="1234abcd")
    >>> user = Client(username="Username12345", domain="domain.example.com", perm_token="*login*Username12345*pwd*abcdefgh12345678+jklm==*sgn*ANDR")
    Methods:
        info(): Obtains basic information about the user.
        add_modules(*args): Extends the functionality with another module/s.
    '''

    def __init__(self, username: str, password=None, domain=None, perm_token=None):
        super().__init__()
        self.url = "https://{}/login.aspx".format(domain)

        if password:
            self.perm_token = self.__permanent_token(username, password)
            token = self.__token(self.perm_token)
            if not self.__is_token_valid(token):
                raise BakalibError("Token is invalid\nInvalid password")
            self.token = token
        elif perm_token:
            self.perm_token = perm_token
            self.token = self.__token(self.perm_token)
        else:
            raise BakalibError("Incorrect arguments")

    def __permanent_token(self, user: str, password: str) -> str:
        '''
        Generates a permanent access token with securely hashed password.\n
        Returns a `str` containing the token.
        '''
        r = requests.get(url=self.url, params={"gethx": user}, verify=False)
        xml = xmltodict.parse(r.content)
        if not xml["results"]["res"] == "01":
            raise BakalibError("Invalid username")
        salt = xml["results"]["salt"]
        ikod = xml["results"]["ikod"]
        typ = xml["results"]["typ"]
        salted_password = (salt + ikod + typ + password).encode("utf-8")
        hashed_password = base64.b64encode(
            hashlib.sha512(salted_password).digest())
        permtoken = "*login*" + user + "*pwd*" + \
            hashed_password.decode("utf8") + "*sgn*ANDR"
        return permtoken

    def __token(self, permtoken: str) -> str:
        today = datetime.date.today()
        datecode = "{:04}{:02}{:02}".format(today.year, today.month, today.day)
        hash = hashlib.sha512((permtoken + datecode).encode("utf-8")).digest()
        token = base64.urlsafe_b64encode(hash).decode("utf-8")
        return token

    def __is_token_valid(self, token: str) -> bool:
        try:
            request(self.url, token, "login")
            return True
        except BakalibError:
            return False

    def info(self):
        '''
        Obtains basic information about the user into a NamedTuple.
        >>> user.info().name
        >>> user.info().class_ # <-- due to class being reserved keyword.
        >>> user.info().school
        '''
        class Result(NamedTuple):
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
                response.get(element).get(
                    "newmarkdays") if element == "params" else response.get(element)
                for element in response if not element == "result"
            ]
        )
        return result

    def add_modules(self, *modules):
        '''
        Extends the functionality of the Client class with another module(s).
        >>> user.add_modules("timetable", "grades")
        >>> user.timetable.this_week()
        '''
        if modules:
            for module in modules:
                if module == "timetable":
                    self.timetable = Timetable(self.url, self.token)
                elif module == "grades":
                    self.grades = Grades(self.url, self.token)
                else:
                    raise BakalibError("Bad module name was provided")
        else:
            raise BakalibError("No modules were provided")


class Timetable(object):
    '''
    Obtains information from the "rozvrh" module of Bakaláři.
    >>> timetable = Timetable(url, token)
    Methods:
        prev_week(): Decrements self.date by 7 days and points to date_week(self.date).
        this_week(): Points to date_week() with current date.
        next_week(): Increments self.date by 7 days and points to date_week(self.date).
        date_week(date): Obtains all timetable data about the week of the provided date.
    '''
    cache = cachetools.TTLCache(60, 300)

    def __init__(self, url, token):
        super().__init__()
        self.url = url
        self.token = token
        self.today = datetime.date.today()

  # #region `Convenience methods - self.prev_week(), self.this_week(), self.next_week()`

    def prev_week(self):
        date = self.today - datetime.timedelta(7)
        return self.date_week(date)

    def this_week(self):
        return self.date_week(self.today + datetime.timedelta(days=-self.today.weekday(), weeks=1))

    def next_week(self):
        date = self.today + datetime.timedelta(7)
        return self.date_week(date)
  # #endregion

    @cachetools.cached(cache)
    def date_week(self, date):
        '''
        Obtains all timetable data about the week of the provided date.
        >>> this_week = timetable.date_week(datetime.date.today())
        >>> for header in this_week.headers:
        >>>     header.caption
        >>> for day in this_week.days:
        >>>     day.abbr
        >>>     for lesson in day.lessons:
        >>>         lesson.name
        >>>         lesson.teacher
        '''
        response = request(
            self.url,
            self.token,
            "rozvrh",
            "{:04}{:02}{:02}".format(date.year, date.month, date.day)
        )

        class Result(NamedTuple):
            headers: list
            days: list

        class Header(NamedTuple):
            caption: str
            time_begin: str
            time_end: str

        class Day(NamedTuple):
            abbr: str
            date: str
            lessons: list

        class Lesson(NamedTuple):
            idcode: str
            type: str
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

        headers = [
            Header(
                header["caption"],
                header["begintime"],
                header["endtime"]
            ) for header in response["rozvrh"]["hodiny"]["hod"]
        ]
        days = [
            Day(day["zkratka"], day["datum"],
                [
                    Lesson(
                        lesson.get("idcode"), lesson.get("typ"),
                        lesson.get("zkrpr"), lesson.get("pr"),
                        lesson.get("zkruc"), lesson.get("uc"),
                        lesson.get("zkrmist"), lesson.get("mist"),
                        lesson.get("zkrabs"), lesson.get("abs"),
                        lesson.get("tema"), lesson.get("zkrskup"),
                        lesson.get("skup"), lesson.get("cycle"),
                        lesson.get("uvol"), lesson.get("chng"),
                        lesson.get("notice"), header.caption,
                        header.time_begin, header.time_end
                    ) for header, lesson in zip(headers, day["hodiny"]["hod"])
            ]
            ) for day in response["rozvrh"]["dny"]["den"]
        ]
        return Result(headers, days)


class Grades(object):
    '''
    Obtains information from the "znamky" module of Bakaláři.
    >>> grades = Grades(url, token)
    Methods:
        grades(): Obtains all grades.
    '''
    cache = cachetools.TTLCache(5, 300)

    def __init__(self, url, token):
        super().__init__()
        self.url = url
        self.token = token

    @cachetools.cached(cache)
    def grades(self):
        '''
        Obtains all grades.
        >>> for subject in grades.grades().subjects:
        >>>     subject.name
        >>>     for grade in subject.grades:
        >>>         grade.caption
        >>>         grade.grade
        '''
        response = request(
            self.url,
            self.token,
            "znamky"
        )
        if response["predmety"] is None:
            BakalibError("Grades module returned None, no grades were found.")
            return None

        class Result(NamedTuple):
            subjects: list

        class Subject(NamedTuple):
            name: str
            abbr: str
            average_round: str
            average: str
            grades: list

        class Grade(NamedTuple):
            subject: str
            maxb: str
            grade: str
            gr: str
            date: str
            date_granted: str
            weight: str
            caption: str
            type: str
            description: str

        print(response["predmety"]["predmet"])
        subjects = [
            Subject(
                subject["nazev"],
                subject["zkratka"],
                subject["prumer"],
                subject["numprumer"],
                [
                    Grade(
                        grade.get("pred"),
                        grade.get("maxb"),
                        grade.get("znamka"),
                        grade.get("zn"),
                        grade.get("datum"),
                        grade.get("udeleno"),
                        grade.get("vaha"),
                        grade.get("caption"),
                        grade.get("typ"),
                        grade.get("ozn")
                    ) for grade in subject["znamky"]["znamka"]
                ]
            ) for subject in response["predmety"]["predmet"]
        ]
        return Result(subjects)
