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


def button_login_handler(event, *args):
    global default_color
    user = dialog.textUser.GetLineText(0)
    pwd = dialog.textPass.GetLineText(0)
    domain = dialog.textUrl.GetLineText(0)
    firstrun = True
    if commonlib.auth_file_path.is_file():
        firstrun = False
    if default_color is None:
        default_color = dialog.textUser.GetBackgroundColour()
    dialog.textUser.SetBackgroundColour(default_color)
    dialog.textPass.SetBackgroundColour(default_color)
    dialog.cityComboBox.SetBackgroundColour(default_color)
    dialog.schoolComboBox.SetBackgroundColour(default_color)
    token_resp = bakalib.generate_token_permanent(domain, user, pwd)
    if token_resp == "wrong username":
        dialog.textUser.SetBackgroundColour((255, 0, 0))
        return init_login(args)
    if token_resp == "wrong password":
        dialog.textPass.SetBackgroundColour((255, 0, 0))
        return init_login(args)
    if token_resp == "wrong username and password":
        dialog.textUser.SetBackgroundColour((255, 0, 0))
        dialog.textPass.SetBackgroundColour((255, 0, 0))
        return init_login(args)
    if token_resp == "wrong domain":
        if not dialog.schoolComboBox.GetValue():
            dialog.schoolComboBox.SetBackgroundColour((255, 0, 0))
        if not dialog.cityComboBox.GetValue():
            dialog.cityComboBox.SetBackgroundColour((255, 0, 0))
        return init_login(args)
    dialog.Hide()
    dialog.textUser.Clear()
    dialog.textPass.Clear()
    if not firstrun:
        return updategrid()
    init_main()
    App.MainLoop()
    event.Skip()


def combobox_city_handler(event, city):
    dialog.schoolComboBox.Clear()
    dialog.textUrl.Clear()
    schools = bakalib.getschools(city)
    for school in schools:
        dialog.schoolComboBox.Append(school["name"])
    dialog.schoolComboBox.Bind(
        wx.EVT_COMBOBOX, lambda event: combobox_school_handler(event, schools, dialog.schoolComboBox.GetValue())
    )
    event.Skip()


def combobox_school_handler(event, school, schoolname):
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


def RozvrhGrid_handler(event, date):
    ret = rozvrh.lessons(date)
    lessoncount = ret[1]
    table_extended = ret[6]
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
    init_login("arg")
    event.Skip()


def updategrid(date=rozvrh.defaultdate):
    default_color = App.frameRozvrh.RozvrhGrid.GetCellBackgroundColour(0, 0)
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
    nazevcyklu = ret[7]

    wxdate = wx.DateTime.FromDMY(weekmonday.day, weekmonday.month - 1, weekmonday.year)
    App.frameRozvrh.dateWeek.SetValue(wxdate)
    App.frameRozvrh.RozvrhGrid.Bind(wx.grid.EVT_GRID_CMD_CELL_LEFT_CLICK, lambda event: RozvrhGrid_handler(event, date))
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
    table_chng_col = ret[5]
    nazevcyklu = ret[7]

    App.frameRozvrh.SetMinSize((640, 480))

    App.frameRozvrh.buttonNext.Bind(wx.EVT_BUTTON, button_next_handler)
    App.frameRozvrh.buttonPrev.Bind(wx.EVT_BUTTON, button_prev_handler)
    App.frameRozvrh.buttonChangeUser.Bind(wx.EVT_BUTTON, button_changeuser_handler)
    App.frameRozvrh.RozvrhGrid.Bind(wx.grid.EVT_GRID_CMD_CELL_LEFT_CLICK, lambda event: RozvrhGrid_handler(event, date))
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


def init_login(*args):
    dialog.SetSize((400, 350))
    dialog.textUser.SetHint('Uživatelské jméno: ')
    dialog.textPass.SetHint('Heslo: ')
    dialog.cityComboBox.SetHint("Město: ")
    dialog.schoolComboBox.SetHint("Škola: ")
    cities = bakalib.getcities()
    dialog.cityComboBox.SetItems(cities)
    dialog.cityComboBox.Bind(
        wx.EVT_COMBOBOX, lambda event: combobox_city_handler(event, dialog.cityComboBox.GetValue())
    )
    if args:
        dialog.buttonLogin.Bind(wx.EVT_BUTTON, lambda event: button_login_handler(event, args))
    else:
        dialog.buttonLogin.Bind(wx.EVT_BUTTON, button_login_handler)
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
