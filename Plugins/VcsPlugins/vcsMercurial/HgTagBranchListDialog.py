# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show a list of tags or branches.
"""

from PyQt6.QtCore import QCoreApplication, QPoint, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QMenu,
    QTreeWidgetItem,
)

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

from .Ui_HgTagBranchListDialog import Ui_HgTagBranchListDialog


class HgTagBranchListDialog(QDialog, Ui_HgTagBranchListDialog):
    """
    Class implementing a dialog to show a list of tags or branches.
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

        self.refreshButton = self.buttonBox.addButton(
            self.tr("&Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the list"))
        self.refreshButton.setEnabled(False)

        self.vcs = vcs
        self.tagsList = None
        self.allTagsList = None
        self.__hgClient = vcs.getClient()
        self.__currentRevision = ""
        self.__currentBranch = ""

        self.tagList.headerItem().setText(self.tagList.columnCount(), "")
        self.tagList.header().setSortIndicator(3, Qt.SortOrder.AscendingOrder)

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

    def start(self, tags, tagsList, allTagsList):
        """
        Public slot to start the tags command.

        @param tags flag indicating a list of tags is requested
            (False = branches, True = tags)
        @type bool
        @param tagsList reference to string list receiving the tags
        @type list of str
        @param allTagsList reference to string list all tags
        @type list of str
        """
        self.errorGroup.hide()
        self.tagList.clear()

        self.intercept = False
        self.tagsMode = tags
        if not tags:
            self.setWindowTitle(self.tr("Mercurial Branches List"))
            self.tagList.headerItem().setText(2, self.tr("Status"))
            if self.vcs.isExtensionActive("closehead"):
                self.tagList.setSelectionMode(
                    QAbstractItemView.SelectionMode.ExtendedSelection
                )
        self.activateWindow()

        self.tagsList = tagsList
        self.allTagsList = allTagsList

        if self.tagsMode:
            args = self.vcs.initCommand("tags")
            args.append("--verbose")
        else:
            args = self.vcs.initCommand("branches")
            args.append("--closed")

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
        self.refreshButton.setEnabled(True)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        if not self.tagsMode:
            self.__highlightCurrentBranch()
        self.__resizeColumns()
        self.__resort()

        # restore current item
        if self.__currentRevision:
            items = self.tagList.findItems(
                self.__currentRevision, Qt.MatchFlag.MatchExactly, 0
            )
            if items:
                self.tagList.setCurrentItem(items[0])
                self.__currentRevision = ""
                self.tagList.setFocus(Qt.FocusReason.OtherFocusReason)

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
        self.tagList.sortItems(
            self.tagList.sortColumn(), self.tagList.header().sortIndicatorOrder()
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.tagList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.tagList.header().setStretchLastSection(True)

    def __generateItem(self, revision, changeset, status, name):
        """
        Private method to generate a tag item in the tag list.

        @param revision revision of the tag/branch
        @type str
        @param changeset changeset of the tag/branch
        @type str
        @param status of the tag/branch
        @type str
        @param name name of the tag/branch
        @type str
        """
        itm = QTreeWidgetItem(self.tagList)
        itm.setData(0, Qt.ItemDataRole.DisplayRole, int(revision))
        itm.setData(1, Qt.ItemDataRole.DisplayRole, changeset)
        itm.setData(2, Qt.ItemDataRole.DisplayRole, status)
        itm.setData(3, Qt.ItemDataRole.DisplayRole, name)
        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignHCenter)

    def __processOutputLine(self, line):
        """
        Private method to process the lines of output.

        @param line output line to be processed
        @type str
        """
        li = line.split()
        if li[-1][0] in "1234567890":
            # last element is a rev:changeset
            if self.tagsMode:
                status = ""
            else:
                status = self.tr("active")
            rev, changeset = li[-1].split(":", 1)
            del li[-1]
        else:
            if self.tagsMode:
                status = self.tr("yes")
            else:
                status = li[-1][1:-1]
            rev, changeset = li[-2].split(":", 1)
            del li[-2:]
        name = " ".join(li)
        self.__generateItem(rev, changeset, status, name)
        if name not in ["tip", "default"]:
            if self.tagsList is not None:
                self.tagsList.append(name)
            if self.allTagsList is not None:
                self.allTagsList.append(name)

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()

    def __highlightCurrentBranch(self):
        """
        Private method to highlight the current branch with a bold font.
        """
        self.__currentBranch = self.vcs.hgGetCurrentBranch()
        if self.__currentBranch:
            items = self.tagList.findItems(
                self.__currentBranch, Qt.MatchFlag.MatchCaseSensitive, 3
            )
            if len(items) == 1:
                font = items[0].font(3)
                font.setBold(True)
                for column in range(4):
                    items[0].setFont(column, font)

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the log.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.refreshButton.setEnabled(False)

        # save the current items commit ID
        itm = self.tagList.currentItem()
        if itm is not None:
            self.__currentRevision = itm.text(0)
        else:
            self.__currentRevision = ""

        self.start(self.tagsMode, self.tagsList, self.allTagsList)

    @pyqtSlot(QPoint)
    def on_tagList_customContextMenuRequested(self, pos):
        """
        Private slot to handle the context menu request.

        @param pos position the context menu was requested at
        @type QPoint
        """
        itm = self.tagList.itemAt(pos)
        if itm is not None:
            menu = QMenu(self.tagList)
            if self.tagsMode:
                menu.addAction(
                    EricPixmapCache.getIcon("vcsSwitch"),
                    self.tr("Switch to"),
                    self.__switchTo,
                )
            else:
                act = menu.addAction(
                    EricPixmapCache.getIcon("vcsSwitch"),
                    self.tr("Switch to"),
                    self.__switchTo,
                )
                act.setEnabled(itm.text(3) != self.__currentBranch)
                menu.addSeparator()
                if self.vcs.isExtensionActive("closehead"):
                    act = menu.addAction(
                        EricPixmapCache.getIcon("closehead"),
                        self.tr("Close Branches"),
                        self.__closeBranchHeads,
                    )
                    act.setEnabled(
                        len(
                            [
                                itm
                                for itm in self.tagList.selectedItems()
                                if itm.text(3) != "default"
                            ]
                        )
                        > 0
                    )
                else:
                    act = menu.addAction(
                        EricPixmapCache.getIcon("closehead"),
                        self.tr("Close Branch"),
                        self.__closeBranch,
                    )
                    act.setEnabled(itm.text(3) != "default")
            menu.popup(self.tagList.mapToGlobal(pos))

    def __switchTo(self):
        """
        Private slot to switch the working directory to the selected revision.
        """
        itm = self.tagList.currentItem()
        rev = itm.text(0).strip()
        if rev:
            shouldReopen = self.vcs.vcsUpdate(revision=rev)
            if shouldReopen:
                res = EricMessageBox.yesNo(
                    None,
                    self.tr("Switch"),
                    self.tr("""The project should be reread. Do this now?"""),
                    yesDefault=True,
                )
                if res:
                    ericApp().getObject("Project").reopenProject()
                    return

            self.on_refreshButton_clicked()

    def __closeBranch(self):
        """
        Private slot to close the selected branch.
        """
        itm = self.tagList.currentItem()
        branch = itm.text(3).strip()
        if branch == "default":
            EricMessageBox.warning(
                self,
                self.tr("Close Branch"),
                self.tr("""The branch "default" cannot be closed. Aborting..."""),
            )
            return

        yes = EricMessageBox.yesNo(
            self,
            self.tr("Close Branch"),
            self.tr("""<p>Shall the branch <b>{0}</b> really be closed?</p>""").format(
                branch
            ),
        )
        if yes:
            switched = False
            currentBranch = self.vcs.hgGetCurrentBranch()
            if currentBranch != branch:
                # step 1: switch to branch to be closed
                switched = True
                self.vcs.vcsUpdate(noDialog=True, revision=branch)

            ppath = ericApp().getObject("Project").getProjectPath()
            self.vcs.vcsCommit(
                ppath,
                "Branch <{0}> closed.".format(branch),
                noDialog=True,
                closeBranch=True,
            )
            if switched:
                self.vcs.vcsUpdate(noDialog=True, revision=currentBranch)

            self.on_refreshButton_clicked()

    def __closeBranchHeads(self):
        """
        Private slot to close the selected branches.
        """
        branches = [
            itm.text(3)
            for itm in self.tagList.selectedItems()
            if itm.text(3) != "default"
        ]

        dlg = DeleteFilesConfirmationDialog(
            self.parent(),
            self.tr("Close Branches"),
            self.tr("Do you really want to close all listed branches?"),
            branches,
        )
        yes = dlg.exec() == QDialog.DialogCode.Accepted
        if yes:
            self.vcs.getExtensionObject("closehead").hgCloseheads(branches)

            self.on_refreshButton_clicked()
