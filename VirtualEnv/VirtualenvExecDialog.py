# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the virtualenv execution dialog.
"""

import os

from PyQt6.QtCore import QProcess, QTimer, QUrl, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Preferences
from eric7.SystemUtilities import OSUtilities, PythonUtilities

from .Ui_VirtualenvExecDialog import Ui_VirtualenvExecDialog
from .VirtualenvMeta import VirtualenvMetaData


class VirtualenvExecDialog(QDialog, Ui_VirtualenvExecDialog):
    """
    Class implementing the virtualenv execution dialog.

    This class starts a QProcess and displays a dialog that
    shows the output of the virtualenv or pyvenv process.
    """

    def __init__(self, configuration, venvManager, parent=None):
        """
        Constructor

        @param configuration dictionary containing the configuration parameters
            as returned by the command configuration dialog
        @type dict
        @param venvManager reference to the virtual environment manager
        @type VirtualenvManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.__pyvenv = configuration["envType"] == "pyvenv"
        self.__targetDir = configuration["targetDirectory"]
        self.__openTarget = configuration["openTarget"]
        self.__createLog = configuration["createLog"]
        self.__createScript = configuration["createScript"]
        self.__venvName = configuration["logicalName"]
        self.__venvManager = venvManager

        self.__process = None
        self.__cmd = ""

        if self.__pyvenv:
            self.__calls = []
            if configuration["pythonExe"]:
                self.__calls.append((configuration["pythonExe"], ["-m", "venv"]))
            self.__calls.extend(
                [
                    (PythonUtilities.getPythonExecutable(), ["-m", "venv"]),
                    ("python3", ["-m", "venv"]),
                    ("python", ["-m", "venv"]),
                ]
            )
        else:
            self.__calls = [
                (PythonUtilities.getPythonExecutable(), ["-m", "virtualenv"]),
                ("virtualenv", []),
            ]
        self.__callIndex = 0
        self.__callArgs = []

    def start(self, arguments):
        """
        Public slot to start the virtualenv command.

        @param arguments commandline arguments for virtualenv/pyvenv program
        @type list of str
        """
        if self.__callIndex == 0:
            # first attempt, add a given python interpreter and do
            # some other setup
            self.errorGroup.hide()
            self.contents.clear()
            self.errors.clear()

            self.__process = QProcess()
            self.__process.readyReadStandardOutput.connect(self.__readStdout)
            self.__process.readyReadStandardError.connect(self.__readStderr)
            self.__process.finished.connect(self.__finish)

            if not self.__pyvenv:
                for arg in arguments:
                    if arg.startswith("--python="):
                        prog = arg.replace("--python=", "")
                        self.__calls.insert(0, (prog, ["-m", "virtualenv"]))
                        break
            self.__callArgs = arguments

        prog, args = self.__calls[self.__callIndex]
        args.extend(self.__callArgs)
        self.__cmd = "{0} {1}".format(prog, " ".join(args))
        self.__logOutput(self.tr("Executing: {0}\n").format(self.__cmd))
        self.__process.start(prog, args)
        procStarted = self.__process.waitForStarted(5000)
        if not procStarted:
            self.__logOutput(self.tr("Failed\n\n"))
            self.__nextAttempt()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.accept()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__finish(0, 0, giveUp=True)

    @pyqtSlot(int, QProcess.ExitStatus)
    def __finish(self, exitCode, _exitStatus, giveUp=False):
        """
        Private slot called when the process finished.

        It is called when the process finished or the user pressed the button.

        @param exitCode exit code of the process
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        @param giveUp flag indicating to not start another attempt
        @type bool
        """
        if (
            self.__process is not None
            and self.__process.state() != QProcess.ProcessState.NotRunning
        ):
            self.__process.terminate()
            QTimer.singleShot(2000, self.__process.kill)
            self.__process.waitForFinished(3000)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        if not giveUp:
            if exitCode != 0:
                self.__logOutput(self.tr("Failed\n\n"))
                if len(self.errors.toPlainText().splitlines()) == 1:
                    self.errors.clear()
                    self.errorGroup.hide()
                    self.__nextAttempt()
                    return

            self.__process = None

            if self.__pyvenv:
                self.__logOutput(self.tr("\npyvenv finished.\n"))
            else:
                self.__logOutput(self.tr("\nvirtualenv finished.\n"))

            if os.path.exists(self.__targetDir):
                if self.__createScript:
                    self.__writeScriptFile()

                if self.__createLog:
                    self.__writeLogFile()

                if self.__openTarget:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(self.__targetDir))

                if self.__venvManager:
                    metadata = VirtualenvMetaData(
                        name=self.__venvName, path=self.__targetDir
                    )
                    self.__venvManager.addVirtualEnv(metadata)

    def __nextAttempt(self):
        """
        Private method to start another attempt.
        """
        self.__callIndex += 1
        if self.__callIndex < len(self.__calls):
            self.start(self.__callArgs)
        else:
            if self.__pyvenv:
                self.__logError(
                    self.tr("No suitable pyvenv program could be started.\n")
                )
            else:
                self.__logError(
                    self.tr("No suitable virtualenv program could be started.\n")
                )
            self.__cmd = ""
            self.__finish(0, 0, giveUp=True)

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        self.__process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        while self.__process.canReadLine():
            s = str(
                self.__process.readLine(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.__logOutput(s)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        self.__process.setReadChannel(QProcess.ProcessChannel.StandardError)

        while self.__process.canReadLine():
            s = str(
                self.__process.readLine(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.__logError(s)

    def __logOutput(self, s):
        """
        Private method to log some output.

        @param s output string to log
        @type str
        """
        self.contents.insertPlainText(s)
        self.contents.ensureCursorVisible()

    def __logError(self, s):
        """
        Private method to log an error.

        @param s error string to log
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(s)
        self.errors.ensureCursorVisible()

    def __writeLogFile(self):
        """
        Private method to write a log file to the virtualenv directory.
        """
        outtxt = self.contents.toPlainText()
        logFile = (
            os.path.join(self.__targetDir, "pyvenv.log")
            if self.__pyvenv
            else os.path.join(self.__targetDir, "virtualenv.log")
        )
        self.__logOutput(self.tr("\nWriting log file '{0}'.\n").format(logFile))

        try:
            with open(logFile, "w", encoding="utf-8") as f:
                f.write(self.tr("Output:\n"))
                f.write(outtxt)
                errtxt = self.errors.toPlainText()
                if errtxt:
                    f.write("\n")
                    f.write(self.tr("Errors:\n"))
                    f.write(errtxt)
        except OSError as err:
            self.__logError(
                self.tr(
                    """The logfile '{0}' could not be written.\nReason: {1}\n"""
                ).format(logFile, str(err))
            )
        self.__logOutput(self.tr("Done.\n"))

    def __writeScriptFile(self):
        """
        Private method to write a script file to the virtualenv directory.
        """
        basename = "create_pyvenv" if self.__pyvenv else "create_virtualenv"
        if OSUtilities.isWindowsPlatform():
            script = os.path.join(self.__targetDir, basename + ".cmd")
            txt = self.__cmd
        else:
            script = os.path.join(self.__targetDir, basename + ".sh")
            txt = "#!/usr/bin/env sh\n\n" + self.__cmd

        self.__logOutput(self.tr("\nWriting script file '{0}'.\n").format(script))

        try:
            with open(script, "w", encoding="utf-8") as f:
                f.write(txt)
        except OSError as err:
            self.__logError(
                self.tr(
                    """The script file '{0}' could not be written.\n"""
                    """Reason: {1}\n"""
                ).format(script, str(err))
            )
        self.__logOutput(self.tr("Done.\n"))
