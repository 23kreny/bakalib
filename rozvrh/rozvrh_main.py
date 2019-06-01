import datetime

import wx
import wx.grid

from rozvrh import rozvrh_ui
from rozvrh import rozvrhlib


def pydt_to_wxdt(date):
    day = date.day
    month = date.month
    year = date.year
    return wx.DateTime.FromDMY(day=day, month=month - 1, year=year)


def wxdt_to_pydt(date):
    date = date.Format("%d/%m/%Y")
    return datetime.datetime.strptime(date, "%d/%m/%Y")


def main_close_handler(event):
    App.frameRozvrh.Hide()
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


def gridRozvrh_handler(event, lessoncount, table_extended):
    item = event.GetRow() * lessoncount + event.GetCol()
    message = table_extended[item]
    if message:
        wx.MessageBox(message, caption="Podrobnosti")
    else:
        wx.MessageBox("Není zde nic k zobrazení", caption="Podrobnosti")


def gridRozvrh_useless_handler(event):
    App.frameRozvrh.gridRozvrh.ClearSelection()
    event.Skip()


def updategrid(date=rozvrhlib.defaultdate):
    ret = rozvrhlib.lessons(date)
    weekmonday = ret[0]
    lessoncount = ret[1]
    columns_lessoncaptions = ret[2]
    rows_days = ret[3]
    table = ret[4]
    table_chng_col = ret[5]
    table_extended = ret[6]
    nazevcyklu = ret[7]
    App.frameRozvrh.gridRozvrh.ClearGrid()

    if lessoncount != App.frameRozvrh.gridRozvrh.GetNumberCols() != 0:
        App.frameRozvrh.gridRozvrh.DeleteCols(numCols=App.frameRozvrh.gridRozvrh.GetNumberCols())
        App.frameRozvrh.gridRozvrh.AppendCols(lessoncount)

    wxdate = wx.DateTime.FromDMY(weekmonday.day, weekmonday.month - 1, weekmonday.year)
    App.frameRozvrh.dateWeek.SetValue(wxdate)
    App.frameRozvrh.gridRozvrh.Bind(
        wx.grid.EVT_GRID_CMD_CELL_LEFT_CLICK, lambda event: gridRozvrh_handler(event, lessoncount, table_extended)
    )
    for col in range(len(columns_lessoncaptions)):
        App.frameRozvrh.gridRozvrh.SetColLabelValue(col, columns_lessoncaptions[col])
    for row in range(len(rows_days)):
        App.frameRozvrh.gridRozvrh.SetRowLabelValue(row, rows_days[row])
        for col in range(lessoncount):
            App.frameRozvrh.gridRozvrh.SetCellValue(row, col, table[0])
            App.frameRozvrh.gridRozvrh.SetCellBackgroundColour(row, col, table_chng_col[0])
            table.remove(table[0])
            table_chng_col.remove(table_chng_col[0])

    App.frameRozvrh.statusbar.SetStatusText(nazevcyklu.capitalize())
    App.frameRozvrh.gridRozvrh.Update()
    App.frameRozvrh.gridRozvrh.AutoSize()
    (w, x) = App.frameRozvrh.GetClientSize()
    App.frameRozvrh.SetMinClientSize((w, x))
    App.frameRozvrh.SetMaxClientSize((-1, x))
    App.frameRozvrh.Layout()


def init_main(date=rozvrhlib.defaultdate):
    ret = rozvrhlib.lessons(date)
    weekmonday = ret[0]
    lessoncount = ret[1]
    columns_lessoncaptions = ret[2]
    rows_days = ret[3]
    table = ret[4]
    table_extended = ret[6]
    table_chng_col = ret[5]
    nazevcyklu = ret[7]

    wxdate = wx.DateTime.FromDMY(weekmonday.day, weekmonday.month - 1, weekmonday.year)
    App.frameRozvrh.dateWeek.SetValue(wxdate)
    App.frameRozvrh.gridRozvrh.SetDefaultCellAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

    for col in range(len(columns_lessoncaptions)):
        App.frameRozvrh.gridRozvrh.AppendCols()
        App.frameRozvrh.gridRozvrh.SetColLabelValue(col, columns_lessoncaptions[col])
    for row in range(len(rows_days)):
        App.frameRozvrh.gridRozvrh.AppendRows()
        App.frameRozvrh.gridRozvrh.SetRowLabelValue(row, rows_days[row])
        for col in range(lessoncount):
            App.frameRozvrh.gridRozvrh.SetCellValue(row, col, table[0])
            App.frameRozvrh.gridRozvrh.SetCellHighlightPenWidth(0)
            App.frameRozvrh.gridRozvrh.SetCellHighlightROPenWidth(0)
            App.frameRozvrh.gridRozvrh.SetCellBackgroundColour(row, col, table_chng_col[0])
            table.remove(table[0])
            table_chng_col.remove(table_chng_col[0])
    App.frameRozvrh.buttonNext.Bind(wx.EVT_BUTTON, button_next_handler)
    App.frameRozvrh.buttonPrev.Bind(wx.EVT_BUTTON, button_prev_handler)
    App.frameRozvrh.gridRozvrh.Bind(
        wx.grid.EVT_GRID_CMD_CELL_LEFT_CLICK, lambda event: gridRozvrh_handler(event, lessoncount, table_extended)
    )
    App.frameRozvrh.gridRozvrh.Bind(wx.grid.EVT_GRID_RANGE_SELECT, gridRozvrh_useless_handler)
    App.frameRozvrh.Bind(wx.EVT_CLOSE, main_close_handler)

    App.frameRozvrh.statusbar.SetStatusText(nazevcyklu.capitalize())
    App.frameRozvrh.gridRozvrh.AutoSize()
    App.frameRozvrh.gridRozvrh.Update()
    (w, x) = App.frameRozvrh.GetClientSize()
    App.frameRozvrh.SetMinClientSize((w, x))
    App.frameRozvrh.SetMaxClientSize((-1, x))
    App.frameRozvrh.Layout()
    App.MainLoop()


if __name__ == "__main__":
    App = rozvrh_ui.appRozvrh()
    init_main()
