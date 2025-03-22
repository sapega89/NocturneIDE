# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit the commit message of a revision.
"""

from PyQt6.QtCore import QCoreApplication, pyqtSlot
from PyQt6.QtWidgets import QDialog
from Ui_HgHisteditCommitEditor import Ui_HgHisteditCommitEditor

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricMessageBox


class HgHisteditCommitEditor(QDialog, Ui_HgHisteditCommitEditor):
    """
    Class implementing a dialog to edit the commit message of a revision.
    """

    def __init__(self, fileName, parent=None):
        """
        Constructor

        @param fileName name of the file containing the commit message
            to be edited
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__fileName = fileName
        self.__readFile()

        self.recentCommitMessages = EricUtilities.toList(
            Preferences.getSettings().value("Mercurial/Commits")
        )
        self.recentComboBox.clear()
        self.recentComboBox.addItem("")
        self.recentComboBox.addItems(self.recentCommitMessages)

    def __readFile(self):
        """
        Private method to read the file containing the commit message and
        populate the dialog.
        """
        try:
            with open(self.__fileName, "r") as f:
                txt = f.read()
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("Edit Commit Message"),
                self.tr(
                    """<p>The file <b>{0}</b> could not be read.</p>"""
                    """<p>Reason: {1}</p>"""
                ).format(self.__fileName, str(err)),
            )
            self.on_buttonBox_rejected()
            return

        msgLines = []
        infoLines = []
        for line in txt.splitlines():
            if line.startswith("#"):
                infoLines.append(line[1:].lstrip())
            elif line.startswith("HG:"):
                infoLines.append(line[3:].lstrip())
            else:
                msgLines.append(line)

        # remove empty lines at end of message
        for row in range(len(msgLines) - 1, -1, -1):
            if msgLines[row] == "":
                del msgLines[row]
            else:
                break

        self.messageEdit.setPlainText("\n".join(msgLines))
        self.infoEdit.setPlainText("\n".join(infoLines))

    @pyqtSlot()
    def on_buttonBox_accepted(self):
        """
        Private slot called by the buttonBox accepted signal.
        """
        msg = self.messageEdit.toPlainText()
        try:
            with open(self.__fileName, "w") as f:
                f.write(msg)
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("Edit Commit Message"),
                self.tr(
                    """<p>The file <b>{0}</b> could not be read.</p>"""
                    """<p>Reason: {1}</p>"""
                ).format(self.__fileName, str(err)),
            )
            self.on_buttonBox_rejected()
            return

        self.close()
        QCoreApplication.exit(0)

    @pyqtSlot()
    def on_buttonBox_rejected(self):
        """
        Private slot called by the buttonBox rejected signal.
        """
        self.close()
        QCoreApplication.exit(1)

    @pyqtSlot(int)
    def on_recentComboBox_activated(self, index):
        """
        Private slot to select a commit message from recent ones.

        @param index index of the selected entry
        @type int
        """
        txt = self.recentComboBox.itemText(index)
        if txt:
            self.messageEdit.setPlainText(txt)
