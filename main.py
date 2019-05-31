import sys

import wx

import bakalib
import commonlib
import main_ui

default_color = None
App = main_ui.appMain()
dialog = main_ui.dialogLogin(None, wx.ID_ANY, "")


def button_login_handler(event):
    global default_color
    user = dialog.textUser
    pwd = dialog.textPass
    domain = dialog.textUrl
    if default_color is None:
        default_color = dialog.textUser.GetBackgroundColour()
    dialog.textUser.SetBackgroundColour(default_color)
    dialog.textPass.SetBackgroundColour(default_color)
    dialog.textUrl.SetBackgroundColour(default_color)
    for count, arg in enumerate((user, pwd, domain)):
        if not arg.GetLineText(0):
            arg.SetBackgroundColour((255, 0, 0))
            if count == 2:
                return dialog.Refresh()
    token_resp = bakalib.generate_token_permanent(domain.GetLineText(0), user.GetLineText(0), pwd.GetLineText(0))
    if token_resp.startswith("wrong"):
        if token_resp == "wrong username":
            dialog.textUser.SetBackgroundColour((255, 0, 0))
        if token_resp == "wrong password":
            dialog.textPass.SetBackgroundColour((255, 0, 0))
        if token_resp == "wrong domain":
            dialog.textUrl.SetBackgroundColour((255, 0, 0))
        return dialog.Refresh()
    dialog.Hide()
    credtitle = "Zpracování údajů"
    credmessage = "Vaše údaje jsou ukládány ve formátu: \n\n%s\n\n" \
                  "Heslo je zde bezpečně zašifrováno.\nSoubor naleznete v %s" \
                  % (token_resp, commonlib.auth_file.rstrip("auth.json"))
    wx.MessageBox(credmessage, credtitle)
    init_main()
    event.Skip()


def combobox_city_handler(event, city):
    dialog.cityComboBox.SetBackgroundColour(default_color)
    dialog.schoolComboBox.Clear()
    dialog.schoolComboBox.Enable()
    dialog.textUrl.Clear()
    schools = bakalib.getschools(city)
    for school in schools:
        dialog.schoolComboBox.Append(school["name"])
    dialog.schoolComboBox.Bind(
        wx.EVT_COMBOBOX, lambda event: combobox_school_handler(event, schools, dialog.schoolComboBox.GetValue())
    )
    event.Skip()


def combobox_school_handler(event, school, schoolname):
    dialog.schoolComboBox.SetBackgroundColour(default_color)
    try:
        dialog.textUrl.SetValue(bakalib.getdomain(school, schoolname))
    except TypeError:
        pass
    event.Skip()


def login_close_handler(event):
    dialog.Hide()
    event.Skip()


def main_close_handler(event):
    event.Skip()
    sys.exit()


def rozvrh_handler(event):
    App.frameMain.Hide()
    import rozvrh.rozvrh_main
    rozvrh.rozvrh_main.init_main()
    event.Skip()


def znamky_handler(event):
    '''import znamky.znamky_main
    znamky.znamky_main.init_main()
    event.Skip()'''
    wx.MessageBox("Něco tu chybí", "WIP")
    event.Skip()


def absence_handler(event):
    '''import absence.absence_main
        absence.absence_main.init_main()
        event.Skip()'''
    wx.MessageBox("Něco tu chybí", "WIP")
    event.Skip()


def changeuser_handler(event):
    dialog.textUser.SetBackgroundColour(default_color)
    dialog.textPass.SetBackgroundColour(default_color)
    dialog.cityComboBox.SetBackgroundColour(default_color)
    dialog.schoolComboBox.SetBackgroundColour(default_color)
    dialog.textUser.Clear()
    dialog.textPass.Clear()
    dialog.cityComboBox.Clear()
    dialog.schoolComboBox.Clear()
    dialog.textUrl.Clear()
    init_login()
    event.Skip()


def init_login():
    dialog.SetSize((300, 365))
    dialog.schoolComboBox.Disable()
    dialog.cityComboBox.SetItems(bakalib.getcities())
    dialog.buttonLogin.Bind(wx.EVT_BUTTON, button_login_handler)
    dialog.cityComboBox.Bind(
        wx.EVT_COMBOBOX, lambda event: combobox_city_handler(event, dialog.cityComboBox.GetValue())
    )
    dialog.Bind(wx.EVT_CLOSE, login_close_handler)
    dialog.Update()
    dialog.Show()


def init_main():
    size = (235, 295)
    App.frameMain.SetMinClientSize(size)
    App.frameMain.SetMaxClientSize(size)
    App.frameMain.buttonRozvrh.Bind(wx.EVT_LEFT_DOWN, rozvrh_handler)
    App.frameMain.buttonZnamky.Bind(wx.EVT_LEFT_DOWN, znamky_handler)
    App.frameMain.buttonAbsence.Bind(wx.EVT_LEFT_DOWN, absence_handler)
    App.frameMain.buttonChangeuser.Bind(wx.EVT_BUTTON, changeuser_handler)
    App.frameMain.Bind(wx.EVT_CLOSE, main_close_handler)
    App.MainLoop()


if __name__ == "__main__":
    if commonlib.auth_file_path.is_file():
        if bakalib.istoken_valid():
            init_main()
        else:
            init_login()
            dialog.ShowModal()
    else:
        init_login()
        dialog.ShowModal()
