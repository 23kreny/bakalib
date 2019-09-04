import base64
import datetime
import hashlib
import json
import pathlib
import re
from typing import NamedTuple

import lxml.etree as ET
import requests
import urllib3
import xmltodict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BakalibError(Exception):
    pass


class Municipality:
    '''
    Provides info about all schools that use the Bakaláři system.\n
    Navigate through it like a dictionary:\n
        >>> m = Municipality()
        >>> hodonin = m.cities["Hodonín"]
        >>> for school in hodonin:
        >>>     for name in school:
        >>>        domain = school[name]
        >>>         print("{}: {}".format(name, domain))
        Základní škola Hodonín, U Červených domků 40: bakalari.zsdomkyhod.cz:8088/bakaweb
        Základní škola Hodonín, Vančurova 2, příspěvková organizace: zsvancur.bakalari.cz
        Základní škola Hodonín, Mírové náměstí 19: zshodonin.bakalari.cz/bakaweb
        Střední škola průmyslová a umělecká, Hodonín, Brandlova 32: prumyslovka.bakalari.cz:446/bakaweb
    Methods:\n
            build(): Builds the local database from the 'https://sluzby.bakalari.cz/api/v1/municipality'.
                     Library comes prepackaged with the database json.
                     Use only when needed.
    '''
    conf_dir = pathlib.Path.home().joinpath(".bakalib")
    schooldb_file = conf_dir.joinpath("schooldb.json")

    def __init__(self):
        super().__init__()
        if not self.conf_dir.is_dir():
            self.conf_dir.mkdir()
        if self.schooldb_file.is_file():
            self.cities = json.loads(self.schooldb_file.read_text(encoding='utf-8'), encoding='utf-8')
        else:
            self.cities = self.rebuild()

    def build(self) -> dict:
        from time import sleep
        url = "https://sluzby.bakalari.cz/api/v1/municipality/"
        parser = ET.XMLParser(recover=True)
        schooldb = {}
        rc = requests.get(url, stream=True)
        rc.raw.decode_content = True
        cities_xml = ET.parse(rc.raw, parser=parser)
        for municInfo in cities_xml.iter("municipalityInfo"):
            city_name = municInfo.find("name").text
            if city_name:
                schooldb[city_name] = []
                rs = requests.get(url + requests.utils.quote(city_name), stream=True)
                rs.raw.decode_content = True
                school_xml = ET.parse(rs.raw, parser=parser)
                for school in school_xml.iter("schoolInfo"):
                    school_name = school.find("name").text
                    if school_name:
                        domain = re.sub("http(s)?://(www.)?", "", school.find("schoolUrl").text)
                        domain = re.sub("((/)?login.aspx(/)?)?", "", domain).rstrip("/")
                        schooldb[city_name].append({school_name: domain})
                sleep(0.05)
        schooldb_file.write_text(json.dumps(schooldb, indent=4, sort_keys=True), encoding='utf-8')
        return schooldb


def request(url: str, token: str, *args) -> dict:
    '''
    Make a GET request to school URL.\n
    Module names are available at `https://github.com/bakalari-api/bakalari-api/tree/master/moduly`.\n
    Returns a response `lxml.etree._Element`
    '''
    if args is None or len(args) > 2:
        raise ValueError("Bad arguments")
        return None
    params = {"hx": token, "pm": args[0]}
    if len(args) > 1:
        params.update({"pmd": args[1]})
    r = requests.get(url=url, params=params, verify=False, stream=True)
    r.raw.decode_content = True
    response = xmltodict.parse(r.raw)
    try:
        if not response["results"]["result"] == "01":
            raise LookupError("Received response is invalid.")
            return None
    except KeyError:
        raise LookupError("Wrong request")
        return None
    return response["results"]


