# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to display profile data.
"""

import os
import pickle  # secok
import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QMenu,
    QTreeWidgetItem,
)

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities, PythonUtilities

from .Ui_PyProfileDialog import Ui_PyProfileDialog


class ProfileTreeWidgetItem(QTreeWidgetItem):
    """
    Class implementing a custom QTreeWidgetItem to allow sorting on numeric
    values.
    """

    def __getNC(self, itm):
        """
        Private method to get the value to compare on for the first column.

        @param itm item to operate on
        @type ProfileTreeWidgetItem
        @return comparison value for the first column
        @rtype int
        """
        s = itm.text(0)
        return int(s.split("/")[0])

    def __lt__(self, other):
        """
        Special method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type ProfileTreeWidgetItem
        @return true, if this item is less than other
        @rtype bool
        """
        column = self.treeWidget().sortColumn()
        if column == 0:
            return self.__getNC(self) < self.__getNC(other)
        if column == 6:
            return int(self.text(column)) < int(other.text(column))
        return self.text(column) < other.text(column)


class PyProfileDialog(QDialog, Ui_PyProfileDialog):
    """
    Class implementing a dialog to display the results of a profiling run.
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

        self.cancelled = False
        self.exclude = True
        self.ericpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.pyLibPath = PythonUtilities.getPythonLibPath()

        self.summaryList.headerItem().setText(self.summaryList.columnCount(), "")
        self.resultList.headerItem().setText(self.resultList.columnCount(), "")
        self.resultList.header().setSortIndicator(0, Qt.SortOrder.DescendingOrder)

        self.__menu = QMenu(self)
        self.filterItm = self.__menu.addAction(
            self.tr("Exclude Python Library"), self.__filter
        )
        self.__menu.addSeparator()
        self.__menu.addAction(self.tr("Erase Profiling Info"), self.__eraseProfile)
        self.__menu.addAction(self.tr("Erase Timing Info"), self.__eraseTiming)
        self.__menu.addSeparator()
        self.__menu.addAction(self.tr("Erase All Infos"), self.__eraseAll)
        self.resultList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.resultList.customContextMenuRequested.connect(self.__showContextMenu)
        self.summaryList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.summaryList.customContextMenuRequested.connect(self.__showContextMenu)

        # eric-ide server interface
        self.__serverFsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

    def __createResultItem(
        self,
        calls,
        totalTime,
        totalTimePerCall,
        cumulativeTime,
        cumulativeTimePerCall,
        file,
        line,
        functionName,
    ):
        """
        Private method to create an entry in the result list.

        @param calls number of calls
        @type int
        @param totalTime total time
        @type float
        @param totalTimePerCall total time per call
        @type float
        @param cumulativeTime cumulative time
        @type float
        @param cumulativeTimePerCall cumulative time per call
        @type float
        @param file filename of file
        @type str
        @param line linenumber
        @type int
        @param functionName function name
        @type str
        """
        itm = ProfileTreeWidgetItem(
            self.resultList,
            [
                calls,
                "{0: 8.3f}".format(totalTime),
                totalTimePerCall,
                "{0: 8.3f}".format(cumulativeTime),
                cumulativeTimePerCall,
                file,
                str(line),
                functionName,
            ],
        )
        for col in [0, 1, 2, 3, 4, 6]:
            itm.setTextAlignment(col, Qt.AlignmentFlag.AlignRight)

    def __createSummaryItem(self, label, contents):
        """
        Private method to create an entry in the summary list.

        @param label text of the first column
        @type str
        @param contents text of the second column
        @type str
        """
        itm = QTreeWidgetItem(self.summaryList, [label, contents])
        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)

    def __resortResultList(self):
        """
        Private method to resort the tree.
        """
        self.resultList.sortItems(
            self.resultList.sortColumn(), self.resultList.header().sortIndicatorOrder()
        )

    def __populateLists(self, exclude=False):
        """
        Private method used to populate the listviews.

        @param exclude flag indicating whether files residing in the
                Python library should be excluded
        @type bool
        """
        self.resultList.clear()
        self.summaryList.clear()

        self.checkProgress.setMaximum(len(self.stats))
        QApplication.processEvents()

        total_calls = 0
        prim_calls = 0
        total_tt = 0

        try:
            # disable updates of the list for speed
            self.resultList.setUpdatesEnabled(False)
            self.resultList.setSortingEnabled(False)

            # now go through all the files
            now = time.monotonic()
            for progress, (func, (cc, nc, tt, ct, _callers)) in enumerate(
                self.stats.items(), start=1
            ):
                if self.cancelled:
                    return

                if (
                    not (self.ericpath and func[0].startswith(self.ericpath))
                    and not func[0].startswith("DebugClients")
                    and func[0] != "profile"
                    and not (
                        exclude
                        and (func[0].startswith(self.pyLibPath) or func[0] == "")
                    )
                    and (
                        self.file is None
                        or func[0].startswith(self.file)
                        or func[0].startswith(self.pyLibPath)
                    )
                ):
                    # calculate the totals
                    total_calls += nc
                    prim_calls += cc
                    total_tt += tt

                    if nc != cc:
                        c = "{0:d}/{1:d}".format(nc, cc)
                    else:
                        c = str(nc)
                    if nc == 0:
                        tpc = "{0: 8.3f}".format(0.0)
                    else:
                        tpc = "{0: 8.3f}".format(tt / nc)
                    if cc == 0:
                        cpc = "{0: 8.3f}".format(0.0)
                    else:
                        cpc = "{0: 8.3f}".format(ct / cc)
                    self.__createResultItem(
                        c, tt, tpc, ct, cpc, func[0], func[1], func[2]
                    )

                self.checkProgress.setValue(progress)
                if time.monotonic() - now > 0.01:
                    QApplication.processEvents()
                    now = time.monotonic()
        finally:
            # reenable updates of the list
            self.resultList.setSortingEnabled(True)
            self.resultList.setUpdatesEnabled(True)
        self.__resortResultList()

        # now do the summary stuff
        self.__createSummaryItem(self.tr("function calls"), str(total_calls))
        if total_calls != prim_calls:
            self.__createSummaryItem(self.tr("primitive calls"), str(prim_calls))
        self.__createSummaryItem(self.tr("CPU seconds"), "{0:.3f}".format(total_tt))

    def start(self, pfn, fn=None):
        """
        Public slot to start the calculation of the profile data.

        @param pfn basename of the profiling file
        @type str
        @param fn file to display the profiling data for
        @type str
        """
        self.basename = os.path.splitext(pfn)[0]

        fname = "{0}.profile".format(self.basename)
        if (
            FileSystemUtilities.isRemoteFileName(fname)
            and not self.__serverFsInterface.exists(fname)
        ) or (FileSystemUtilities.isPlainFileName(fname) and not os.path.exists(fname)):
            EricMessageBox.warning(
                self,
                self.tr("Profile Results"),
                self.tr(
                    """<p>There is no profiling data"""
                    """ available for <b>{0}</b>.</p>"""
                ).format(pfn),
            )
            self.close()
            return
        try:
            if FileSystemUtilities.isRemoteFileName(fname):
                data = self.__serverFsInterface.readFile(fname)
                self.stats = pickle.loads(data)  # secok
            else:
                with open(fname, "rb") as f:
                    self.stats = pickle.load(f)  # secok
        except (EOFError, OSError, pickle.PickleError):
            EricMessageBox.critical(
                self,
                self.tr("Loading Profiling Data"),
                self.tr(
                    """<p>The profiling data could not be"""
                    """ read from file <b>{0}</b>.</p>"""
                ).format(fname),
            )
            self.close()
            return

        if FileSystemUtilities.isRemoteFileName(fname) and fn is not None:
            self.file = FileSystemUtilities.plainFileName(fn)
        else:
            self.file = fn
        self.__populateLists()
        self.__finish()

    def __finish(self):
        """
        Private slot called when the action finished or the user pressed the
        button.
        """
        self.cancelled = True
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        QApplication.processEvents()
        self.resultList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.resultList.header().setStretchLastSection(True)
        self.summaryList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.summaryList.header().setStretchLastSection(True)

    def __unfinish(self):
        """
        Private slot called to revert the effects of the __finish slot.
        """
        self.cancelled = False
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

    def closeEvent(self, _evt):
        """
        Protected method to handle the close event.

        @param _evt reference to the close event (unused)
        @type QCloseEvent
        """
        self.cancelled = True
        # The rest is done by the __populateLists() method.

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

    def __showContextMenu(self, coord):
        """
        Private slot to show the context menu of the listview.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        self.__menu.popup(self.mapToGlobal(coord))

    def __eraseProfile(self):
        """
        Private slot to handle the Erase Profile context menu action.
        """
        fname = "{0}.profile".format(self.basename)
        if os.path.exists(fname):
            os.remove(fname)

    def __eraseTiming(self):
        """
        Private slot to handle the Erase Timing context menu action.
        """
        fname = "{0}.timings".format(self.basename)
        if os.path.exists(fname):
            os.remove(fname)

    def __eraseAll(self):
        """
        Private slot to handle the Erase All context menu action.
        """
        self.__eraseProfile()
        self.__eraseTiming()

    def __filter(self):
        """
        Private slot to handle the Exclude/Include Python Library context menu
        action.
        """
        self.__unfinish()
        if self.exclude:
            self.exclude = False
            self.filterItm.setText(self.tr("Include Python Library"))
            self.__populateLists(True)
        else:
            self.exclude = True
            self.filterItm.setText(self.tr("Exclude Python Library"))
            self.__populateLists(False)
        self.__finish()
