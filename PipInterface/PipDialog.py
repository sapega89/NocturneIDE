# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing the output of a pip command.
"""

from PyQt6.QtCore import QCoreApplication, QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox

from .Ui_PipDialog import Ui_PipDialog


class PipDialog(QDialog, Ui_PipDialog):
    """
    Class implementing a dialog showing the output of a 'python -m pip'
    command.
    """

    def __init__(self, text, parent=None):
        """
        Constructor

        @param text text to be shown by the label
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.proc = None
        self.__processQueue = []
        self.__ioEncoding = Preferences.getSystem("IOEncoding")

        self.outputGroup.setTitle(text)

        self.show()
        QCoreApplication.processEvents()

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        self.__cancel()
        e.accept()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        if (
            self.proc is not None
            and self.proc.state() != QProcess.ProcessState.NotRunning
        ):
            self.proc.terminate()
            QTimer.singleShot(2000, self.proc.kill)
            self.proc.waitForFinished(3000)

        self.proc = None

        if self.__processQueue:
            cmd, args = self.__processQueue.pop(0)
            self.__addOutput("\n\n")
            self.startProcess(cmd, args)
        else:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(
                True
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(
                False
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(
                True
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
                Qt.FocusReason.OtherFocusReason
            )

    def __cancel(self):
        """
        Private slot to cancel the current action.
        """
        self.__processQueue = []
        self.__finish()

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__cancel()

    @pyqtSlot(int, QProcess.ExitStatus)
    def __procFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        self.__finish()

    def startProcess(self, cmd, args, showArgs=True):
        """
        Public slot used to start the process.

        @param cmd name of the pip executable to be used
        @type str
        @param args list of arguments for the process
        @type list of str
        @param showArgs flag indicating to show the arguments
        @type bool
        @return flag indicating a successful start of the process
        @rtype bool
        """
        if len(self.errors.toPlainText()) == 0:
            self.errorGroup.hide()

        if showArgs:
            self.resultbox.append(cmd + " " + " ".join(args))
            self.resultbox.append("")

        self.proc = QProcess()
        self.proc.finished.connect(self.__procFinished)
        self.proc.readyReadStandardOutput.connect(self.__readStdout)
        self.proc.readyReadStandardError.connect(self.__readStderr)
        self.proc.start(cmd, args)
        procStarted = self.proc.waitForStarted(5000)
        if not procStarted:
            self.buttonBox.setFocus()
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr("The process {0} could not be started.").format(cmd),
            )
        return procStarted

    def startProcesses(self, processParams):
        """
        Public method to issue a list of commands to be executed.

        @param processParams list of tuples containing the command
            and arguments
        @type list of tuples of (str, list of str)
        @return flag indicating a successful start of the first process
        @rtype bool
        """
        if len(processParams) > 1:
            for cmd, args in processParams[1:]:
                self.__processQueue.append((cmd, args[:]))
        cmd, args = processParams[0]
        return self.startProcess(cmd, args)

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        if self.proc is not None:
            txt = str(self.proc.readAllStandardOutput(), self.__ioEncoding, "replace")
            self.__addOutput(txt)

    def __addOutput(self, txt):
        """
        Private method to add some text to the output pane.

        @param txt text to be added
        @type str
        """
        self.resultbox.insertPlainText(txt)
        self.resultbox.ensureCursorVisible()
        QCoreApplication.processEvents()

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.proc is not None:
            s = str(self.proc.readAllStandardError(), self.__ioEncoding, "replace")
            self.errorGroup.show()
            self.errors.insertPlainText(s)
            self.errors.ensureCursorVisible()

            QCoreApplication.processEvents()
