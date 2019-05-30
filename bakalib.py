import base64
import datetime
import hashlib
import json

import bs4
import requests
import urllib3
import xmltodict
from lxml import etree

import commonlib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def getcities():
    url = "https://sluzby.bakalari.cz/api/v1/municipality"
    citylist = []
    r = requests.get(url, stream=True)
    r.raw.decode_content = True
    content = etree.iterparse(r.raw)
    for i, elem in content:
        if elem.tag == "name":
            if elem.text is not None:
                citylist.append(elem.text)
    return citylist


def getschools(city):
    url = "https://sluzby.bakalari.cz/api/v1/municipality/" + requests.utils.quote(city)
    schoollist = []
    r = requests.get(url)
    soup = bs4.BeautifulSoup(r.content, "html.parser")
    xml = soup.encode("utf-8")
    xmldict = xmltodict.parse(xml)
    jsonxml = json.loads(json.dumps(xmldict, indent=4, sort_keys=True))
    for school in jsonxml["municipality"]["schools"]["schoolinfo"]:
        if isinstance(school, str):
            schoollist.append(jsonxml["municipality"]["schools"]["schoolinfo"])
            break
        schoollist.append(school)
    return schoollist


def getdomain(school, schoolname):
    for school in school:
        if school["name"] == schoolname:
            domain = school["schoolurl"]
            domain = domain.replace("https://", "").replace("http://", "").rstrip("/login.aspx").rstrip("/")
            return domain


def generate_token_permanent(domain, *args):
    if not args:
        return None
    else:
        try:
            user = args[0]
            pwd = args[1]
        except IndexError:
            return None
    if not domain:
        return "wrong domain"
    if not user or not pwd:
        return "wrong username"
    params = {"gethx": user}
    url = "https://" + domain + "/login.aspx"
    r = requests.get(url=url, params=params)
    soup = bs4.BeautifulSoup(r.content, "html.parser")
    xml = soup.encode("utf-8")
    xmldict = xmltodict.parse(xml)
    jsonxml = json.loads(json.dumps(xmldict, indent=4, sort_keys=True))
    if jsonxml["results"]["res"] == "02":
        return "wrong username"
    salt = jsonxml["results"]["salt"] + jsonxml["results"]["ikod"] + jsonxml["results"]["typ"]
    hashstring = (salt + pwd).encode("utf-8")
    hashpass = base64.b64encode(hashlib.sha512(hashstring).digest())
    permtoken = "*login*" + user + "*pwd*" + hashpass.decode("utf8") + "*sgn*ANDR"
    json_auth = {
        "Domain": domain,
        "PermToken": permtoken
    }
    if not commonlib.conf_dir.is_dir():
        commonlib.conf_dir.mkdir()
    with open(commonlib.auth_file, "w") as f:
        json.dump(json_auth, f, indent=4, sort_keys=True)
    if not istoken_valid():
        commonlib.auth_file_path.unlink()
        return "wrong password"
    return permtoken


def generate_token():
    if not commonlib.auth_file_path.is_file():
        return None
    else:
        with open(commonlib.auth_file, "r") as f:
            permtoken = json.load(f)["PermToken"]
    now = datetime.date.today().strftime("%Y%m%d")
    h = hashlib.sha512((permtoken + now).encode("utf8")).digest()
    token = base64.urlsafe_b64encode(h).decode("utf8")
    return token


def istoken_valid():
    content = request("rozvrh")
    if content["results"]["result"] == "-1":
        return False
    return True


def request(*args):
    with open(commonlib.auth_file, "r") as f:
        domain = json.load(f)["Domain"]
    params = {"hx": generate_token()}
    if args is None or len(args) > 2:
        print("not enough or too many params")
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


if __name__ == "__main__":
    pass
