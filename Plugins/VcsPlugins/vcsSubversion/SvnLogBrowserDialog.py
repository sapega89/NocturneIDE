# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to browse the log history.
"""

import os
import re

from PyQt6.QtCore import QDate, QPoint, QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QHeaderView,
    QLineEdit,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursorProcess
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_SvnLogBrowserDialog import Ui_SvnLogBrowserDialog


class SvnLogBrowserDialog(QWidget, Ui_SvnLogBrowserDialog):
    """
    Class implementing a dialog to browse the log history.
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

        self.__position = QPoint()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.upButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.downButton.setIcon(EricPixmapCache.getIcon("1downarrow"))

        self.filesTree.headerItem().setText(self.filesTree.columnCount(), "")
        self.filesTree.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.vcs = vcs

        self.__initData()

        self.fromDate.setDisplayFormat("yyyy-MM-dd")
        self.toDate.setDisplayFormat("yyyy-MM-dd")
        self.__resetUI()

        self.__messageRole = Qt.ItemDataRole.UserRole
        self.__changesRole = Qt.ItemDataRole.UserRole + 1

        self.__process = EricOverrideCursorProcess()
        self.__process.finished.connect(self.__procFinished)
        self.__process.readyReadStandardOutput.connect(self.__readStdout)
        self.__process.readyReadStandardError.connect(self.__readStderr)

        self.rx_sep1 = re.compile("\\-+\\s*")
        self.rx_sep2 = re.compile("=+\\s*")
        self.rx_rev1 = re.compile(r"rev ([0-9]+):  ([^|]*) \| ([^|]*) \| ([0-9]+) .*")
        # "rev" followed by one or more decimals followed by a colon followed
        # anything up to " | " (twice) followed by one or more decimals
        # followed by anything
        self.rx_rev2 = re.compile(r"r([0-9]+) \| ([^|]*) \| ([^|]*) \| ([0-9]+) .*")
        # "r" followed by one or more decimals followed by " | " followed
        # anything up to " | " (twice) followed by one or more decimals
        # followed by anything
        self.rx_flags1 = re.compile(
            r"""   ([ADM])\s(.*)\s+\(\w+\s+(.*):([0-9]+)\)\s*"""
        )
        # three blanks followed by A or D or M followed by path followed by
        # path copied from followed by copied from revision
        self.rx_flags2 = re.compile("   ([ADM]) (.*)\\s*")
        # three blanks followed by A or D or M followed by path

        self.flags = {
            "A": self.tr("Added"),
            "D": self.tr("Deleted"),
            "M": self.tr("Modified"),
            "R": self.tr("Replaced"),
        }
        self.intercept = False

        self.__logTreeNormalFont = self.logTree.font()
        self.__logTreeNormalFont.setBold(False)
        self.__logTreeBoldFont = self.logTree.font()
        self.__logTreeBoldFont.setBold(True)

        self.__finishCallbacks = []

    def __addFinishCallback(self, callback):
        """
        Private method to add a method to be called once the process finished.

        The callback methods are invoke in a FIFO style and are consumed. If
        a callback method needs to be called again, it must be added again.

        @param callback callback method
        @type function
        """
        if callback not in self.__finishCallbacks:
            self.__finishCallbacks.append(callback)

    def __initData(self):
        """
        Private method to (re-)initialize some data.
        """
        self.__maxDate = QDate()
        self.__minDate = QDate()
        self.__filterLogsEnabled = True

        self.buf = []  # buffer for stdout
        self.diff = None
        self.__started = False
        self.__lastRev = 0

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if (
            self.__process is not None
            and self.__process.state() != QProcess.ProcessState.NotRunning
        ):
            self.__process.terminate()
            QTimer.singleShot(2000, self.__process.kill)
            self.__process.waitForFinished(3000)

        self.__position = self.pos()

        e.accept()

    def show(self):
        """
        Public slot to show the dialog.
        """
        if not self.__position.isNull():
            self.move(self.__position)
        self.__resetUI()

        super().show()

    def __resetUI(self):
        """
        Private method to reset the user interface.
        """
        self.fromDate.setDate(QDate.currentDate())
        self.toDate.setDate(QDate.currentDate())
        self.fieldCombo.setCurrentIndex(self.fieldCombo.findText(self.tr("Message")))
        self.limitSpinBox.setValue(self.vcs.getPlugin().getPreferences("LogLimit"))
        self.stopCheckBox.setChecked(
            self.vcs.getPlugin().getPreferences("StopLogOnCopy")
        )

        self.logTree.clear()

        self.nextButton.setEnabled(True)
        self.limitSpinBox.setEnabled(True)

    def __resizeColumnsLog(self):
        """
        Private method to resize the log tree columns.
        """
        self.logTree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.logTree.header().setStretchLastSection(True)

    def __resortLog(self):
        """
        Private method to resort the log tree.
        """
        self.logTree.sortItems(
            self.logTree.sortColumn(), self.logTree.header().sortIndicatorOrder()
        )

    def __resizeColumnsFiles(self):
        """
        Private method to resize the changed files tree columns.
        """
        self.filesTree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.filesTree.header().setStretchLastSection(True)

    def __resortFiles(self):
        """
        Private method to resort the changed files tree.
        """
        sortColumn = self.filesTree.sortColumn()
        self.filesTree.sortItems(1, self.filesTree.header().sortIndicatorOrder())
        self.filesTree.sortItems(
            sortColumn, self.filesTree.header().sortIndicatorOrder()
        )

    def __generateLogItem(self, author, date, message, revision, changedPaths):
        """
        Private method to generate a log tree entry.

        @param author author info
        @type str
        @param date date info
        @type str
        @param message text of the log message
        @type list of str
        @param revision revision info
        @type str
        @param changedPaths list of dictionary objects containing
            info about the changed files/directories
        @type dict
        @return reference to the generated item
        @rtype QTreeWidgetItem
        """
        msg = []
        for line in message:
            msg.append(line.strip())

        itm = QTreeWidgetItem(self.logTree)
        itm.setData(0, Qt.ItemDataRole.DisplayRole, int(revision))
        itm.setData(1, Qt.ItemDataRole.DisplayRole, author)
        itm.setData(2, Qt.ItemDataRole.DisplayRole, date)
        itm.setData(3, Qt.ItemDataRole.DisplayRole, " ".join(msg))

        itm.setData(0, self.__messageRole, message)
        itm.setData(0, self.__changesRole, changedPaths)

        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignLeft)
        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignLeft)
        itm.setTextAlignment(3, Qt.AlignmentFlag.AlignLeft)
        itm.setTextAlignment(4, Qt.AlignmentFlag.AlignLeft)

        try:
            self.__lastRev = int(revision)
        except ValueError:
            self.__lastRev = 0

        return itm

    def __generateFileItem(self, action, path, copyFrom, copyRev):
        """
        Private method to generate a changed files tree entry.

        @param action indicator for the change action ("A", "D" or "M")
        @type str
        @param path path of the file in the repository
        @type str
        @param copyFrom path the file was copied from
        @type str
        @param copyRev revision the file was copied from
        @type str
        @return reference to the generated item
        @rtype QTreeWidgetItem
        """
        itm = QTreeWidgetItem(
            self.filesTree,
            [
                self.flags[action],
                path,
                copyFrom,
                copyRev,
            ],
        )

        itm.setTextAlignment(3, Qt.AlignmentFlag.AlignRight)

        return itm

    def __getLogEntries(self, startRev=None):
        """
        Private method to retrieve log entries from the repository.

        @param startRev revision number to start from
        @type int or str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        QApplication.processEvents()

        self.intercept = False
        self.__process.kill()

        self.buf = []
        self.cancelled = False
        self.errors.clear()

        args = []
        args.append("log")
        self.vcs.addArguments(args, self.vcs.options["global"])
        self.vcs.addArguments(args, self.vcs.options["log"])
        args.append("--verbose")
        args.append("--limit")
        args.append("{0:d}".format(self.limitSpinBox.value()))
        if startRev is not None:
            args.append("--revision")
            args.append("{0}:0".format(startRev))
        if self.stopCheckBox.isChecked():
            args.append("--stop-on-copy")
        args.append(self.fname)

        self.__process.setWorkingDirectory(self.dname)

        self.inputGroup.setEnabled(True)
        self.inputGroup.show()

        self.__process.start("svn", args)
        procStarted = self.__process.waitForStarted(5000)
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

    def start(self, fn, isFile=False):
        """
        Public slot to start the svn log command.

        @param fn filename to show the log for
        @type str
        @param isFile flag indicating log for a file is to be shown
        @type bool
        """
        self.sbsCheckBox.setEnabled(isFile)
        self.sbsCheckBox.setVisible(isFile)

        self.errorGroup.hide()
        QApplication.processEvents()

        self.__initData()

        self.filename = fn
        self.dname, self.fname = self.vcs.splitPath(fn)

        self.activateWindow()
        self.raise_()

        self.logTree.clear()
        self.__started = True
        self.__getLogEntries()

    @pyqtSlot(int, QProcess.ExitStatus)
    def __procFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        self.__processBuffer()
        self.__finish()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed the
        button.
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

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()

        while self.__finishCallbacks:
            self.__finishCallbacks.pop(0)()

    def __processBuffer(self):
        """
        Private method to process the buffered output of the svn log command.
        """
        noEntries = 0
        log = {"message": []}
        changedPaths = []
        for s in self.buf:
            match = (
                self.rx_rev1.fullmatch(s)
                or self.rx_rev2.fullmatch(s)
                or self.rx_flags1.fullmatch(s)
                or self.rx_flags2.fullmatch(s)
                or self.rx_sep1.fullmatch(s)
                or self.rx_sep2.fullmatch(s)
            )
            if match is None:
                if s.strip().endswith(":") or not s.strip():
                    continue
                else:
                    log["message"].append(s)
            elif match.re is self.rx_rev1:
                log["revision"] = match.group(1)
                log["author"] = match.group(2)
                log["date"] = match.group(3)
                # number of lines is ignored
            elif match.re is self.rx_rev2:
                log["revision"] = match.group(1)
                log["author"] = match.group(2)
                log["date"] = " ".join(match.group(3).split()[:2])
                # number of lines is ignored
            elif match.re is self.rx_flags1:
                changedPaths.append(
                    {
                        "action": match.group(1).strip(),
                        "path": match.group(2).strip(),
                        "copyfrom_path": match.group(3).strip(),
                        "copyfrom_revision": match.group(4).strip(),
                    }
                )
            elif match.re is self.rx_flags2:
                changedPaths.append(
                    {
                        "action": match.group(1).strip(),
                        "path": match.group(2).strip(),
                        "copyfrom_path": "",
                        "copyfrom_revision": "",
                    }
                )
            elif (match.re is self.rx_sep1 or match.re is self.rx_sep2) and len(
                log
            ) > 1:
                self.__generateLogItem(
                    log["author"],
                    log["date"],
                    log["message"],
                    log["revision"],
                    changedPaths,
                )
                dt = QDate.fromString(log["date"], Qt.DateFormat.ISODate)
                if not self.__maxDate.isValid() and not self.__minDate.isValid():
                    self.__maxDate = dt
                    self.__minDate = dt
                else:
                    if self.__maxDate < dt:
                        self.__maxDate = dt
                    if self.__minDate > dt:
                        self.__minDate = dt
                noEntries += 1
                log = {"message": []}
                changedPaths = []

        self.__resizeColumnsLog()
        self.__resortLog()

        if self.__started:
            self.logTree.setCurrentItem(self.logTree.topLevelItem(0))
            self.__started = False

        if noEntries < self.limitSpinBox.value() and not self.cancelled:
            self.nextButton.setEnabled(False)
            self.limitSpinBox.setEnabled(False)

        self.__filterLogsEnabled = False
        self.fromDate.setMinimumDate(self.__minDate)
        self.fromDate.setMaximumDate(self.__maxDate)
        self.fromDate.setDate(self.__minDate)
        self.toDate.setMinimumDate(self.__minDate)
        self.toDate.setMaximumDate(self.__maxDate)
        self.toDate.setDate(self.__maxDate)
        self.__filterLogsEnabled = True
        self.__filterLogs()

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process and inserts it into a buffer.
        """
        self.__process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        while self.__process.canReadLine():
            line = str(
                self.__process.readLine(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.buf.append(line)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.__process is not None:
            self.errorGroup.show()
            s = str(
                self.__process.readAllStandardError(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.errors.insertPlainText(s)
            self.errors.ensureCursorVisible()

    def __diffRevisions(self, rev1, rev2):
        """
        Private method to do a diff of two revisions.

        @param rev1 first revision number
        @type int
        @param rev2 second revision number
        @type int
        """
        from .SvnDiffDialog import SvnDiffDialog

        if self.sbsCheckBox.isEnabled() and self.sbsCheckBox.isChecked():
            self.vcs.vcsSbsDiff(self.filename, revisions=(str(rev1), str(rev2)))
        else:
            if self.diff is None:
                self.diff = SvnDiffDialog(self.vcs)
            self.diff.show()
            self.diff.raise_()
            self.diff.start(self.filename, [rev1, rev2])

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.cancelled = True
            self.__finish()

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_logTree_currentItemChanged(self, current, previous):
        """
        Private slot called, when the current item of the log tree changes.

        @param current reference to the new current item
        @type QTreeWidgetItem
        @param previous reference to the old current item
        @type QTreeWidgetItem
        """
        if current is not None:
            self.messageEdit.clear()
            for line in current.data(0, self.__messageRole):
                self.messageEdit.append(line.strip())

            self.filesTree.clear()
            changes = current.data(0, self.__changesRole)
            if len(changes) > 0:
                for change in changes:
                    self.__generateFileItem(
                        change["action"],
                        change["path"],
                        change["copyfrom_path"],
                        change["copyfrom_revision"],
                    )
                self.__resizeColumnsFiles()
            self.__resortFiles()

        self.diffPreviousButton.setEnabled(
            current != self.logTree.topLevelItem(self.logTree.topLevelItemCount() - 1)
        )

        # Highlight the current entry using a bold font
        for col in range(self.logTree.columnCount()):
            current and current.setFont(col, self.__logTreeBoldFont)
            previous and previous.setFont(col, self.__logTreeNormalFont)

        # set the state of the up and down buttons
        self.upButton.setEnabled(
            current is not None and self.logTree.indexOfTopLevelItem(current) > 0
        )
        self.downButton.setEnabled(current is not None and int(current.text(0)) > 1)

    @pyqtSlot()
    def on_logTree_itemSelectionChanged(self):
        """
        Private slot called, when the selection has changed.
        """
        self.diffRevisionsButton.setEnabled(len(self.logTree.selectedItems()) == 2)

    @pyqtSlot()
    def on_nextButton_clicked(self):
        """
        Private slot to handle the Next button.
        """
        if self.__lastRev > 1:
            self.__getLogEntries(self.__lastRev - 1)

    @pyqtSlot()
    def on_diffPreviousButton_clicked(self):
        """
        Private slot to handle the Diff to Previous button.
        """
        itm = self.logTree.currentItem()
        if itm is None:
            self.diffPreviousButton.setEnabled(False)
            return
        rev2 = int(itm.text(0))

        itm = self.logTree.topLevelItem(self.logTree.indexOfTopLevelItem(itm) + 1)
        if itm is None:
            self.diffPreviousButton.setEnabled(False)
            return
        rev1 = int(itm.text(0))

        self.__diffRevisions(rev1, rev2)

    @pyqtSlot()
    def on_diffRevisionsButton_clicked(self):
        """
        Private slot to handle the Compare Revisions button.
        """
        items = self.logTree.selectedItems()
        if len(items) != 2:
            self.diffRevisionsButton.setEnabled(False)
            return

        rev2 = int(items[0].text(0))
        rev1 = int(items[1].text(0))

        self.__diffRevisions(min(rev1, rev2), max(rev1, rev2))

    @pyqtSlot(QDate)
    def on_fromDate_dateChanged(self, _date):
        """
        Private slot called, when the from date changes.

        @param _date new date (unused)
        @type QDate
        """
        self.__filterLogs()

    @pyqtSlot(QDate)
    def on_toDate_dateChanged(self, _date):
        """
        Private slot called, when the from date changes.

        @param _date new date (unused)
        @type QDate
        """
        self.__filterLogs()

    @pyqtSlot(int)
    def on_fieldCombo_activated(self, _index):
        """
        Private slot called, when a new filter field is selected.

        @param _index index of the selected entry (unused)
        @type int
        """
        self.__filterLogs()

    @pyqtSlot(str)
    def on_rxEdit_textChanged(self, _txt):
        """
        Private slot called, when a filter expression is entered.

        @param _txt filter expression
        @type str
        """
        self.__filterLogs()

    def __filterLogs(self):
        """
        Private method to filter the log entries.
        """
        if self.__filterLogsEnabled:
            from_ = self.fromDate.date().toString("yyyy-MM-dd")
            to_ = self.toDate.date().addDays(1).toString("yyyy-MM-dd")
            txt = self.fieldCombo.currentText()
            if txt == self.tr("Author"):
                fieldIndex = 1
                searchRx = re.compile(self.rxEdit.text(), re.IGNORECASE)
            elif txt == self.tr("Revision"):
                fieldIndex = 0
                txt = self.rxEdit.text()
                if txt.startswith("^"):
                    searchRx = re.compile(r"^\s*{0}".format(txt[1:]), re.IGNORECASE)
                else:
                    searchRx = re.compile(txt, re.IGNORECASE)
            else:
                fieldIndex = 3
                searchRx = re.compile(self.rxEdit.text(), re.IGNORECASE)

            currentItem = self.logTree.currentItem()
            for topIndex in range(self.logTree.topLevelItemCount()):
                topItem = self.logTree.topLevelItem(topIndex)
                if (
                    topItem.text(2) <= to_
                    and topItem.text(2) >= from_
                    and searchRx.match(topItem.text(fieldIndex)) is not None
                ):
                    topItem.setHidden(False)
                    if topItem is currentItem:
                        self.on_logTree_currentItemChanged(topItem, None)
                else:
                    topItem.setHidden(True)
                    if topItem is currentItem:
                        self.messageEdit.clear()
                        self.filesTree.clear()

    @pyqtSlot(bool)
    def on_stopCheckBox_clicked(self, _checked):
        """
        Private slot called, when the stop on copy/move checkbox is clicked.

        @param _checked flag indicating the checked state (unused)
        @type bool
        """
        self.vcs.getPlugin().setPreferences(
            "StopLogOnCopy", self.stopCheckBox.isChecked()
        )
        self.nextButton.setEnabled(True)
        self.limitSpinBox.setEnabled(True)

    @pyqtSlot()
    def on_upButton_clicked(self):
        """
        Private slot to move the current item up one entry.
        """
        itm = self.logTree.itemAbove(self.logTree.currentItem())
        if itm:
            self.logTree.setCurrentItem(itm)

    @pyqtSlot()
    def on_downButton_clicked(self):
        """
        Private slot to move the current item down one entry.
        """
        itm = self.logTree.itemBelow(self.logTree.currentItem())
        if itm:
            self.logTree.setCurrentItem(itm)
        else:
            # load the next bunch and try again
            self.__addFinishCallback(self.on_downButton_clicked)
            self.on_nextButton_clicked()

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
        self.errorGroup.show()

        self.__process.write(strToQByteArray(inputTxt))

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