class Client(object):
    def __init__(self, username: str, password=None, domain=None, auth_file=None):
        super().__init__()
        if auth_file:
            if not password and not domain:
                if auth_file.is_file():
                    auth_dict = json.loads(auth_file.read_text(encoding='utf-8'), encoding='utf-8')
                    isFound = False
                    for user in auth_dict:
                        if user["Username"] == username:
                            self.url = user["URL"]
                            self.token = self.__token(user["PermanentToken"])
                            isFound = True
                    if not isFound:
                        raise BakalibError("Auth file was specified without password and domain, but it didn't contain the user")
                else:
                    raise BakalibError("Auth file was specified but not found")
            else:
                self.url = "https://{}/login.aspx".format(domain)
                permtoken = self.__permanent_token(username, password)
                if self.__is_token_valid(self.__token(permtoken)):
                    auth_dict = [{"Username": username, "URL": self.url, "PermanentToken": permtoken}]
                    auth_file.write_text(json.dumps(auth_dict, indent=4), encoding='utf-8')
                    self.token = self.__token(permtoken)
                else:
                    raise BakalibError("Token is invalid. That often means the password is wrong")
        elif password and domain:
            self.url = "https://{}/login.aspx".format(domain)
            permtoken = self.__permanent_token(username, password)
            if self.__is_token_valid(self.__token(permtoken)):
                self.token = self.__token(permtoken)
            else:
                raise BakalibError("Token is invalid. That often means the password is wrong")
        else:
            raise BakalibError("Incorrect arguments")
            raise SystemExit("Exiting due to errors")

        self.basic_info = self.__basic_info()

    def __basic_info(self):
        class Result(NamedTuple):
            version: str
            name: str
            type: str
            type_name: str
            school_name: str
            school_type: str
            class_: str
            year: str
            modules: str
            newmarkdays: str
        temp_list = []

        response = request(self.url, self.token, "login")

        for element in response:
            if not element == "result":
                if element == "params":
                    temp_list.append(response.get(element).get("newmarkdays"))
                else:
                    temp_list.append(response.get(element))
        return Result(*temp_list)

    def __permanent_token(self, user: str, password: str) -> str:
        '''
        Generates a permanent access token with securely hashed password.\n
        Returns a `str` containing the token.
        '''
        params = {"gethx": user}
        r = requests.get(url=self.url, params=params, verify=False, stream=True)
        r.raw.decode_content = True
        xml = ET.parse(r.raw)
        for result in xml.iter("results"):
            if result.find("res").text == "02":
                return "wrong username"
            salt = result.find("salt").text
            ikod = result.find("ikod").text
            typ = result.find("typ").text
        salted_password = (salt + ikod + typ + password).encode("utf-8")
        hashed_password = base64.b64encode(hashlib.sha512(salted_password).digest())
        permtoken = "*login*" + user + "*pwd*" + hashed_password.decode("utf8") + "*sgn*ANDR"
        return permtoken

    def __token(self, permtoken: str) -> str:
        today = datetime.date.today()
        datecode = "{:04}{:02}{:02}".format(today.year, today.month, today.day)
        hash = hashlib.sha512((permtoken + datecode).encode("utf-8")).digest()
        token = base64.urlsafe_b64encode(hash).decode("utf-8")
        return token

    def __is_token_valid(self, token: str) -> bool:
        if not request(self.url, token, "login"):
            return False
        return True

    def add_modules(self, *modules):
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
    def __init__(self, url, token):
        super().__init__()
        self.url = url
        self.token = token
        self.date = datetime.date.today()

  # #region `Convenience methods - self.prev_week(), self.this_week(), self.next_week()`

    def prev_week(self):
        self.date = self.date - datetime.timedelta(7)
        return self.date_week(self.date)

    def this_week(self):
        return self.date_week()

    def next_week(self):
        self.date = self.date + datetime.timedelta(7)
        return self.date_week(self.date)
  # #endregion

    def date_week(self, date=datetime.date.today()):
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
            begintime: str
            endtime: str

        class Day(NamedTuple):
            abbr: str
            date: str
            lessons: list

        class Lesson(NamedTuple):
            idcode: str
            type_: str
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
            caption: str
            notice: str

        headers = []
        days = []


        for lesson in response["rozvrh"]["hodiny"]["hod"]:
            headers.append(Header(
                lesson["caption"],
                lesson["begintime"],
                lesson["endtime"],
            ))
        for day in response["rozvrh"]["dny"]["den"]:
            temp_list = []
            for lesson in day["hodiny"]["hod"]:
                temp_list.append(Lesson(
                    lesson.get("idcode"),
                    lesson.get("typ"),
                    lesson.get("zkrpr"),
                    lesson.get("pr"),
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
                    lesson.get("caption"),
                    lesson.get("notice"),
                ))
            days.append(Day(day["zkratka"], day["datum"], temp_list))
        return Result(headers, days)


class Grades(object):
    def __init__(self, url, token):
        super().__init__()
        self.url = url
        self.token = token

    def grades(self):
        response = request(
            self.url,
            self.token,
            "znamky"
        )
        if response["predmety"] is None:
            raise BakalibError("Grades module returned None, no grades were found.")
            return "grades_none"

        subjects = []

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
            type_: str
            description: str

        for subject in response["predmety"]["predmet"]:
            temp_list = []
            for grade in subject["znamky"]["znamka"]:
                temp_list.append(Grade(
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
                ))
            subjects.append(temp_list)
        return Result(subjects)
