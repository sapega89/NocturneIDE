# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to manage sessions.
"""

import datetime
import pathlib

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .Ui_SessionManagerDialog import Ui_SessionManagerDialog


class SessionManagerDialog(QDialog, Ui_SessionManagerDialog):
    """
    Class implementing a dialog to manage sessions.
    """

    SessionFileRole = Qt.ItemDataRole.UserRole
    BackupSessionRole = Qt.ItemDataRole.UserRole + 1
    ActiveSessionRole = Qt.ItemDataRole.UserRole + 2
    DefaultSessionRole = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.newButton.clicked.connect(self.__newSession)
        self.renameButton.clicked.connect(self.__renameSession)
        self.cloneButton.clicked.connect(self.__cloneSession)
        self.deleteButton.clicked.connect(self.__deleteSession)
        self.switchButton.clicked.connect(self.__switchToSession)
        self.sessionsList.currentItemChanged.connect(self.__updateButtons)

        self.__refresh()
        WebBrowserWindow.sessionManager().sessionsMetaDataChanged.connect(
            self.__refresh
        )

    @pyqtSlot()
    def __refresh(self):
        """
        Private slot to refresh the list of sessions.
        """
        self.sessionsList.clear()

        sessions = WebBrowserWindow.sessionManager().sessionMetaData(
            includeBackups=True
        )
        for session in sessions:
            if pathlib.Path(session.filePath).exists():
                itm = QTreeWidgetItem()
                itm.setText(0, session.name)
                itm.setText(
                    1,
                    datetime.datetime.fromtimestamp(
                        pathlib.Path(session.filePath).stat().st_mtime,
                        tz=datetime.timezone.utc,
                    ).isoformat(sep=" ", timespec="minutes"),
                )
                itm.setData(0, SessionManagerDialog.SessionFileRole, session.filePath)
                itm.setData(0, SessionManagerDialog.BackupSessionRole, session.isBackup)
                itm.setData(0, SessionManagerDialog.ActiveSessionRole, session.isActive)
                itm.setData(
                    0, SessionManagerDialog.DefaultSessionRole, session.isDefault
                )
                self.__updateSessionItem(itm)
                self.sessionsList.addTopLevelItem(itm)

        self.__updateButtons()

    def __updateButtons(self):
        """
        Private method to update the button state.
        """
        itm = self.sessionsList.currentItem()
        if itm:
            isBackup = itm.data(0, SessionManagerDialog.BackupSessionRole)
            isActive = itm.data(0, SessionManagerDialog.ActiveSessionRole)
            isDefault = itm.data(0, SessionManagerDialog.DefaultSessionRole)

            self.renameButton.setEnabled(not isDefault and not isBackup)
            self.cloneButton.setEnabled(not isBackup)
            self.deleteButton.setEnabled(
                not isBackup and not isDefault and not isActive
            )
            self.switchButton.setEnabled(not isActive)
            if isBackup:
                self.switchButton.setText(self.tr("Restore"))
            else:
                self.switchButton.setText(self.tr("Switch To"))
        else:
            self.renameButton.setEnabled(False)
            self.cloneButton.setEnabled(False)
            self.deleteButton.setEnabled(False)
            self.switchButton.setEnabled(False)
            self.switchButton.setText(self.tr("Switch To"))

    def __updateSessionItem(self, itm):
        """
        Private method to set various item properties.

        @param itm reference to the item to be updated
        @type QTreeWidgetItem
        """
        isBackup = itm.data(0, SessionManagerDialog.BackupSessionRole)
        isActive = itm.data(0, SessionManagerDialog.ActiveSessionRole)
        isDefault = itm.data(0, SessionManagerDialog.DefaultSessionRole)

        font = itm.font(0)

        if isBackup:
            color = self.palette().color(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText
            )
            itm.setForeground(0, color)
            itm.setForeground(1, color)

        if isActive:
            font.setBold(True)
            itm.setFont(0, font)
            itm.setFont(1, font)

        if isDefault:
            font.setItalic(True)
            itm.setFont(0, font)
            itm.setFont(1, font)

    def showEvent(self, evt):
        """
        Protected method handling the dialog being shown.

        @param evt reference to the event object
        @type QShowEvent
        """
        super().showEvent(evt)
        self.__resizeViewHeader()

    def resizeEvent(self, evt):
        """
        Protected method handling the dialog being resized.

        @param evt reference to the event object
        @type QResizeEvent
        """
        super().resizeEvent(evt)
        self.__resizeViewHeader()

    def __resizeViewHeader(self):
        """
        Private method to resize the session column of the list.
        """
        headerWidth = self.sessionsList.header().width()
        self.sessionsList.header().resizeSection(
            0, int(headerWidth - headerWidth / 2.5)
        )

    @pyqtSlot()
    def __newSession(self):
        """
        Private slot to create a new session.
        """
        WebBrowserWindow.sessionManager().newSession()

    @pyqtSlot()
    def __renameSession(self):
        """
        Private slot to rename the selected session.
        """
        itm = self.sessionsList.currentItem()
        if itm is None:
            return

        filePath = itm.data(0, SessionManagerDialog.SessionFileRole)
        if filePath:
            WebBrowserWindow.sessionManager().renameSession(filePath)

    @pyqtSlot()
    def __cloneSession(self):
        """
        Private slot to clone the selected session.
        """
        itm = self.sessionsList.currentItem()
        if itm is None:
            return

        filePath = itm.data(0, SessionManagerDialog.SessionFileRole)
        if filePath:
            WebBrowserWindow.sessionManager().cloneSession(filePath)

    @pyqtSlot()
    def __deleteSession(self):
        """
        Private slot to delete the selected session.
        """
        itm = self.sessionsList.currentItem()
        if itm is None:
            return

        filePath = itm.data(0, SessionManagerDialog.SessionFileRole)
        if filePath:
            WebBrowserWindow.sessionManager().deleteSession(filePath)

    @pyqtSlot()
    def __switchToSession(self):
        """
        Private slot to switch to the selected session.
        """
        itm = self.sessionsList.currentItem()
        if itm is None:
            return

        filePath = itm.data(0, SessionManagerDialog.SessionFileRole)
        if filePath:
            if itm.data(0, SessionManagerDialog.BackupSessionRole):
                res = WebBrowserWindow.sessionManager().replaceSession(filePath)
            else:
                res = WebBrowserWindow.sessionManager().switchToSession(filePath)

            if res:
                self.close()
