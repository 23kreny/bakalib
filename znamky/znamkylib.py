import datetime

import bakalib


def dateformat(date):
    datein = datetime.datetime.strptime(date, "%y%m%d")
    dateout = datetime.datetime.strftime(datein, "%d.%m. %Y")
    return dateout


class Lessons:
    content = []

    def __init__(self):
        super(Lessons, self).__init__()

    def refreshjson(self):
        self.content = bakalib.request("znamky")

    def getlessonnames(self):
        if not self.content:
            self.refreshjson()
        if self.content["results"]["predmety"] is None:
            return None
        result = []
        print(self.content)
        for predmet in self.content["results"]["predmety"]["predmet"]:
            result.append(predmet["nazev"])
        return result


class Predmet(object):
    def __init__(self, nazev, predmety):
        super(Predmet, self).__init__()
        self.nazev = nazev
        self.lessons = predmety

    def getgrades(self):
        result = []
        for predmet in self.lessons.content["results"]["predmety"]["predmet"]:
            if self.nazev == predmet["nazev"]:
                for znamka in predmet["znamky"]["znamka"]:
                    if not isinstance(znamka, str):
                        tempdict = {
                            "titulek": znamka["caption"],
                            "poznamka": znamka["poznamka"],
                            "datum": dateformat(znamka["datum"]),
                            "znamka": znamka["znamka"]
                        }
                        result.append(tempdict)
                    else:
                        tempdict = {
                            "titulek": predmet["znamky"]["znamka"]["caption"],
                            "poznamka": predmet["znamky"]["znamka"]["poznamka"],
                            "datum": dateformat(predmet["znamky"]["znamka"]["datum"]),
                            "znamka": predmet["znamky"]["znamka"]["znamka"]
                        }
                        result.append(tempdict)
                        break
        return result


if __name__ == "__main__":
    lessons = Lessons()
    grades = {}
    lesson_list = lessons.getlessonnames()
    for i, zkr in enumerate(lesson_list):
        grades[zkr] = Predmet(zkr, lessons).getgrades()
    for predmet in grades:
        print(predmet)
        print(len(grades[predmet]))
        for grade in grades[predmet]:
            print(grade)
        print("*************************")
