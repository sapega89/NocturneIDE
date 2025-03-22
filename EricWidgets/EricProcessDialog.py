# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog starting a process and showing its output.
"""

import os
import re

from PyQt6.QtCore import (
    QCoreApplication,
    QProcess,
    QProcessEnvironment,
    Qt,
    QTimer,
    pyqtSlot,
)
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit

from eric7.EricUtilities import strToQByteArray
from eric7.EricWidgets import EricMessageBox

from .Ui_EricProcessDialog import Ui_EricProcessDialog


class EricProcessDialog(QDialog, Ui_EricProcessDialog):
    """
    Class implementing a dialog starting a process and showing its output.

    It starts a QProcess and displays a dialog that shows the output of the
    process. The dialog is modal, which causes a synchronized execution of
    the process.
    """

    def __init__(
        self,
        outputTitle="",
        windowTitle="",
        showProgress=False,
        showInput=True,
        combinedOutput=False,
        monospacedFont=None,
        encoding="utf-8",
        parent=None,
    ):
        """
        Constructor

        @param outputTitle title for the output group (defaults to "")
        @type str (optional)
        @param windowTitle title of the dialog (defaults to "")
        @type str (optional)
        @param showProgress flag indicating to show a progress bar (defaults to False)
        @type bool (optional)
        @param showInput flag indicating to allow input to the process (defaults to
            True)
        @type bool (optional)
        @param combinedOutput flag indicating to show output of the stderr channel
            in the main output pane (defaults to False)
        @type bool (optional)
        @param monospacedFont font to be used (should be a monospaced one) (defaults
            to None)
        @type QFont
        @param encoding encoding used for the communication with the process (defaults
            to "utf-8")
        @type str (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        if monospacedFont is None:
            monospacedFont = QFont("Monospace")
        self.resultbox.setFontFamily(monospacedFont.family())
        self.resultbox.setFontPointSize(monospacedFont.pointSize())
        self.errors.setFontFamily(monospacedFont.family())
        self.errors.setFontPointSize(monospacedFont.pointSize())

        self.__ioEncoding = encoding

        if windowTitle:
            self.setWindowTitle(windowTitle)
        if outputTitle:
            self.outputGroup.setTitle(outputTitle)
        self.__showProgress = showProgress
        self.progressBar.setVisible(self.__showProgress)

        self.__showInput = showInput
        self.__combinedOutput = combinedOutput

        if not self.__showInput:
            self.inputGroup.setEnabled(False)
            self.inputGroup.hide()

        self.__process = None
        self.__progressRe = re.compile(r"""(\d{1,3})\s*%""")

        self.show()
        QCoreApplication.processEvents()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        if (
            self.__process is not None
            and self.__process.state() != QProcess.ProcessState.NotRunning
        ):
            self.__process.terminate()
            QTimer.singleShot(2000, self.__process.kill)
            self.__process.waitForFinished(3000)

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()

        self.__process = None

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
        self.__normal = (exitStatus == QProcess.ExitStatus.NormalExit) and (
            exitCode == 0
        )
        if self.__normal:
            self.statusLabel.setText(self.tr("Process finished successfully."))
        elif exitStatus == QProcess.ExitStatus.CrashExit:
            self.statusLabel.setText(self.tr("Process crashed."))
        else:
            self.statusLabel.setText(
                self.tr("Process finished with exit code {0}").format(exitCode)
            )
        self.__finish()

    def startProcess(
        self, program, args, workingDir=None, showArgs=True, environment=None
    ):
        """
        Public slot used to start the process.

        @param program path of the program to be executed
        @type str
        @param args list of arguments for the process
        @type list of str
        @param workingDir working directory for the process
        @type str
        @param showArgs flag indicating to show the arguments
        @type bool
        @param environment dictionary of environment settings to add
            or change for the process
        @type dict
        @return flag indicating a successful start of the process
        @rtype bool
        """
        self.errorGroup.hide()
        self.__normal = False
        self.__intercept = False

        if environment is None:
            environment = {}

        if showArgs:
            self.resultbox.append(program + " " + " ".join(args))
            self.resultbox.append("")

        self.__process = QProcess()
        if environment:
            env = QProcessEnvironment.systemEnvironment()
            for key, value in environment.items():
                env.insert(key, value)
            self.__process.setProcessEnvironment(env)

        self.__process.finished.connect(self.__procFinished)
        self.__process.readyReadStandardOutput.connect(self.__readStdout)
        self.__process.readyReadStandardError.connect(self.__readStderr)

        if workingDir:
            self.__process.setWorkingDirectory(workingDir)

        self.__process.start(program, args)
        procStarted = self.__process.waitForStarted(10000)
        if not procStarted:
            self.buttonBox.setFocus()
            self.inputGroup.setEnabled(False)
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr("<p>The process <b>{0}</b> could not be started.</p>").format(
                    program
                ),
            )
        elif self.__showInput:
            self.inputGroup.setEnabled(True)
            self.inputGroup.show()

        return procStarted

    def normalExit(self):
        """
        Public method to check for a normal process termination.

        @return flag indicating normal process termination
        @rtype bool
        """
        return self.__normal

    def normalExitWithoutErrors(self):
        """
        Public method to check for a normal process termination without
        error messages.

        @return flag indicating normal process termination
        @rtype bool
        """
        return self.__normal and self.errors.toPlainText() == ""

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process and inserts it into the
        output pane.
        """
        if self.__process is not None:
            s = str(
                self.__process.readAllStandardOutput(),
                self.__ioEncoding,
                "replace",
            )
            if self.__showProgress:
                match = self.__progressRe.search(s)
                if match:
                    progress = int(match.group(1))
                    self.progressBar.setValue(progress)
                    if not s.endswith("\n"):
                        s += "\n"
            self.resultbox.insertPlainText(s)
            self.resultbox.ensureCursorVisible()

            QCoreApplication.processEvents()

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.__process is not None:
            s = str(
                self.__process.readAllStandardError(),
                self.__ioEncoding,
                "replace",
            )

            if self.__combinedOutput:
                self.resultbox.insertPlainText(s)
                self.resultbox.ensureCursorVisible()
            else:
                self.errorGroup.show()
                self.errors.insertPlainText(s)
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

        self.__process.write(strToQByteArray(inputTxt))

        self.passwordCheckBox.setChecked(False)
        self.input.clear()

    def on_input_returnPressed(self):
        """
        Private slot to handle the press of the return key in the input field.
        """
        self.__intercept = True
        self.on_sendButton_clicked()

    def keyPressEvent(self, evt):
        """
        Protected slot to handle a key press event.

        @param evt the key press event
        @type QKeyEvent
        """
        if self.__intercept:
            self.__intercept = False
            evt.accept()
            return

        super().keyPressEvent(evt)
