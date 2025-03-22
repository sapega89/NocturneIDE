# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the closehead extension interface.
"""

from PyQt6.QtWidgets import QDialog

from ..HgDialog import HgDialog
from ..HgExtension import HgExtension


class Closehead(HgExtension):
    """
    Class implementing the closehead extension interface.
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

    def hgCloseheads(self, revisions=None):
        """
        Public method to close arbitrary heads.

        @param revisions list of revisions of branch heads to be closed
        @type list of str
        """
        from .HgCloseHeadSelectionDialog import HgCloseHeadSelectionDialog

        message = ""
        if not revisions:
            dlg = HgCloseHeadSelectionDialog(self.vcs, parent=self.ui)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                revisions, message = dlg.getData()

        if not revisions:
            # still no revisions given; abort...
            return

        args = self.vcs.initCommand("close-head")
        if not message:
            if len(revisions) == 1:
                message = self.tr("Revision <{0}> closed.").format(revisions[0])
            else:
                message = self.tr("Revisions <{0}> closed.").format(
                    ", ".join(revisions)
                )
        args += ["--message", message]
        for revision in revisions:
            args += ["--rev", revision]

        dia = HgDialog(self.tr("Closing Heads"), hg=self.vcs, parent=self.ui)
        res = dia.startProcess(args)
        if res:
            dia.exec()
