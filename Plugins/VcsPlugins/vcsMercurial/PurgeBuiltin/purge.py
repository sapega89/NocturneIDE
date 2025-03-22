# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the purge extension interface.
"""

from PyQt6.QtWidgets import QDialog

from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

from ..HgDialog import HgDialog
from ..HgExtension import HgExtension


class Purge(HgExtension):
    """
    Class implementing the purge extension interface.
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

        self.purgeListDialog = None

    def shutdown(self):
        """
        Public method used to shutdown the purge interface.
        """
        if self.purgeListDialog is not None:
            self.purgeListDialog.close()

    def __getEntries(self, deleteAll, ignoredOnly):
        """
        Private method to get a list of files/directories about to be purged.

        @param deleteAll flag indicating to delete all files including ignored
            ones
        @type bool
        @param ignoredOnly flag indicating to delete ignored files only
        @type bool
        @return name of the current patch
        @rtype str
        """
        purgeEntries = []

        args = self.vcs.initCommand("purge")
        args.extend(["--print", "--no-confirm"])
        if deleteAll:
            args.append("--all")
        elif ignoredOnly:
            args.append("--ignored")

        client = self.vcs.getClient()
        out, _err = client.runcommand(args)
        if out:
            purgeEntries = out.strip().split()

        return purgeEntries

    def hgPurge(self, deleteAll=False, ignoredOnly=False):
        """
        Public method to purge files and directories not tracked by Mercurial.

        @param deleteAll flag indicating to delete all files including ignored
            ones (defaults to False)
        @type bool (optional)
        @param ignoredOnly flag indicating to delete ignored files only (defaults
            to False)
        @type bool (optional)
        """
        if deleteAll:
            title = self.tr("Purge All Files")
            message = self.tr(
                """Do really want to delete all files not tracked by"""
                """ Mercurial (including ignored ones)?"""
            )
        else:
            title = self.tr("Purge Files")
            message = self.tr(
                """Do really want to delete files not tracked by Mercurial?"""
            )
        entries = self.__getEntries(deleteAll, ignoredOnly)
        dlg = DeleteFilesConfirmationDialog(self.ui, title, message, entries)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            args = self.vcs.initCommand("purge")
            args.append("--no-confirm")
            if deleteAll:
                args.append("--all")
            elif ignoredOnly:
                args.append("--ignored")
            args.append("-v")

            dia = HgDialog(title, hg=self.vcs, parent=self.ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()

    def hgPurgeList(self, deleteAll=False, ignoredOnly=False):
        """
        Public method to list files and directories not tracked by Mercurial.

        @param deleteAll flag indicating to delete all files including ignored
            ones (defaults to False)
        @type bool (optional)
        @param ignoredOnly flag indicating to delete ignored files only (defaults
            to False)
        @type bool (optional)
        """
        from .HgPurgeListDialog import HgPurgeListDialog

        entries = self.__getEntries(deleteAll, ignoredOnly)
        self.purgeListDialog = HgPurgeListDialog(entries)
        self.purgeListDialog.show()
