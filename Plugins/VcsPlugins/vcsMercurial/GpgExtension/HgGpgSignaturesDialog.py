# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing signed changesets.
"""

import re

from PyQt6.QtCore import QCoreApplication, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHeaderView, QTreeWidgetItem

from .Ui_HgGpgSignaturesDialog import Ui_HgGpgSignaturesDialog


class HgGpgSignaturesDialog(QDialog, Ui_HgGpgSignaturesDialog):
    """
    Class implementing a dialog showing signed changesets.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Hg
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.vcs = vcs
        self.__hgClient = vcs.getClient()

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

        self.intercept = False
        self.activateWindow()

        args = self.vcs.initCommand("sigs")

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

        if self.signaturesList.topLevelItemCount() == 0:
            # no patches present
            self.__generateItem("", "", self.tr("no signatures found"))
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
            self.__hgClient.cancel()

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.signaturesList.sortItems(
            self.signaturesList.sortColumn(),
            self.signaturesList.header().sortIndicatorOrder(),
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.signaturesList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.signaturesList.header().setStretchLastSection(True)

    def __generateItem(self, revision, changeset, signature):
        """
        Private method to generate a patch item in the list of patches.

        @param revision revision number
        @type str
        @param changeset changeset of the bookmark
        @type str
        @param signature signature of the changeset
        @type str
        """
        if revision == "" and changeset == "":
            QTreeWidgetItem(self.signaturesList, [signature])
        else:
            revString = "{0:>7}:{1}".format(revision, changeset)
            topItems = self.signaturesList.findItems(
                revString, Qt.MatchFlag.MatchExactly
            )
            if len(topItems) == 0:
                # first signature for this changeset
                topItm = QTreeWidgetItem(
                    self.signaturesList, ["{0:>7}:{1}".format(revision, changeset)]
                )
                topItm.setExpanded(True)
                font = topItm.font(0)
                font.setBold(True)
                topItm.setFont(0, font)
            else:
                topItm = topItems[0]
            QTreeWidgetItem(topItm, [signature])

    def __processOutputLine(self, line):
        """
        Private method to process the lines of output.

        @param line output line to be processed
        @type str
        """
        li = line.split()
        if li[-1][0] in "1234567890":
            # last element is a rev:changeset
            rev, changeset = li[-1].split(":", 1)
            del li[-1]
            signature = " ".join(li)
            self.__generateItem(rev, changeset, signature)

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
    def on_signaturesList_itemSelectionChanged(self):
        """
        Private slot handling changes of the selection.
        """
        selectedItems = self.signaturesList.selectedItems()
        if (
            len(selectedItems) == 1
            and self.signaturesList.indexOfTopLevelItem(selectedItems[0]) != -1
        ):
            self.verifyButton.setEnabled(True)
        else:
            self.verifyButton.setEnabled(False)

    @pyqtSlot()
    def on_verifyButton_clicked(self):
        """
        Private slot to verify the signatures of the selected revision.
        """
        rev = self.signaturesList.selectedItems()[0].text(0).split(":")[0].strip()
        self.vcs.getExtensionObject("gpg").hgGpgVerifySignatures(rev)

    @pyqtSlot(int)
    def on_categoryCombo_activated(self, _index):
        """
        Private slot called, when a new filter category is selected.

        @param _index index of the selected entry (unused)
        @type int
        """
        self.__filterSignatures()

    @pyqtSlot(str)
    def on_rxEdit_textChanged(self, _txt):
        """
        Private slot called, when a filter expression is entered.

        @param _txt filter expression (unused)
        @type str
        """
        self.__filterSignatures()

    def __filterSignatures(self):
        """
        Private method to filter the log entries.
        """
        searchRxText = self.rxEdit.text()
        filterTop = self.categoryCombo.currentText() == self.tr("Revision")
        searchRx = (
            re.compile(r"^\s*{0}".format(searchRxText[1:]), re.IGNORECASE)
            if filterTop and searchRxText.startswith("^")
            else re.compile(searchRxText, re.IGNORECASE)
        )
        for topIndex in range(self.signaturesList.topLevelItemCount()):
            topLevelItem = self.signaturesList.topLevelItem(topIndex)
            if filterTop:
                topLevelItem.setHidden(searchRx.search(topLevelItem.text(0)) is None)
            else:
                visibleChildren = topLevelItem.childCount()
                for childIndex in range(topLevelItem.childCount()):
                    childItem = topLevelItem.child(childIndex)
                    if searchRx.search(childItem.text(0)) is None:
                        childItem.setHidden(True)
                        visibleChildren -= 1
                    else:
                        childItem.setHidden(False)
                topLevelItem.setHidden(visibleChildren == 0)
