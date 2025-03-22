# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog starting a process and showing its output.
"""

import os

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_SvnDialog import Ui_SvnDialog


class SvnDialog(QDialog, Ui_SvnDialog):
    """
    Class implementing a dialog starting a process and showing its output.

    It starts a QProcess and displays a dialog that
    shows the output of the process. The dialog is modal,
    which causes a synchronized execution of the process.
    """

    def __init__(self, text, parent=None):
        """
        Constructor

        @param text text to be shown by the label
        @type str
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.errorGroup.hide()
        self.inputGroup.hide()

        self.process = None
        self.username = ""
        self.password = ""

        self.outputGroup.setTitle(text)

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed the
        button.
        """
        if (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        ):
            self.process.terminate()
            QTimer.singleShot(2000, self.process.kill)
            self.process.waitForFinished(3000)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()

        self.process = None

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
            self.__finish()

    def __procFinished(self, exitCode, exitStatus):
        """
        Private slot connected to the finished signal.

        @param exitCode exit code of the process
        @type int
        @param exitStatus exit status of the process
        @type QProcess.ExitStatus
        """
        self.normal = exitStatus == QProcess.ExitStatus.NormalExit and exitCode == 0
        self.__finish()

    def startProcess(self, args, workingDir=None, setLanguage=False):
        """
        Public slot used to start the process.

        @param args list of arguments for the process
        @type list of str
        @param workingDir working directory for the process
        @type str
        @param setLanguage flag indicating to set the language to "C"
        @type bool
        @return flag indicating a successful start of the process
        @rtype bool
        """
        self.errorGroup.hide()
        self.normal = False
        self.intercept = False

        self.__hasAddOrDelete = False

        self.process = QProcess()
        if setLanguage:
            env = QProcessEnvironment.systemEnvironment()
            env.insert("LANG", "C")
            self.process.setProcessEnvironment(env)
        nargs = []
        lastWasPwd = False
        for arg in args:
            if lastWasPwd:
                lastWasPwd = True
                continue
            nargs.append(arg)
            if arg == "--password":
                lastWasPwd = True
                nargs.append("*****")

        self.resultbox.append(" ".join(nargs))
        self.resultbox.append("")

        self.process.finished.connect(self.__procFinished)
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)

        if workingDir:
            self.process.setWorkingDirectory(workingDir)
        self.process.start("svn", args)
        procStarted = self.process.waitForStarted(5000)
        if not procStarted:
            self.buttonBox.setFocus()
            self.inputGroup.setEnabled(False)
            self.inputGroup.hide()
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("svn"),
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

    def __readStdout(self):
        """
        Private slot to handle the readyReadStdout signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        if self.process is not None:
            s = str(
                self.process.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.resultbox.insertPlainText(s)
            self.resultbox.ensureCursorVisible()
            if not self.__hasAddOrDelete and len(s) > 0:
                # check the output
                for line in s.split(os.linesep):
                    if ".epj" in line:
                        self.__hasAddOrDelete = True
                        break
                    if line and line[0:2].strip() in ["A", "D"]:
                        self.__hasAddOrDelete = True
                        break

    def __readStderr(self):
        """
        Private slot to handle the readyReadStderr signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.process is not None:
            self.errorGroup.show()
            s = str(
                self.process.readAllStandardError(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.errors.insertPlainText(s)
            self.errors.ensureCursorVisible()

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
        Private slot to send the input to the subversion process.
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
