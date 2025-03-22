# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to manage the list of ignored serial devices.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_IgnoredDevicesDialog import Ui_IgnoredDevicesDialog


class IgnoredDevicesDialog(QDialog, Ui_IgnoredDevicesDialog):
    """
    Class implementing a dialog to manage the list of ignored serial devices.
    """

    def __init__(self, deviceList, parent=None):
        """
        Constructor

        @param deviceList list of ignored serial devices given by VID and PID
        @type list of tuple of (int, int)
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.devicesEditWidget.setList(
            [
                "{0} ({1:04x}/{2:04x})".format(description, vid, pid)
                for vid, pid, description in deviceList
            ]
        )

        self.devicesEditWidget.setResetVisible(False)
        self.devicesEditWidget.setDefaultVisible(False)
        self.devicesEditWidget.setAddVisible(False)

    def getDevices(self):
        """
        Public method to get the list of ignored serial devices.

        @return list of tuples containing the VID, PID and a description
            of each ignored device
        @rtype list of tuple of (int, int, str)
        """
        deviceList = []
        textList = self.devicesEditWidget.getList()
        for entry in textList:
            description, vid_pid = entry.rsplit(None, 1)
            vid, pid = vid_pid[1:-1].split("/", 1)
            deviceList.append((int(vid, 16), int(pid, 16), description))

        return deviceList
