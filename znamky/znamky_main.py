import wx

from znamky import znamkylib, znamky_ui


def close_handler(event):
    App.frameZnamky.Hide()
    event.Skip()


def init_main():
    wait = wx.BusyCursor()

    lessons = znamkylib.Lessons()
    grades = {}
    lesson_list = lessons.getlessonnames()
    if lesson_list is None:
        return App.frameZnamky.tree_ctrl_1.AddRoot("Nemáš ještě žádné známky!")
    App.frameZnamky.SetTitle("Známky")
    root = App.frameZnamky.tree_ctrl_1.AddRoot("Známky")
    for i, zkr in enumerate(lesson_list):
        grades[zkr] = znamkylib.Predmet(zkr, lessons).getgrades()
    for predmet in grades:
        item1 = App.frameZnamky.tree_ctrl_1.AppendItem(root, predmet)
        App.frameZnamky.tree_ctrl_1.AppendItem(item1, "Počet známek: %d" % (len(grades[predmet])))
        for grade in grades[predmet]:
            if not isinstance(grade["titulek"], type(None)):
                item2str = ("%s: %s" % (grade["znamka"], grade["titulek"]))
            else:
                item2str = ("%s: %s" % (grade["znamka"], grade["poznamka"]))
            item2 = App.frameZnamky.tree_ctrl_1.AppendItem(item1, item2str)
            try:
                if grade["poznamka"] not in item2str:
                    try:
                        App.frameZnamky.tree_ctrl_1.AppendItem(item2, grade["poznamka"])
                    except TypeError:
                        pass
            except TypeError:
                pass
            App.frameZnamky.tree_ctrl_1.AppendItem(item2, grade["datum"])
    App.frameZnamky.tree_ctrl_1.Expand(root)

    del wait
    App.MainLoop()


if __name__ == "__main__":
    App = znamky_ui.appZnamky()
    init_main()
