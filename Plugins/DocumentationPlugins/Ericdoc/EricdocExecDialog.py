# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the ericdoc process.
"""

import os.path

from PyQt6.QtCore import QProcess, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox

from .Ui_EricdocExecDialog import Ui_EricdocExecDialog


class EricdocExecDialog(QDialog, Ui_EricdocExecDialog):
    """
    Class implementing a dialog to show the output of the ericdoc process.

    This class starts a QProcess and displays a dialog that
    shows the output of the documentation command process.

    @signal processFinished() emitted to indicate the eric7_doc process finished
    """

    processFinished = pyqtSignal()

    def __init__(self, cmdname, parent=None):
        """
        Constructor

        @param cmdname name of the documentation generator
        @type str
        @param parent parent widget of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.process = None
        self.cmdname = cmdname

    def start(self, args, fn):
        """
        Public slot to start the ericdoc command.

        @param args commandline arguments for ericdoc program
        @type list of str
        @param fn filename or dirname to be processed by ericdoc program
        @type str
        @return flag indicating the successful start of the process
        @rtype bool
        """
        self.errorGroup.hide()

        self.filename = fn
        if os.path.isdir(self.filename):
            dname = os.path.abspath(self.filename)
            fname = "."
            if os.path.exists(os.path.join(dname, "__init__.py")):
                fname = os.path.basename(dname)
                dname = os.path.dirname(dname)
        else:
            dname = os.path.dirname(self.filename)
            fname = os.path.basename(self.filename)

        self.contents.clear()
        self.errors.clear()

        program = args[0]
        del args[0]
        args.append(fname)

        self.process = QProcess()
        self.process.setWorkingDirectory(dname)

        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)
        self.process.finished.connect(self.__finish)

        self.setWindowTitle(self.tr("{0} - {1}").format(self.cmdname, self.filename))
        self.process.start(program, args)
        procStarted = self.process.waitForStarted(5000)
        if not procStarted:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format(program),
            )
        return procStarted

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.accept()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__finish()

    def __finish(self):
        """
        Private slot called when the process finished.

        It is called when the process finished or
        the user pressed the button.
        """
        if self.process is not None:
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.terminate()
                QTimer.singleShot(2000, self.process.kill)
                self.process.waitForFinished(3000)
            if self.process.exitStatus() == QProcess.ExitStatus.CrashExit:
                self.contents.insertPlainText(
                    self.tr("\n{0} crashed.\n").format(self.cmdname)
                )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.process = None

        self.contents.insertPlainText(self.tr("\n{0} finished.\n").format(self.cmdname))
        self.contents.ensureCursorVisible()

        self.processFinished.emit()

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        self.process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        while self.process.canReadLine():
            s = str(
                self.process.readLine(), Preferences.getSystem("IOEncoding"), "replace"
            )
            self.contents.insertPlainText(s)
            self.contents.ensureCursorVisible()

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        self.process.setReadChannel(QProcess.ProcessChannel.StandardError)

        while self.process.canReadLine():
            self.errorGroup.show()
            s = str(
                self.process.readLine(), Preferences.getSystem("IOEncoding"), "replace"
            )
            self.errors.insertPlainText(s)
            self.errors.ensureCursorVisible()
