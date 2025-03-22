# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the commit message of the current patch.
"""

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Utilities

from .Ui_HgQueuesHeaderDialog import Ui_HgQueuesHeaderDialog


class HgQueuesHeaderDialog(QDialog, Ui_HgQueuesHeaderDialog):
    """
    Class implementing a dialog to show the commit message of the current
    patch.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Hg
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.vcs = vcs
        self.__hgClient = vcs.getClient()

        self.show()
        QCoreApplication.processEvents()

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if self.__hgClient.isExecuting():
            self.__hgClient.cancel()

        e.accept()

    def start(self):
        """
        Public slot to start the list command.
        """
        self.activateWindow()

        args = self.vcs.initCommand("qheader")

        out, err = self.__hgClient.runcommand(
            args, output=self.__showOutput, error=self.__showError
        )
        if err:
            self.__showError(err)
        if out:
            self.__showOutPut(out)
        self.__finish()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            if self.__hgClient:
                self.__hgClient.cancel()
            else:
                self.__finish()

    def __showOutput(self, out):
        """
        Private slot to show some output.

        @param out output to be shown
        @type str
        """
        self.messageEdit.appendPlainText(Utilities.filterAnsiSequences(out))

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.messageEdit.appendPlainText(self.tr("Error: "))
        self.messageEdit.appendPlainText(Utilities.filterAnsiSequences(out))
