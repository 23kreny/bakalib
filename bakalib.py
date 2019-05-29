import base64
import datetime
import hashlib
import json

import bs4
import requests
import urllib3
import xmltodict

import commonlib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
domain = "prumyslovka.bakalari.cz:446/bakaweb"


def getcities():
    url = "https://sluzby.bakalari.cz/api/v1/municipality"
    requests.get(url)


def getschools(city):
    pass


def getdomain(school):
    pass


def generate_token_permanent(*args):
    if not args:
        user = input("Username: ")
        pwd = input("Password: ")
        if user == "" or pwd == "":
            print("Cannot be empty")
            return generate_token_permanent()
    else:
        user = args[0]
        pwd = args[1]
    if user == "" or pwd == "":
        return None
    r = requests.get("https://" + domain + "/login.aspx?gethx=" + user)
    soup = bs4.BeautifulSoup(r.content, "html.parser")
    xml = soup.encode("utf-8")
    xmldict = xmltodict.parse(xml)
    jsonxml = json.loads(json.dumps(xmldict, indent=4, sort_keys=True))
    if jsonxml["results"]["res"] == "02":
        return None
    salt = jsonxml["results"]["salt"] + jsonxml["results"]["ikod"] + jsonxml["results"]["typ"]
    hashstring = (salt + pwd).encode("utf-8")
    hashpass = base64.b64encode(hashlib.sha512(hashstring).digest())
    permtoken = "*login*" + user + "*pwd*" + hashpass.decode("utf8") + "*sgn*ANDR"
    json_auth = {"PermToken": permtoken}
    if not commonlib.conf_dir.is_dir():
        commonlib.conf_dir.mkdir()
    with open(commonlib.auth_file, "w") as f:
        json.dump(json_auth, f, indent=4, sort_keys=True)
    if not istoken_valid():
        commonlib.auth_file_path.unlink()
        return None
    return json.loads(json.dumps(json_auth, indent=4, sort_keys=True))


def generate_token():
    if not commonlib.auth_file_path.is_file():
        print("Permanent token not found, generating...")
        permtoken = generate_token_permanent()["PermToken"]
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
    url = "https://" + domain + "/login.aspx"
    params = {"hx": generate_token()}
    if args is None or len(args) > 2:
        print("not enough or too many params")
        return None
    params.update({"pm": args[0]})
    if len(args) > 1:
        params.update({"pmd": args[1]})
    r = requests.get(url=url, params=params, verify=False)
    soup = bs4.BeautifulSoup(r.content, "html.parser")
    xml = soup.encode("utf-8")
    xmldict = xmltodict.parse(xml)
    return json.loads(json.dumps(xmldict, indent=4, sort_keys=True))


if __name__ == "__main__":
    pass
