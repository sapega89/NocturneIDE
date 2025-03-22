# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show a list of bookmarks.
"""

from PyQt6.QtCore import QCoreApplication, QPoint, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeWidgetItem,
)

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from .Ui_HgBookmarksListDialog import Ui_HgBookmarksListDialog


class HgBookmarksListDialog(QDialog, Ui_HgBookmarksListDialog):
    """
    Class implementing a dialog to show a list of bookmarks.
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

        self.refreshButton = self.buttonBox.addButton(
            self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the bookmarks display"))
        self.refreshButton.setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.vcs = vcs
        self.__bookmarksList = None
        self.__hgClient = vcs.getClient()
        self.__bookmarksDefined = False
        self.__currentRevision = ""

        self.bookmarksList.headerItem().setText(self.bookmarksList.columnCount(), "")
        self.bookmarksList.header().setSortIndicator(3, Qt.SortOrder.AscendingOrder)

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

    def start(self, bookmarksList):
        """
        Public slot to start the bookmarks command.

        @param bookmarksList reference to string list receiving the bookmarks
        @type list of str
        """
        self.bookmarksList.clear()
        self.__bookmarksDefined = False

        self.errorGroup.hide()

        self.intercept = False
        self.activateWindow()

        self.__bookmarksList = bookmarksList
        self.__bookmarksList.clear()

        args = self.vcs.initCommand("bookmarks")

        self.refreshButton.setEnabled(False)

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

        if self.bookmarksList.topLevelItemCount() == 0:
            # no bookmarks defined
            self.__generateItem(self.tr("no bookmarks defined"), "", "", "")
            self.__bookmarksDefined = False
        else:
            self.__bookmarksDefined = True

        self.__resizeColumns()
        self.__resort()

        # restore current item
        if self.__currentRevision:
            items = self.bookmarksList.findItems(
                self.__currentRevision, Qt.MatchFlag.MatchExactly, 0
            )
            if items:
                self.bookmarksList.setCurrentItem(items[0])
                self.__currentRevision = ""
                self.bookmarksList.setFocus(Qt.FocusReason.OtherFocusReason)

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            if self.__hgClient:
                self.__hgClient.cancel()
            else:
                self.__finish()
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.bookmarksList.sortItems(
            self.bookmarksList.sortColumn(),
            self.bookmarksList.header().sortIndicatorOrder(),
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.bookmarksList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.bookmarksList.header().setStretchLastSection(True)

    def __generateItem(self, revision, changeset, status, name):
        """
        Private method to generate a bookmark item in the bookmarks list.

        @param revision revision of the bookmark
        @type str
        @param changeset changeset of the bookmark
        @type str
        @param status of the bookmark
        @type str
        @param name name of the bookmark
        @type str
        """
        itm = QTreeWidgetItem(self.bookmarksList)
        if revision[0].isdecimal():
            # valid bookmark entry
            itm.setData(0, Qt.ItemDataRole.DisplayRole, int(revision))
            itm.setData(1, Qt.ItemDataRole.DisplayRole, changeset)
            itm.setData(2, Qt.ItemDataRole.DisplayRole, status)
            itm.setData(3, Qt.ItemDataRole.DisplayRole, name)
            itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)
            itm.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)
            itm.setTextAlignment(2, Qt.AlignmentFlag.AlignHCenter)
        else:
            # error message
            itm.setData(0, Qt.ItemDataRole.DisplayRole, revision)

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
            if li[0] == "*":
                status = "current"
                del li[0]
            else:
                status = ""
            name = " ".join(li)
            self.__generateItem(rev, changeset, status, name)
            if self.__bookmarksList is not None:
                self.__bookmarksList.append(name)

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
        Private slot to refresh the status display.
        """
        # save the current items commit ID
        itm = self.bookmarksList.currentItem()
        if itm is not None:
            self.__currentRevision = itm.text(0)
        else:
            self.__currentRevision = ""

        self.start(self.__bookmarksList)

    @pyqtSlot(QPoint)
    def on_bookmarksList_customContextMenuRequested(self, pos):
        """
        Private slot to handle the context menu request.

        @param pos position the context menu was requetsed at
        @type QPoint
        """
        itm = self.bookmarksList.itemAt(pos)
        if itm is not None and self.__bookmarksDefined:
            menu = QMenu(self.bookmarksList)
            menu.addAction(
                EricPixmapCache.getIcon("vcsSwitch"),
                self.tr("Switch to"),
                self.__switchTo,
            )
            menu.addSeparator()
            menu.addAction(
                EricPixmapCache.getIcon("deleteBookmark"),
                self.tr("Delete"),
                self.__deleteBookmark,
            )
            menu.addAction(
                EricPixmapCache.getIcon("renameBookmark"),
                self.tr("Rename"),
                self.__renameBookmark,
            )
            menu.addSeparator()
            act = menu.addAction(
                EricPixmapCache.getIcon("pullBookmark"),
                self.tr("Pull"),
                self.__pullBookmark,
            )
            act.setEnabled(self.vcs.canPull())
            act = menu.addAction(
                EricPixmapCache.getIcon("pushBookmark"),
                self.tr("Push"),
                self.__pushBookmark,
            )
            act.setEnabled(self.vcs.canPush())
            menu.addSeparator()
            act = menu.addAction(
                EricPixmapCache.getIcon("pushBookmark"),
                self.tr("Push Current"),
                self.__pushCurrentBookmark,
            )
            act.setEnabled(self.vcs.canPush())
            if self.vcs.version >= (5, 7):
                act = menu.addAction(
                    EricPixmapCache.getIcon("pushBookmark"),
                    self.tr("Push All"),
                    self.__pushAllBookmarks,
                )
                act.setEnabled(self.vcs.canPush())

            menu.popup(self.bookmarksList.mapToGlobal(pos))

    def __switchTo(self):
        """
        Private slot to switch the working directory to the selected revision.
        """
        itm = self.bookmarksList.currentItem()
        bookmark = itm.text(3).strip()
        if bookmark:
            shouldReopen = self.vcs.vcsUpdate(revision=bookmark)
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

    def __deleteBookmark(self):
        """
        Private slot to delete the selected bookmark.
        """
        itm = self.bookmarksList.currentItem()
        bookmark = itm.text(3).strip()
        if bookmark:
            yes = EricMessageBox.yesNo(
                self,
                self.tr("Delete Bookmark"),
                self.tr(
                    """<p>Shall the bookmark <b>{0}</b> really be deleted?</p>"""
                ).format(bookmark),
            )
            if yes:
                self.vcs.hgBookmarkDelete(bookmark=bookmark)
                self.on_refreshButton_clicked()

    def __renameBookmark(self):
        """
        Private slot to rename the selected bookmark.
        """
        itm = self.bookmarksList.currentItem()
        bookmark = itm.text(3).strip()
        if bookmark:
            newName, ok = QInputDialog.getText(
                self,
                self.tr("Rename Bookmark"),
                self.tr("<p>Enter the new name for bookmark <b>{0}</b>:</p>").format(
                    bookmark
                ),
                QLineEdit.EchoMode.Normal,
            )
            if ok and bool(newName):
                self.vcs.hgBookmarkRename((bookmark, newName))
                self.on_refreshButton_clicked()

    def __pullBookmark(self):
        """
        Private slot to pull the selected bookmark.
        """
        itm = self.bookmarksList.currentItem()
        bookmark = itm.text(3).strip()
        if bookmark:
            self.vcs.hgBookmarkPull(bookmark=bookmark)
            self.on_refreshButton_clicked()

    def __pushBookmark(self):
        """
        Private slot to push the selected bookmark.
        """
        itm = self.bookmarksList.currentItem()
        bookmark = itm.text(3).strip()
        if bookmark:
            self.vcs.hgBookmarkPush(bookmark=bookmark)
            self.on_refreshButton_clicked()

    def __pushCurrentBookmark(self):
        """
        Private slot to push the current bookmark.
        """
        self.vcs.hgBookmarkPush(current=True)
        self.on_refreshButton_clicked()

    def __pushAllBookmarks(self):
        """
        Private slot to push all bookmarks.
        """
        self.vcs.hgBookmarkPush(allBookmarks=True)
        self.on_refreshButton_clicked()
