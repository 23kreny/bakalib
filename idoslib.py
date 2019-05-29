import requests

url = "https://main.crws.cz/API.svc/VlakBusMHDVSECZ/connections"


def getdata(start, dest, date, time):
    params = {
        "dateTime": date + " " + time,
        "remMask": "16867328",
        "isDep": "true",
        "userDesc": "cz.mafra.jizdnirady;Android|246|28|Xiaomi Redmi 3S|c5d7b3dd90b881d1^7c0fa8107d43|6d8fc952-e332-6081-0000-0165e3e7a121|en|US|252|720|1280",
        "lang": "1",
        "userId": "03E349E0-15D5-401B-BE99-BEB580162018",
        "maxCount": "6",
        "ttDetails": "289356276064845857",
        "ttInfoDetails": "256469",
    }
    payload = {
        "from": [{"name": start, "listId": 1}],
        "to": [{"name": dest, "listId": 1}],
        "priceRequestInfo": {"priceDetails": 416},
    }

    r = requests.post(url, params=params, json=payload)
    return r.json()


def parsejson(json_file):
    # WIP
    return json_file


if __name__ == "__main__":
    pass
