# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of a conda execution.
"""

import json

from PyQt6.QtCore import QProcess, QTimer, pyqtSlot
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricMessageBox

from .Ui_CondaExecDialog import Ui_CondaExecDialog


class CondaExecDialog(QDialog, Ui_CondaExecDialog):
    """
    Class implementing a dialog to show the output of a conda execution.
    """

    def __init__(self, command, parent=None):
        """
        Constructor

        @param command conda command executed
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.__condaCommand = command

        self.__process = None
        self.__condaExe = Preferences.getConda("CondaExecutable")
        if not self.__condaExe:
            self.__condaExe = "conda"

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.accept()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__finish(1, 0)

    def start(self, arguments):
        """
        Public slot to start the conda command.

        @param arguments commandline arguments for conda program
        @type list of str
        """
        self.errorGroup.hide()
        self.progressLabel.hide()
        self.progressBar.hide()

        self.contents.clear()
        self.errors.clear()
        self.progressLabel.clear()
        self.progressBar.setValue(0)

        self.__bufferedStdout = None
        self.__json = "--json" in arguments
        self.__firstProgress = True
        self.__lastFetchFile = ""

        self.__statusOk = False
        self.__result = None

        self.__logOutput(self.__condaExe + " " + " ".join(arguments) + "\n\n")

        self.__process = QProcess()
        self.__process.readyReadStandardOutput.connect(self.__readStdout)
        self.__process.readyReadStandardError.connect(self.__readStderr)
        self.__process.finished.connect(self.__finish)

        self.__process.start(self.__condaExe, arguments)
        procStarted = self.__process.waitForStarted(5000)
        if not procStarted:
            EricMessageBox.critical(
                self,
                self.tr("Conda Execution"),
                self.tr(
                    """The conda executable could not be started. Is it"""
                    """ configured correctly?"""
                ),
            )
            self.__finish(1, 0)
        else:
            self.__logOutput(self.tr("Operation started.\n"))

    @pyqtSlot(int, QProcess.ExitStatus)
    def __finish(self, exitCode, _exitStatus):
        """
        Private slot called when the process finished.

        It is called when the process finished or
        the user pressed the button.

        @param exitCode exit code of the process
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
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

        self.progressLabel.hide()
        self.progressBar.hide()

        self.__statusOk = exitCode == 0

        self.__logOutput(self.tr("Operation finished.\n"))
        if not self.__json and self.__bufferedStdout:
            self.__logOutput(self.__bufferedStdout)

        if self.__json and self.__bufferedStdout:
            index = self.__bufferedStdout.find("{")
            rindex = self.__bufferedStdout.rfind("}")
            self.__bufferedStdout = self.__bufferedStdout[index : rindex + 1]
            try:
                self.__result = json.loads(self.__bufferedStdout)
            except Exception as error:
                self.__result = {}
                self.__logError(str(error))
                return

            if "error" in self.__result:
                self.__logError(self.__result["error"])
                self.__statusOk = False
            elif "success" in self.__result and not self.__result["success"]:
                self.__logError(
                    self.tr("Conda command '{0}' did not return success.").format(
                        self.__condaCommand
                    )
                )
                if "message" in self.__result:
                    self.__logError("\n")
                    self.__logError(
                        self.tr("\nConda Message: {0}").format(self.__result["message"])
                    )
                self.__statusOk = False
            elif "message" in self.__result:
                self.__logOutput(
                    self.tr("\nConda Message: {0}").format(self.__result["message"])
                )

    def getResult(self):
        """
        Public method to the result of the command execution.

        @return tuple containing a flag indicating success and the result data.
        @rtype tuple of (bool, dict)
        """
        return self.__statusOk, self.__result

    def __setProgressValues(self, jsonDict, progressType):
        """
        Private method to set the value of the progress bar.

        @param jsonDict dictionary containing the progress info
        @type dict
        @param progressType action type to check for
        @type str
        @return flag indicating success
        @rtype bool
        """
        if progressType in jsonDict and "progress" in jsonDict:
            if jsonDict["maxval"] == 1:
                self.progressBar.setMaximum(100)
                # percent values
                self.progressBar.setValue(int(jsonDict["progress"] * 100))
                parts = jsonDict["fetch"].split("|")
                filename = parts[0].strip()
                filesize = parts[1].strip()
            else:
                self.progressBar.setMaximum(jsonDict["maxval"])
                self.progressBar.setValue(jsonDict["progress"])
                filename = jsonDict["fetch"].strip()
                filesize = EricUtilities.dataString(int(jsonDict["maxval"]))

            self.progressLabel.setText(
                self.tr("{0} (Size: {1})").format(filename, filesize)
            )

            if progressType == "fetch":
                if filename != self.__lastFetchFile:
                    self.__logOutput(self.tr("Fetching {0} ...").format(filename))
                    self.__lastFetchFile = filename
                elif jsonDict["finished"]:
                    self.__logOutput(self.tr(" Done.\n"))

            if self.__firstProgress:
                self.progressLabel.show()
                self.progressBar.show()
                self.__firstProgress = False

            return True

        return False

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        all_stdout = str(
            self.__process.readAllStandardOutput(),
            Preferences.getSystem("IOEncoding"),
            "replace",
        )
        all_stdout = all_stdout.replace("\x00", "")
        if self.__json:
            for stdout in all_stdout.splitlines():
                try:
                    jsonDict = json.loads(stdout.replace("\x00", "").strip())
                    if self.__setProgressValues(jsonDict, "fetch"):
                        # nothing to do anymore
                        pass
                    elif "progress" not in jsonDict:
                        if self.__bufferedStdout is None:
                            self.__bufferedStdout = stdout
                        else:
                            self.__bufferedStdout += stdout
                except (TypeError, ValueError):
                    if self.__bufferedStdout is None:
                        self.__bufferedStdout = stdout
                    else:
                        self.__bufferedStdout += stdout
        else:
            self.__logOutput(all_stdout)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        self.__process.setReadChannel(QProcess.ProcessChannel.StandardError)

        while self.__process.canReadLine():
            stderr = str(
                self.__process.readLine(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.__logError(stderr)

    def __logOutput(self, stdout):
        """
        Private method to log some output.

        @param stdout output string to log
        @type str
        """
        self.contents.insertPlainText(stdout)
        self.contents.ensureCursorVisible()

    def __logError(self, stderr):
        """
        Private method to log an error.

        @param stderr error string to log
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(stderr)
        self.errors.ensureCursorVisible()
