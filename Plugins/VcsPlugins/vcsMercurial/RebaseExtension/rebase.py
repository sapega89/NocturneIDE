# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the rebase extension interface.
"""

from PyQt6.QtWidgets import QDialog

from ..HgDialog import HgDialog
from ..HgExtension import HgExtension


class Rebase(HgExtension):
    """
    Class implementing the rebase extension interface.
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

    def hgRebase(self):
        """
        Public method to rebase changesets to a different branch.

        @return flag indicating that the project should be reread
        @rtype bool
        """
        from .HgRebaseDialog import HgRebaseDialog

        res = False
        dlg = HgRebaseDialog(
            self.vcs.hgGetTagsList(),
            self.vcs.hgGetBranchesList(),
            self.vcs.hgGetBookmarksList(),
            self.vcs.version,
            parent=self.ui,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                indicator,
                sourceRev,
                destRev,
                collapse,
                keep,
                keepBranches,
                detach,
                dryRunOnly,
                dryRunConfirm,
            ) = dlg.getData()

            args = self.vcs.initCommand("rebase")
            if indicator == "S":
                args.append("--source")
                args.append(sourceRev)
            elif indicator == "B":
                args.append("--base")
                args.append(sourceRev)
            if destRev:
                args.append("--dest")
                args.append(destRev)
            if collapse:
                args.append("--collapse")
            if keep:
                args.append("--keep")
            if keepBranches:
                args.append("--keepbranches")
            if detach:
                args.append("--detach")
            if dryRunOnly:
                args.append("--dry-run")
            elif dryRunConfirm:
                args.append("--confirm")
            args.append("--verbose")

            dia = HgDialog(self.tr("Rebase Changesets"), hg=self.vcs, parent=self.ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()
                res = dia.hasAddOrDelete()
                self.vcs.checkVCSStatus()
        return res

    def hgRebaseContinue(self):
        """
        Public method to continue rebasing changesets from another branch.

        @return flag indicating that the project should be reread
        @rtype bool
        """
        args = self.vcs.initCommand("rebase")
        args.append("--continue")
        args.append("--verbose")

        dia = HgDialog(
            self.tr("Rebase Changesets (Continue)"), hg=self.vcs, parent=self.ui
        )
        res = dia.startProcess(args)
        if res:
            dia.exec()
            res = dia.hasAddOrDelete()
            self.vcs.checkVCSStatus()
        return res

    def hgRebaseAbort(self):
        """
        Public method to abort rebasing changesets from another branch.

        @return flag indicating that the project should be reread
        @rtype bool
        """
        args = self.vcs.initCommand("rebase")
        args.append("--abort")
        args.append("--verbose")

        dia = HgDialog(
            self.tr("Rebase Changesets (Abort)"), hg=self.vcs, parent=self.ui
        )
        res = dia.startProcess(args)
        if res:
            dia.exec()
            res = dia.hasAddOrDelete()
            self.vcs.checkVCSStatus()
        return res
