# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the largefiles extension interface.
"""

import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from ..HgClient import HgClient
from ..HgDialog import HgDialog
from ..HgExtension import HgExtension


class Largefiles(HgExtension):
    """
    Class implementing the largefiles extension interface.
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

    def hgLfconvert(self, direction, projectFile):
        """
        Public slot to convert the repository format of the current project.

        @param direction direction of the conversion (one of 'largefiles' or 'normal')
        @type str
        @param projectFile file name of the current project file
        @type str
        @exception ValueError raised to indicate a bad value for the
            'direction' parameter.
        """
        from .LfConvertDataDialog import LfConvertDataDialog

        if direction not in ["largefiles", "normal"]:
            raise ValueError("Bad value for 'direction' parameter.")

        projectDir = os.path.dirname(projectFile)

        dlg = LfConvertDataDialog(projectDir, direction, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            newName, minSize, patterns = dlg.getData()
            newProjectFile = os.path.join(newName, os.path.basename(projectFile))

            # step 1: convert the current project to new project
            args = self.vcs.initCommand("lfconvert")
            if direction == "normal":
                args.append("--to-normal")
            else:
                args.append("--size")
                args.append(str(minSize))
            args.append(projectDir)
            args.append(newName)
            if direction == "largefiles" and patterns:
                args.extend(patterns)

            dia = HgDialog(
                self.tr("Convert Project - Converting"), hg=self.vcs, parent=self.ui
            )
            res = dia.startProcess(args)
            if res:
                dia.exec()
                res = dia.normalExit() and os.path.isdir(
                    os.path.join(newName, self.vcs.adminDir)
                )

            # step 2: create working directory contents
            if res:
                # step 2.1: start a command server client for the new repo
                client = HgClient(newName, "utf-8", self.vcs)
                ok, err = client.startServer()
                if not ok:
                    EricMessageBox.warning(
                        None,
                        self.tr("Mercurial Command Server"),
                        self.tr(
                            """<p>The Mercurial Command Server could not be"""
                            """ started.</p><p>Reason: {0}</p>"""
                        ).format(err),
                    )
                    return

                # step 2.2: create working directory contents
                args = self.vcs.initCommand("update")
                args.append("--verbose")
                dia = HgDialog(
                    self.tr("Convert Project - Extracting"), hg=self.vcs, parent=self.ui
                )
                res = dia.startProcess(args)
                if res:
                    dia.exec()
                    res = dia.normalExit() and os.path.isfile(newProjectFile)

                # step 2.3: stop the command server client for the new repo
                client.stopServer()

            # step 3: close current project and open new one
            if res:
                if direction == "largefiles":
                    self.vcs.hgEditConfig(
                        repoName=newName,
                        largefilesData={"minsize": minSize, "pattern": patterns},
                    )
                else:
                    self.vcs.hgEditConfig(repoName=newName, withLargefiles=False)
                QTimer.singleShot(
                    0,
                    lambda: ericApp().getObject("Project").openProject(newProjectFile),
                )

    def hgAdd(self, names, mode):
        """
        Public method used to add a file to the Mercurial repository.

        @param names file name(s) to be added
        @type str or list of str
        @param mode add mode (one of 'normal' or 'large')
        @type str
        """
        args = self.vcs.initCommand("add")
        args.append("-v")
        if mode == "large":
            args.append("--large")
        else:
            args.append("--normal")

        if isinstance(names, list):
            self.vcs.addArguments(args, names)
        else:
            args.append(names)

        dia = HgDialog(
            self.tr("Adding files to the Mercurial repository"),
            hg=self.vcs,
            parent=self.ui,
        )
        res = dia.startProcess(args)
        if res:
            dia.exec()

    def hgLfPull(self, revisions=None):
        """
        Public method to pull missing large files into the local repository.

        @param revisions list of revisions to pull
        @type list of str
        """
        from .LfRevisionsInputDialog import LfRevisionsInputDialog

        revs = []
        if revisions:
            revs = revisions
        else:
            dlg = LfRevisionsInputDialog(parent=self.ui)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                revs = dlg.getRevisions()

        if revs:
            args = self.vcs.initCommand("lfpull")
            args.append("-v")
            for rev in revs:
                args.append("--rev")
                args.append(rev)

            dia = HgDialog(self.tr("Pulling large files"), hg=self.vcs, parent=self.ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()

    def hgLfVerify(self, mode):
        """
        Public method to verify large files integrity.

        @param mode verify mode (one of 'large', 'lfa' or 'lfc')
        @type str
        """
        args = self.vcs.initCommand("verify")
        if mode == "large":
            args.append("--large")
        elif mode == "lfa":
            args.append("--lfa")
        elif mode == "lfc":
            args.append("--lfc")
        else:
            return

        dia = HgDialog(
            self.tr("Verifying the integrity of large files"),
            hg=self.vcs,
            parent=self.ui,
        )
        res = dia.startProcess(args)
        if res:
            dia.exec()
