# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the gpg extension interface.
"""

from PyQt6.QtWidgets import QDialog

from ..HgDialog import HgDialog
from ..HgExtension import HgExtension
from ..HgRevisionSelectionDialog import HgRevisionSelectionDialog


class Gpg(HgExtension):
    """
    Class implementing the gpg extension interface.
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

        self.gpgSignaturesDialog = None

    def shutdown(self):
        """
        Public method used to shutdown the gpg interface.
        """
        if self.gpgSignaturesDialog is not None:
            self.gpgSignaturesDialog.close()

    def hgGpgSignatures(self):
        """
        Public method used to list all signed changesets.
        """
        from .HgGpgSignaturesDialog import HgGpgSignaturesDialog

        self.gpgSignaturesDialog = HgGpgSignaturesDialog(self.vcs)
        self.gpgSignaturesDialog.show()
        self.gpgSignaturesDialog.start()

    def hgGpgVerifySignatures(self, rev=None):
        """
        Public method used to verify the signatures of a revision.

        @param rev revision to check
        @type str
        """
        if rev is None:
            dlg = HgRevisionSelectionDialog(
                self.vcs.hgGetTagsList(),
                self.vcs.hgGetBranchesList(),
                bookmarksList=self.vcs.hgGetBookmarksList(),
                revset=False,
                parent=self.ui,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                rev = dlg.getRevision()

        if rev is not None:
            if rev == "":
                rev = "tip"
            args = self.vcs.initCommand("sigcheck")
            args.append(rev)

            dia = HgDialog(self.tr("Verify Signatures"), hg=self.vcs, parent=self.ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()

    def hgGpgSign(self, revisions=None):
        """
        Public method used to list the available bookmarks.

        @param revisions list containing the revisions to be signed
        @type list of str
        """
        from .HgGpgSignDialog import HgGpgSignDialog

        if revisions is None:
            dlg = HgGpgSignDialog(
                self.vcs.hgGetTagsList(),
                self.vcs.hgGetBranchesList(),
                self.vcs.hgGetBookmarksList(),
                parent=self.ui,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                revision, noCommit, message, keyId, local, force = dlg.getData()
                if revision:
                    revisions = [revision]
                else:
                    revisions = []
            else:
                return
        else:
            noCommit = False
            message = ""
            keyId = ""
            local = False
            force = False

        args = self.vcs.initCommand("sign")
        if noCommit:
            args.append("--no-commit")
        if message:
            args.append("--message")
            args.append(message)
        if keyId:
            args.append("--key")
            args.append(keyId)
        if local:
            args.append("--local")
        if force:
            args.append("--force")
        for rev in revisions:
            args.append(rev)

        dia = HgDialog(self.tr("Sign Revision"), hg=self.vcs, parent=self.ui)
        res = dia.startProcess(args)
        if res:
            dia.exec()
