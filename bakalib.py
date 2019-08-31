import base64
import datetime
import hashlib
import json
import re

import bs4
import lxml.etree as ET
import requests
import urllib3
import xmltodict

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
            `self.update()`: Downloads updated `schooldb.json` file from bitbucket repository.
            `self.rebuild()`: Rebuilds the database from url 'https://sluzby.bakalari.cz/api/v1/municipality'.
    '''
    def __init__(self):
        super().__init__()
        if util.schooldb_file_path.is_file():
            self.db = json.loads(util.schooldb_file_path.read_text(encoding='utf-8'), encoding='utf-8')
        else:
            self.db = self.update()

    def update(self) -> dict:
        '''
        Updates the `schooldb.json` file from my bitbucket repo.\n
        Calls `self.rebuild()` when updated `.json` cannot be found and the municipality `.xml` differs.
        '''
        return self.rebuild()

    def rebuild(self) -> dict:
        '''
        Rebuilds the `schooldb.json` file from the internet.\n
        Takes several minutes. Use only when needed.\n
        Gets called when `self.update()` doesn't have a new version but the municipality `.xml` differs.
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
    def __init__(self, user: str, password: str, domain: str):
        super().__init__()
        if util.token_file_path.is_file():
            self.permtoken = util.token_file_path.read_text(encoding='utf-8')
        else:
            self.permtoken = self.permanent_token(user, password, domain)

    def basic_info(self):
        content = self.request("login")["results"]
        return content["jmeno"], content["skola"]

    def request(self, *args):
        with open(util.auth_file, "r") as f:
            domain = json.load(f)["Domain"]
        params = {"hx": self.token()}
        if args is None or len(args) > 2:
            print("Bad parameters.")
            return None
        params.update({"pm": args[0]})
        if len(args) > 1:
            params.update({"pmd": args[1]})
        url = "https://" + domain + "/login.aspx"
        r = requests.get(url=url, params=params, verify=False)
        soup = bs4.BeautifulSoup(r.content, "html.parser")
        xml = soup.encode("utf-8")
        xmldict = xmltodict.parse(xml)
        return json.loads(json.dumps(xmldict, indent=4, sort_keys=True))

    def permanent_token(self, user: str, password: str, domain: str):
        params = {"gethx": user}
        url = "https://" + domain + "/login.aspx"
        r = requests.get(url=url, params=params, verify=False, stream=True)
        r.raw.decode_content = True
        xml = ET.parse(r.raw)
        for elem in xml.find("res"):
            print(elem)
        salt = jsonxml["results"]["salt"] + jsonxml["results"]["ikod"] + jsonxml["results"]["typ"]
        hashstring = (salt + self.password).encode("utf-8")
        hashpass = base64.b64encode(hashlib.sha512(hashstring).digest())
        permtoken = "*login*" + self.user + "*pwd*" + hashpass.decode("utf8") + "*sgn*ANDR"
        json_auth = {
            "Domain": domain,
            "PermanentToken": permtoken
        }
        if not util.conf_dir.is_dir():
            util.conf_dir.mkdir()
        with open(util.auth_file, "w") as f:
            json.dump(json_auth, f, indent=4, sort_keys=True)
        if not self.istoken_valid():
            util.auth_file_path.unlink()
            return "Password is incorrect."
        return json.dumps(json_auth, indent=4, sort_keys=True)


    def token(self, permtoken: str):
        if not util.auth_file_path.is_file():
            return "Auth file doesn't exist."
        else:
            with open(util.auth_file, "r") as f:
                permtoken = json.load(f)["PermToken"]
        now = datetime.date.today().strftime("%Y%m%d")
        h = hashlib.sha512((permtoken + now).encode("utf8")).digest()
        token = base64.urlsafe_b64encode(h).decode("utf8")
        return token


    def istoken_valid(self):
        content = self.request("rozvrh")
        if content["results"]["result"] == "-1":
            return False
        return True


if __name__ == '__main__':
    user = Client("xKrone97645", "placeholder", "prumyslovka.bakalari.cz:446/bakaweb")
    user.permanent_token()
