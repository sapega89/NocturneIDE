# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the commit message.
"""

from PyQt6.QtCore import QDateTime, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_HgCommitDialog import Ui_HgCommitDialog


class HgCommitDialog(QWidget, Ui_HgCommitDialog):
    """
    Class implementing a dialog to enter the commit message.

    @signal accepted() emitted, if the dialog was accepted
    @signal rejected() emitted, if the dialog was rejected
    """

    accepted = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, vcs, msg, mq, merge, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Hg
        @param msg initial message
        @type str
        @param mq flag indicating a queue commit
        @type bool
        @param merge flag indicating a merge commit
        @type bool
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setupUi(self)

        self.__vcs = vcs

        project = ericApp().getObject("Project")
        pwl, pel = project.getProjectDictionaries()
        language = project.getProjectSpellLanguage()
        self.logEdit.setLanguageWithPWL(language, pwl or None, pel or None)
        self.logEdit.setPlainText(msg)

        if mq or merge:
            self.amendCheckBox.setVisible(False)
            self.subrepoCheckBox.setVisible(False)
        else:
            self.subrepoCheckBox.setVisible(vcs.hasSubrepositories())

    def showEvent(self, _evt):
        """
        Protected method called when the dialog is about to be shown.

        @param _evt reference to the event object (unused)
        @type QShowEvent
        """
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

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.logEdit.clear()

    def on_buttonBox_accepted(self):
        """
        Private slot called by the buttonBox accepted signal.
        """
        self.close()
        self.accepted.emit()

    def on_buttonBox_rejected(self):
        """
        Private slot called by the buttonBox rejected signal.
        """
        self.close()
        self.rejected.emit()

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

    def getCommitData(self):
        """
        Public method to retrieve the entered data for the commit.

        @return tuple containing the log message, a flag indicating to amend
            the last commit, a flag indicating to commit subrepositories as
            well, name of the author and date/time of the commit
        @rtype tuple of str, bool, bool, str, str
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
            self.amendCheckBox.isChecked(),
            self.subrepoCheckBox.isChecked(),
            author,
            dateTime,
        )
