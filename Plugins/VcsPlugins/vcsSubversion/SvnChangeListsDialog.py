# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to browse the change lists.
"""

import os
import re

from PyQt6.QtCore import QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QListWidgetItem

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_SvnChangeListsDialog import Ui_SvnChangeListsDialog


class SvnChangeListsDialog(QDialog, Ui_SvnChangeListsDialog):
    """
    Class implementing a dialog to browse the change lists.
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
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.vcs = vcs

        self.process = QProcess()
        self.process.finished.connect(self.__procFinished)
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)

        self.rx_status = re.compile(
            "(.{8,9})\\s+([0-9-]+)\\s+([0-9?]+)\\s+(\\S+)\\s+(.+)\\s*"
        )
        # flags (8 or 9 anything), revision, changed rev, author, path
        self.rx_status2 = re.compile("(.{8,9})\\s+(.+)\\s*")
        # flags (8 or 9 anything), path
        self.rx_changelist = re.compile("--- \\S+ .([\\w\\s]+).:\\s+")
        # three dashes, Changelist (translated), quote,
        # changelist name, quote, :

    @pyqtSlot(QListWidgetItem, QListWidgetItem)
    def on_changeLists_currentItemChanged(self, current, _previous):
        """
        Private slot to handle the selection of a new item.

        @param current current item
        @type QListWidgetItem
        @param _previous previous current item (unused)
        @type QListWidgetItem
        """
        self.filesList.clear()
        if current is not None:
            changelist = current.text()
            if changelist in self.changeListsDict:
                self.filesList.addItems(sorted(self.changeListsDict[changelist]))

    def start(self, path):
        """
        Public slot to populate the data.

        @param path directory name to show change lists for
        @type str
        """
        self.changeListsDict = {}

        self.filesLabel.setText(self.tr("Files (relative to {0}):").format(path))

        self.errorGroup.hide()
        self.intercept = False

        self.path = path
        self.currentChangelist = ""

        args = []
        args.append("status")
        self.vcs.addArguments(args, self.vcs.options["global"])
        self.vcs.addArguments(args, self.vcs.options["status"])
        if (
            "--verbose" not in self.vcs.options["global"]
            and "--verbose" not in self.vcs.options["status"]
        ):
            args.append("--verbose")
        if isinstance(path, list):
            self.dname, fnames = self.vcs.splitPathList(path)
            self.vcs.addArguments(args, fnames)
        else:
            self.dname, fname = self.vcs.splitPath(path)
            args.append(fname)

        self.process.setWorkingDirectory(self.dname)

        self.process.start("svn", args)
        procStarted = self.process.waitForStarted(5000)
        if not procStarted:
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

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()

        if len(self.changeListsDict) == 0:
            self.changeLists.addItem(self.tr("No change lists found"))
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
                Qt.FocusReason.OtherFocusReason
            )
        else:
            self.changeLists.addItems(sorted(self.changeListsDict))
            self.changeLists.setCurrentRow(0)
            self.changeLists.setFocus(Qt.FocusReason.OtherFocusReason)

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

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        if self.process is not None:
            self.process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

            while self.process.canReadLine():
                s = str(
                    self.process.readLine(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )
                match = self.rx_status.fullmatch(s) or self.rx_status2.fullmatch(s)
                if self.currentChangelist != "" and match is not None:
                    if match.re is self.rx_status:
                        file = match.group(5).strip()
                        filename = file.replace(self.path + os.sep, "")
                        if filename not in self.changeListsDict[self.currentChangelist]:
                            self.changeListsDict[self.currentChangelist].append(
                                filename
                            )
                    else:
                        file = match.group(2).strip()
                        filename = file.replace(self.path + os.sep, "")
                        if filename not in self.changeListsDict[self.currentChangelist]:
                            self.changeListsDict[self.currentChangelist].append(
                                filename
                            )
                else:
                    match = self.rx_changelist.fullmatch(s)
                    if match is not None:
                        self.currentChangelist = match.group(1)
                        if self.currentChangelist not in self.changeListsDict:
                            self.changeListsDict[self.currentChangelist] = []

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

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
