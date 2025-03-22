# -*- coding: utf-8 -*-

# Copyright (c) 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the uncommit data.
"""

from PyQt6.QtCore import QDateTime, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_HgUncommitDialog import Ui_HgUncommitDialog


class HgUncommitDialog(QDialog, Ui_HgUncommitDialog):
    """
    Class implementing a dialog to enter the uncommit data.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the version control object
        @type Hg
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__vcs = vcs

        project = ericApp().getObject("Project")
        pwl, pel = project.getProjectDictionaries()
        language = project.getProjectSpellLanguage()
        self.logEdit.setLanguageWithPWL(language, pwl or None, pel or None)

        commitMessages = self.__vcs.vcsCommitMessages()
        self.recentComboBox.clear()
        self.recentComboBox.addItem("")
        for message in commitMessages:
            abbrMsg = message[:60]
            if len(message) > 60:
                abbrMsg += "..."
            self.recentComboBox.addItem(abbrMsg, message)

        commitAuthors = self.__vcs.getPlugin().getPreferences("CommitAuthors")
        self.authorComboBox.clear()
        self.authorComboBox.addItem("")
        self.authorComboBox.addItems(commitAuthors)

        self.dateTimeEdit.setDateTime(QDateTime.currentDateTime())

        self.logEdit.setFocus(Qt.FocusReason.OtherFocusReason)

    @pyqtSlot(int)
    def on_recentComboBox_activated(self, index):
        """
        Private slot to select a commit message from recent ones.

        @param index index of the selected entry
        @type int
        """
        txt = self.recentComboBox.itemText(index)
        if txt:
            self.logEdit.setPlainText(self.recentComboBox.currentData())

    def getUncommitData(self):
        """
        Public method to retrieve the entered uncommit data.

        @return tuple containing the commit message, a flag indicating to
            allow an empty commit, a flag indicating to allow an uncommit
            with outstanding changes, name of the author and date/time of
            the commit
        @rtype tuple of (str, bool, bool, str, str)
        """
        msg = self.logEdit.toPlainText()
        if msg:
            self.__vcs.vcsAddCommitMessage(msg)

        author = self.authorComboBox.currentText()
        if author:
            commitAuthors = self.__vcs.getPlugin().getPreferences("CommitAuthors")
            if author in commitAuthors:
                commitAuthors.remove(author)
            commitAuthors.insert(0, author)
            no = self.__vcs.getPlugin().getPreferences("CommitAuthorsLimit")
            del commitAuthors[no:]
            self.__vcs.getPlugin().setPreferences("CommitAuthors", commitAuthors)

        dateTime = (
            self.dateTimeEdit.dateTime().toString("yyyy-MM-dd hh:mm")
            if self.dateTimeGroup.isChecked()
            else ""
        )

        return (
            msg,
            self.keepCheckBox.isChecked(),
            self.allowDirtyCheckBox.isChecked(),
            author,
            dateTime,
        )
