# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the GreaseMonkey scripts configuration dialog.
"""

from PyQt6.QtCore import Qt, QUrl, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QListWidgetItem

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox

from .Ui_GreaseMonkeyConfigurationDialog import Ui_GreaseMonkeyConfigurationDialog


class GreaseMonkeyConfigurationDialog(QDialog, Ui_GreaseMonkeyConfigurationDialog):
    """
    Class implementing the GreaseMonkey scripts configuration dialog.
    """

    ScriptVersionRole = Qt.ItemDataRole.UserRole
    ScriptDescriptionRole = Qt.ItemDataRole.UserRole + 1
    ScriptRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the manager object
        @type GreaseMonkeyManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.iconLabel.setPixmap(EricPixmapCache.getPixmap("greaseMonkey48"))

        self.__manager = manager

        self.__loadScripts()

        self.scriptsList.removeItemRequested.connect(self.__removeItem)
        self.scriptsList.itemChanged.connect(self.__itemChanged)

    @pyqtSlot()
    def on_openDirectoryButton_clicked(self):
        """
        Private slot to open the GreaseMonkey scripts directory.
        """
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.__manager.scriptsDirectory()))

    @pyqtSlot(str)
    def on_downloadLabel_linkActivated(self, link):
        """
        Private slot to open the greasyfork.org web site.

        @param link URL
        @type str
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        if not link or "userscript.org" in link:
            # userscript.org is down, default to Greasy Fork.
            link = "https://greasyfork.org/"
        WebBrowserWindow.mainWindow().newTab(QUrl(link))
        self.close()

    @pyqtSlot(QListWidgetItem)
    def on_scriptsList_itemDoubleClicked(self, item):
        """
        Private slot to show information about the selected script.

        @param item reference to the double clicked item
        @type QListWidgetItem
        """
        from .GreaseMonkeyConfigurationScriptInfoDialog import (
            GreaseMonkeyConfigurationScriptInfoDialog,
        )

        script = self.__getScript(item)
        if script is not None:
            infoDlg = GreaseMonkeyConfigurationScriptInfoDialog(script, parent=self)
            infoDlg.exec()

    def __loadScripts(self):
        """
        Private method to load all the available scripts.
        """
        for script in self.__manager.allScripts():
            itm = QListWidgetItem(self.scriptsList)
            itm.setText(script.name())
            icon = script.icon()
            if icon.isNull:
                icon = EricPixmapCache.getIcon("greaseMonkeyScript")
            itm.setIcon(icon)
            itm.setData(
                GreaseMonkeyConfigurationDialog.ScriptVersionRole, script.version()
            )
            itm.setData(
                GreaseMonkeyConfigurationDialog.ScriptDescriptionRole,
                script.description(),
            )
            itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if script.isEnabled():
                itm.setCheckState(Qt.CheckState.Checked)
            else:
                itm.setCheckState(Qt.CheckState.Unchecked)
            itm.setData(GreaseMonkeyConfigurationDialog.ScriptRole, script)
            self.scriptsList.addItem(itm)

        self.scriptsList.sortItems()

        itemMoved = True
        while itemMoved:
            itemMoved = False
            for row in range(self.scriptsList.count()):
                topItem = self.scriptsList.item(row)
                bottomItem = self.scriptsList.item(row + 1)
                if topItem is None or bottomItem is None:
                    continue

                if (
                    topItem.checkState() == Qt.CheckState.Unchecked
                    and bottomItem.checkState == Qt.CheckState.Checked
                ):
                    itm = self.scriptsList.takeItem(row + 1)
                    self.scriptsList.insertItem(row, itm)
                    itemMoved = True

    def __getScript(self, itm):
        """
        Private method to get the script for the given item.

        @param itm item to get script for
        @type QListWidgetItem
        @return reference to the script object
        @rtype GreaseMonkeyScript
        """
        if itm is None:
            return None

        script = itm.data(GreaseMonkeyConfigurationDialog.ScriptRole)
        return script

    def __removeItem(self, itm):
        """
        Private slot to remove a script item.

        @param itm item to be removed
        @type QListWidgetItem
        """
        script = self.__getScript(itm)
        if script is None:
            return

        removeIt = EricMessageBox.yesNo(
            self,
            self.tr("Remove Script"),
            self.tr("""<p>Are you sure you want to remove <b>{0}</b>?</p>""").format(
                script.name()
            ),
        )
        if removeIt and self.__manager.removeScript(script):
            self.scriptsList.takeItem(self.scriptsList.row(itm))
            del itm

    def __itemChanged(self, itm):
        """
        Private slot to handle changes of a script item.

        @param itm changed item
        @type QListWidgetItem
        """
        script = self.__getScript(itm)
        if script is None:
            return

        if itm.checkState() == Qt.CheckState.Checked:
            self.__manager.enableScript(script)
        else:
            self.__manager.disableScript(script)
