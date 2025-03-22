# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the hg diff command process.
"""

import pathlib

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from eric7 import Preferences
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from .HgDiffGenerator import HgDiffGenerator
from .HgDiffHighlighter import HgDiffHighlighter
from .Ui_HgDiffDialog import Ui_HgDiffDialog


class HgDiffDialog(QWidget, Ui_HgDiffDialog):
    """
    Class implementing a dialog to show the output of the hg diff command
    process.
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

        self.refreshButton = self.buttonBox.addButton(
            self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the display"))
        self.refreshButton.setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.searchWidget.attachTextEdit(self.contents)

        self.vcs = vcs

        font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.contents.document().setDefaultFont(font)

        self.highlighter = HgDiffHighlighter(self.contents.document())

        self.__diffGenerator = HgDiffGenerator(vcs, self)
        self.__diffGenerator.finished.connect(self.__generatorFinished)

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        self.__diffGenerator.stopProcess()
        e.accept()

    def start(self, fn, versions=None, bundle=None, qdiff=False, refreshable=False):
        """
        Public slot to start the hg diff command.

        @param fn filename to be diffed
        @type str
        @param versions list of versions to be diffed or None
        @type list of [str, str]
        @param bundle name of a bundle file
        @type str
        @param qdiff flag indicating qdiff command shall be used
        @type bool
        @param refreshable flag indicating a refreshable diff
        @type bool
        """
        self.refreshButton.setVisible(refreshable)

        self.errorGroup.hide()
        self.filename = fn

        self.highlighter.regenerateRules(
            {
                "text": Preferences.getDiffColour("TextColor"),
                "added": Preferences.getDiffColour("AddedColor"),
                "removed": Preferences.getDiffColour("RemovedColor"),
                "replaced": Preferences.getDiffColour("ReplacedColor"),
                "context": Preferences.getDiffColour("ContextColor"),
                "header": Preferences.getDiffColour("HeaderColor"),
                "whitespace": Preferences.getDiffColour("BadWhitespaceColor"),
            },
            Preferences.getEditorOtherFonts("MonospacedFont"),
        )

        self.contents.clear()
        self.filesCombo.clear()

        if qdiff:
            self.setWindowTitle(self.tr("Patch Contents"))

        self.raise_()
        self.activateWindow()

        procStarted = self.__diffGenerator.start(
            fn, versions=versions, bundle=bundle, qdiff=qdiff
        )
        if not procStarted:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("hg"),
            )

    def __generatorFinished(self):
        """
        Private slot connected to the finished signal.
        """
        self.refreshButton.setEnabled(True)

        diff, errors, fileSeparators = self.__diffGenerator.getResult()

        if diff:
            self.contents.setPlainText("".join(diff))
        else:
            self.contents.setPlainText(self.tr("There is no difference."))

        if errors:
            self.errorGroup.show()
            self.errors.setPlainText("".join(errors))
            self.errors.ensureCursorVisible()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(
            bool(diff)
        )
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        tc = self.contents.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.Start)
        self.contents.setTextCursor(tc)
        self.contents.ensureCursorVisible()

        self.filesCombo.addItem(self.tr("<Start>"), 0)
        self.filesCombo.addItem(self.tr("<End>"), -1)
        for oldFile, newFile, pos in sorted(fileSeparators):
            if not oldFile:
                self.filesCombo.addItem(newFile, pos)
            elif oldFile != newFile:
                self.filesCombo.addItem("{0}\n{1}".format(oldFile, newFile), pos)
            else:
                self.filesCombo.addItem(oldFile, pos)

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Save):
            self.on_saveButton_clicked()
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

    @pyqtSlot(int)
    def on_filesCombo_activated(self, index):
        """
        Private slot to handle the selection of a file.

        @param index activated row
        @type int
        """
        para = self.filesCombo.itemData(index)

        if para == 0:
            tc = self.contents.textCursor()
            tc.movePosition(QTextCursor.MoveOperation.Start)
            self.contents.setTextCursor(tc)
            self.contents.ensureCursorVisible()
        elif para == -1:
            tc = self.contents.textCursor()
            tc.movePosition(QTextCursor.MoveOperation.End)
            self.contents.setTextCursor(tc)
            self.contents.ensureCursorVisible()
        else:
            # step 1: move cursor to end
            tc = self.contents.textCursor()
            tc.movePosition(QTextCursor.MoveOperation.End)
            self.contents.setTextCursor(tc)
            self.contents.ensureCursorVisible()

            # step 2: move cursor to desired line
            tc = self.contents.textCursor()
            delta = tc.blockNumber() - para
            tc.movePosition(
                QTextCursor.MoveOperation.PreviousBlock,
                QTextCursor.MoveMode.MoveAnchor,
                delta,
            )
            self.contents.setTextCursor(tc)
            self.contents.ensureCursorVisible()

    @pyqtSlot()
    def on_saveButton_clicked(self):
        """
        Private slot to handle the Save button press.

        It saves the diff shown in the dialog to a file in the local
        filesystem.
        """
        if isinstance(self.filename, list):
            if len(self.filename) > 1:
                fname = self.vcs.splitPathList(self.filename)[0]
            else:
                dname, fname = self.vcs.splitPath(self.filename[0])
                if fname != ".":
                    fname = "{0}.diff".format(self.filename[0])
                else:
                    fname = dname
        else:
            fname = self.vcs.splitPath(self.filename)[0]

        fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Save Diff"),
            fname,
            self.tr("Patch Files (*.diff)"),
            None,
            EricFileDialog.DontConfirmOverwrite,
        )

        if not fname:
            return  # user aborted

        fpath = pathlib.Path(fname)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)
        if fpath.exists():
            res = EricMessageBox.yesNo(
                self,
                self.tr("Save Diff"),
                self.tr(
                    "<p>The patch file <b>{0}</b> already exists. Overwrite it?</p>"
                ).format(fpath),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return

        eol = ericApp().getObject("Project").getEolString()
        try:
            with fpath.open("w", encoding="utf-8", newline="") as f:
                f.write(eol.join(self.contents.toPlainText().splitlines()))
        except OSError as why:
            EricMessageBox.critical(
                self,
                self.tr("Save Diff"),
                self.tr(
                    "<p>The patch file <b>{0}</b> could not be saved."
                    "<br>Reason: {1}</p>"
                ).format(fpath, str(why)),
            )

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the display.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        self.refreshButton.setEnabled(False)

        self.start(self.filename, refreshable=True)
