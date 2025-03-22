# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing the isort code formatting progress and the results.
"""

import contextlib
import copy
import io
import multiprocessing
import os
import pathlib

from dataclasses import dataclass

from isort import settings
from isort.api import check_file, sort_file
from isort.exceptions import ISortError
from PyQt6.QtCore import QCoreApplication, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidgetItem,
)

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox

from .FormattingDiffWidget import FormattingDiffWidget
from .IsortFormattingAction import IsortFormattingAction
from .Ui_IsortFormattingDialog import Ui_IsortFormattingDialog


class IsortFormattingDialog(QDialog, Ui_IsortFormattingDialog):
    """
    Class implementing a dialog showing the isort code formatting progress and the
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
        action=IsortFormattingAction.Sort,
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
        @param action action to be performed (defaults to IsortFormattingAction.Sort)
        @type IsortFormattingAction (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.resultsList.header().setSortIndicator(1, Qt.SortOrder.AscendingOrder)

        self.__project = project

        self.__config = copy.deepcopy(configuration)
        self.__config["quiet"] = True  # we don't want extra output
        self.__config["overwrite_in_place"] = True  # we want to overwrite the files
        if "config_source" in self.__config:
            del self.__config["config_source"]

        # Create an isort Config object and pre-load it with parameters contained in
        # project specific configuration files (like pyproject.toml). The configuration
        # given as a dictionary (i.e. data entered in the configuration dialog)
        # overwrites these. If the project is not passed, the isort config is based on
        # the isort defaults.
        if project:
            with contextlib.suppress(AttributeError):
                # for isort < 5.13.0
                # clear the caches in order to force a re-read of config files
                settings._get_config_data.cache_clear()
                settings._find_config.cache_clear()
        try:
            self.__isortConfig = (
                settings.Config(settings_path=project.getProjectPath(), **self.__config)
                if project
                else settings.Config(**self.__config)
            )
        except KeyError:
            # invalid configuration entry found in some config file; use just the dialog
            # parameters
            self.__isortConfig = settings.Config(**self.__config)

        self.__config["__action__"] = action  # needed by the workers

        self.__filesList = filesList[:]

        self.__diffDialog = None

        self.__allFilter = self.tr("<all>")

        self.__sortImportsButton = self.buttonBox.addButton(
            self.tr("Sort Imports"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__sortImportsButton.setVisible(False)

        self.show()
        QCoreApplication.processEvents()

        self.__performAction()

    def __performAction(self):
        """
        Private method to execute the requested sorting action.
        """
        self.progressBar.setMaximum(len(self.__filesList))
        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)

        self.statisticsGroup.setVisible(False)
        self.__statistics = IsortStatistics()

        self.__cancelled = False

        self.statusFilterComboBox.clear()
        self.resultsList.clear()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        files = self.__filterFiles(self.__filesList)
        if len(files) > 1:
            self.__sortManyFiles(files)
        elif len(files) == 1:
            self.__sortOneFile(files[0])

    def __filterFiles(self, filesList):
        """
        Private method to filter the given list of files according the
        configuration parameters.

        @param filesList list of files
        @type list of str
        @return list of filtered files
        @rtype list of str
        """
        files = []
        for file in filesList:
            if not self.__isortConfig.is_supported_filetype(
                file
            ) or self.__isortConfig.is_skipped(pathlib.Path(file)):
                self.__handleIsortResult(file, "skipped")
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
                    IsortFormattingDialog.StatusColumn
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

        self.__sortImportsButton.setVisible(
            self.__config["__action__"] is not IsortFormattingAction.Sort
            and self.__statistics.changeCount > 0
        )

        self.__updateStatistics()
        self.__populateStatusFilterCombo()

    def __updateStatistics(self):
        """
        Private method to update the statistics about the recent sorting run and
        make them visible.
        """
        self.reformattedLabel.setText(
            self.tr("Resorted:")
            if self.__config["__action__"] is IsortFormattingAction.Sort
            else self.tr("Would Resort:")
        )

        total = self.progressBar.maximum()

        self.totalCountLabel.setText("{0:n}".format(total))
        self.skippedCountLabel.setText("{0:n}".format(self.__statistics.skippedCount))
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
        elif button is self.__sortImportsButton:
            self.__sortImportsButtonClicked()

    @pyqtSlot()
    def __sortImportsButtonClicked(self):
        """
        Private slot handling the selection of the 'Sort Imports' button.
        """
        files = []
        for row in range(self.resultsList.topLevelItemCount()):
            itm = self.resultsList.topLevelItem(row)
            if itm.data(0, IsortFormattingDialog.StatusRole) == "changed":
                files.append(itm.data(0, IsortFormattingDialog.FileNameRole))
        if files:
            self.__filesList = files

        self.__config["__action__"] = IsortFormattingAction.Sort
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
        dataType = item.data(0, IsortFormattingDialog.DataTypeRole)
        if dataType == "error":
            EricMessageBox.critical(
                self,
                self.tr("Imports Sorting Failure"),
                self.tr(
                    "<p>Imports sorting failed due to this error.</p><p>{0}</p>"
                ).format(item.data(0, IsortFormattingDialog.DataRole)),
            )
        elif dataType == "diff":
            if self.__diffDialog is None:
                self.__diffDialog = FormattingDiffWidget()
            self.__diffDialog.showDiff(item.data(0, IsortFormattingDialog.DataRole))

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
                and itm.text(IsortFormattingDialog.StatusColumn) != status
            )

    def closeEvent(self, evt):
        """
        Protected slot implementing a close event handler.

        @param evt reference to the close event
        @type QCloseEvent
        """
        if self.__diffDialog is not None:
            self.__diffDialog.close()
        evt.accept()

    def __handleIsortResult(self, filename, status, data=""):
        """
        Private method to handle an isort sorting result.

        @param filename name of the processed file
        @type str
        @param status status of the performed action (one of 'changed', 'failed',
            'skipped' or 'unchanged')
        @type str
        @param data action data (error message or unified diff) (defaults to "")
        @type str (optional)
        """
        isError = False

        if status == "changed":
            statusMsg = (
                self.tr("would resort")
                if self.__config["__action__"]
                in (IsortFormattingAction.Check, IsortFormattingAction.Diff)
                else self.tr("resorted")
            )
            self.__statistics.changeCount += 1

        elif status == "unchanged":
            statusMsg = self.tr("unchanged")
            self.__statistics.sameCount += 1

        elif status == "skipped":
            statusMsg = self.tr("skipped")
            self.__statistics.skippedCount += 1

        elif status == "failed":
            statusMsg = self.tr("failed")
            self.__statistics.failureCount += 1
            isError = True

        elif status == "unsupported":
            statusMsg = self.tr("error")
            data = self.tr("Unsupported 'isort' action ({0}) given.").format(
                self.__config["__action__"]
            )
            self.__statistics.failureCount += 1
            isError = True

        else:
            statusMsg = self.tr("invalid status ({0})").format(status)
            self.__statistics.failureCount += 1
            isError = True

        if status != "skipped":
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
        itm.setData(0, IsortFormattingDialog.StatusRole, status)
        itm.setData(0, IsortFormattingDialog.FileNameRole, filename)
        if data:
            itm.setData(
                0, IsortFormattingDialog.DataTypeRole, "error" if isError else "diff"
            )
            itm.setData(0, IsortFormattingDialog.DataRole, data)

        self.progressBar.setValue(self.progressBar.value() + 1)

        QCoreApplication.processEvents()

    def __sortManyFiles(self, files):
        """
        Private method to sort imports of the list of files according the configuration
        using multiple processes in parallel.

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
            taskQueue.put((file, self.__config["__action__"]))

        # Start worker processes
        workers = [
            multiprocessing.Process(
                target=self.sortingWorkerTask,
                args=(taskQueue, doneQueue, self.__isortConfig),
            )
            for _ in range(NumberOfProcesses)
        ]
        for worker in workers:
            worker.start()

        # Get the results from the worker tasks
        for _ in range(tasks):
            result = doneQueue.get()
            self.__handleIsortResult(result.filename, result.status, data=result.data)

            if self.__cancelled:
                break

            if files:
                file = files.pop(0)
                taskQueue.put((file, self.__config["__action__"]))

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
    def sortingWorkerTask(inputQueue, outputQueue, isortConfig):
        """
        Static method acting as the parallel worker for the formatting task.

        @param inputQueue input queue
        @type multiprocessing.Queue
        @param outputQueue output queue
        @type multiprocessing.Queue
        @param isortConfig config object for isort
        @type isort.Config
        """
        for file, action in iter(inputQueue.get, "STOP"):
            if action == IsortFormattingAction.Diff:
                result = IsortFormattingDialog.__isortCheckFile(
                    file,
                    isortConfig,
                    withDiff=True,
                )

            elif action == IsortFormattingAction.Sort:
                result = IsortFormattingDialog.__isortSortFile(
                    file,
                    isortConfig,
                )

            else:
                result = IsortResult(
                    status="unsupported",
                    filename=file,
                )

            outputQueue.put(result)

    def __sortOneFile(self, file):
        """
        Private method to sort the imports of the list of files according the
        configuration.

        @param file name of the file to be processed
        @type str
        """
        if self.__config["__action__"] == IsortFormattingAction.Diff:
            result = IsortFormattingDialog.__isortCheckFile(
                file,
                self.__isortConfig,
                withDiff=True,
            )

        elif self.__config["__action__"] == IsortFormattingAction.Sort:
            result = IsortFormattingDialog.__isortSortFile(
                file,
                self.__isortConfig,
            )

        else:
            result = IsortResult(
                status="unsupported",
                filename=file,
            )

        self.__handleIsortResult(result.filename, result.status, data=result.data)

        self.__finish()

    @staticmethod
    def __isortCheckFile(filename, isortConfig, withDiff=True):
        """
        Static method to check, if a file's import statements need to be changed.

        @param filename name of the file to be processed
        @type str
        @param isortConfig config object for isort
        @type isort.Config
        @param withDiff flag indicating to return a unified diff, if the file needs to
            be changed (defaults to True)
        @type bool (optional)
        @return result object
        @rtype IsortResult
        """
        try:
            diffIO = io.StringIO() if withDiff else False
            with open(os.devnull, "w") as devnull, contextlib.redirect_stderr(devnull):
                ok = check_file(
                    filename,
                    show_diff=diffIO,
                    config=isortConfig,
                )
            if withDiff:
                data = "" if ok else diffIO.getvalue()
                diffIO.close()
            else:
                data = ""

            status = "unchanged" if ok else "changed"
        except ISortError as err:
            status = "failed"
            data = str(err)

        return IsortResult(status=status, filename=filename, data=data)

    @staticmethod
    def __isortSortFile(filename, isortConfig):
        """
        Static method to sort the import statements of a file.

        @param filename name of the file to be processed
        @type str
        @param isortConfig config object for isort
        @type isort.Config
        @return result object
        @rtype IsortResult
        """
        try:
            with open(os.devnull, "w") as devnull, contextlib.redirect_stderr(devnull):
                ok = sort_file(
                    filename,
                    config=isortConfig,
                    ask_to_apply=False,
                    write_to_stdout=False,
                    show_diff=False,
                )

            status = "changed" if ok else "unchanged"
            data = ""
        except ISortError as err:
            status = "failed"
            data = str(err)

        return IsortResult(status=status, filename=filename, data=data)


@dataclass
class IsortStatistics:
    """
    Class containing the isort statistic data.
    """

    skippedCount: int = 0
    changeCount: int = 0
    sameCount: int = 0
    failureCount: int = 0
    processedCount: int = 0


@dataclass
class IsortResult:
    """
    Class containing the isort result data.
    """

    status: str = ""
    filename: str = ""
    data: str = ""
