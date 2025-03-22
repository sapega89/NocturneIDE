# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog starting a process and showing its output.
"""

import os

from PyQt6.QtCore import (
    QCoreApplication,
    QProcess,
    QProcessEnvironment,
    Qt,
    QTimer,
    pyqtSlot,
)
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_GitDialog import Ui_GitDialog


class GitDialog(QDialog, Ui_GitDialog):
    """
    Class implementing a dialog starting a process and showing its output.

    It starts a QProcess and displays a dialog that
    shows the output of the process. The dialog is modal,
    which causes a synchronized execution of the process.
    """

    def __init__(self, text, git=None, parent=None):
        """
        Constructor

        @param text text to be shown by the label
        @type str
        @param git reference to the Git interface object
        @type Git
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.errorGroup.hide()
        self.inputGroup.hide()

        self.process = None
        self.username = ""
        self.password = ""
        self.vcs = git

        self.outputGroup.setTitle(text)

        self.show()
        QCoreApplication.processEvents()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        if (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        ):
            self.process.terminate()
            QTimer.singleShot(2000, self.process.kill)
            self.process.waitForFinished(3000)

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()

        self.process = None

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        if self.normal and self.errors.toPlainText():
            self.errorGroup.setTitle(self.tr("Additional Output"))

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
            self.statusLabel.setText(self.tr("Process canceled."))
            self.__finish()

    def __procFinished(self, exitCode, exitStatus):
        """
        Private slot connected to the finished signal.

        @param exitCode exit code of the process
        @type int
        @param exitStatus exit status of the process
        @type QProcess.ExitStatus
        """
        self.normal = (exitStatus == QProcess.ExitStatus.NormalExit) and (exitCode == 0)
        if self.normal:
            self.statusLabel.setText(self.tr("Process finished successfully."))
        elif exitStatus == QProcess.ExitStatus.CrashExit:
            self.statusLabel.setText(self.tr("Process crashed."))
        else:
            self.statusLabel.setText(
                self.tr("Process finished with exit code {0}").format(exitCode)
            )
        self.__finish()

    def startProcess(self, args, workingDir=None, showArgs=True, environment=None):
        """
        Public slot used to start the process.

        @param args list of arguments for the process
        @type list of str
        @param workingDir working directory for the process
        @type str
        @param showArgs flag indicating to show the arguments
        @type bool
        @param environment dictionary of environment settings to add
            or change for the git process
        @type dict
        @return flag indicating a successful start of the process
        @rtype bool
        """
        self.errorGroup.hide()
        self.normal = False
        self.intercept = False

        if environment is None:
            environment = {}

        self.__hasAddOrDelete = False
        if args[0] in [
            "checkout",
            "fetch",
            "pull",
            "rebase",
            "reset",
            "merge",
            "cherry-pick",
            "stash",
        ]:
            self.__updateCommand = True
        else:
            self.__updateCommand = False

        if showArgs:
            self.resultbox.append(" ".join(args))
            self.resultbox.append("")

        self.process = QProcess()
        if environment:
            env = QProcessEnvironment.systemEnvironment()
            for key, value in environment.items():
                env.insert(key, value)
            self.process.setProcessEnvironment(env)

        self.process.finished.connect(self.__procFinished)
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)

        if workingDir:
            self.process.setWorkingDirectory(workingDir)
        self.process.start("git", args)
        procStarted = self.process.waitForStarted(5000)
        if not procStarted:
            self.buttonBox.setFocus()
            self.inputGroup.setEnabled(False)
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("git"),
            )
        else:
            self.inputGroup.setEnabled(True)
            self.inputGroup.show()
        return procStarted

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

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        if self.process is not None:
            s = str(
                self.process.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.__showOutput(s)

    def __showOutput(self, out):
        """
        Private slot to show some output.

        @param out output to be shown
        @type str
        """
        self.resultbox.insertPlainText(out)
        self.resultbox.ensureCursorVisible()

        # check for a changed project file
        if self.__updateCommand:
            for line in out.splitlines():
                if ".epj" in line:
                    self.__hasAddOrDelete = True
                    break

        QCoreApplication.processEvents()

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.process is not None:
            s = str(
                self.process.readAllStandardError(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.__showError(s)

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()

        QCoreApplication.processEvents()

    def on_passwordCheckBox_toggled(self, isOn):
        """
        Private slot to handle the password checkbox toggled.

        @param isOn flag indicating the status of the check box
        @type bool
        """
        if isOn:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)

    @pyqtSlot()
    def on_sendButton_clicked(self):
        """
        Private slot to send the input to the git process.
        """
        inputTxt = self.input.text()
        inputTxt += os.linesep

        if self.passwordCheckBox.isChecked():
            self.errors.insertPlainText(os.linesep)
            self.errors.ensureCursorVisible()
        else:
            self.errors.insertPlainText(inputTxt)
            self.errors.ensureCursorVisible()

        self.process.write(strToQByteArray(inputTxt))

        self.passwordCheckBox.setChecked(False)
        self.input.clear()

    def on_input_returnPressed(self):
        """
        Private slot to handle the press of the return key in the input field.
        """
        self.intercept = True
        self.on_sendButton_clicked()

    def keyPressEvent(self, evt):
        """
        Protected slot to handle a key press event.

        @param evt the key press event
        @type QKeyEvent
        """
        if self.intercept:
            self.intercept = False
            evt.accept()
            return
        super().keyPressEvent(evt)

    def hasAddOrDelete(self):
        """
        Public method to check, if the last action contained an add or delete.

        @return flag indicating the presence of an add or delete
        @rtype bool
        """
        return self.__hasAddOrDelete
