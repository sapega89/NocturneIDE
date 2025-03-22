# -*- coding: utf-8 -*-

# Copyright (c) 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the fastexport extension interface.
"""

import os

from PyQt6.QtCore import QProcess, pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricProgressDialog import EricProgressDialog

from ..HgExtension import HgExtension
from ..HgUtilities import getHgExecutable, parseProgressInfo, prepareProcess


class Fastexport(HgExtension):
    """
    Class implementing the fastexport extension interface.
    """

    def __init__(self, vcs, ui=None):
        """
        Constructor

        @param vcs reference to the Mercurial vcs object
        @type Hg
        @param ui reference to a UI widget (defaults to None)
        @type QWidget
        """
        super().__init__(vcs, ui=ui)

        self.__process = None
        self.__progress = None

    def hgFastexport(self, revisions=None):
        """
        Public method to export the repository as a git fast-import stream.

        @param revisions list of revisions to be exported
        @type list of str
        """
        from .HgFastexportConfigDialog import HgFastexportConfigDialog

        dlg = HgFastexportConfigDialog(revisions=revisions, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            outputFile, revisions, authormap, importMarks, exportMarks = dlg.getData()

            if os.path.exists(outputFile):
                overwrite = EricMessageBox.yesNo(
                    self.ui,
                    self.tr("Mercurial Fastexport"),
                    self.tr(
                        "<p>The output file <b>{0}</b> exists already. Overwrite it?"
                        "</p>"
                    ).format(outputFile),
                )
                if not overwrite:
                    return

            repoPath = self.vcs.getClient().getRepository()
            hgExecutable = getHgExecutable()

            args = self.vcs.initCommand("fastexport")
            args.extend(["--config", "progress.assume-tty=True"])
            args.extend(["--config", "progress.format=topic bar number estimate"])
            if authormap:
                args.extend(["--authormap", authormap])
            if importMarks:
                args.extend(["--import-marks", importMarks])
            if exportMarks:
                args.extend(["--export-marks", exportMarks])
            for revision in revisions:
                args.extend(["--rev", revision])

            self.__progress = None

            self.__process = QProcess(parent=self)
            prepareProcess(self.__process)
            self.__process.setStandardOutputFile(outputFile)
            self.__process.setWorkingDirectory(repoPath)
            self.__process.readyReadStandardError.connect(self.__readStderr)
            self.__process.finished.connect(self.__processFinished)
            self.__process.start(hgExecutable, args)

    @pyqtSlot()
    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.
        """
        if self.__process is not None:
            output = str(
                self.__process.readAllStandardError(), self.vcs.getEncoding(), "replace"
            )
            msg = output.splitlines()[-1].strip()
            topic, value, maximum, estimate = parseProgressInfo(msg)
            if topic:
                # it is a valid progress line
                if self.__progress is None:
                    self.__progress = EricProgressDialog(
                        labelText="",
                        cancelButtonText=self.tr("Cancel"),
                        minimum=0,
                        maximum=maximum,
                        labelFormat=self.tr("%v/%m Changesets"),
                        parent=self.ui,
                    )
                    self.__progress.setWindowTitle(self.tr("Mercurial Fastexport"))
                    self.__progress.show()
                self.__progress.setLabelText(
                    self.tr("Exporting repository (time remaining: {0}) ...").format(
                        estimate
                    )
                )
                self.__progress.setValue(value)

                if self.__progress.wasCanceled() and self.__process is not None:
                    self.__process.terminate()

            else:
                if (
                    self.__progress
                    and not self.__progress.wasCanceled()
                    and output.strip()
                ):
                    EricMessageBox.warning(
                        self.ui,
                        self.tr("Mercurial Fastexport"),
                        self.tr(
                            "<p>The repository fastexport process sent an error"
                            " message.</p><p>{0}</p>"
                        ).format(output.strip()),
                    )

    @pyqtSlot(int, QProcess.ExitStatus)
    def __processFinished(self, exitCode, exitStatus):
        """
        Private slot to handle the process finished signal.

        @param exitCode exit code of the process
        @type int
        @param exitStatus exit status
        @type QProcess.ExitStatus
        """
        if self.__progress is not None:
            self.__progress.hide()
            self.__progress.deleteLater()
            self.__progress = None

        if exitStatus == QProcess.ExitStatus.NormalExit:
            if exitCode == 0:
                EricMessageBox.information(
                    self.ui,
                    self.tr("Mercurial Fastexport"),
                    self.tr(
                        "<p>The repository fastexport process finished"
                        " successfully.</p>"
                    ),
                )
            elif exitCode == 255:
                EricMessageBox.warning(
                    self.ui,
                    self.tr("Mercurial Fastexport"),
                    self.tr("<p>The repository fastexport process was cancelled.</p>"),
                )
            else:
                EricMessageBox.warning(
                    self.ui,
                    self.tr("Mercurial Fastexport"),
                    self.tr(
                        "<p>The repository fastexport process finished"
                        " with exit code <b>{0}</b>.</p>"
                    ).format(exitCode),
                )
        else:
            EricMessageBox.critical(
                self.ui,
                self.tr("Mercurial Fastexport"),
                self.tr("<p>The repository fastexport process crashed.</p>"),
            )

        self.__process.deleteLater()
        self.__process = None
