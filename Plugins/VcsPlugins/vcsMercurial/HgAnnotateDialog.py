# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the hg annotate command.
"""

import re

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHeaderView, QTreeWidgetItem

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox

from .Ui_HgAnnotateDialog import Ui_HgAnnotateDialog


class HgAnnotateDialog(QDialog, Ui_HgAnnotateDialog):
    """
    Class implementing a dialog to show the output of the hg annotate command.
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

        self.__annotateRe = re.compile(
            r"""(.+)\s+(\d+)\s+([0-9a-fA-F]+)\s+([0-9-]+)\s+(.+?)([:*])(.*)"""
        )

        self.annotateList.headerItem().setText(self.annotateList.columnCount(), "")
        font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.annotateList.setFont(font)

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

    def start(self, fn, skiplist=""):
        """
        Public slot to start the annotate command.

        @param fn filename to show the annotation for
        @type str
        @param skiplist name of a skip list file
        @type str
        """
        self.annotateList.clear()
        self.errorGroup.hide()
        self.intercept = False
        self.activateWindow()
        self.lineno = 1

        args = self.vcs.initCommand("annotate")
        args.append("--follow")
        args.append("--user")
        args.append("--date")
        args.append("--number")
        args.append("--changeset")
        args.append("--quiet")
        if skiplist:
            args.extend(self.__buildSkipList(skiplist))
        args.append(fn)

        out, err = self.__hgClient.runcommand(args)
        if err:
            self.__showError(err)
        if out:
            for line in out.splitlines():
                self.__processOutputLine(line)
                if self.__hgClient.wasCanceled():
                    break
        self.__finish()

    def __buildSkipList(self, skiplist):
        """
        Private method to build a program arguments list of changesets to be skipped.

        @param skiplist name of a skip list file
        @type str
        @return list of arguments
        @rtype list of str
        """
        skipArgs = []

        try:
            with open(skiplist, "r") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        skipArgs.extend(["--skip", line])
        except OSError as err:
            EricMessageBox.information(
                None,
                self.tr("Mercurial Annotate"),
                self.tr(
                    "<p>The skip list file <b>{0}</b> could not be read. The skip list"
                    " will be ignored.</p><p>Reason: {1}</p>"
                ).format(skiplist, str(err)),
            )
            skipArgs = []

        return skipArgs

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

        self.__resizeColumns()

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

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.annotateList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )

    def __generateItem(self, marker, revision, changeset, author, date, text):
        """
        Private method to generate an annotate item in the annotation list.

        @param marker marker character for skipped revisions
        @type str
        @param revision revision string
        @type str
        @param changeset changeset string
        @type str
        @param author author of the change
        @type str
        @param date date of the change
        @type str
        @param text text of the change
        @type str
        """
        itm = QTreeWidgetItem(
            self.annotateList,
            [
                marker,
                revision,
                changeset,
                author,
                date,
                "{0:d}".format(self.lineno),
                text,
            ],
        )
        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(5, Qt.AlignmentFlag.AlignRight)

        if marker == "*":
            itm.setToolTip(0, self.tr("Changed by skipped commit"))

        self.lineno += 1

    def __processOutputLine(self, line):
        """
        Private method to process the lines of output.

        @param line output line to be processed
        @type str
        """
        match = self.__annotateRe.match(line)
        author, rev, changeset, date, _file, marker, text = match.groups()
        if marker == ":":
            marker = ""
        self.__generateItem(
            marker, rev.strip(), changeset.strip(), author.strip(), date.strip(), text
        )

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()
