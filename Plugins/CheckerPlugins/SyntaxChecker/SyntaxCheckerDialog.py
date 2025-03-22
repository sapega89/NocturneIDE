# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a simple Python syntax checker.
"""

import fnmatch
import os
import time

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidgetItem,
)

from eric7 import Utilities
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_SyntaxCheckerDialog import Ui_SyntaxCheckerDialog


class SyntaxCheckerDialog(QDialog, Ui_SyntaxCheckerDialog):
    """
    Class implementing a dialog to display the results of a syntax check run.
    """

    filenameRole = Qt.ItemDataRole.UserRole + 1
    lineRole = Qt.ItemDataRole.UserRole + 2
    indexRole = Qt.ItemDataRole.UserRole + 3
    errorRole = Qt.ItemDataRole.UserRole + 4
    warningRole = Qt.ItemDataRole.UserRole + 5

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.showButton = self.buttonBox.addButton(
            self.tr("Show"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.showButton.setToolTip(
            self.tr("Press to show all files containing an issue")
        )
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.resultList.headerItem().setText(self.resultList.columnCount(), "")
        self.resultList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.noResults = True
        self.cancelled = False
        self.__lastFileItem = None
        self.__batch = False
        self.__finished = True
        self.__errorItem = None
        self.__timenow = time.monotonic()

        self.__fileList = []
        self.__project = None
        self.__arguments = ()
        self.__statistics = self.__defaultStatistics()
        self.filterFrame.setVisible(False)

        self.checkProgress.setVisible(False)

        try:
            self.syntaxCheckService = ericApp().getObject("SyntaxCheckService")
            self.syntaxCheckService.syntaxChecked.connect(self.__processResult)
            self.syntaxCheckService.batchFinished.connect(self.__batchFinished)
            self.syntaxCheckService.error.connect(self.__processError)
        except KeyError:
            self.syntaxCheckService = None
        self.filename = None

        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.resultList.sortItems(
            self.resultList.sortColumn(), self.resultList.header().sortIndicatorOrder()
        )

    def __defaultStatistics(self):
        """
        Private method to return the default statistics entry.

        @return dictionary with default statistics entry
        @rtype dict
        """
        return {
            "files_checked": 0,
            "files_issues": 0,
            "errors": 0,
            "py_warnings": 0,
            "warnings": 0,
        }

    def __updateStatistics(self, fileStatistics):
        """
        Private method to update the statistics.

        @param fileStatistics dictionary containing the file statistics
        @type dict
        """
        self.__statistics["files_checked"] += 1
        if any(fileStatistics.values()):
            self.__statistics["files_issues"] += 1
        self.__statistics["errors"] += fileStatistics["errors"]
        self.__statistics["py_warnings"] += fileStatistics["py_warnings"]
        self.__statistics["warnings"] += fileStatistics["warnings"]

    def __resetStatistics(self, skipped):
        """
        Private method to reset the statistics data.

        @param skipped number of files not being checked
        @type int
        """
        self.__statistics["files_checked"] = 0
        self.__statistics["files_skipped"] = skipped
        self.__statistics["files_issues"] = 0
        self.__statistics["errors"] = 0
        self.__statistics["py_warnings"] = 0
        self.__statistics["warnings"] = 0

    def __createFileStatistics(self, problems):
        """
        Private method to return the file statistics entry.

        @param problems dictionary with the keys 'error', 'py_warnings' and
            'warnings' which hold a list of issues each
        @type dict
        @return dictionary with the file statistics
        @rtype dict
        """
        return {
            "errors": 1 if problems.get("error") else 0,
            "py_warnings": len(problems.get("py_warnings", [])),
            "warnings": len(problems.get("warnings", [])),
        }

    def __createErrorItem(self, filename, message):
        """
        Private slot to create a new error item in the result list.

        @param filename name of the file
        @type str
        @param message error message
        @type str
        """
        if self.__errorItem is None:
            self.__errorItem = QTreeWidgetItem(self.resultList, [self.tr("Errors")])
            self.__errorItem.setExpanded(True)
            self.__errorItem.setForeground(0, Qt.GlobalColor.red)

        msg = "{0} ({1})".format(self.__project.getRelativePath(filename), message)
        if not self.resultList.findItems(msg, Qt.MatchFlag.MatchExactly):
            itm = QTreeWidgetItem(self.__errorItem, [msg])
            itm.setForeground(0, Qt.GlobalColor.red)
            itm.setFirstColumnSpanned(True)
            itm.setData(0, self.filenameRole, filename)

    def __createHeaderItem(self, filename, fileStatistics=None):
        """
        Private method to create a header item in the result list.

        @param filename file name of file
        @type str
        @param fileStatistics dictionary containing statistical data of the check
            result (defaults to None)
        @type dict (optional)
        """
        itemText = self.__project.getRelativePath(filename)

        if fileStatistics:
            statisticsTextList = []
            if fileStatistics["errors"]:
                statisticsTextList.append(
                    self.tr("Errors: {0}").format(fileStatistics["errors"])
                )
            if fileStatistics["py_warnings"]:
                statisticsTextList.append(
                    self.tr("Python Warnings: {0}").format(
                        fileStatistics["py_warnings"]
                    )
                )
            if fileStatistics["warnings"]:
                statisticsTextList.append(
                    self.tr("Warnings: {0}").format(fileStatistics["warnings"])
                )
            if statisticsTextList:
                itemText += "{0}\n{1}".format(itemText, ", ".join(statisticsTextList))

        self.__lastFileItem = QTreeWidgetItem(self.resultList, [itemText])
        self.__lastFileItem.setFirstColumnSpanned(True)
        self.__lastFileItem.setExpanded(True)
        self.__lastFileItem.setData(0, self.filenameRole, filename)

    def __createResultItem(
        self, filename, line, index, error, sourcecode, isWarning=False
    ):
        """
        Private method to create an entry in the result list.

        @param filename file name of file
        @type str
        @param line line number of faulty source
        @type int or str
        @param index index number of fault
        @type int
        @param error error text
        @type str
        @param sourcecode faulty line of code
        @type str
        @param isWarning flag indicating a warning message
        @type bool
        """
        if (
            self.__lastFileItem is None
            or self.__lastFileItem.data(0, self.filenameRole) != filename
        ):
            # It's a new file
            self.__createHeaderItem(filename)

        itm = QTreeWidgetItem(self.__lastFileItem)
        if isWarning:
            itm.setIcon(0, EricPixmapCache.getIcon("warning"))
        else:
            itm.setIcon(0, EricPixmapCache.getIcon("syntaxError"))
        itm.setData(0, Qt.ItemDataRole.DisplayRole, line)
        itm.setData(1, Qt.ItemDataRole.DisplayRole, error)
        itm.setData(2, Qt.ItemDataRole.DisplayRole, sourcecode)
        itm.setData(0, self.filenameRole, filename)
        itm.setData(0, self.lineRole, int(line))
        itm.setData(0, self.indexRole, index)
        itm.setData(0, self.errorRole, error)
        itm.setData(0, self.warningRole, isWarning)

    def setArguments(self, args):
        """
        Public method to set additional arguments to be used by the syntax check.

        @param args tuple containing the additional arguments
        @type tuple of Any
        """
        self.__arguments = args

    def prepare(self, fileList, project):
        """
        Public method to prepare the dialog with a list of filenames.

        @param fileList list of filenames
        @type list of str
        @param project reference to the project object
        @type Project
        """
        self.__fileList = fileList[:]
        self.__project = project

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.filterFrame.setVisible(True)

        self.__data = self.__project.getData("CHECKERSPARMS", "SyntaxChecker")
        if self.__data is None or "ExcludeFiles" not in self.__data:
            self.__data = {"ExcludeFiles": ""}
        if "AdditionalBuiltins" not in self.__data:
            self.__data["AdditionalBuiltins"] = ""

        self.excludeFilesEdit.setText(self.__data["ExcludeFiles"])
        self.builtinsEdit.setText(self.__data["AdditionalBuiltins"])

    def startForBrowser(self, fn):
        """
        Public slot to start the syntax check for the project sources browser.

        @param fn file or list of files or directory to be checked
        @type str or list of str
        """
        isdir = isinstance(fn, str) and (
            self.__remotefsInterface.isdir(fn)
            if FileSystemUtilities.isRemoteFileName(fn)
            else os.path.isdir(fn)
        )

        if isinstance(fn, list):
            files = fn
        elif isdir:
            if FileSystemUtilities.isRemoteFileName(fn):
                files = self.__remotefsInterface.direntries(
                    fn,
                    filesonly=True,
                    pattern=[
                        "*{0}".format(ext)
                        for ext in self.syntaxCheckService.getExtensions()
                    ],
                    followsymlinks=False,
                )
            else:
                files = FileSystemUtilities.direntries(
                    fn,
                    filesonly=True,
                    pattern=[
                        "*{0}".format(ext)
                        for ext in self.syntaxCheckService.getExtensions()
                    ],
                    followsymlinks=False,
                )
        else:
            files = [fn]

        if files:
            if self.__project is None:
                self.__project = ericApp().getObject("Project")

            self.__fileList = files[:]

            self.filterFrame.setVisible(True)

            self.__data = self.__project.getData("CHECKERSPARMS", "SyntaxChecker")
            if self.__data is None or "ExcludeFiles" not in self.__data:
                self.__data = {"ExcludeFiles": ""}
            if "AdditionalBuiltins" not in self.__data:
                self.__data["AdditionalBuiltins"] = ""

            self.excludeFilesEdit.setText(self.__data["ExcludeFiles"])
            self.builtinsEdit.setText(self.__data["AdditionalBuiltins"])

            self.on_startButton_clicked()  # press the start button

    def start(self, fn, codestring="", skipped=0):
        """
        Public slot to start the syntax check.

        @param fn file or list of files or directory to be checked
        @type str or list of str
        @param codestring string containing the code to be checked. If this is given,
            fn must be a single file name.
        @type str
        @param skipped number of files not being checked
        @type int
        """
        self.__batch = False

        if self.syntaxCheckService is not None:
            if self.__project is None:
                self.__project = ericApp().getObject("Project")

            self.cancelled = False
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(
                False
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(
                True
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(
                True
            )
            self.showButton.setEnabled(False)
            self.checkProgress.setVisible(True)
            QApplication.processEvents()

            isdir = isinstance(fn, str) and (
                self.__remotefsInterface.isdir(fn)
                if FileSystemUtilities.isRemoteFileName(fn)
                else os.path.isdir(fn)
            )

            if isinstance(fn, list):
                self.files = fn
            elif isdir:
                self.files = []
                for ext in self.syntaxCheckService.getExtensions():
                    self.files.extend(
                        self.__remotefsInterface.direntries(
                            fn, True, "*{0}".format(ext), False
                        )
                        if FileSystemUtilities.isRemoteFileName(fn)
                        else FileSystemUtilities.direntries(
                            fn, True, "*{0}".format(ext), False
                        )
                    )
            else:
                self.files = [fn]

            self.__errorItem = None
            self.__clearErrors(self.files)
            self.__resetStatistics(skipped)

            if codestring or len(self.files) > 0:
                self.checkProgress.setMaximum(max(1, len(self.files)))
                self.checkProgress.setVisible(len(self.files) > 1)
                QApplication.processEvents()

                # now go through all the files
                self.progress = 0
                self.files.sort()
                self.__timenow = time.monotonic()
                if codestring or len(self.files) == 1:
                    self.__batch = False
                    self.check(codestring)
                else:
                    self.__batch = True
                    self.checkBatch()

    def check(self, codestring=""):
        """
        Public method to start a check for one file.

        The results are reported to the __processResult slot.

        @param codestring optional sourcestring
        @type str
        """
        if self.syntaxCheckService is None or not self.files:
            self.checkProgress.setMaximum(1)
            self.checkProgress.setValue(1)
            self.__finish()
            return

        self.filename = self.files.pop(0)
        self.checkProgress.setValue(self.progress)
        QApplication.processEvents()
        self.__resort()

        if self.cancelled:
            return

        self.__lastFileItem = None
        self.__finished = False

        if codestring:
            self.source = Utilities.normalizeCode(codestring)
        else:
            try:
                if FileSystemUtilities.isRemoteFileName(self.filename):
                    self.source = self.__remotefsInterface.readEncodedFile(
                        self.filename
                    )[0]
                else:
                    self.source = Utilities.readEncodedFile(self.filename)[0]
                self.source = Utilities.normalizeCode(self.source)
            except (OSError, UnicodeError) as msg:
                self.noResults = False
                self.__createResultItem(
                    self.filename,
                    1,
                    0,
                    self.tr("Error: {0}").format(str(msg)).rstrip(),
                    "",
                )
                self.progress += 1
                # Continue with next file
                self.check()
                return

        self.syntaxCheckService.syntaxCheck(
            None, self.filename, self.source, *self.__arguments
        )

    def checkBatch(self):
        """
        Public method to start a style check batch job.

        The results are reported to the __processResult slot.
        """
        self.__lastFileItem = None
        self.__finished = False

        argumentsList = []
        for progress, filename in enumerate(self.files, start=1):
            self.checkProgress.setValue(progress)
            if time.monotonic() - self.__timenow > 0.01:
                QApplication.processEvents()
                self.__timenow = time.monotonic()

            try:
                source = (
                    self.__remotefsInterface.readEncodedFile(filename)[0]
                    if FileSystemUtilities.isRemoteFileName(filename)
                    else Utilities.readEncodedFile(filename)[0]
                )
                source = Utilities.normalizeCode(source)
            except (OSError, UnicodeError) as msg:
                self.noResults = False
                self.__createResultItem(
                    self.filename,
                    1,
                    0,
                    self.tr("Error: {0}").format(str(msg)).rstrip(),
                    "",
                )
                continue

            argumentsList.append((filename, source, *self.__arguments))

        # reset the progress bar to the checked files
        self.checkProgress.setValue(self.progress)
        QApplication.processEvents()

        self.syntaxCheckService.syntaxBatchCheck(argumentsList)

    def __batchFinished(self):
        """
        Private slot handling the completion of a batch job.
        """
        self.checkProgress.setMaximum(1)
        self.checkProgress.setValue(1)
        self.__finish()

    def __processError(self, fn, msg):
        """
        Private slot to process an error indication from the service.

        @param fn filename of the file
        @type str
        @param msg error message
        @type str
        """
        self.__createErrorItem(fn, msg)

        if not self.__batch:
            self.check()

    def __processResult(self, fn, problems):
        """
        Private slot to display the reported messages.

        @param fn filename of the checked file
        @type str
        @param problems list of dictionaries with the keys 'error', 'py_warnings' and
            'warnings' which contain a tuple with details about the syntax error or a
            list of tuples with details about Python warnings and PyFlakes warnings.
            Each tuple contains the file name, line number, column, code string (only
            for syntax errors), the message and an optional list with arguments for
            the message.
        @type list of dict
        """
        if self.__finished:
            return

        # Check if it's the requested file, otherwise ignore signal if not
        # in batch mode
        if not self.__batch and fn != self.filename:
            return

        fileStatistics = self.__createFileStatistics(problems)
        self.__updateStatistics(fileStatistics)
        if any(fileStatistics.values()):
            self.__createHeaderItem(fn, fileStatistics)

            error = problems.get("error")
            if error:
                self.noResults = False
                filename, lineno, col, code, msg = error
                self.__createResultItem(filename, lineno, col, msg, code, False)

            warnings = problems.get("py_warnings", []) + problems.get("warnings", [])
            if warnings:
                if self.__batch:
                    try:
                        source = Utilities.readEncodedFile(fn)[0]
                        source = Utilities.normalizeCode(source)
                        source = source.splitlines()
                    except (OSError, UnicodeError):
                        source = ""
                else:
                    source = self.source.splitlines()
                for filename, lineno, col, _code, msg in warnings:
                    self.noResults = False
                    if source:
                        try:
                            src_line = source[lineno - 1].strip()
                        except IndexError:
                            src_line = ""
                    else:
                        src_line = ""
                    self.__createResultItem(filename, lineno, col, msg, src_line, True)

        self.progress += 1
        self.checkProgress.setValue(self.progress)
        if time.monotonic() - self.__timenow > 0.01:
            QApplication.processEvents()
            self.__timenow = time.monotonic()
        self.__resort()

        if not self.__batch:
            self.check()

    def __updateStatisticsArea(self):
        """
        Private method to update the statistics area of the dialog.
        """
        self.totalLabel.setText(
            str(self.__statistics["files_skipped"] + self.__statistics["files_checked"])
        )
        self.skippedLabel.setText(str(self.__statistics["files_skipped"]))
        self.checkedLabel.setText(str(self.__statistics["files_checked"]))
        self.issuesLabel.setText(str(self.__statistics["files_issues"]))
        self.errorsLabel.setText(str(self.__statistics["errors"]))
        self.warningsLabel.setText(str(self.__statistics["warnings"]))
        self.pyWarningsLabel.setText(str(self.__statistics["py_warnings"]))

    def __finish(self):
        """
        Private slot called when the syntax check finished or the user
        pressed the button.
        """
        if not self.__finished:
            self.__finished = True

            self.cancelled = True
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(
                True
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(
                False
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(
                True
            )

            if self.noResults:
                QTreeWidgetItem(self.resultList, [self.tr("No issues found.")])
                QApplication.processEvents()
                self.showButton.setEnabled(False)
            else:
                self.showButton.setEnabled(True)
            self.resultList.header().resizeSections(
                QHeaderView.ResizeMode.ResizeToContents
            )
            self.resultList.header().setStretchLastSection(True)
            self.__updateStatisticsArea()

            self.checkProgress.setVisible(False)

    def __cancel(self):
        """
        Private method to cancel the current check run.
        """
        if self.__batch:
            self.syntaxCheckService.cancelSyntaxBatchCheck()
            QTimer.singleShot(1000, self.__finish)
        else:
            self.__finish()

    def closeEvent(self, _evt):
        """
        Protected method to handle a close event.

        @param _evt reference to the close event (unused)
        @type QCloseEvent
        """
        self.__cancel()

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
        elif button == self.showButton:
            self.on_showButton_clicked()

    @pyqtSlot()
    def on_startButton_clicked(self):
        """
        Private slot to start a syntax check run.
        """
        fileList = self.__fileList[:]
        totalLen = len(fileList)

        filterString = self.excludeFilesEdit.text()
        self.__data["ExcludeFiles"] = filterString
        self.__data["AdditionalBuiltins"] = self.builtinsEdit.text().strip()
        if self.__data != self.__project.getData("CHECKERSPARMS", "SyntaxChecker"):
            self.__project.setData("CHECKERSPARMS", "SyntaxChecker", self.__data)
        filterList = [f.strip() for f in filterString.split(",") if f.strip()]
        if filterList:
            for fileFilter in filterList:
                fileList = [f for f in fileList if not fnmatch.fnmatch(f, fileFilter)]

        self.resultList.clear()
        self.noResults = True
        self.cancelled = False
        self.setArguments((self.__data["AdditionalBuiltins"].split(),))
        self.start(fileList, skipped=totalLen - len(fileList))

    @pyqtSlot(QTreeWidgetItem, int)
    def on_resultList_itemActivated(self, itm, col):
        """
        Private slot to handle the activation of an item.

        @param itm reference to the activated item
        @type QTreeWidgetItem
        @param col column the item was activated in
        @type int
        """
        if self.noResults or itm.data(0, self.filenameRole) is None:
            return

        vm = ericApp().getObject("ViewManager")

        if itm.parent():
            fn = itm.data(0, self.filenameRole)
            lineno = itm.data(0, self.lineRole)
            index = itm.data(0, self.indexRole)
            error = itm.data(0, self.errorRole)

            vm.openSourceFile(fn, lineno)
            editor = vm.getOpenEditor(fn)

            if itm.data(0, self.warningRole):
                editor.toggleWarning(lineno, 0, True, error)
            else:
                editor.toggleSyntaxError(lineno, index, True, error, show=True)
        else:
            fn = itm.data(0, self.filenameRole)
            vm.openSourceFile(fn)
            editor = vm.getOpenEditor(fn)
            for index in range(itm.childCount()):
                citm = itm.child(index)
                lineno = citm.data(0, self.lineRole)
                index = citm.data(0, self.indexRole)
                error = citm.data(0, self.errorRole)
                if citm.data(0, self.warningRole):
                    editor.toggleWarning(lineno, 0, True, error)
                else:
                    editor.toggleSyntaxError(lineno, index, True, error, show=True)

        editor = vm.activeWindow()
        editor.updateVerticalScrollBar()

    @pyqtSlot()
    def on_showButton_clicked(self):
        """
        Private slot to handle the "Show" button press.
        """
        vm = ericApp().getObject("ViewManager")

        selectedIndexes = []
        for index in range(self.resultList.topLevelItemCount()):
            if self.resultList.topLevelItem(index).isSelected():
                selectedIndexes.append(index)
        if len(selectedIndexes) == 0:
            selectedIndexes = list(range(self.resultList.topLevelItemCount()))
        for index in selectedIndexes:
            itm = self.resultList.topLevelItem(index)
            if itm.data(0, self.filenameRole) is not None:
                fn = itm.data(0, self.filenameRole)
                vm.openSourceFile(fn, 1)
                editor = vm.getOpenEditor(fn)
                editor.clearSyntaxError()
                editor.clearFlakesWarnings()
                for cindex in range(itm.childCount()):
                    citm = itm.child(cindex)
                    lineno = citm.data(0, self.lineRole)
                    index = citm.data(0, self.indexRole)
                    error = citm.data(0, self.errorRole)
                    if citm.data(0, self.warningRole):
                        editor.toggleWarning(lineno, 0, True, error)
                    else:
                        editor.toggleSyntaxError(lineno, index, True, error, show=True)

        # go through the list again to clear syntax error and
        # flakes warning markers for files, that are ok
        errorFiles = []
        for index in range(self.resultList.topLevelItemCount()):
            itm = self.resultList.topLevelItem(index)
            errorFiles.append(itm.data(0, self.filenameRole))
        for fn in vm.getOpenFilenames():
            if fn not in errorFiles:
                editor = vm.getOpenEditor(fn)
                editor.clearSyntaxError()
                editor.clearFlakesWarnings()

        editor = vm.activeWindow()
        editor.updateVerticalScrollBar()

    def __clearErrors(self, files):
        """
        Private method to clear all error and warning markers of
        open editors to be checked.

        @param files list of files to be checked
        @type list of str
        """
        vm = ericApp().getObject("ViewManager")
        openFiles = vm.getOpenFilenames()
        for file in [f for f in openFiles if f in files]:
            editor = vm.getOpenEditor(file)
            editor.clearSyntaxError()
            editor.clearFlakesWarnings()
