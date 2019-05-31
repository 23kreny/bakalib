import datetime

import bakalib

defaultdate = datetime.date.today().strftime("%Y%m%d")


def pocethodin(date=defaultdate):
    result = ""
    content = bakalib.request("rozvrh", date)
    for dny in content["results"]["rozvrh"]["dny"]["den"]:
        for hodiny in dny["hodiny"]["hod"]:
            if "idcode" and "caption" in hodiny.keys():
                if hodiny["idcode"].startswith(date):
                    result = hodiny["caption"]
    return result


def endtime(lastlesson, date=defaultdate):
    result = ""
    content = bakalib.request("rozvrh", date)
    for times in content["results"]["rozvrh"]["hodiny"]["hod"]:
        if times["caption"] == lastlesson:
            result = times["endtime"]
    return result


def lessons(date=defaultdate):
    content = bakalib.request("rozvrh", date)
    weekmonday = datetime.datetime.strptime(
        content["results"]["rozvrh"]["dny"]["den"][0]["datum"], "%Y%m%d"
    )
    lessoncount = int(content["results"]["rozvrh"]["hodiny"]["pocet"])
    columns_lessoncaptions = []
    rows_days = []
    table = []
    table_chng_col = []
    table_extended = []
    nazev_cyklu = content["results"]["rozvrh"]["nazevcyklu"]

    for hod in content["results"]["rozvrh"]["hodiny"]["hod"]:
        columns_lessoncaptions.append(
            "%s\n%s - %s" % (hod["caption"], hod["begintime"], hod["endtime"])
        )
    for den in content["results"]["rozvrh"]["dny"]["den"]:
        datum = datetime.datetime.strptime(den["datum"], "%Y%m%d")
        rows_days.append(
            "%s\n%s"
            % (den["zkratka"], datum.strftime("%d. %m.").lstrip("0").replace(" 0", ""))
        )
        for hod in den["hodiny"]["hod"]:
            tempstr = ""
            if "zkrpr" in hod:
                tempstr = tempstr + ("%s" % (hod["zkrpr"]))
            if "zkruc" in hod:
                tempstr = tempstr + ("\n%s" % (hod["zkruc"]))
            if "zkrmist" in hod:
                if hod["zkrmist"] is not None:
                    tempstr = tempstr + ("\n%s" % (hod["zkrmist"]))
            table.append(tempstr)
            if "chng" in hod and hod["chng"] is not None:
                table_chng_col.append(
                    (255, 0, 0)
                )
            else:
                table_chng_col.append(None)
        for hod in den["hodiny"]["hod"]:
            tempstr = ""
            if "pr" in hod:
                tempstr = tempstr + ("%s" % (hod["pr"]))
            if "uc" in hod:
                tempstr = tempstr + ("\n%s" % (hod["uc"]))
            if "tema" in hod:
                if hod["tema"] is not None:
                    tempstr = tempstr + ("\n%s" % (hod["tema"]))
            if "chng" in hod:
                if hod["chng"] is not None:
                    tempstr = tempstr + ("\n\n%s" % (hod["chng"]))
            table_extended.append(tempstr)
    return (
        weekmonday,
        lessoncount,
        columns_lessoncaptions,
        rows_days,
        table,
        table_chng_col,
        table_extended,
        nazev_cyklu,
    )


if __name__ == "__main__":
    pass
