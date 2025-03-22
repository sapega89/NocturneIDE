# -*- coding: utf-8 -*-

# Copyright (c) 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the uncommit extension interface.
"""

from PyQt6.QtWidgets import QDialog

from ..HgDialog import HgDialog
from ..HgExtension import HgExtension


class Uncommit(HgExtension):
    """
    Class implementing the uncommit extension interface.
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

    def hgUncommit(self, names=None):
        """
        Public method to undo the effect of a local commit.

        @param names list of file or directory paths (defaults to None)
        @type list of str
        @return flag indicating that the project should be reread
        @rtype bool
        """
        from .HgUncommitDialog import HgUncommitDialog

        res = False
        dlg = HgUncommitDialog(vcs=self.vcs, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            message, keep, dirty, author, date = dlg.getUncommitData()

            args = self.vcs.initCommand("uncommit")
            if message:
                args.extend(["--message", message])
            if keep:
                args.append("--keep")
            if dirty:
                args.append("--allow-dirty-working-copy")
            if author:
                args.extend(["--user", author])
            if date:
                args.extend(["--date", date])
            args.append("--verbose")

            if names is not None:
                self.vcs.addArguments(args, names)

            dia = HgDialog(self.tr("Undo Local Commit"), hg=self.vcs, parent=self.ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()
                res = dia.hasAddOrDelete()
                self.vcs.checkVCSStatus()
        return res
