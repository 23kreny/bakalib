#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# generated by wxGlade 0.9.3 on Fri May 31 17:30:18 2019
#

import wx
import wx.adv
import wx.grid


# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade


class frameRozvrh(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: frameRozvrh.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((640, 480))
        self.statusbar = self.CreateStatusBar(1)
        self.buttonPrev = wx.Button(self, wx.ID_ANY, "<<")
        self.dateWeek = wx.adv.DatePickerCtrl(self, wx.ID_ANY, style=wx.adv.DP_DEFAULT)
        self.buttonNext = wx.Button(self, wx.ID_ANY, ">>")
        self.gridRozvrh = wx.grid.Grid(self, wx.ID_ANY, size=(1500, 1000))

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: frameRozvrh.__set_properties
        self.SetTitle("Rozvrh hodin")
        self.statusbar.SetStatusWidths([-1])

        # statusbar fields
        statusbar_fields = [u"Aktuální týden"]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)
        self.dateWeek.Enable(False)
        self.gridRozvrh.CreateGrid(0, 0)
        self.gridRozvrh.EnableEditing(0)
        self.gridRozvrh.EnableDragColSize(0)
        self.gridRozvrh.EnableDragRowSize(0)
        self.gridRozvrh.EnableDragGridSize(0)
        self.gridRozvrh.SetFocus()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: frameRozvrh.__do_layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_1 = wx.GridBagSizer(0, 0)
        sizer_1.Add(self.buttonPrev, (0, 0), (1, 1), wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)
        sizer_1.Add(self.dateWeek, (0, 1), (1, 1), wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)
        sizer_1.Add(self.buttonNext, (0, 2), (1, 1), wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)
        sizer_1.AddGrowableCol(0)
        sizer_1.AddGrowableCol(1)
        sizer_1.AddGrowableCol(2)
        sizer.Add(sizer_1, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
        sizer_2.Add(self.gridRozvrh, flag=wx.ALIGN_CENTRE)
        sizer.Add(sizer_2, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
        self.SetSizer(sizer)
        self.Layout()
        # end wxGlade


# end of class frameRozvrh

class appRozvrh(wx.App):
    def OnInit(self):
        self.frameRozvrh = frameRozvrh(None, wx.ID_ANY, "")
        self.SetTopWindow(self.frameRozvrh)
        self.frameRozvrh.Show()
        return True

# end of class appRozvrh
