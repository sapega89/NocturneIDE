# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show GreaseMonkey script information.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7.EricGui import EricPixmapCache

from ..GreaseMonkeyScript import GreaseMonkeyScriptStartPoint
from .Ui_GreaseMonkeyConfigurationScriptInfoDialog import (
    Ui_GreaseMonkeyConfigurationScriptInfoDialog,
)


class GreaseMonkeyConfigurationScriptInfoDialog(
    QDialog, Ui_GreaseMonkeyConfigurationScriptInfoDialog
):
    """
    Class implementing a dialog to show GreaseMonkey script information.
    """

    def __init__(self, script, parent=None):
        """
        Constructor

        @param script reference to the script
        @type GreaseMonkeyScript
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.iconLabel.setPixmap(EricPixmapCache.getPixmap("greaseMonkey48"))

        self.__scriptFileName = script.fileName()

        self.setWindowTitle(self.tr("Script Details of {0}").format(script.name()))

        self.nameLabel.setText(script.fullName())
        self.versionLabel.setText(script.version())
        self.urlLabel.setText(script.downloadUrl().toString())
        if script.startAt() == GreaseMonkeyScriptStartPoint.DocumentStart:
            self.startAtLabel.setText("document-start")
        else:
            self.startAtLabel.setText("document-end")
        self.descriptionBrowser.setHtml(script.description())
        self.runsAtBrowser.setHtml("<br/>".join(script.include()))
        self.doesNotRunAtBrowser.setHtml("<br/>".join(script.exclude()))

    @pyqtSlot()
    def on_showScriptSourceButton_clicked(self):
        """
        Private slot to show an editor window with the script source code.
        """
        from eric7.QScintilla.MiniEditor import MiniEditor

        editor = MiniEditor(self.__scriptFileName, "JavaScript", self)
        editor.show()
