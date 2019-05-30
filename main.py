import datetime
import sys

import wx
import wx.grid

import bakalib
import commonlib
import rozvrh
import rozvrhappui

default_color = None
App = rozvrhappui.RozvrhApp()
dialog = rozvrhappui.dialogLogin(None, wx.ID_ANY, "")


def pydt_to_wxdt(date):
    day = date.day
    month = date.month
    year = date.year
    return wx.DateTime.FromDMY(day=day, month=month - 1, year=year)


def wxdt_to_pydt(date):
    date = date.Format("%d/%m/%Y")
    return datetime.datetime.strptime(date, "%d/%m/%Y")


def mainwindow_close_handler(event):
    event.Skip()
    sys.exit()


def login_close_handler(event):
    dialog.Hide()
    dialog.textUser.Clear()
    dialog.textPass.Clear()
    event.Skip()


def button_login_handler(event):
    global default_color
    user = dialog.textUser
    pwd = dialog.textPass
    domain = dialog.textUrl
    firstrun = True
    if commonlib.auth_file_path.is_file():
        firstrun = False
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
    dialog.textUser.Clear()
    dialog.textPass.Clear()
    credtitle = "Zpracování údajů"
    credmessage = "Vaše údaje jsou ukládány ve formátu: \n\n%s\n\n" \
                  "Heslo je zde bezpečně zašifrováno.\nSoubor naleznete v %s" \
                  % (token_resp, commonlib.auth_file.rstrip("auth.json"))
    if not firstrun:
        return updategrid()
    wx.MessageBox(credmessage, credtitle)
    init_main()
    App.MainLoop()
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


def button_next_handler(event):
    date = wxdt_to_pydt(App.frameRozvrh.dateWeek.GetValue())
    date = date + datetime.timedelta(days=7)
    updategrid(date.strftime("%Y%m%d"))
    event.Skip()


def button_prev_handler(event):
    date = wxdt_to_pydt(App.frameRozvrh.dateWeek.GetValue())
    date = date - datetime.timedelta(days=7)
    updategrid(date.strftime("%Y%m%d"))
    event.Skip()


def RozvrhGrid_handler(event, lessoncount, table_extended):
    item = (event.GetRow()) * lessoncount + (event.GetCol() + 1)
    message = table_extended[item - 1]
    if message:
        wx.MessageBox(message, caption="Podrobnosti")
    else:
        wx.MessageBox("Není zde nic k zobrazení", caption="Podrobnosti")


def RozvrhGrid_useless_handler(event):
    App.frameRozvrh.RozvrhGrid.ClearSelection()
    event.Skip()


def button_changeuser_handler(event):
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


def updategrid(date=rozvrh.defaultdate):
    App.frameRozvrh.RozvrhGrid.ClearGrid()
    for row in range(App.frameRozvrh.RozvrhGrid.GetNumberRows()):
        for col in range(App.frameRozvrh.RozvrhGrid.GetNumberCols()):
            App.frameRozvrh.RozvrhGrid.SetCellBackgroundColour(row, col, default_color)

    ret = rozvrh.lessons(date)
    weekmonday = ret[0]
    lessoncount = ret[1]
    columns_lessoncaptions = ret[2]
    rows_days = ret[3]
    table = ret[4]
    table_chng_col = ret[5]
    table_extended = ret[6]
    nazevcyklu = ret[7]

    wxdate = wx.DateTime.FromDMY(weekmonday.day, weekmonday.month - 1, weekmonday.year)
    App.frameRozvrh.dateWeek.SetValue(wxdate)
    App.frameRozvrh.RozvrhGrid.Bind(
        wx.grid.EVT_GRID_CMD_CELL_LEFT_CLICK, lambda event: RozvrhGrid_handler(event, lessoncount, table_extended)
    )
    for col in range(len(columns_lessoncaptions)):
        App.frameRozvrh.RozvrhGrid.SetColLabelValue(col, columns_lessoncaptions[col])
    for row in range(len(rows_days)):
        App.frameRozvrh.RozvrhGrid.SetRowLabelValue(row, rows_days[row])
        for col in range(lessoncount):
            App.frameRozvrh.RozvrhGrid.SetCellValue(row, col, table[0])
            App.frameRozvrh.RozvrhGrid.SetCellBackgroundColour(row, col, table_chng_col[0])
            table.remove(table[0])
            table_chng_col.remove(table_chng_col[0])

    App.frameRozvrh.statusbar.SetStatusText(nazevcyklu.capitalize())
    App.frameRozvrh.RozvrhGrid.AutoSize()
    App.frameRozvrh.RozvrhGrid.Update()
    App.frameRozvrh.Layout()


def init_main(date=rozvrh.defaultdate):
    ret = rozvrh.lessons(date)
    weekmonday = ret[0]
    lessoncount = ret[1]
    columns_lessoncaptions = ret[2]
    rows_days = ret[3]
    table = ret[4]
    table_extended = ret[6]
    table_chng_col = ret[5]
    nazevcyklu = ret[7]

    App.frameRozvrh.SetMinSize((640, 480))
    App.frameRozvrh.SetMaxSize((-1, 540))

    App.frameRozvrh.buttonNext.Bind(wx.EVT_BUTTON, button_next_handler)
    App.frameRozvrh.buttonPrev.Bind(wx.EVT_BUTTON, button_prev_handler)
    App.frameRozvrh.buttonChangeUser.Bind(wx.EVT_BUTTON, button_changeuser_handler)
    App.frameRozvrh.RozvrhGrid.Bind(
        wx.grid.EVT_GRID_CMD_CELL_LEFT_CLICK, lambda event: RozvrhGrid_handler(event, lessoncount, table_extended)
    )
    App.frameRozvrh.RozvrhGrid.Bind(wx.grid.EVT_GRID_RANGE_SELECT, RozvrhGrid_useless_handler)
    App.frameRozvrh.Bind(wx.EVT_CLOSE, mainwindow_close_handler)

    wxdate = wx.DateTime.FromDMY(weekmonday.day, weekmonday.month - 1, weekmonday.year)
    App.frameRozvrh.dateWeek.SetValue(wxdate)
    App.frameRozvrh.RozvrhGrid.SetDefaultCellAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

    for col in range(len(columns_lessoncaptions)):
        App.frameRozvrh.RozvrhGrid.AppendCols()
        App.frameRozvrh.RozvrhGrid.SetColLabelValue(col, columns_lessoncaptions[col])
    for row in range(len(rows_days)):
        App.frameRozvrh.RozvrhGrid.AppendRows()
        App.frameRozvrh.RozvrhGrid.SetRowLabelValue(row, rows_days[row])
        for col in range(lessoncount):
            App.frameRozvrh.RozvrhGrid.SetCellValue(row, col, table[0])
            App.frameRozvrh.RozvrhGrid.SetCellHighlightPenWidth(0)
            App.frameRozvrh.RozvrhGrid.SetCellHighlightROPenWidth(0)
            App.frameRozvrh.RozvrhGrid.SetCellBackgroundColour(row, col, table_chng_col[0])
            table.remove(table[0])
            table_chng_col.remove(table_chng_col[0])

    App.frameRozvrh.statusbar.SetStatusText(nazevcyklu.capitalize())
    App.frameRozvrh.RozvrhGrid.AutoSize()
    App.frameRozvrh.RozvrhGrid.Update()
    App.frameRozvrh.Layout()
    App.MainLoop()


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
