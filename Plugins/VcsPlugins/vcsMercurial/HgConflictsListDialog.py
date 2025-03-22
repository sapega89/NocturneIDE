# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show a list of files which had or still have
conflicts.
"""

from PyQt6.QtCore import QPoint, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidgetItem,
    QWidget,
)

from eric7.EricWidgets.EricApplication import ericApp
from eric7.Utilities import MimeTypes

from .Ui_HgConflictsListDialog import Ui_HgConflictsListDialog


class HgConflictsListDialog(QWidget, Ui_HgConflictsListDialog):
    """
    Class implementing a dialog to show a list of files which had or still
    have conflicts.
    """

    StatusRole = Qt.ItemDataRole.UserRole + 1
    FilenameRole = Qt.ItemDataRole.UserRole + 2

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

        self.__position = QPoint()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.conflictsList.headerItem().setText(self.conflictsList.columnCount(), "")
        self.conflictsList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.refreshButton = self.buttonBox.addButton(
            self.tr("&Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the list of conflicts"))
        self.refreshButton.setEnabled(False)

        self.vcs = vcs
        self.project = ericApp().getObject("Project")

        self.__hgClient = vcs.getClient()

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

        super().show()

    def start(self):
        """
        Public slot to start the tags command.
        """
        self.errorGroup.hide()
        QApplication.processEvents()

        self.intercept = False

        self.activateWindow()
        self.raise_()

        self.conflictsList.clear()
        self.__started = True
        self.__getEntries()

    def __getEntries(self):
        """
        Private method to get the conflict entries.
        """
        args = self.vcs.initCommand("resolve")
        args.append("--list")

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

        self.refreshButton.setEnabled(True)

        self.__resizeColumns()
        self.__resort()
        self.on_conflictsList_itemSelectionChanged()

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
            self.__hgClient.cancel()
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.conflictsList.sortItems(
            self.conflictsList.sortColumn(),
            self.conflictsList.header().sortIndicatorOrder(),
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.conflictsList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.conflictsList.header().setStretchLastSection(True)

    def __generateItem(self, status, name):
        """
        Private method to generate a tag item in the tag list.

        @param status status of the file
        @type str
        @param name name of the file
        @type str
        """
        itm = QTreeWidgetItem(self.conflictsList)
        if status == "U":
            itm.setText(0, self.tr("Unresolved"))
        elif status == "R":
            itm.setText(0, self.tr("Resolved"))
        else:
            itm.setText(0, self.tr("Unknown Status"))
        itm.setText(1, name)

        itm.setData(0, self.StatusRole, status)
        itm.setData(0, self.FilenameRole, self.project.getAbsolutePath(name))

    def __processOutputLine(self, line):
        """
        Private method to process the lines of output.

        @param line output line to be processed
        @type str
        """
        status, filename = line.strip().split(None, 1)
        self.__generateItem(status, filename)

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the log.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.refreshButton.setEnabled(False)
        self.start()

    @pyqtSlot(QTreeWidgetItem, int)
    def on_conflictsList_itemDoubleClicked(self, _item, _column):
        """
        Private slot to open the double clicked entry.

        @param _item reference to the double clicked item (unused)
        @type QTreeWidgetItem
        @param _column column that was double clicked (unused)
        @type int
        """
        self.on_editButton_clicked()

    @pyqtSlot()
    def on_conflictsList_itemSelectionChanged(self):
        """
        Private slot to handle a change of selected conflict entries.
        """
        selectedCount = len(self.conflictsList.selectedItems())
        unresolved = resolved = 0
        for itm in self.conflictsList.selectedItems():
            status = itm.data(0, self.StatusRole)
            if status == "U":
                unresolved += 1
            elif status == "R":
                resolved += 1

        self.resolvedButton.setEnabled(unresolved > 0)
        self.unresolvedButton.setEnabled(resolved > 0)
        self.reMergeButton.setEnabled(unresolved > 0)
        self.editButton.setEnabled(
            selectedCount == 1
            and MimeTypes.isTextFile(
                self.conflictsList.selectedItems()[0].data(0, self.FilenameRole)
            )
        )

    @pyqtSlot()
    def on_resolvedButton_clicked(self):
        """
        Private slot to mark the selected entries as resolved.
        """
        names = [
            itm.data(0, self.FilenameRole)
            for itm in self.conflictsList.selectedItems()
            if itm.data(0, self.StatusRole) == "U"
        ]
        if names:
            self.vcs.vcsResolved(names)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_unresolvedButton_clicked(self):
        """
        Private slot to mark the selected entries as unresolved.
        """
        names = [
            itm.data(0, self.FilenameRole)
            for itm in self.conflictsList.selectedItems()
            if itm.data(0, self.StatusRole) == "R"
        ]
        if names:
            self.vcs.vcsResolved(names, unresolve=True)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_reMergeButton_clicked(self):
        """
        Private slot to re-merge the selected entries.
        """
        names = [
            itm.data(0, self.FilenameRole)
            for itm in self.conflictsList.selectedItems()
            if itm.data(0, self.StatusRole) == "U"
        ]
        if names:
            self.vcs.hgReMerge(names)

    @pyqtSlot()
    def on_editButton_clicked(self):
        """
        Private slot to open the selected file in an editor.
        """
        itm = self.conflictsList.selectedItems()[0]
        filename = itm.data(0, self.FilenameRole)
        if MimeTypes.isTextFile(filename):
            ericApp().getObject("ViewManager").getEditor(filename)
