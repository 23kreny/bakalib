import base64
import datetime
import hashlib
import json
import pathlib
import re
from typing import NamedTuple
from threading import Thread
from concurrent.futures.thread import ThreadPoolExecutor

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


cache = cachetools.TTLCache(32, 300)

@cachetools.cached(cache)
def request(url: str, token: str, *args) -> dict:
    '''
    Make a GET request to school URL.\n
    Module names are available at `https://github.com/bakalari-api/bakalari-api/tree/master/moduly`.
    '''
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


class Client(object):
    '''
    Creates an instance with access to basic information of the user.
    >>> user = Client(username="User12345", domain="domain.example.com/bakaweb", password="1234abcd")
    >>> user = Client(username="User12345", domain="domain.example.com/bakaweb", perm_token="*login*User12345*pwd*abcdefgh12345678+jklm==*sgn*ANDR")
    >>> user.info()
    Methods:
        info(): Obtains basic information about the user.
        add_modules(*args): Extends the functionality with another module/s.
    '''
    def __init__(self, username: str, password=None, domain=None, perm_token=None):
        super().__init__()
        self.username = username
        self.domain = domain
        self.url = "https://{}/login.aspx".format(self.domain)

        self.timetable = Timetable
        self.grades = Grades

        if perm_token:
            self.perm_token = perm_token
            token = self._token(self.perm_token)
        elif password:
            self.perm_token = self._permanent_token(username, password)
            token = self._token(self.perm_token)
        else:
            raise BakalibError("Incorrect arguments")

        if self._is_token_valid(token):
            self.token = token
        else:
            raise BakalibError("Token is invalid: Invalid password/perm_token")
            
    def _permanent_token(self, user: str, password: str) -> str:
        '''
        Generates a permanent access token with securely hashed password.
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
        perm_token = "*login*" + user + "*pwd*" + \
            hashed_password.decode("utf8") + "*sgn*ANDR"
        return perm_token

    def _token(self, perm_token: str) -> str:
        '''
        Generates an access token using current time.
        '''
        today = datetime.date.today()
        datecode = "{:04}{:02}{:02}".format(today.year, today.month, today.day)
        hash = hashlib.sha512((perm_token + datecode).encode("utf-8")).digest()
        token = base64.urlsafe_b64encode(hash).decode("utf-8")
        return token

    def _is_token_valid(self, token: str) -> bool:
        '''
        Checks for token validity.
        '''
        try:
            request(self.url, token, "login")
            return True
        except BakalibError:
            return False

    def add_modules(self, *modules) -> None:
        '''
        Extends the functionality of the Client class with another module(s).\n
        Supported modules: timetable, grades\n
        WIP: absence
        >>> user.add_modules("timetable", "grades")
        >>> user.timetable.this_week()
        >>> user.grades.grades()
        '''
        if modules:
            for module in modules:
                if module == "timetable":
                    if self.timetable == Timetable:
                        self.timetable = Timetable(self.url, self.token)
                elif module == "grades":
                    if self.grades == Grades:
                        self.grades = Grades(self.url, self.token)
                else:
                    raise BakalibError("Bad module name was provided")
        else:
            raise BakalibError("No modules were provided")

    def info(self):
        '''
        Obtains basic information about the user into a NamedTuple.
        >>> user.info().name
        >>> user.info().class_ # <-- due to class being a reserved keyword.
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


class Timetable(object):
    '''
    Obtains information from the "rozvrh" module of Bakaláři.
    >>> timetable = Timetable(url, token)
    Methods:
        prev_week(): Decrements self.date by 7 days and points to self.date_week.
        this_week(): Points to date_week() with current date.
        next_week(): Increments self.date by 7 days and points to self.date_week.
        date_week(date): Obtains all timetable data about the week of the provided date.
    '''
    def __init__(self, url, token, date=datetime.date.today()):
        super().__init__()
        self.url = url
        self.token = token
        self.date = date

        self.threadpool = ThreadPoolExecutor(max_workers=8)
        self.threadpool.submit(self._date_week, self.date)

    # ----------------------------------------------------

    def prev_week(self):
        self.date = self.date - datetime.timedelta(7)
        return self.date_week(self.date)

    def this_week(self):
        self.date = datetime.date.today()
        return self.date_week(self.date)

    def next_week(self):
        self.date = self.date + datetime.timedelta(7)
        return self.date_week(self.date)

    # ----------------------------------------------------

    def date_week(self, date=None):
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
        global cache

        self.date = date if date else self.date
        date_str = "{:04}{:02}{:02}".format(date.year, date.month, date.day)

        if not (self.url, self.token, "rozvrh", date_str) in cache:
            self.threadpool.shutdown(wait=True)
            self.threadpool = ThreadPoolExecutor(max_workers=8)

        self.threadpool.submit(
            self._date_week, self.date - datetime.timedelta(7))
        self.threadpool.submit(
            self._date_week, self.date + datetime.timedelta(7))
        return self._date_week(self.date)

    def _date_week(self, date):
        date_str = "{:04}{:02}{:02}".format(date.year, date.month, date.day)

        response = request(
            self.url,
            self.token,
            "rozvrh",
            date_str
        )

        class Result(NamedTuple):
            headers: list
            days: list
            cycle_name: str

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
            Day(
                day["zkratka"],
                day["datum"],
                [Lesson(
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
                ) for header, lesson in zip(headers, day["hodiny"]["hod"])]
            ) for day in response["rozvrh"]["dny"]["den"]
        ]
        return Result(headers, days, response["rozvrh"]["nazevcyklu"])


class Grades(object):
    '''
    Obtains information from the "znamky" module of Bakaláři.
    >>> grades = Grades(url, token)
    >>> for subject in grades.grades().subjects:
    >>>     for grade in subject.grades:
    >>>         print(grade.subject)
    >>>         print(grade.caption)
    >>>         print(grade.grade)
    Methods:
        grades(): Obtains all grades.
    '''
    def __init__(self, url, token):
        super().__init__()
        self.url = url
        self.token = token

        self.thread = Thread(target=self._grades)
        self.thread.start()

    def grades(self):
        '''
        Obtains all grades.
        >>> for subject in grades.grades().subjects:
        >>>     subject.name
        >>>     for grade in subject.grades:
        >>>         grade.caption
        >>>         grade.grade
        '''
        if self.thread.is_alive():
            self.thread.join()
        return self._grades()

    def _grades(self):
        response = request(
            self.url,
            self.token,
            "znamky"
        )
        if response["predmety"] is None:
            raise BakalibError("Grades module returned None, no grades were found.")

        for index, subject in enumerate(response["predmety"]["predmet"]):
            if not isinstance(subject["znamky"]["znamka"], list):
                response["predmety"]["predmet"][index]["znamky"]["znamka"] = [subject["znamky"]["znamka"]]

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
            note: str

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
                        grade.get("ozn"),
                        grade.get("poznamka")
                    ) for grade in subject["znamky"]["znamka"]
                ]
            ) for subject in response["predmety"]["predmet"]
        ]
        return Result(subjects)

    def refresh_cache(self):
        self.cache.clear()
        self.thread.start()
