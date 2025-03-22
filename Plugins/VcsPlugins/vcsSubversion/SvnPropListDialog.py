# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the svn proplist command
process.
"""

import re

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QDialogButtonBox, QHeaderView, QTreeWidgetItem, QWidget

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox

from .Ui_SvnPropListDialog import Ui_SvnPropListDialog


class SvnPropListDialog(QWidget, Ui_SvnPropListDialog):
    """
    Class implementing a dialog to show the output of the svn proplist command
    process.
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

        self.refreshButton = self.buttonBox.addButton(
            self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(
            self.tr("Press to refresh the properties display")
        )
        self.refreshButton.setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.process = QProcess()
        env = QProcessEnvironment.systemEnvironment()
        env.insert("LANG", "C")
        self.process.setProcessEnvironment(env)
        self.vcs = vcs

        self.propsList.headerItem().setText(self.propsList.columnCount(), "")
        self.propsList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.process.finished.connect(self.__procFinished)
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)

        self.rx_path = re.compile(r"Properties on '([^']+)':\s*")
        self.rx_prop = re.compile(r"  (.*) *: *(.*)[\r\n]")

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.propsList.sortItems(
            self.propsList.sortColumn(), self.propsList.header().sortIndicatorOrder()
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.propsList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.propsList.header().setStretchLastSection(True)

    def __generateItem(self, path, propName, propValue):
        """
        Private method to generate a properties item in the properties list.

        @param path file/directory name the property applies to
        @type str
        @param propName name of the property
        @type str
        @param propValue value of the property
        @type str
        """
        QTreeWidgetItem(self.propsList, [path, propName, propValue.strip()])

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        ):
            self.process.terminate()
            QTimer.singleShot(2000, self.process.kill)
            self.process.waitForFinished(3000)

        e.accept()

    def start(self, fn, recursive=False):
        """
        Public slot to start the svn status command.

        @param fn filename(s)
        @type str or list of str
        @param recursive flag indicating a recursive list is requested
        @type bool
        """
        self.errorGroup.hide()

        self.propsList.clear()
        self.lastPath = None
        self.lastProp = None
        self.propBuffer = ""

        self.__args = fn
        self.__recursive = recursive

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        self.refreshButton.setEnabled(False)

        self.process.kill()

        args = []
        args.append("proplist")
        self.vcs.addArguments(args, self.vcs.options["global"])
        args.append("--verbose")
        if recursive:
            args.append("--recursive")
        if isinstance(fn, list):
            dname, fnames = self.vcs.splitPathList(fn)
            self.vcs.addArguments(args, fnames)
        else:
            dname, fname = self.vcs.splitPath(fn)
            args.append(fname)

        self.process.setWorkingDirectory(dname)

        self.process.start("svn", args)
        procStarted = self.process.waitForStarted(5000)
        if not procStarted:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("svn"),
            )

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

        self.refreshButton.setEnabled(True)

        if self.lastProp:
            self.__generateItem(self.lastPath, self.lastProp, self.propBuffer)

        self.__resort()
        self.__resizeColumns()

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
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the status display.
        """
        self.start(self.__args, recursive=self.__recursive)

    @pyqtSlot(int, QProcess.ExitStatus)
    def __procFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        if self.lastPath is None:
            self.__generateItem("", "None", "")

        self.__finish()

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
            match = self.rx_path.fullmatch(s) or self.rx_prop.fullmatch(s)
            if match is None:
                self.propBuffer += " "
                self.propBuffer += s
            elif match.re is self.rx_path:
                if self.lastProp:
                    self.__generateItem(self.lastPath, self.lastProp, self.propBuffer)
                self.lastPath = match.group(1)
                self.lastProp = None
                self.propBuffer = ""
            elif match.re is self.rx_prop:
                if self.lastProp:
                    self.__generateItem(self.lastPath, self.lastProp, self.propBuffer)
                self.lastProp = match.group(1)
                self.propBuffer = match.group(2)

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
