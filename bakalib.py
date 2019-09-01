import base64
import collections
import datetime
import hashlib
import json
import pathlib
import re

import lxml.etree as ET
import requests
import urllib3
import xmltodict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

conf_dir = pathlib.Path.home().joinpath(".bakalib")
schooldb_file = conf_dir.joinpath("schooldb.json")


class Municipality:
    '''
    Provides info about all schools in all cities in Czech Republic.\n
    Navigate through it like a dictionary:\n
            municipality = Municipality()
            hodonin = municipality.db["Hodonín"]
            for school in hodonin:
                for name in school:
                    domain = school[name]
                    print("{}: {}".format(name, domain))
    Methods:\n
            `self.__init__()`: Initiates a `self.db` variable containing the database
            `self.rebuild()`: Rebuilds the database from url 'https://sluzby.bakalari.cz/api/v1/municipality'.
    '''
    def __init__(self):
        super().__init__()
        if not conf_dir.is_dir():
            conf_dir.mkdir()
        if schooldb_file.is_file():
            self.db = json.loads(schooldb_file.read_text(encoding='utf-8'), encoding='utf-8')
        else:
            self.db = self.rebuild()

    def rebuild(self) -> dict:
        '''
        Rebuilds the `schooldb.json` file from the internet.\n
        Takes several minutes. Use only when needed.\n
        Returns a `dict` of all cities and schools in it, also with school domains.
        '''
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
        util.schooldb_file_path.write_text(json.dumps(schooldb, indent=4, sort_keys=True), encoding='utf-8')
        return schooldb


def request(url: str, token: str, *args) -> dict:
    '''
    Make a GET request to school URL.\n
    Module names are available at `https://github.com/bakalari-api/bakalari-api/tree/master/moduly`.\n
    Returns a response `lxml.etree._Element`
    '''
    if args is None or len(args) > 2:
        return "bad params"
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
                        raise ValueError("Auth file was specified without password and domain, but it didn't contain the user")
                else:
                    raise FileNotFoundError("Auth file was specified but not found")
            else:
                self.url = "https://{}/login.aspx".format(domain)
                permtoken = self.__permanent_token(username, password)
                if self.__is_token_valid(self.__token(permtoken)):
                    auth_dict = [{"Username": username, "URL": self.url, "PermanentToken": permtoken}]
                    auth_file.write_text(json.dumps(auth_dict, indent=4), encoding='utf-8')
                    self.token = self.__token(permtoken)
                else:
                    raise ValueError("Token is invalid. That often means the password is wrong")
        elif password and domain:
            self.url = "https://{}/login.aspx".format(domain)
            permtoken = self.__permanent_token(username, password)
            if self.__is_token_valid(self.__token(permtoken)):
                self.token = self.__token(permtoken)
            else:
                raise ValueError("Token is invalid. That often means the password is wrong")
        else:
            raise ValueError("Incorrect arguments")
            raise SystemExit("Exiting due to errors")

        self.basic_info = self.__basic_info()

        self.timetable = Timetable(self.url, self.token)

    def __basic_info(self) -> collections.namedtuple:
        result = request(self.url, self.token, "login")
        Result = collections.namedtuple("Result", "version name type type_name school_name school_type class_ year modules newmarkdays")
        temp_list = []
        for element in result:
            if not element == "result":
                if element == "params":
                    temp_list.append(result.get(element).get("newmarkdays"))
                else:
                    temp_list.append(result.get(element))
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
        result = request(self.url, token, "login")
        if not result:
            return False
        return True


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
        Result = collections.namedtuple("Result", "header days")

        header = []
        for lesson in response["rozvrh"]["hodiny"]["hod"]:
            header.append({
                "Caption": lesson["caption"],
                "BeginTime": lesson["begintime"],
                "EndTime": lesson["endtime"],
            })

        days = []
        for day in response["rozvrh"]["dny"]["den"]:
            temp_list = []
            for lesson in day["hodiny"]["hod"]:
                temp_list.append({
                    "IdCode": lesson.get("idcode"),
                    "Type": lesson.get("typ"),
                    "LessonAbbreviation": lesson.get("zkrpr"),
                    "LessonName": lesson.get("pr"),
                    "TeacherAbbreviation": lesson.get("zkruc"),
                    "TeacherName": lesson.get("uc"),
                    "RoomAbbreviation": lesson.get("zkrmist"),
                    "RoomName": lesson.get("mist"),
                    "AbsenceAbbreviation": lesson.get("zkrabs"),
                    "Absence": lesson.get("abs"),
                    "Theme": lesson.get("tema"),
                    "GroupAbbreviation": lesson.get("zkrskup"),
                    "GroupName": lesson.get("skup"),
                    "Cycle": lesson.get("cycle"),
                    "Disengaged": lesson.get("uvol"),
                    "ChangeDescription": lesson.get("chng"),
                    "Caption": lesson.get("caption"),
                    "Notice": lesson.get("notice"),
                })
            days.append(temp_list)
        return Result(header, days)


class Grades(object):
    pass


if __name__ == "__main__":
    import paths
    user = Client(username="xKrone97645", auth_file=paths.auth_file)