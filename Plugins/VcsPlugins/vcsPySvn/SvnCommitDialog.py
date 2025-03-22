# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the commit message.
"""

import pysvn

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_SvnCommitDialog import Ui_SvnCommitDialog


class SvnCommitDialog(QWidget, Ui_SvnCommitDialog):
    """
    Class implementing a dialog to enter the commit message.

    @signal accepted() emitted, if the dialog was accepted
    @signal rejected() emitted, if the dialog was rejected
    """

    accepted = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Subversion
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

        if pysvn.svn_version < (1, 5, 0) or pysvn.version < (1, 6, 0):
            self.changeListsGroup.hide()
        else:
            self.changeLists.addItems(sorted(vcs.svnGetChangelists()))

    def showEvent(self, _evt):
        """
        Protected method called when the dialog is about to be shown.

        @param _evt reference to the event object (unused)
        @type QShowEvent
        """
        commitMessages = self.__vcs.vcsCommitMessages()
        self.recentComboBox.clear()
        self.recentComboBox.addItem("")
        self.recentComboBox.addItems(commitMessages)

        self.logEdit.setFocus(Qt.FocusReason.OtherFocusReason)

    def logMessage(self):
        """
        Public method to retrieve the log message.

        This method has the side effect of saving the 20 most recent
        commit messages for reuse.

        @return the log message
        @rtype str
        """
        msg = self.logEdit.toPlainText()
        if msg:
            self.__vcs.vcsAddCommitMessage(msg)
        return msg

    def hasChangelists(self):
        """
        Public method to check, if the user entered some change lists.

        @return flag indicating availability of change lists
        @rtype bool
        """
        return len(self.changeLists.selectedItems()) > 0

    def changelistsData(self):
        """
        Public method to retrieve the change lists data.

        @return tuple containing the change lists and a flag indicating to keep
            the change lists
        @rtype tuple of (list of str, bool)
        """
        slists = [
            line.text().strip()
            for line in self.changeLists.selectedItems()
            if line.text().strip() != ""
        ]

        if len(slists) == 0:
            return [], False

        return slists, self.keepChangeListsCheckBox.isChecked()

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
            self.logEdit.setPlainText(txt)
