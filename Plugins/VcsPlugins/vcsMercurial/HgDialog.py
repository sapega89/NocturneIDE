# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog starting a process and showing its output.
"""

from PyQt6.QtCore import QCoreApplication, QEventLoop, Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Preferences, Utilities

from .HgUtilities import parseProgressInfo
from .Ui_HgDialog import Ui_HgDialog


class HgDialog(QDialog, Ui_HgDialog):
    """
    Class implementing a dialog starting a process and showing its output.

    It starts a QProcess and displays a dialog that
    shows the output of the process. The dialog is modal,
    which causes a synchronized execution of the process.
    """

    def __init__(self, text, hg=None, parent=None):
        """
        Constructor

        @param text text to be shown by the label
        @type str
        @param hg reference to the Mercurial interface object
        @type Hg
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.progressWidget.hide()
        self.errorGroup.hide()
        self.inputGroup.hide()

        self.username = ""
        self.password = ""
        self.vcs = hg

        self.outputGroup.setTitle(text)

        self.show()
        QCoreApplication.processEvents()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        self.progressWidget.hide()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        if (
            Preferences.getVCS("AutoClose")
            and self.normal
            and self.errors.toPlainText() == ""
        ):
            self.accept()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.vcs.getClient().cancel()

    def startProcess(self, args, showArgs=True, client=None):
        """
        Public slot used to start the process.

        @param args list of arguments for the process
        @type list of str
        @param showArgs flag indicating to show the arguments
        @type bool
        @param client reference to a non-standard command client
        @type HgClient
        @return flag indicating a successful start of the process
        @rtype bool
        """
        self.progressWidget.hide()
        self.errorGroup.hide()
        self.inputGroup.hide()
        self.normal = False

        self.__hasAddOrDelete = False
        if args[0] in [
            "qpush",
            "qpop",
            "qgoto",
            "rebase",
            "update",
            "import",
            "revert",
            "graft",
            "shelve",
            "unshelve",
            "strip",
            "histedit",
            "uncommit",
            "unamend",
        ] or (
            args[0] in ["pull", "unbundle"]
            and ("--update" in args[1:] or "--rebase" in args[1:])
        ):
            self.__updateCommand = True
        else:
            self.__updateCommand = False

        if showArgs:
            self.resultbox.append(" ".join(args))
            self.resultbox.append("")

        if client is None:
            client = self.vcs.getClient()
        out, err = client.runcommand(
            args,
            prompt=self.__getInput,
            output=self.__showOutput,
            error=self.__showError,
        )

        if err:
            self.__showError(err)
        if out:
            self.__showOutput(out)

        self.normal = True

        self.__finish()

        return True

    def normalExit(self):
        """
        Public method to check for a normal process termination.

        @return flag indicating normal process termination
        @rtype bool
        """
        return self.normal

    def normalExitWithoutErrors(self):
        """
        Public method to check for a normal process termination without
        error messages.

        @return flag indicating normal process termination
        @rtype bool
        """
        return self.normal and self.errors.toPlainText() == ""

    def __showOutput(self, out):
        """
        Private slot to show some output.

        @param out output sent to the stdout channel
        @type str
        """
        self.progressWidget.hide()

        self.resultbox.insertPlainText(Utilities.filterAnsiSequences(out))
        self.resultbox.ensureCursorVisible()

        # check for a changed project file
        if self.__updateCommand:
            for line in out.splitlines():
                if ".epj" in line:
                    self.__hasAddOrDelete = True
                    break

        QCoreApplication.processEvents()

    def __showError(self, out):
        """
        Private slot to show some error or progress information.

        @param out output sent to the stderr channel
        @type str
        """
        for line in out.splitlines(keepends=True):
            if line.strip():
                topic, value, maximum, estimate = parseProgressInfo(line.strip())
                if topic:
                    self.topicLabel.setText(topic.capitalize())
                    self.remainingTimeLabel.setText(
                        self.tr("Time remaining: {0}").format(estimate)
                    )
                    self.progressBar.setMaximum(maximum)
                    self.progressBar.setValue(value)
                    self.progressWidget.setVisible(value != maximum)
                else:
                    self.errorGroup.show()
                    self.errors.insertPlainText(Utilities.filterAnsiSequences(line))
                    self.errors.ensureCursorVisible()

        QCoreApplication.processEvents()

    def hasAddOrDelete(self):
        """
        Public method to check, if the last action contained an add or delete.

        @return flag indicating the presence of an add or delete
        @rtype bool
        """
        return self.__hasAddOrDelete

    def __getInput(self, size, message):
        """
        Private method to get some input from the user.

        @param size maximum length of the requested input
        @type int
        @param message message sent by the server
        @type str
        @return tuple containing data entered by the user and
            a flag indicating a password input
        @rtype tuple of (str, bool)
        """
        self.inputGroup.show()
        self.input.setMaxLength(size)
        self.input.setFocus(Qt.FocusReason.OtherFocusReason)

        self.resultbox.ensureCursorVisible()
        self.errors.ensureCursorVisible()

        loop = QEventLoop(self)
        self.sendButton.clicked[bool].connect(loop.quit)
        self.input.returnPressed.connect(loop.quit)
        loop.exec()
        message = self.input.text() + "\n"
        isPassword = self.passwordCheckBox.isChecked()

        self.input.clear()
        self.inputGroup.hide()

        return message, isPassword
