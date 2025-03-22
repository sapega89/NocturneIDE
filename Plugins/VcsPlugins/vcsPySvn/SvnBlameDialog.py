# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the svn blame command.
"""

import os

import pysvn

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHeaderView, QTreeWidgetItem

from eric7 import Preferences
from eric7.EricUtilities.EricMutexLocker import EricMutexLocker

from .SvnDialogMixin import SvnDialogMixin
from .Ui_SvnBlameDialog import Ui_SvnBlameDialog


class SvnBlameDialog(QDialog, SvnDialogMixin, Ui_SvnBlameDialog):
    """
    Class implementing a dialog to show the output of the svn blame command.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Subversion
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        SvnDialogMixin.__init__(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.vcs = vcs

        self.blameList.headerItem().setText(self.blameList.columnCount(), "")
        font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.blameList.setFont(font)

        self.client = self.vcs.getClient()
        self.client.callback_cancel = self._clientCancelCallback
        self.client.callback_get_login = self._clientLoginCallback
        self.client.callback_ssl_server_trust_prompt = (
            self._clientSslServerTrustPromptCallback
        )

    def start(self, fn):
        """
        Public slot to start the svn blame command.

        @param fn filename to show the blame for
        @type str
        """
        self.blameList.clear()
        self.errorGroup.hide()
        self.activateWindow()

        dname, fname = self.vcs.splitPath(fn)

        cwd = os.getcwd()
        os.chdir(dname)
        try:
            with EricMutexLocker(self.vcs.vcsExecutionMutex):
                annotations = self.client.annotate(fname)
            for annotation in annotations:
                author = annotation["author"]
                line = annotation["line"]
                self.__generateItem(
                    annotation["revision"].number,
                    author,
                    annotation["number"] + 1,
                    line,
                )
        except pysvn.ClientError as e:
            self.__showError(e.args[0] + "\n")
        self.__finish()
        os.chdir(cwd)

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed the
        button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.__resizeColumns()

        self._cancel()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__finish()

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.blameList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)

    def __generateItem(self, revision, author, lineno, text):
        """
        Private method to generate a blame item in the blame list.

        @param revision revision string
        @type str
        @param author author of the change
        @type str
        @param lineno linenumber
        @type str
        @param text line of text from the annotated file
        @type str
        """
        itm = QTreeWidgetItem(
            self.blameList,
            ["{0:d}".format(revision), author, "{0:d}".format(lineno), text],
        )
        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignRight)

    def __showError(self, msg):
        """
        Private slot to show an error message.

        @param msg error message to show
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(msg)
        self.errors.ensureCursorVisible()
