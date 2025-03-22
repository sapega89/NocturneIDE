# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the svn diff command
process.
"""

import os
import pathlib

import pysvn

from PyQt6.QtCore import QDateTime, Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricUtilities.EricMutexLocker import EricMutexLocker
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import OSUtilities

from .SvnDialogMixin import SvnDialogMixin
from .SvnDiffHighlighter import SvnDiffHighlighter
from .Ui_SvnDiffDialog import Ui_SvnDiffDialog


class SvnDiffDialog(QWidget, SvnDialogMixin, Ui_SvnDiffDialog):
    """
    Class implementing a dialog to show the output of the svn diff command.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Subversion
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        SvnDialogMixin.__init__(self)

        self.refreshButton = self.buttonBox.addButton(
            self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the display"))
        self.refreshButton.setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.searchWidget.attachTextEdit(self.contents)

        self.vcs = vcs

        font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.contents.document().setDefaultFont(font)

        self.highlighter = SvnDiffHighlighter(self.contents.document())

        self.client = self.vcs.getClient()
        self.client.callback_cancel = self._clientCancelCallback
        self.client.callback_get_login = self._clientLoginCallback
        self.client.callback_ssl_server_trust_prompt = (
            self._clientSslServerTrustPromptCallback
        )

    def __getVersionArg(self, version):
        """
        Private method to get a pysvn revision object for the given version
        number.

        @param version revision
        @type int or str
        @return revision object
        @rtype pysvn.Revision
        """
        if isinstance(version, int):
            return pysvn.Revision(pysvn.opt_revision_kind.number, version)
        elif version.startswith("{"):
            dateStr = version[1:-1]
            secs = QDateTime.fromString(dateStr, Qt.DateFormat.ISODate).toTime_t()
            return pysvn.Revision(pysvn.opt_revision_kind.date, secs)
        else:
            return {
                "HEAD": pysvn.Revision(pysvn.opt_revision_kind.head),
                "COMMITTED": pysvn.Revision(pysvn.opt_revision_kind.committed),
                "BASE": pysvn.Revision(pysvn.opt_revision_kind.base),
                "WORKING": pysvn.Revision(pysvn.opt_revision_kind.working),
                "PREV": pysvn.Revision(pysvn.opt_revision_kind.previous),
            }.get(version, pysvn.Revision(pysvn.opt_revision_kind.unspecified))

    def __getDiffSummaryKind(self, summaryKind):
        """
        Private method to get a string descripion of the diff summary.

        @param summaryKind
        @type pysvn.diff_summarize.summarize_kind
        @return one letter string indicating the change type
        @rtype str
        """
        if summaryKind == pysvn.diff_summarize_kind.delete:
            return "D"
        elif summaryKind == pysvn.diff_summarize_kind.modified:
            return "M"
        elif summaryKind == pysvn.diff_summarize_kind.added:
            return "A"
        elif summaryKind == pysvn.diff_summarize_kind.normal:
            return "N"
        else:
            return " "

    def start(
        self,
        fn,
        versions=None,
        urls=None,
        summary=False,
        pegRev=None,
        refreshable=False,
    ):
        """
        Public slot to start the svn diff command.

        @param fn filename to be diffed
        @type str
        @param versions list of versions to be diffed
        @type list of up to 2 int or None
        @param urls list of repository URLs
        @type list of [str, str]
        @param summary flag indicating a summarizing diff
            (only valid for URL diffs)
        @type bool
        @param pegRev revision number the filename is valid
        @type int
        @param refreshable flag indicating a refreshable diff
        @type bool
        """
        self.refreshButton.setVisible(refreshable)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self._reset()
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
        self.paras = 0

        self.filesCombo.clear()

        self.__oldFile = ""
        self.__oldFileLine = -1
        self.__fileSeparators = []

        if OSUtilities.hasEnvironmentEntry("TEMP"):
            tmpdir = OSUtilities.getEnvironmentEntry("TEMP")
        elif OSUtilities.hasEnvironmentEntry("TMPDIR"):
            tmpdir = OSUtilities.getEnvironmentEntry("TMPDIR")
        elif OSUtilities.hasEnvironmentEntry("TMP"):
            tmpdir = OSUtilities.getEnvironmentEntry("TMP")
        elif os.path.exists("/var/tmp"):  # secok
            tmpdir = "/var/tmp"  # secok
        elif os.path.exists("/usr/tmp"):
            tmpdir = "/usr/tmp"
        elif os.path.exists("/tmp"):  # secok
            tmpdir = "/tmp"  # secok
        else:
            EricMessageBox.critical(
                self,
                self.tr("Subversion Diff"),
                self.tr("""There is no temporary directory available."""),
            )
            return

        tmpdir = os.path.join(tmpdir, "svn_tmp")
        if not os.path.exists(tmpdir):
            os.mkdir(tmpdir)

        opts = self.vcs.options["global"] + self.vcs.options["diff"]
        recurse = "--non-recursive" not in opts

        if versions is not None:
            self.raise_()
            self.activateWindow()
            rev1 = self.__getVersionArg(versions[0])
            if len(versions) == 1:
                rev2 = self.__getVersionArg("WORKING")
            else:
                rev2 = self.__getVersionArg(versions[1])
        else:
            rev1 = self.__getVersionArg("BASE")
            rev2 = self.__getVersionArg("WORKING")

        if urls is not None:
            rev1 = self.__getVersionArg("HEAD")
            rev2 = self.__getVersionArg("HEAD")

        if isinstance(fn, list):
            dname, fnames = self.vcs.splitPathList(fn)
        else:
            dname, fname = self.vcs.splitPath(fn)
            fnames = [fname]

        with EricOverrideCursor():
            cwd = os.getcwd()
            os.chdir(dname)
            try:
                dname = ericApp().getObject("Project").getRelativePath(dname)
                if dname:
                    dname += "/"
                with EricMutexLocker(self.vcs.vcsExecutionMutex):
                    for name in fnames:
                        self.__showError(
                            self.tr("Processing file '{0}'...\n").format(name)
                        )
                        if urls is not None:
                            url1 = "{0}/{1}{2}".format(urls[0], dname, name)
                            url2 = "{0}/{1}{2}".format(urls[1], dname, name)
                            if summary:
                                diff_summary = self.client.diff_summarize(
                                    url1,
                                    revision1=rev1,
                                    url_or_path2=url2,
                                    revision2=rev2,
                                    recurse=recurse,
                                )
                                diff_list = []
                                for diff_sum in diff_summary:
                                    path = diff_sum["path"]
                                    diff_list.append(
                                        "{0} {1}".format(
                                            self.__getDiffSummaryKind(
                                                diff_sum["summarize_kind"]
                                            ),
                                            path,
                                        )
                                    )
                                diffText = os.linesep.join(diff_list)
                            else:
                                diffText = self.client.diff(
                                    tmpdir,
                                    url1,
                                    revision1=rev1,
                                    url_or_path2=url2,
                                    revision2=rev2,
                                    recurse=recurse,
                                )
                        else:
                            if pegRev is not None:
                                diffText = self.client.diff_peg(
                                    tmpdir,
                                    name,
                                    peg_revision=self.__getVersionArg(pegRev),
                                    revision_start=rev1,
                                    revision_end=rev2,
                                    recurse=recurse,
                                )
                            else:
                                diffText = self.client.diff(
                                    tmpdir,
                                    name,
                                    revision1=rev1,
                                    revision2=rev2,
                                    recurse=recurse,
                                )
                        for counter, line in enumerate(diffText.splitlines()):
                            if line.startswith("--- ") or line.startswith("+++ "):
                                self.__processFileLine(line)

                            self.__appendText("{0}{1}".format(line, os.linesep))
                            if counter % 30 == 0 and self._clientCancelCallback():
                                # check for cancel every 30 lines
                                break
                        if self._clientCancelCallback():
                            break
            except pysvn.ClientError as e:
                self.__showError(e.args[0])
            os.chdir(cwd)
        self.__finish()

        if self.paras == 0:
            self.contents.setPlainText(self.tr("There is no difference."))

        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(
            self.paras > 0
        )

    def __appendText(self, line):
        """
        Private method to append text to the end of the contents pane.

        @param line line of text to insert
        @type str
        """
        tc = self.contents.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.End)
        self.contents.setTextCursor(tc)
        self.contents.insertPlainText(line)
        self.paras += 1

    def __extractFileName(self, line):
        """
        Private method to extract the file name out of a file separator line.

        @param line line to be processed
        @type str
        @return extracted file name
        @rtype str
        """
        f = line.split(None, 1)[1]
        f = f.rsplit(None, 2)[0]
        return f

    def __processFileLine(self, line):
        """
        Private slot to process a line giving the old/new file.

        @param line line to be processed
        @type str
        """
        if line.startswith("---"):
            self.__oldFileLine = self.paras
            self.__oldFile = self.__extractFileName(line)
        else:
            self.__fileSeparators.append(
                (self.__oldFile, self.__extractFileName(line), self.__oldFileLine)
            )

    def __finish(self):
        """
        Private slot called when the user pressed the button.
        """
        self.refreshButton.setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        tc = self.contents.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.Start)
        self.contents.setTextCursor(tc)
        self.contents.ensureCursorVisible()

        self.filesCombo.addItem(self.tr("<Start>"), 0)
        self.filesCombo.addItem(self.tr("<End>"), -1)
        for oldFile, newFile, pos in sorted(self.__fileSeparators):
            if oldFile != newFile:
                self.filesCombo.addItem("{0}\n{1}".format(oldFile, newFile), pos)
            else:
                self.filesCombo.addItem(oldFile, pos)

        self._cancel()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__finish()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Save):
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

    def __showError(self, msg):
        """
        Private slot to show an error message.

        @param msg error message to show
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(msg)
        self.errors.ensureCursorVisible()
