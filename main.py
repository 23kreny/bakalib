import wx
import datetime
import rozvrhappui
import rozvrh
import commonlib
import bakalib


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

def buttonLogin_handler(event, *args):
    global default_color
    user = dialog.textUser.GetLineText(0)
    pwd = dialog.textPass.GetLineText(0)
    if default_color is None:
        default_color = dialog.textUser.GetBackgroundColour()
    dialog.textUser.SetBackgroundColour(default_color)
    dialog.textPass.SetBackgroundColour(default_color)
    if bakalib.generate_token_permanent(user, pwd) is None:
        dialog.textUser.SetBackgroundColour((255, 0, 0))
        dialog.textPass.SetBackgroundColour((255, 0, 0))
        return init_login()
    dialog.Hide()
    dialog.textUser.Clear()
    dialog.textPass.Clear()
    if args:
        return updategrid()
    init_main()
    return App.MainLoop()

def closeLogin_handler(event):
    dialog.Hide()
    dialog.textUser.Clear()
    dialog.textPass.Clear()

def buttonNext_handler(event):
    date = wxdt_to_pydt(App.frameRozvrh.dateWeek.GetValue())
    date = date + datetime.timedelta(days=7)
    updategrid(date.strftime("%Y%m%d"))
    event.Skip()

def buttonPrev_handler(event):
    date = wxdt_to_pydt(App.frameRozvrh.dateWeek.GetValue())
    date = date - datetime.timedelta(days=7)
    updategrid(date.strftime("%Y%m%d"))
    event.Skip()

def RozvrhGrid_handler(event, date):
    ret = rozvrh.lessons(date)
    lessoncount = ret[1]
    table_extended = ret[6]
    item = (event.GetRow()) * lessoncount + (event.GetCol() + 1)
    message = table_extended[item-1]
    if message:
        wx.MessageBox(message, caption="Podrobnosti")
    else:
        wx.MessageBox("Není zde nic k zobrazení", caption="Podrobnosti")

def RozvrhGrid_useless_handler(event):
    App.frameRozvrh.RozvrhGrid.ClearSelection()
    event.Skip()

def buttonChangeUser_handler(event):
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

    App.frameRozvrh.buttonNext.Bind(wx.EVT_BUTTON, buttonNext_handler)
    App.frameRozvrh.buttonPrev.Bind(wx.EVT_BUTTON, buttonPrev_handler)
    App.frameRozvrh.buttonChangeUser.Bind(wx.EVT_BUTTON, buttonChangeUser_handler)
    App.frameRozvrh.RozvrhGrid.Bind(wx.grid.EVT_GRID_CMD_CELL_LEFT_CLICK, lambda event: RozvrhGrid_handler(event, date))
    App.frameRozvrh.RozvrhGrid.Bind(wx.grid.EVT_GRID_RANGE_SELECT, RozvrhGrid_useless_handler)

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
    App.MainLoop()

def init_login(*args):
    dialog.textUser.SetHint('Uživatelské jméno: ')
    dialog.textPass.SetHint('Heslo: ')
    if args:
        dialog.buttonLogin.Bind(wx.EVT_BUTTON, lambda event: buttonLogin_handler(event, args))
    else:
        dialog.buttonLogin.Bind(wx.EVT_BUTTON, buttonLogin_handler)
    dialog.Bind(wx.EVT_CLOSE, closeLogin_handler)
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
