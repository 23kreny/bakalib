import sys

import wx

import bakalib
import commonlib
import icons
import main_ui
from rozvrh import rozvrh_main, rozvrh_ui
from znamky import znamky_main, znamky_ui


# from absence import absence_main, absence_ui


class MainApp(object):
    app = main_ui.appMain()
    icon_main = wx.Icon(icons.bakalaris.GetIcon())
    icon_rozvrh = wx.Icon(icons.rozvrh.GetIcon())
    icon_znamky = wx.Icon(icons.znamky.GetIcon())
    icon_absence = wx.Icon(icons.absence.GetIcon())

    def __init__(self, wxdialog):
        super(MainApp, self).__init__()
        self.wxdialog = wxdialog

    def main_close_handler(self, event):
        event.Skip()
        sys.exit()

    def rozvrh_handler(self, event):
        rozvrh_main.App = rozvrh_ui.appRozvrh()
        rozvrh_main.App.frameRozvrh.SetIcon(self.icon_rozvrh)
        rozvrh_main.init_main()
        event.Skip()

    def znamky_handler(self, event):
        znamky_main.App = znamky_ui.appZnamky()
        znamky_main.App.frameZnamky.SetIcon(self.icon_znamky)
        znamky_main.init_main()
        event.Skip()

    def absence_handler(self, event):
        # absence_main.App = absence_ui.appZnamky()
        # absence_main.App.frameAbsence.SetIcon(icon_absence)
        # absence_main.init_main()
        wx.MessageBox("Něco tu chybí", "WIP")
        event.Skip()

    def changeuser_handler(self, event):
        self.wxdialog.init()
        event.Skip()

    def init(self):
        wait = wx.BusyCursor()

        size = (235, 295)
        self.app.frameMain.SetMinClientSize(size)
        self.app.frameMain.SetMaxClientSize((-1, size[1]))
        self.app.frameMain.SetIcon(self.icon_main)
        self.app.frameMain.buttonRozvrh.Bind(wx.EVT_LEFT_DOWN, self.rozvrh_handler)
        self.app.frameMain.buttonZnamky.Bind(wx.EVT_LEFT_DOWN, self.znamky_handler)
        self.app.frameMain.buttonAbsence.Bind(wx.EVT_LEFT_DOWN, self.absence_handler)
        self.app.frameMain.buttonChangeuser.Bind(wx.EVT_BUTTON, self.changeuser_handler)
        self.app.frameMain.Bind(wx.EVT_CLOSE, self.main_close_handler)

        jmeno, skola = bakalib.getbasicinfo()
        App.app.frameMain.statusbar.SetStatusText("%s - %s" % (jmeno, skola))

        self.app.frameMain.Update()
        self.app.frameMain.Refresh()

        del wait
        App.app.MainLoop()


class LoginDialog:
    default_color = None
    dialog = main_ui.dialogLogin(None, wx.ID_ANY, "")

    def __init__(self):
        super(LoginDialog, self).__init__()

    def init(self):
        wait = wx.BusyCursor()

        self.dialog.SetSize((300, 365))
        self.dialog.schoolComboBox.Disable()
        if self.default_color:
            self.dialog.textUser.SetBackgroundColour(self.default_color)
            self.dialog.textPass.SetBackgroundColour(self.default_color)
            self.dialog.cityComboBox.SetBackgroundColour(self.default_color)
            self.dialog.schoolComboBox.SetBackgroundColour(self.default_color)
        self.dialog.textUser.Clear()
        self.dialog.textPass.Clear()
        self.dialog.cityComboBox.Clear()
        self.dialog.schoolComboBox.Clear()
        self.dialog.textUrl.Clear()
        self.dialog.cityComboBox.SetItems(bakalib.getcities())
        self.dialog.buttonLogin.Bind(wx.EVT_BUTTON, self.button_login_handler)
        self.dialog.textUrl.SetLabelText("Prosím vyberte školu.")
        self.dialog.cityComboBox.Bind(
            wx.EVT_COMBOBOX, lambda event: self.combobox_city_handler(event, self.dialog.cityComboBox.GetValue())
        )
        self.dialog.Bind(wx.EVT_CLOSE, self.login_close_handler)
        self.dialog.buttonLogin.Enable()
        self.dialog.Update()
        self.dialog.Show()

        del wait
        App.init()

    def button_login_handler(self, event):
        wait = wx.BusyCursor()

        user = self.dialog.textUser
        pwd = self.dialog.textPass
        domain = self.dialog.textUrl
        if self.default_color is None:
            self.default_color = self.dialog.textUser.GetBackgroundColour()
        self.dialog.textUser.SetBackgroundColour(self.default_color)
        self.dialog.textPass.SetBackgroundColour(self.default_color)
        self.dialog.textUrl.SetBackgroundColour(self.default_color)
        for count, arg in enumerate((user, pwd, domain)):
            if not arg.GetLineText(0):
                arg.SetBackgroundColour((255, 0, 0))
                if count == 2:
                    return self.dialog.Refresh()
        token_resp = bakalib.generate_token_permanent(domain.GetLineText(0), user.GetLineText(0), pwd.GetLineText(0))
        if token_resp.startswith("wrong"):
            if token_resp == "wrong username":
                self.dialog.textUser.SetBackgroundColour((255, 0, 0))
            if token_resp == "wrong password":
                self.dialog.textPass.SetBackgroundColour((255, 0, 0))
            if token_resp == "wrong domain":
                self.dialog.textUrl.SetBackgroundColour((255, 0, 0))
            return self.dialog.Refresh()
        self.dialog.Hide()
        credtitle = "Zpracování údajů"
        credmessage = "Vaše údaje jsou ukládány ve formátu: \n\n%s\n\n" \
                      "Heslo je zde bezpečně zašifrováno.\nSoubor naleznete v %s" \
                      % (token_resp, commonlib.auth_file.rstrip("auth.json"))
        wx.MessageBox(credmessage, credtitle)

        jmeno, skola = bakalib.getbasicinfo()
        App.app.frameMain.statusbar.SetStatusText("%s - %s" % (jmeno, skola))

        del wait
        self.dialog.buttonLogin.Disable()
        event.Skip()

    def combobox_city_handler(self, event, city):
        wait = wx.BusyCursor()

        self.dialog.cityComboBox.SetBackgroundColour(self.default_color)
        self.dialog.schoolComboBox.Clear()
        self.dialog.schoolComboBox.Enable()
        self.dialog.textUrl.Clear()
        schools = bakalib.getschools(city)
        for school in schools:
            self.dialog.schoolComboBox.Append(school["name"])
        self.dialog.schoolComboBox.Bind(
            wx.EVT_COMBOBOX, lambda event: self.combobox_school_handler(
                event, schools, self.dialog.schoolComboBox.GetValue()
            )
        )

        del wait
        event.Skip()

    def combobox_school_handler(self, event, school, schoolname):
        self.dialog.schoolComboBox.SetBackgroundColour(self.default_color)
        try:
            self.dialog.textUrl.SetValue(bakalib.getdomain(school, schoolname))
        except TypeError:
            pass
        event.Skip()

    def login_close_handler(self, event):
        self.dialog.Hide()
        event.Skip()


if __name__ == "__main__":
    Dialog = LoginDialog()
    App = MainApp(Dialog)
    if commonlib.auth_file_path.is_file() and bakalib.istoken_valid():
        App.init()
    else:
        Dialog.init()
        Dialog.dialog.ShowModal()
        App.init()
