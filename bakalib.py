import base64
import datetime
import hashlib
import json
import re

import lxml.etree as ET
import requests
import urllib3

import util

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
        if util.schooldb_file_path.is_file():
            self.db = json.loads(util.schooldb_file_path.read_text(encoding='utf-8'), encoding='utf-8')
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


class Client(object):
    def __init__(self, username: str, password=None, domain=None):
        self.username = username
        super().__init__()
        if util.auth_file_path.is_file():
            auth_file = json.loads(util.auth_file_path.read_text(encoding='utf-8'), encoding='utf-8')
            for user in auth_file:
                if user["Username"] == username:
                    self.url = user["URL"]
                    self.token = self.token(user["PermanentToken"])
        else:
            self.url = "https://{}/login.aspx".format(domain)
            self.token = self.token(self.permanent_token(user, password))

    def permanent_token(self, user: str, password: str) -> str:
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
        if self.is_token_valid(self.token(permtoken)):
            if util.auth_file_path.is_file():
                auth_file = json.loads(util.auth_file_path.read_text(encoding='utf-8'))
                auth_file.append({"Username": user, "URL": self.url, "PermanentToken": permtoken})
            else:
                auth_file = [{"Username": user, "URL": self.url, "PermanentToken": permtoken}]
            util.auth_file_path.write_text(json.dumps(auth_file, indent=4), encoding='utf-8')
            return permtoken
        return "wrong password"

    def token(self, permtoken: str) -> str:
        today = datetime.date.today()
        datecode = "{:04}{:02}{:02}".format(today.year, today.month, today.day)
        hash = hashlib.sha512((permtoken + datecode).encode("utf-8")).digest()
        token = base64.urlsafe_b64encode(hash).decode("utf-8")
        return token

    def is_token_valid(self, token: str) -> bool:
        result = self.request(token, "login")
        if result.find("result").text == "-1":
            return False
        return True

    def request(self, token: str, *args) -> ET._Element:
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
        r = requests.get(url=self.url, params=params, verify=False, stream=True)
        r.raw.decode_content = True
        xml = ET.parse(r.raw)
        return [result for result in xml.iter("results")][0]


class Rozvrh(Client):
    def __init__(self, Client):
        self.client = Client
        self.url = self.client.url
        print(self.client.username)
        super().__init__(Client)
        self.date = datetime.date.today()
# #region `Convenience methods`
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
        response = self.request(
            self.token, "rozvrh", "{:04}{:02}{:02}"
            .format(date.year, date.month, date.day)
        )
        for element in response:
            print(element)


if __name__ == "__main__":
    
    rozvrh = Rozvrh(User)
    print(rozvrh.this_week())
