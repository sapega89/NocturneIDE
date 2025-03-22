# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show a list of applied and unapplied patches.
"""

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHeaderView, QTreeWidgetItem

from .Ui_HgQueuesListDialog import Ui_HgQueuesListDialog


class HgQueuesListDialog(QDialog, Ui_HgQueuesListDialog):
    """
    Class implementing a dialog to show a list of applied and unapplied
    patches.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Hg
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.vcs = vcs
        self.__hgClient = vcs.getClient()

        self.patchesList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.__statusDict = {
            "A": self.tr("applied"),
            "U": self.tr("not applied"),
            "G": self.tr("guarded"),
            "D": self.tr("missing"),
        }

        self.show()
        QCoreApplication.processEvents()

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if self.__hgClient.isExecuting():
            self.__hgClient.cancel()

        e.accept()

    def start(self):
        """
        Public slot to start the list command.
        """
        self.errorGroup.hide()
        self.activateWindow()

        self.__getSeries()

    def __getSeries(self, missing=False):
        """
        Private slot to get the list of applied, unapplied and guarded patches
        and patches missing in the series file.

        @param missing flag indicating to get the patches missing in the
            series file
        @type bool
        """
        if missing:
            self.__mode = "missing"
        else:
            self.__mode = "qseries"

        args = self.vcs.initCommand("qseries")
        args.append("--summary")
        args.append("--verbose")
        if missing:
            args.append("--missing")

        out, err = self.__hgClient.runcommand(args)
        if err:
            self.__showError(err)
        if out:
            for line in out.splitlines():
                self.__processOutputLine(line)
                if self.__hgClient.wasCanceled():
                    self.__mode = ""
                    break
        if self.__mode == "qseries":
            self.__getSeries(True)
        elif self.__mode == "missing":
            self.__getTop()
        else:
            self.__finish()

    def __getTop(self):
        """
        Private slot to get patch at the top of the stack.
        """
        self.__mode = "qtop"

        args = self.vcs.initCommand("qtop")

        out, err = self.__hgClient.runcommand(args)
        if err:
            self.__showError(err)
        if out:
            for line in out.splitlines():
                self.__processOutputLine(line)
                if self.__hgClient.wasCanceled():
                    break
        self.__finish()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        if self.patchesList.topLevelItemCount() == 0:
            # no patches present
            self.__generateItem(0, "", self.tr("no patches found"), "", True)
        self.__resizeColumns()
        self.__resort()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__mode = ""
            self.__hgClient.cancel()

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.patchesList.sortItems(
            self.patchesList.sortColumn(),
            self.patchesList.header().sortIndicatorOrder(),
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.patchesList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.patchesList.header().setStretchLastSection(True)

    def __generateItem(self, index, status, name, summary, error=False):
        """
        Private method to generate a patch item in the list of patches.

        @param index index of the patch (-1 for missing)
        @type int
        @param status status of the patch
        @type str
        @param name name of the patch
        @type str
        @param summary first line of the patch header
        @type str
        @param error flag indicating an error entry
        @type bool
        """
        if error:
            itm = QTreeWidgetItem(self.patchesList, ["", name, "", summary])
        else:
            if index == -1:
                index = ""
            try:
                statusStr = self.__statusDict[status]
            except KeyError:
                statusStr = self.tr("unknown")
            itm = QTreeWidgetItem(self.patchesList)
            itm.setData(0, Qt.ItemDataRole.DisplayRole, index)
            itm.setData(1, Qt.ItemDataRole.DisplayRole, name)
            itm.setData(2, Qt.ItemDataRole.DisplayRole, statusStr)
            itm.setData(3, Qt.ItemDataRole.DisplayRole, summary)
            if status == "A":
                # applied
                for column in range(itm.columnCount()):
                    itm.setForeground(column, Qt.GlobalColor.blue)
            elif status == "D":
                # missing
                for column in range(itm.columnCount()):
                    itm.setForeground(column, Qt.GlobalColor.red)

        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignHCenter)

    def __markTopItem(self, name):
        """
        Private slot to mark the top patch entry.

        @param name name of the patch
        @type str
        """
        items = self.patchesList.findItems(name, Qt.MatchFlag.MatchCaseSensitive, 1)
        if items:
            itm = items[0]
            for column in range(itm.columnCount()):
                font = itm.font(column)
                font.setBold(True)
                itm.setFont(column, font)

    def __processOutputLine(self, line):
        """
        Private method to process the lines of output.

        @param line output line to be processed
        @type str
        """
        if self.__mode == "qtop":
            self.__markTopItem(line)
        else:
            li = line.split(": ", 1)
            if len(li) == 1:
                data, summary = li[0][:-1], ""
            else:
                data, summary = li[0], li[1]
            li = data.split(None, 2)
            if len(li) == 2:
                # missing entry
                index, status, name = -1, li[0], li[1]
            elif len(li) == 3:
                index, status, name = li[:3]
            else:
                return
            self.__generateItem(index, status, name, summary)

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()
