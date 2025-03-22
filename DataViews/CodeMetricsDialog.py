# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a code metrics dialog.
"""

import collections
import fnmatch
import os
import time

from PyQt6.QtCore import QLocale, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QMenu,
    QTreeWidgetItem,
)

from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities

from . import CodeMetrics
from .Ui_CodeMetricsDialog import Ui_CodeMetricsDialog


class CodeMetricsDialog(QDialog, Ui_CodeMetricsDialog):
    """
    Class implementing a dialog to display the code metrics.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.summaryList.headerItem().setText(self.summaryList.columnCount(), "")
        self.summaryList.header().resizeSection(0, 200)
        self.summaryList.header().resizeSection(1, 100)

        self.resultList.headerItem().setText(self.resultList.columnCount(), "")

        self.cancelled = False

        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        self.__menu = QMenu(self)
        self.__menu.addAction(self.tr("Collapse All"), self.__resultCollapse)
        self.__menu.addAction(self.tr("Expand All"), self.__resultExpand)
        self.resultList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.resultList.customContextMenuRequested.connect(self.__showContextMenu)

        self.__fileList = []
        self.__project = ericApp().getObject("Project")
        self.filterFrame.setVisible(False)

    def __resizeResultColumns(self):
        """
        Private method to resize the list columns.
        """
        self.resultList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.resultList.header().setStretchLastSection(True)

    def __createResultItem(self, parent, values):
        """
        Private slot to create a new item in the result list.

        @param parent parent of the new item
        @type QTreeWidget or QTreeWidgetItem
        @param values values to be displayed
        @type list of int
        @return the generated item
        @rtype QTreeWidgetItem
        """
        data = [values[0]]
        for value in values[1:]:
            try:
                data.append("{0:5}".format(int(value)))
            except ValueError:
                data.append(value)
        itm = QTreeWidgetItem(parent, data)
        for col in range(1, 7):
            itm.setTextAlignment(col, Qt.AlignmentFlag.AlignRight)
        return itm

    def __resizeSummaryColumns(self):
        """
        Private method to resize the list columns.
        """
        self.summaryList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.summaryList.header().setStretchLastSection(True)

    def __createSummaryItem(self, col0, col1):
        """
        Private slot to create a new item in the summary list.

        @param col0 string for column 0
        @type str
        @param col1 string for column 1
        @type str
        """
        itm = QTreeWidgetItem(self.summaryList, [col0, col1])
        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)

    def prepare(self, fileList):
        """
        Public method to prepare the dialog with a list of filenames.

        @param fileList list of filenames
        @type list of str
        """
        self.__fileList = fileList[:]

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.filterFrame.setVisible(True)

        self.__data = self.__project.getData("OTHERTOOLSPARMS", "CodeMetrics")
        if self.__data is None or "ExcludeFiles" not in self.__data:
            self.__data = {"ExcludeFiles": ""}
        self.excludeFilesEdit.setText(self.__data["ExcludeFiles"])

    def start(self, fn):
        """
        Public slot to start the code metrics determination.

        @param fn file or list of files or directory to show
                the code metrics for
        @type str or list of str
        """
        self.cancelled = False
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        QApplication.processEvents()

        loc = QLocale()
        if isinstance(fn, list):
            files = fn
        elif FileSystemUtilities.isRemoteFileName(
            fn
        ) and self.__remotefsInterface.isdir(fn):
            files = self.__remotefsInterface.direntries(fn, True, "*.py", False)
        elif FileSystemUtilities.isPlainFileName(fn) and os.path.isdir(fn):
            files = FileSystemUtilities.direntries(fn, True, "*.py", False)
        else:
            files = [fn]
        files.sort()
        # check for missing files
        for f in files[:]:
            if FileSystemUtilities.isRemoteFileName(f):
                if not self.__remotefsInterface.exists(f):
                    files.remove(f)
            else:
                if not os.path.exists(f):
                    files.remove(f)

        self.checkProgress.setMaximum(len(files))
        QApplication.processEvents()

        total = collections.defaultdict(int)
        CodeMetrics.summarize(total, "files", len(files))

        try:
            # disable updates of the list for speed
            self.resultList.setUpdatesEnabled(False)
            self.resultList.setSortingEnabled(False)

            # now go through all the files
            now = time.monotonic()
            for progress, file in enumerate(files, start=1):
                if self.cancelled:
                    return

                stats = CodeMetrics.analyze(file, total)

                v = self.__getValues(loc, stats, "TOTAL ")
                # make the file name project relative
                fitm = self.__createResultItem(
                    self.resultList, [self.__project.getRelativePath(file)] + v
                )

                identifiers = stats.identifiers
                for identifier in identifiers:
                    v = self.__getValues(loc, stats, identifier)

                    self.__createResultItem(fitm, [identifier] + v)
                self.resultList.expandItem(fitm)

                self.checkProgress.setValue(progress)
                if time.monotonic() - now > 0.01:
                    QApplication.processEvents()
                    now = time.monotonic()
        finally:
            # reenable updates of the list
            self.resultList.setSortingEnabled(True)
            self.resultList.setUpdatesEnabled(True)
        self.__resizeResultColumns()

        # now do the summary stuff
        self.__createSummaryItem(self.tr("files"), loc.toString(total["files"]))
        self.__createSummaryItem(self.tr("lines"), loc.toString(total["lines"]))
        self.__createSummaryItem(self.tr("bytes"), loc.toString(total["bytes"]))
        self.__createSummaryItem(self.tr("comments"), loc.toString(total["comments"]))
        self.__createSummaryItem(
            self.tr("comment lines"), loc.toString(total["commentlines"])
        )
        self.__createSummaryItem(
            self.tr("empty lines"), loc.toString(total["empty lines"])
        )
        self.__createSummaryItem(
            self.tr("non-commentary lines"), loc.toString(total["non-commentary lines"])
        )
        self.__resizeSummaryColumns()
        self.__finish()

    def __getValues(self, loc, stats, identifier):
        """
        Private method to extract the code metric values.

        @param loc reference to the locale object
        @type QLocale
        @param stats reference to the code metric statistics object
        @type SourceStat
        @param identifier identifier to get values for
        @type str
        @return list of values suitable for display
        @rtype list of str
        """
        counters = stats.counters.get(identifier, {})
        v = []
        for key in ("start", "end", "lines", "nloc", "commentlines", "empty"):
            if counters.get(key, 0):
                v.append(loc.toString(counters[key]))
            else:
                v.append("")
        return v

    def __finish(self):
        """
        Private slot called when the action finished or the user pressed the
        button.
        """
        self.cancelled = True
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.resultList.header().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.summaryList.header().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )

    def closeEvent(self, _evt):
        """
        Protected method to handle the close event.

        @param _evt reference to the close event (unused)
        @type QCloseEvent
        """
        self.cancelled = True
        # The rest is done by the start() method.

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

    @pyqtSlot()
    def on_startButton_clicked(self):
        """
        Private slot to start a code metrics run.
        """
        fileList = self.__fileList[:]

        filterString = self.excludeFilesEdit.text()
        if (
            "ExcludeFiles" not in self.__data
            or filterString != self.__data["ExcludeFiles"]
        ):
            self.__data["ExcludeFiles"] = filterString
            self.__project.setData("OTHERTOOLSPARMS", "CodeMetrics", self.__data)
        filterList = filterString.split(",")
        if filterList:
            for filterString in filterList:
                fileList = [
                    f for f in fileList if not fnmatch.fnmatch(f, filterString.strip())
                ]

        self.resultList.clear()
        self.summaryList.clear()
        self.start(fileList)

    def __showContextMenu(self, coord):
        """
        Private slot to show the context menu of the listview.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        if self.resultList.topLevelItemCount() > 0:
            self.__menu.popup(self.mapToGlobal(coord))

    def __resultCollapse(self):
        """
        Private slot to collapse all entries of the resultlist.
        """
        for index in range(self.resultList.topLevelItemCount()):
            self.resultList.topLevelItem(index).setExpanded(False)

    def __resultExpand(self):
        """
        Private slot to expand all entries of the resultlist.
        """
        for index in range(self.resultList.topLevelItemCount()):
            self.resultList.topLevelItem(index).setExpanded(True)
