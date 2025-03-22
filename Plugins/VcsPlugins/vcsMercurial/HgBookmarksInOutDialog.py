# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show a list of incoming or outgoing bookmarks.
"""

import enum

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHeaderView, QTreeWidgetItem

from .Ui_HgBookmarksInOutDialog import Ui_HgBookmarksInOutDialog


class HgBookmarksInOutDialogMode(enum.Enum):
    """
    Class defining the modes of the dialog.
    """

    INCOMING = 0
    OUTGOING = 1


class HgBookmarksInOutDialog(QDialog, Ui_HgBookmarksInOutDialog):
    """
    Class implementing a dialog to show a list of incoming or outgoing
    bookmarks.
    """

    def __init__(self, vcs, mode, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Hg
        @param mode mode of the dialog
        @type HgBookmarksInOutDialogMode
        @param parent reference to the parent widget
        @type QWidget
        @exception ValueError raised to indicate an invalid dialog mode
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        if not isinstance(mode, HgBookmarksInOutDialogMode):
            raise ValueError("Bad value for mode")

        if mode == HgBookmarksInOutDialogMode.INCOMING:
            self.setWindowTitle(self.tr("Mercurial Incoming Bookmarks"))
        elif mode == HgBookmarksInOutDialogMode.OUTGOING:
            self.setWindowTitle(self.tr("Mercurial Outgoing Bookmarks"))

        self.vcs = vcs
        self.__mode = mode
        self.__hgClient = vcs.getClient()

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

    def start(self):
        """
        Public slot to start the bookmarks command.
        """
        self.errorGroup.hide()

        self.intercept = False
        self.activateWindow()

        args = (
            self.vcs.initCommand("incoming")
            if self.__mode == HgBookmarksInOutDialogMode.INCOMING
            else self.vcs.initCommand("outgoing")
        )

        args.append("--bookmarks")

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

        if self.bookmarksList.topLevelItemCount() == 0:
            # no bookmarks defined
            self.__generateItem(self.tr("no bookmarks found"), "")
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
            if self.__hgClient:
                self.__hgClient.cancel()
            else:
                self.__finish()

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

    def __generateItem(self, changeset, name):
        """
        Private method to generate a bookmark item in the bookmarks list.

        @param changeset changeset of the bookmark
        @type str
        @param name name of the bookmark
        @type str
        """
        QTreeWidgetItem(self.bookmarksList, [name, changeset])

    def __processOutputLine(self, line):
        """
        Private method to process the lines of output.

        @param line output line to be processed
        @type str
        """
        if line.startswith(" "):
            li = line.strip().split()
            changeset = li[-1]
            del li[-1]
            name = " ".join(li)
            self.__generateItem(changeset, name)

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()
