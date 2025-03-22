# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the commit message.
"""

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_GitCommitDialog import Ui_GitCommitDialog


class GitCommitDialog(QWidget, Ui_GitCommitDialog):
    """
    Class implementing a dialog to enter the commit message.

    @signal accepted() emitted, if the dialog was accepted
    @signal rejected() emitted, if the dialog was rejected
    """

    accepted = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, vcs, msg, amend, commitAll, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Git
        @param msg initial message
        @type str
        @param amend flag indicating to amend the HEAD commit
        @type bool
        @param commitAll flag indicating to commit all local changes
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

        self.amendCheckBox.setChecked(amend)
        self.stagedCheckBox.setChecked(not commitAll)

    def showEvent(self, _evt):
        """
        Protected method called when the dialog is about to be shown.

        @param _evt the event (unused)
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

        self.logEdit.setFocus(Qt.FocusReason.OtherFocusReason)

    def logMessage(self):
        """
        Public method to retrieve the log message.

        @return the log message
        @rtype str
        """
        msg = self.logEdit.toPlainText()
        if msg:
            self.__vcs.vcsAddCommitMessage(msg)

        return msg

    def stagedOnly(self):
        """
        Public method to retrieve the state of the staged only flag.

        @return state of the staged only flag
        @rtype bool
        """
        return self.stagedCheckBox.isChecked()

    def amend(self):
        """
        Public method to retrieve the state of the amend flag.

        @return state of the amend flag
        @rtype bool
        """
        return self.amendCheckBox.isChecked()

    def resetAuthor(self):
        """
        Public method to retrieve the state of the reset author flag.

        @return state of the reset author flag
        @rtype bool
        """
        return self.resetAuthorCheckBox.isChecked()

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
