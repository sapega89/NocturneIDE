# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing Mercurial shelve browser dialog.
"""

from PyQt6.QtCore import QPoint, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QDialogButtonBox,
    QHeaderView,
    QMenu,
    QTreeWidgetItem,
    QWidget,
)

from eric7.EricGui.EricOverrideCursor import EricOverrideCursor

from .Ui_HgShelveBrowserDialog import Ui_HgShelveBrowserDialog


class HgShelveBrowserDialog(QWidget, Ui_HgShelveBrowserDialog):
    """
    Class implementing Mercurial shelve browser dialog.
    """

    NameColumn = 0
    AgeColumn = 1
    MessageColumn = 2

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

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.__position = QPoint()

        self.__fileStatisticsRole = Qt.ItemDataRole.UserRole
        self.__totalStatisticsRole = Qt.ItemDataRole.UserRole + 1

        self.shelveList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.refreshButton = self.buttonBox.addButton(
            self.tr("&Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the list of shelves"))
        self.refreshButton.setEnabled(False)

        self.vcs = vcs
        self.__hgClient = vcs.getClient()
        self.__resetUI()

        self.__contextMenu = QMenu()
        self.__unshelveAct = self.__contextMenu.addAction(
            self.tr("Restore selected shelve"), self.__unshelve
        )
        self.__deleteAct = self.__contextMenu.addAction(
            self.tr("Delete selected shelves"), self.__deleteShelves
        )
        self.__contextMenu.addAction(
            self.tr("Delete all shelves"), self.__cleanupShelves
        )

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if self.__hgClient.isExecuting():
            self.__hgClient.cancel()

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
        self.shelveList.clear()

    def __resizeColumnsShelves(self):
        """
        Private method to resize the shelve list columns.
        """
        self.shelveList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.shelveList.header().setStretchLastSection(True)

    def __generateShelveEntry(self, name, age, message, fileStatistics, totals):
        """
        Private method to generate the shelve items.

        @param name name of the shelve
        @type str
        @param age age of the shelve
        @type str
        @param message shelve message
        @type str
        @param fileStatistics per file change statistics (tuple containing the
            file name, the number of changes, the number of added lines and the
            number of deleted lines)
        @type tuple of (str, str, str, str)
        @param totals overall statistics (tuple containing the number of changed files,
            the number of added lines and the number of deleted lines)
        @type tuple of (str, str, str)
        """
        itm = QTreeWidgetItem(self.shelveList, [name, age, message])
        itm.setData(0, self.__fileStatisticsRole, fileStatistics)
        itm.setData(0, self.__totalStatisticsRole, totals)

    def __getShelveEntries(self):
        """
        Private method to retrieve the list of shelves.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        QApplication.processEvents()

        self.buf = []
        self.errors.clear()
        self.intercept = False

        args = self.vcs.initCommand("shelve")
        args.append("--list")
        args.append("--stat")

        with EricOverrideCursor():
            out, err = self.__hgClient.runcommand(args)
            self.buf = out.splitlines(True)
            if err:
                self.__showError(err)
            self.__processBuffer()
        self.__finish()

    def start(self):
        """
        Public slot to start the hg shelve command.
        """
        self.errorGroup.hide()
        QApplication.processEvents()

        self.activateWindow()
        self.raise_()

        self.shelveList.clear()
        self.__started = True
        self.__getShelveEntries()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.refreshButton.setEnabled(True)

    def __processBuffer(self):
        """
        Private method to process the buffered output of the hg shelve command.
        """
        lastWasFileStats = False
        firstLine = True
        itemData = {}
        for line in self.buf:
            if firstLine:
                name, line = line.split("(", 1)
                age, message = line.split(")", 1)
                itemData["name"] = name.strip()
                itemData["age"] = age.strip()
                itemData["message"] = message.strip()
                itemData["files"] = []
                firstLine = False
            elif "|" in line:
                # file stats: foo.py |  3 ++-
                file, changes = line.strip().split("|", 1)
                if changes.strip().endswith(("+", "-")):
                    total, addDelete = changes.strip().split(None, 1)
                    additions = str(addDelete.count("+"))
                    deletions = str(addDelete.count("-"))
                else:
                    total = changes.strip()
                    additions = "0"
                    deletions = "0"
                itemData["files"].append((file, total, additions, deletions))
                lastWasFileStats = True
            elif lastWasFileStats:
                # summary line
                # 2 files changed, 15 insertions(+), 1 deletions(-)
                total, added, deleted = line.strip().split(",", 2)
                total = total.split()[0]
                added = added.split()[0]
                deleted = deleted.split()[0]
                itemData["summary"] = (total, added, deleted)

                self.__generateShelveEntry(
                    itemData["name"],
                    itemData["age"],
                    itemData["message"],
                    itemData["files"],
                    itemData["summary"],
                )

                lastWasFileStats = False
                firstLine = True
                itemData = {}

        self.__resizeColumnsShelves()

        if self.__started:
            self.shelveList.setCurrentItem(self.shelveList.topLevelItem(0))
            self.__started = False

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()

    @pyqtSlot(QAbstractButton)
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
            self.__hgClient.cancel()
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_shelveList_currentItemChanged(self, current, _previous):
        """
        Private slot called, when the current item of the shelve list changes.

        @param current reference to the new current item
        @type QTreeWidgetItem
        @param _previous reference to the old current item (unused)
        @type QTreeWidgetItem
        """
        self.statisticsList.clear()
        if current:
            for dataSet in current.data(0, self.__fileStatisticsRole):
                QTreeWidgetItem(self.statisticsList, list(dataSet))
            self.statisticsList.header().resizeSections(
                QHeaderView.ResizeMode.ResizeToContents
            )
            self.statisticsList.header().setStretchLastSection(True)

            totals = current.data(0, self.__totalStatisticsRole)
            self.filesLabel.setText(self.tr("%n file(s) changed", None, int(totals[0])))
            self.insertionsLabel.setText(
                self.tr("%n line(s) inserted", None, int(totals[1]))
            )
            self.deletionsLabel.setText(
                self.tr("%n line(s) deleted", None, int(totals[2]))
            )
        else:
            self.filesLabel.setText("")
            self.insertionsLabel.setText("")
            self.deletionsLabel.setText("")

    @pyqtSlot(QPoint)
    def on_shelveList_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu of the shelve list.

        @param pos position of the mouse pointer
        @type QPoint
        """
        selectedItemsCount = len(self.shelveList.selectedItems())
        self.__unshelveAct.setEnabled(selectedItemsCount == 1)
        self.__deleteAct.setEnabled(selectedItemsCount > 0)

        self.__contextMenu.popup(self.mapToGlobal(pos))

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the list of shelves.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.refreshButton.setEnabled(False)

        self.start()

    def __unshelve(self):
        """
        Private slot to restore the selected shelve of changes.
        """
        itm = self.shelveList.selectedItems()[0]
        if itm is not None:
            name = itm.text(self.NameColumn)
            self.vcs.getBuiltinObject("shelve").hgUnshelve(shelveName=name)
            self.on_refreshButton_clicked()

    def __deleteShelves(self):
        """
        Private slot to delete the selected shelves.
        """
        shelveNames = []
        for itm in self.shelveList.selectedItems():
            shelveNames.append(itm.text(self.NameColumn))
        if shelveNames:
            self.vcs.getBuiltinObject("shelve").hgDeleteShelves(shelveNames=shelveNames)
            self.on_refreshButton_clicked()

    def __cleanupShelves(self):
        """
        Private slot to delete all shelves.
        """
        self.vcs.getBuiltinObject("shelve").hgCleanupShelves()
        self.on_refreshButton_clicked()
