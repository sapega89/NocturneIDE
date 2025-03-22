# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing a dialog for adding GreaseMonkey scripts..
"""

import os
import shutil

from PyQt6.QtCore import QDir, pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7.EricGui import EricPixmapCache
from eric7.UI.NotificationWidget import NotificationTypes
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .Ui_GreaseMonkeyAddScriptDialog import Ui_GreaseMonkeyAddScriptDialog


class GreaseMonkeyAddScriptDialog(QDialog, Ui_GreaseMonkeyAddScriptDialog):
    """
    Class implementing a dialog for adding GreaseMonkey scripts..
    """

    def __init__(self, manager, script, parent=None):
        """
        Constructor

        @param manager reference to the GreaseMonkey manager
        @type GreaseMonkeyManager
        @param script GreaseMonkey script to be added
        @type GreaseMonkeyScript
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.iconLabel.setPixmap(EricPixmapCache.getPixmap("greaseMonkey48"))

        self.__manager = manager
        self.__script = script

        runsAt = ""
        doesNotRunAt = ""

        include = script.include()
        exclude = script.exclude()

        if include:
            runsAt = self.tr("<p>runs at:<br/><i>{0}</i></p>").format(
                "<br/>".join(include)
            )

        if exclude:
            doesNotRunAt = self.tr("<p>does not run at:<br/><i>{0}</i></p>").format(
                "<br/>".join(exclude)
            )

        scriptInfoTxt = "<p><b>{0}</b> {1}<br/>{2}</p>{3}{4}".format(
            script.name(), script.version(), script.description(), runsAt, doesNotRunAt
        )
        self.scriptInfo.setHtml(scriptInfoTxt)

        self.accepted.connect(self.__accepted)

    @pyqtSlot()
    def on_showScriptSourceButton_clicked(self):
        """
        Private slot to show an editor window with the source code.
        """
        from eric7.QScintilla.MiniEditor import MiniEditor
        from eric7.WebBrowser.Tools import WebBrowserTools

        tmpFileName = WebBrowserTools.ensureUniqueFilename(
            os.path.join(QDir.tempPath(), "tmp-userscript.js")
        )
        if shutil.copy(self.__script.fileName(), tmpFileName):
            editor = MiniEditor(tmpFileName, "JavaScript", self)
            editor.show()

    def __accepted(self):
        """
        Private slot handling the accepted signal.
        """
        if self.__manager.addScript(self.__script):
            msg = self.tr("<p><b>{0}</b> installed successfully.</p>").format(
                self.__script.name()
            )
            success = True
        else:
            msg = self.tr("<p>Cannot install script.</p>")
            success = False

        if success:
            WebBrowserWindow.showNotification(
                EricPixmapCache.getPixmap("greaseMonkey48"),
                self.tr("GreaseMonkey Script Installation"),
                msg,
            )
        else:
            WebBrowserWindow.showNotification(
                EricPixmapCache.getPixmap("greaseMonkey48"),
                self.tr("GreaseMonkey Script Installation"),
                msg,
                kind=NotificationTypes.CRITICAL,
                timeout=0,
            )
