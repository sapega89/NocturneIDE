# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the git diff command
process.
"""

import pathlib

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from eric7 import Preferences
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricTextEditSearchWidget import EricTextEditSearchWidget

from .GitDiffGenerator import GitDiffGenerator
from .GitDiffHighlighter import GitDiffHighlighter
from .Ui_GitDiffDialog import Ui_GitDiffDialog


class GitDiffDialog(QWidget, Ui_GitDiffDialog):
    """
    Class implementing a dialog to show the output of the git diff command
    process.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Git
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

        self.searchWidget = EricTextEditSearchWidget(self.contentsGroup)
        self.searchWidget.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.searchWidget.setObjectName("searchWidget")
        self.contentsGroup.layout().insertWidget(1, self.searchWidget)
        self.searchWidget.attachTextEdit(self.contents)

        self.searchWidget2 = EricTextEditSearchWidget(self.contentsGroup)
        self.searchWidget2.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.searchWidget2.setObjectName("searchWidget2")
        self.contentsGroup.layout().addWidget(self.searchWidget2)
        self.searchWidget2.attachTextEdit(self.contents2)

        self.setTabOrder(self.filesCombo, self.searchWidget)
        self.setTabOrder(self.searchWidget, self.contents)
        self.setTabOrder(self.contents, self.contents2)
        self.setTabOrder(self.contents2, self.searchWidget2)
        self.setTabOrder(self.searchWidget2, self.errors)

        self.vcs = vcs

        font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.contents.document().setDefaultFont(font)
        self.contents2.document().setDefaultFont(font)

        self.highlighter = GitDiffHighlighter(self.contents.document())
        self.highlighter2 = GitDiffHighlighter(self.contents2.document())

        self.__diffGenerator = GitDiffGenerator(vcs, self)
        self.__diffGenerator.finished.connect(self.__generatorFinished)

        self.__modeMessages = {
            "work2stage": self.tr("Working Tree to Staging Area"),
            "stage2repo": self.tr("Staging Area to HEAD Commit"),
            "work2repo": self.tr("Working Tree to HEAD Commit"),
            "work2stage2repo": self.tr(
                "Working to Staging (top) and Staging to HEAD (bottom)"
            ),
            "stash": self.tr("Stash Contents"),
            "stashName": self.tr("Stash Contents of {0}"),
        }

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        self.__diffGenerator.stopProcesses()
        e.accept()

    def start(
        self, fn, versions=None, diffMode="work2repo", stashName="", refreshable=False
    ):
        """
        Public slot to start the git diff command.

        @param fn filename to be diffed
        @type str
        @param versions list of versions to be diffed
        @type list of up to 2 str or None
        @param diffMode indication for the type of diff to be performed (
            'work2repo' compares the working tree with the HEAD commit,
            'work2stage' compares the working tree with the staging area,
            'stage2repo' compares the staging area with the HEAD commit,
            'work2stage2repo' compares the working tree with the staging area
                and the staging area with the HEAD commit,
            'stash' shows the diff for a stash)
        @type str
        @param stashName name of the stash to show a diff for
        @type str
        @param refreshable flag indicating a refreshable diff
        @type bool
        @exception ValueError raised to indicate a bad value for the 'diffMode'
            parameter.
        """
        if diffMode not in [
            "work2repo",
            "work2stage",
            "stage2repo",
            "work2stage2repo",
            "stash",
        ]:
            raise ValueError("Bad value for 'diffMode' parameter.")

        self.refreshButton.setVisible(refreshable)

        self.__filename = fn
        self.__diffMode = diffMode

        self.errorGroup.hide()

        colors = {
            "text": Preferences.getDiffColour("TextColor"),
            "added": Preferences.getDiffColour("AddedColor"),
            "removed": Preferences.getDiffColour("RemovedColor"),
            "replaced": Preferences.getDiffColour("ReplacedColor"),
            "context": Preferences.getDiffColour("ContextColor"),
            "header": Preferences.getDiffColour("HeaderColor"),
            "whitespace": Preferences.getDiffColour("BadWhitespaceColor"),
        }
        self.highlighter.regenerateRules(
            colors, Preferences.getEditorOtherFonts("MonospacedFont")
        )
        self.highlighter2.regenerateRules(
            colors, Preferences.getEditorOtherFonts("MonospacedFont")
        )

        self.contents.clear()
        self.contents2.clear()
        self.contents2.setVisible(diffMode == "work2stage2repo")
        self.searchWidget2.setVisible(diffMode == "work2stage2repo")

        self.filesCombo.clear()

        if diffMode in ["work2repo", "work2stage", "stage2repo", "work2stage2repo"]:
            self.contentsGroup.setTitle(
                self.tr("Difference ({0})").format(self.__modeMessages[diffMode])
            )

            if versions is not None:
                self.raise_()
                self.activateWindow()
        elif diffMode == "stash":
            if stashName:
                msg = self.__modeMessages["stashName"].format(stashName)
            else:
                msg = self.__modeMessages["stash"]
            self.contentsGroup.setTitle(self.tr("Difference ({0})").format(msg))

        procStarted = self.__diffGenerator.start(
            fn, versions=versions, diffMode=diffMode, stashName=stashName
        )
        if not procStarted:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("git"),
            )
            return

    def __generatorFinished(self):
        """
        Private slot connected to the finished signal.
        """
        self.refreshButton.setEnabled(True)

        diff1, diff2, errors, fileSeparators = self.__diffGenerator.getResult()

        if diff1:
            self.contents.setPlainText("".join(diff1))
        else:
            self.contents.setPlainText(self.tr("There is no difference."))

        if diff2:
            self.contents2.setPlainText("".join(diff2))
        else:
            self.contents2.setPlainText(self.tr("There is no difference."))

        if errors:
            self.errorGroup.show()
            self.errors.setPlainText(errors)
            self.errors.ensureCursorVisible()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(
            bool(diff2)
        )
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        for contents in [self.contents, self.contents2]:
            tc = contents.textCursor()
            tc.movePosition(QTextCursor.MoveOperation.Start)
            contents.setTextCursor(tc)
            contents.ensureCursorVisible()

        fileSeparators = self.__mergeFileSeparators(fileSeparators)
        self.filesCombo.addItem(self.tr("<Start>"), (0, 0))
        self.filesCombo.addItem(self.tr("<End>"), (-1, -1))
        for oldFile, newFile, pos1, pos2 in sorted(fileSeparators):
            if oldFile != newFile:
                self.filesCombo.addItem(
                    "{0} -- {1}".format(oldFile, newFile), (pos1, pos2)
                )
            else:
                self.filesCombo.addItem(oldFile, (pos1, pos2))

    def __mergeFileSeparators(self, fileSeparators):
        """
        Private method to merge the file separator entries.

        @param fileSeparators list of file separator entries to be merged
        @type list of str
        @return merged list of file separator entries
        @rtype list of str
        """
        separators = {}
        for oldFile, newFile, pos1, pos2 in sorted(fileSeparators):
            if (oldFile, newFile) not in separators:
                separators[(oldFile, newFile)] = [oldFile, newFile, pos1, pos2]
            else:
                if pos1 != -2:
                    separators[(oldFile, newFile)][2] = pos1
                if pos2 != -2:
                    separators[(oldFile, newFile)][3] = pos2
        return list(separators.values())

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
        para1, para2 = self.filesCombo.itemData(index)

        for para, contents in [(para1, self.contents), (para2, self.contents2)]:
            if para == 0:
                tc = contents.textCursor()
                tc.movePosition(QTextCursor.MoveOperation.Start)
                contents.setTextCursor(tc)
                contents.ensureCursorVisible()
            elif para == -1:
                tc = contents.textCursor()
                tc.movePosition(QTextCursor.MoveOperation.End)
                contents.setTextCursor(tc)
                contents.ensureCursorVisible()
            else:
                # step 1: move cursor to end
                tc = contents.textCursor()
                tc.movePosition(QTextCursor.MoveOperation.End)
                contents.setTextCursor(tc)
                contents.ensureCursorVisible()

                # step 2: move cursor to desired line
                tc = contents.textCursor()
                delta = tc.blockNumber() - para
                tc.movePosition(
                    QTextCursor.MoveOperation.PreviousBlock,
                    QTextCursor.MoveMode.MoveAnchor,
                    delta,
                )
                contents.setTextCursor(tc)
                contents.ensureCursorVisible()

    @pyqtSlot()
    def on_saveButton_clicked(self):
        """
        Private slot to handle the Save button press.

        It saves the diff shown in the dialog to a file in the local
        filesystem.
        """
        if isinstance(self.__filename, list):
            if len(self.__filename) > 1:
                fname = self.vcs.splitPathList(self.__filename)[0]
            else:
                dname, fname = self.vcs.splitPath(self.__filename[0])
                if fname != ".":
                    fname = "{0}.diff".format(self.__filename[0])
                else:
                    fname = dname
        else:
            fname = self.vcs.splitPath(self.__filename)[0]

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
                f.write(eol.join(self.contents2.toPlainText().splitlines()))
                f.write(eol)
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

        self.start(self.__filename, diffMode=self.__diffMode, refreshable=True)
