import bakalib


class Lessons:
    content = []

    def __init__(self):
        super(Lessons, self).__init__()

    def refreshjson(self):
        self.content = bakalib.request("znamky")

    def getlessonnames(self):
        if not self.content:
            self.refreshjson()
        result = []
        for predmet in self.content["results"]["predmety"]["predmet"]:
            result.append(predmet["zkratka"])
        return result


lessons = Lessons()


class Predmet(object):
    def __init__(self, zkratka):
        super(Predmet, self).__init__()
        self.zkratka = zkratka

    def getgrades(self):
        result = []
        for predmet in lessons.content["results"]["predmety"]["predmet"]:
            if self.zkratka == predmet["zkratka"]:
                for znamka in predmet["znamky"]["znamka"]:
                    if not isinstance(znamka, str):
                        tempdict = {
                            "titulek": znamka["caption"],
                            "poznamka": znamka["poznamka"],
                            "datum": znamka["udeleno"],
                            "znamka": znamka["znamka"]
                        }
                        result.append(tempdict)
        return result


if __name__ == "__main__":
    grades = {}
    lesson_list = lessons.getlessonnames()
    for i, zkr in enumerate(lesson_list):
        grades[zkr] = Predmet(zkr).getgrades()
    import json

    print(lesson_list)
    print(json.dumps(grades, indent=4))
