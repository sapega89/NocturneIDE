# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the histedit extension interface.
"""

import os

from PyQt6.QtWidgets import QDialog

from eric7.SystemUtilities import PythonUtilities

from ..HgDialog import HgDialog
from ..HgExtension import HgExtension


class Histedit(HgExtension):
    """
    Class implementing the histedit extension interface.
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

    def hgHisteditStart(self, rev=""):
        """
        Public method to start a histedit session.

        @param rev revision to start histedit at
        @type str
        @return flag indicating that the project should be reread
        @rtype bool
        """
        from .HgHisteditConfigDialog import HgHisteditConfigDialog

        res = False
        dlg = HgHisteditConfigDialog(
            self.vcs.hgGetTagsList(),
            self.vcs.hgGetBranchesList(),
            self.vcs.hgGetBookmarksList(),
            rev,
            parent=self.ui,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            rev, force, keep = dlg.getData()

            editor = os.path.join(os.path.dirname(__file__), "HgHisteditEditor.py")

            args = self.vcs.initCommand("histedit")
            args.append("-v")
            args.extend(
                [
                    "--config",
                    f"ui.editor={PythonUtilities.getPythonExecutable()} {editor}",
                ]
            )
            if keep:
                args.append("--keep")
            if rev:
                if rev == "--outgoing":
                    if force:
                        args.append("--force")
                else:
                    args.append("--rev")
                args.append(rev)

            dia = HgDialog(
                self.tr("Starting histedit session"), hg=self.vcs, parent=self.ui
            )
            res = dia.startProcess(args)
            if res:
                dia.exec()
                res = dia.hasAddOrDelete()
                self.vcs.checkVCSStatus()
        return res

    def hgHisteditContinue(self):
        """
        Public method to continue an interrupted histedit session.

        @return flag indicating that the project should be reread
        @rtype bool
        """
        editor = os.path.join(os.path.dirname(__file__), "HgHisteditEditor.py")

        args = self.vcs.initCommand("histedit")
        args.append("--continue")
        args.append("-v")
        args.extend(
            [
                "--config",
                f"ui.editor={PythonUtilities.getPythonExecutable()} {editor}",
            ]
        )

        dia = HgDialog(
            self.tr("Continue histedit session"), hg=self.vcs, parent=self.ui
        )
        res = dia.startProcess(args)
        if res:
            dia.exec()
            res = dia.hasAddOrDelete()
            self.vcs.checkVCSStatus()
        return res

    def hgHisteditAbort(self):
        """
        Public method to abort an interrupted histedit session.

        @return flag indicating that the project should be reread
        @rtype bool
        """
        editor = os.path.join(os.path.dirname(__file__), "HgHisteditEditor.py")

        args = self.vcs.initCommand("histedit")
        args.append("--abort")
        args.append("-v")
        args.extend(
            [
                "--config",
                f"ui.editor={PythonUtilities.getPythonExecutable()} {editor}",
            ]
        )

        dia = HgDialog(self.tr("Abort histedit session"), hg=self.vcs, parent=self.ui)
        res = dia.startProcess(args)
        if res:
            dia.exec()
            res = dia.hasAddOrDelete()
            self.vcs.checkVCSStatus()
        return res

    def hgHisteditEditPlan(self):
        """
        Public method to edit the remaining actions list of an interrupted
        histedit session.

        @return flag indicating that the project should be reread
        @rtype bool
        """
        editor = os.path.join(os.path.dirname(__file__), "HgHisteditEditor.py")

        args = self.vcs.initCommand("histedit")
        args.append("--edit-plan")
        args.append("-v")
        args.extend(
            [
                "--config",
                f"ui.editor={PythonUtilities.getPythonExecutable()} {editor}",
            ]
        )

        dia = HgDialog(self.tr("Edit Plan"), hg=self.vcs, parent=self.ui)
        res = dia.startProcess(args)
        if res:
            dia.exec()
            res = dia.hasAddOrDelete()
            self.vcs.checkVCSStatus()
        return res
