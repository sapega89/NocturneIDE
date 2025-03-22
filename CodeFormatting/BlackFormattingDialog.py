# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing the Black code formatting progress and the results.
"""

import copy
import datetime
import multiprocessing
import pathlib

from dataclasses import dataclass

import black

from PyQt6.QtCore import QCoreApplication, QObject, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidgetItem,
)

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.SystemUtilities import FileSystemUtilities

from . import BlackUtilities
from .BlackFormattingAction import BlackFormattingAction
from .FormattingDiffWidget import FormattingDiffWidget
from .Ui_BlackFormattingDialog import Ui_BlackFormattingDialog


class BlackFormattingDialog(QDialog, Ui_BlackFormattingDialog):
    """
    Class implementing a dialog showing the Black code formatting progress and the
    results.
    """

    DataRole = Qt.ItemDataRole.UserRole
    DataTypeRole = Qt.ItemDataRole.UserRole + 1
    FileNameRole = Qt.ItemDataRole.UserRole + 2
    StatusRole = Qt.ItemDataRole.UserRole + 3

    FileNameColumn = 1
    StatusColumn = 0

    def __init__(
        self,
        configuration,
        filesList,
        project=None,
        action=BlackFormattingAction.Format,
        parent=None,
    ):
        """
        Constructor

        @param configuration dictionary containing the configuration parameters
        @type dict
        @param filesList list of absolute file paths to be processed
        @type list of str
        @param project reference to the project object (defaults to None)
        @type Project (optional)
        @param action action to be performed (defaults to BlackFormattingAction.Format)
        @type BlackFormattingAction (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.resultsList.header().setSortIndicator(1, Qt.SortOrder.AscendingOrder)

        self.__config = copy.deepcopy(configuration)
        self.__config["__action__"] = action  # needed by the workers
        self.__project = project

        self.__filesList = filesList[:]

        self.__diffDialog = None

        self.__allFilter = self.tr("<all>")

        self.__formatButton = self.buttonBox.addButton(
            self.tr("Format Code"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__formatButton.setVisible(False)

        self.show()
        QCoreApplication.processEvents()

        self.__performAction()

    def __performAction(self):
        """
        Private method to execute the requested formatting action.
        """
        self.progressBar.setMaximum(len(self.__filesList))
        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)

        self.statisticsGroup.setVisible(False)
        self.__statistics = BlackStatistics()

        self.__cancelled = False

        self.statusFilterComboBox.clear()
        self.resultsList.clear()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        files = self.__filterFiles(self.__filesList)
        if len(files) > 1:
            self.__formatManyFiles(files)
        elif len(files) == 1:
            self.__formatOneFile(files[0])

    def __filterFiles(self, filesList):
        """
        Private method to filter the given list of files according the
        configuration parameters.

        @param filesList list of files
        @type list of str
        @return list of filtered files
        @rtype list of str
        """
        filterRegExps = [
            BlackUtilities.compileRegExp(self.__config[k])
            for k in ["force-exclude", "extend-exclude", "exclude"]
            if k in self.__config
            and bool(self.__config[k])
            and BlackUtilities.validateRegExp(self.__config[k])[0]
        ]

        files = []
        for file in filesList:
            file = FileSystemUtilities.fromNativeSeparators(file)
            for filterRegExp in filterRegExps:
                filterMatch = filterRegExp.search(file)
                if filterMatch and filterMatch.group(0):
                    self.__handleBlackFormattingResult("ignored", file, "")
                    break
            else:
                files.append(file)

        return files

    def __resort(self):
        """
        Private method to resort the result list.
        """
        self.resultsList.sortItems(
            self.resultsList.sortColumn(),
            self.resultsList.header().sortIndicatorOrder(),
        )

    def __resizeColumns(self):
        """
        Private method to resize the columns of the result list.
        """
        self.resultsList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.resultsList.header().setStretchLastSection(True)

    def __populateStatusFilterCombo(self):
        """
        Private method to populate the status filter combo box with allowed selections.
        """
        allowedSelections = set()
        for row in range(self.resultsList.topLevelItemCount()):
            allowedSelections.add(
                self.resultsList.topLevelItem(row).text(
                    BlackFormattingDialog.StatusColumn
                )
            )

        self.statusFilterComboBox.addItem(self.__allFilter)
        self.statusFilterComboBox.addItems(sorted(allowedSelections))

    def __finish(self):
        """
        Private method to perform some actions after the run was performed or canceled.
        """
        self.__resort()
        self.__resizeColumns()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.progressBar.setVisible(False)

        self.__formatButton.setVisible(
            self.__config["__action__"] is not BlackFormattingAction.Format
            and self.__statistics.changeCount > 0
        )

        self.__updateStatistics()
        self.__populateStatusFilterCombo()

    def __updateStatistics(self):
        """
        Private method to update the statistics about the recent formatting run and
        make them visible.
        """
        self.reformattedLabel.setText(
            self.tr("Reformatted:")
            if self.__config["__action__"] is BlackFormattingAction.Format
            else self.tr("Would Reformat:")
        )

        total = self.progressBar.maximum()

        self.totalCountLabel.setText("{0:n}".format(total))
        self.excludedCountLabel.setText("{0:n}".format(self.__statistics.ignoreCount))
        self.failuresCountLabel.setText("{0:n}".format(self.__statistics.failureCount))
        self.processedCountLabel.setText(
            "{0:n}".format(self.__statistics.processedCount)
        )
        self.reformattedCountLabel.setText(
            "{0:n}".format(self.__statistics.changeCount)
        )
        self.unchangedCountLabel.setText("{0:n}".format(self.__statistics.sameCount))

        self.statisticsGroup.setVisible(True)

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot to handle button presses of the dialog buttons.

        @param button reference to the pressed button
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__cancelled = True
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            if self.__diffDialog is not None:
                self.__diffDialog.close()
                self.__diffDialog = None
            self.accept()
        elif button is self.__formatButton:
            self.__formatButtonClicked()

    @pyqtSlot()
    def __formatButtonClicked(self):
        """
        Private slot handling the selection of the 'Format Code' button.
        """
        files = []
        for row in range(self.resultsList.topLevelItemCount()):
            itm = self.resultsList.topLevelItem(row)
            if itm.data(0, BlackFormattingDialog.StatusRole) == "changed":
                files.append(itm.data(0, BlackFormattingDialog.FileNameRole))
        if files:
            self.__filesList = files

        self.__config["__action__"] = BlackFormattingAction.Format
        self.__performAction()

    @pyqtSlot(QTreeWidgetItem, int)
    def on_resultsList_itemDoubleClicked(self, item, _column):
        """
        Private slot handling a double click of a result item.

        @param item reference to the double clicked item
        @type QTreeWidgetItem
        @param _column column number that was double clicked (unused)
        @type int
        """
        dataType = item.data(0, BlackFormattingDialog.DataTypeRole)
        if dataType == "error":
            EricMessageBox.critical(
                self,
                self.tr("Formatting Failure"),
                self.tr("<p>Formatting failed due to this error.</p><p>{0}</p>").format(
                    item.data(0, BlackFormattingDialog.DataRole)
                ),
            )
        elif dataType == "diff":
            if self.__diffDialog is None:
                self.__diffDialog = FormattingDiffWidget()
            self.__diffDialog.showDiff(item.data(0, BlackFormattingDialog.DataRole))

    def __formatManyFiles(self, files):
        """
        Private method to format the list of files according the configuration using
        multiple processes in parallel.

        @param files list of files to be processed
        @type list of str
        """
        maxProcesses = Preferences.getUI("BackgroundServiceProcesses")
        if maxProcesses == 0:
            # determine based on CPU count
            try:
                NumberOfProcesses = multiprocessing.cpu_count()
                if NumberOfProcesses >= 1:
                    NumberOfProcesses -= 1
            except NotImplementedError:
                NumberOfProcesses = 1
        else:
            NumberOfProcesses = maxProcesses

        # Create queues
        taskQueue = multiprocessing.Queue()
        doneQueue = multiprocessing.Queue()

        # Submit tasks (initially two times the number of processes)
        tasks = len(files)
        initialTasks = min(2 * NumberOfProcesses, tasks)
        for _ in range(initialTasks):
            file = files.pop(0)
            relSrc = self.__project.getRelativePath(str(file)) if self.__project else ""
            taskQueue.put((file, relSrc))

        # Start worker processes
        workers = [
            multiprocessing.Process(
                target=self.formattingWorkerTask,
                args=(taskQueue, doneQueue, self.__config),
            )
            for _ in range(NumberOfProcesses)
        ]
        for worker in workers:
            worker.start()

        # Get the results from the worker tasks
        for _ in range(tasks):
            result = doneQueue.get()
            self.__handleBlackFormattingResult(
                result.status, result.filename, result.data
            )

            if self.__cancelled:
                break

            if files:
                file = files.pop(0)
                relSrc = (
                    self.__project.getRelativePath(str(file)) if self.__project else ""
                )
                taskQueue.put((file, relSrc))

        # Tell child processes to stop
        for _ in range(NumberOfProcesses):
            taskQueue.put("STOP")

        for worker in workers:
            worker.join()
            worker.close()

        taskQueue.close()
        doneQueue.close()

        self.__finish()

    @staticmethod
    def formattingWorkerTask(inputQueue, outputQueue, config):
        """
        Static method acting as the parallel worker for the formatting task.

        @param inputQueue input queue
        @type multiprocessing.Queue
        @param outputQueue output queue
        @type multiprocessing.Queue
        @param config dictionary containing the configuration parameters
        @type dict
        """
        report = BlackMultiprocessingReport(outputQueue)
        report.check = config["__action__"] is BlackFormattingAction.Check
        report.diff = config["__action__"] is BlackFormattingAction.Diff

        versions = (
            {black.TargetVersion[target.upper()] for target in config["target-version"]}
            if config["target-version"]
            else set()
        )

        mode = black.Mode(
            target_versions=versions,
            line_length=int(config["line-length"]),
            string_normalization=not config["skip-string-normalization"],
            magic_trailing_comma=not config["skip-magic-trailing-comma"],
        )

        if config["__action__"] is BlackFormattingAction.Diff:
            for file, relSrc in iter(inputQueue.get, "STOP"):
                BlackFormattingDialog.__diffFormatFile(
                    pathlib.Path(file),
                    fast=False,
                    mode=mode,
                    report=report,
                    relSrc=relSrc,
                )
        else:
            writeBack = black.WriteBack.from_configuration(
                check=config["__action__"] is BlackFormattingAction.Check,
                diff=config["__action__"] is BlackFormattingAction.Diff,
            )

            for file, _relSrc in iter(inputQueue.get, "STOP"):
                black.reformat_one(
                    pathlib.Path(file),
                    fast=False,
                    write_back=writeBack,
                    mode=mode,
                    report=report,
                )

    def __formatOneFile(self, file):
        """
        Private method to format the list of files according the configuration.

        @param file name of the file to be processed
        @type str
        """
        report = BlackReport(self)
        report.check = self.__config["__action__"] is BlackFormattingAction.Check
        report.diff = self.__config["__action__"] is BlackFormattingAction.Diff
        report.result.connect(self.__handleBlackFormattingResult)

        writeBack = black.WriteBack.from_configuration(
            check=self.__config["__action__"] is BlackFormattingAction.Check,
            diff=self.__config["__action__"] is BlackFormattingAction.Diff,
        )

        versions = (
            {
                black.TargetVersion[target.upper()]
                for target in self.__config["target-version"]
            }
            if self.__config["target-version"]
            else set()
        )

        mode = black.Mode(
            target_versions=versions,
            line_length=int(self.__config["line-length"]),
            string_normalization=not self.__config["skip-string-normalization"],
            magic_trailing_comma=not self.__config["skip-magic-trailing-comma"],
        )

        if self.__config["__action__"] is BlackFormattingAction.Diff:
            relSrc = self.__project.getRelativePath(str(file)) if self.__project else ""
            self.__diffFormatFile(
                pathlib.Path(file), fast=False, mode=mode, report=report, relSrc=relSrc
            )
        else:
            black.reformat_one(
                pathlib.Path(file),
                fast=False,
                write_back=writeBack,
                mode=mode,
                report=report,
            )

        self.__finish()

    @staticmethod
    def __diffFormatFile(src, fast, mode, report, relSrc=""):
        """
        Static method to check, if the given files need to be reformatted, and generate
        a unified diff.

        @param src path of file to be checked
        @type pathlib.Path
        @param fast flag indicating fast operation
        @type bool
        @param mode code formatting options
        @type black.Mode
        @param report reference to the report object
        @type BlackReport
        @param relSrc name of the file relative to the project (defaults to "")
        @type str (optional)
        """
        then = datetime.datetime.fromtimestamp(
            src.stat().st_mtime, tz=datetime.timezone.utc
        )
        with open(src, "rb") as buf:
            srcContents, _, _ = black.decode_bytes(buf.read())
        try:
            dstContents = black.format_file_contents(srcContents, fast=fast, mode=mode)
        except black.NothingChanged:
            report.done(src, black.Changed.NO)
            return

        fileName = relSrc if bool(relSrc) else str(src)

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        srcName = f"{fileName}\t{then} +0000"
        dstName = f"{fileName}\t{now} +0000"
        diffContents = black.diff(srcContents, dstContents, srcName, dstName)
        report.done(src, black.Changed.YES, diff=diffContents)

    def closeEvent(self, evt):
        """
        Protected slot implementing a close event handler.

        @param evt reference to the close event
        @type QCloseEvent
        """
        if self.__diffDialog is not None:
            self.__diffDialog.close()
        evt.accept()

    @pyqtSlot(str)
    def on_statusFilterComboBox_currentTextChanged(self, status):
        """
        Private slot handling the selection of a status for items to be shown.

        @param status selected status
        @type str
        """
        for row in range(self.resultsList.topLevelItemCount()):
            itm = self.resultsList.topLevelItem(row)
            itm.setHidden(
                status != self.__allFilter
                and itm.text(BlackFormattingDialog.StatusColumn) != status
            )

    @pyqtSlot(str, str, str)
    def __handleBlackFormattingResult(self, status, filename, data):
        """
        Private slot to handle the result of a black reformatting action.

        @param status status of the performed action (one of 'changed', 'failed',
            'ignored', 'unchanged' or 'unmodified')
        @type str
        @param filename name of the processed file
        @type str
        @param data action data (error message or unified diff)
        @type str
        """
        isError = False

        if status == "changed":
            statusMsg = (
                self.tr("would reformat")
                if self.__config["__action__"]
                in (BlackFormattingAction.Check, BlackFormattingAction.Diff)
                else self.tr("reformatted")
            )
            self.__statistics.changeCount += 1

        elif status == "unchanged":
            statusMsg = self.tr("unchanged")
            self.__statistics.sameCount += 1

        elif status == "unmodified":
            statusMsg = self.tr("unmodified")
            self.__statistics.sameCount += 1

        elif status == "ignored":
            statusMsg = self.tr("ignored")
            self.__statistics.ignoreCount += 1

        elif status == "failed":
            statusMsg = self.tr("failed")
            self.__statistics.failureCount += 1
            isError = True

        else:
            statusMsg = self.tr("invalid status ({0})").format(status)
            self.__statistics.failureCount += 1
            isError = True

        if status != "ignored":
            self.__statistics.processedCount += 1

        itm = QTreeWidgetItem(
            self.resultsList,
            [
                statusMsg,
                (
                    self.__project.getRelativePath(filename)
                    if self.__project
                    else filename
                ),
            ],
        )
        itm.setData(0, BlackFormattingDialog.StatusRole, status)
        itm.setData(0, BlackFormattingDialog.FileNameRole, filename)
        if data:
            itm.setData(
                0, BlackFormattingDialog.DataTypeRole, "error" if isError else "diff"
            )
            itm.setData(0, BlackFormattingDialog.DataRole, data)

        self.progressBar.setValue(self.progressBar.value() + 1)

        QCoreApplication.processEvents()


@dataclass
class BlackStatistics:
    """
    Class containing the reformatting statistic data.
    """

    ignoreCount: int = 0
    changeCount: int = 0
    sameCount: int = 0
    failureCount: int = 0
    processedCount: int = 0


class BlackReport(QObject, black.Report):
    """
    Class extending the black Report to work with our dialog.

    @signal result(status, file name, data) emitted to signal the reformatting result
        as three strings giving the status (one of 'changed', 'unchanged', 'unmodified',
        'failed' or 'ignored'), the file name and data related to the result
    """

    result = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object (defaults to None
        @type QObject (optional)
        """
        QObject.__init__(self, parent)
        black.Report.__init__(self)

    def done(self, src, changed, diff=""):
        """
        Public method to handle the end of a reformat.

        @param src name of the processed file
        @type pathlib.Path
        @param changed change status
        @type black.Changed
        @param diff unified diff of potential changes (defaults to "")
        @type str
        """
        if changed is black.Changed.YES:
            status = "changed"

        elif changed is black.Changed.NO:
            status = "unchanged"

        elif changed is black.Changed.CACHED:
            status = "unmodified"

        self.result.emit(status, str(src), diff)

    def failed(self, src, message):
        """
        Public method to handle a reformat failure.

        @param src name of the processed file
        @type pathlib.Path
        @param message error message
        @type str
        """
        self.result.emit("failed", str(src), message)

    def path_ignored(self, src, message=""):  # noqa: U100
        """
        Public method handling an ignored path.

        @param src name of the processed file
        @type pathlib.Path or str
        @param message ignore message (default to "") (unused)
        @type str (optional)
        """
        self.result.emit("ignored", str(src), "")


@dataclass
class BlackMultiprocessingResult:
    """
    Class containing the reformatting result data.

    This class is used when reformatting multiple files in parallel using processes.
    """

    status: str = ""
    filename: str = ""
    data: str = ""


class BlackMultiprocessingReport(black.Report):
    """
    Class extending the black Report to work with multiprocessing.
    """

    def __init__(self, resultQueue):
        """
        Constructor

        @param resultQueue reference to the queue to put the results into
        @type multiprocessing.Queue
        """
        super().__init__()

        self.__queue = resultQueue

    def done(self, src, changed, diff=""):
        """
        Public method to handle the end of a reformat.

        @param src name of the processed file
        @type pathlib.Path
        @param changed change status
        @type black.Changed
        @param diff unified diff of potential changes (defaults to "")
        @type str
        """
        if changed is black.Changed.YES:
            status = "changed"

        elif changed is black.Changed.NO:
            status = "unchanged"

        elif changed is black.Changed.CACHED:
            status = "unmodified"

        self.__queue.put(
            BlackMultiprocessingResult(status=status, filename=str(src), data=diff)
        )

    def failed(self, src, message):
        """
        Public method to handle a reformat failure.

        @param src name of the processed file
        @type pathlib.Path
        @param message error message
        @type str
        """
        self.__queue.put(
            BlackMultiprocessingResult(status="failed", filename=str(src), data=message)
        )

    def path_ignored(self, src, message=""):  # noqa: U100
        """
        Public method handling an ignored path.

        @param src name of the processed file
        @type pathlib.Path or str
        @param message ignore message (default to "") (unused)
        @type str (optional)
        """
        self.__queue.put(
            BlackMultiprocessingResult(status="ignored", filename=str(src), data="")
        )
