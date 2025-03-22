# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the shelve extension interface.
"""

from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets import EricMessageBox
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

from ..HgDialog import HgDialog
from ..HgExtension import HgExtension


class Shelve(HgExtension):
    """
    Class implementing the shelve extension interface.
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

        self.__unshelveKeep = False

        self.__shelveBrowserDialog = None

    def shutdown(self):
        """
        Public method used to shutdown the shelve interface.
        """
        if self.__shelveBrowserDialog is not None:
            self.__shelveBrowserDialog.close()

    def __hgGetShelveNamesList(self):
        """
        Private method to get the list of shelved changes.

        @return list of shelved changes
        @rtype list of str
        """
        args = self.vcs.initCommand("shelve")
        args.append("--list")
        args.append("--quiet")

        client = self.vcs.getClient()
        output = client.runcommand(args)[0]

        shelveNamesList = []
        for line in output.splitlines():
            shelveNamesList.append(line.strip())

        return shelveNamesList[:]

    def hgShelve(self, name):
        """
        Public method to shelve current changes of files or directories.

        @param name directory or file name (string) or list of directory
            or file names
        @type list of str
        @return flag indicating that the project should be reread
        @rtype bool
        """
        from .HgShelveDataDialog import HgShelveDataDialog

        res = False
        dlg = HgShelveDataDialog(self.vcs.version, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            shelveName, dateTime, message, addRemove, keep = dlg.getData()

            args = self.vcs.initCommand("shelve")
            if shelveName:
                args.append("--name")
                args.append(shelveName)
            if message:
                args.append("--message")
                args.append(message)
            if addRemove:
                args.append("--addremove")
            if dateTime.isValid():
                args.append("--date")
                args.append(dateTime.toString("yyyy-MM-dd hh:mm:ss"))
            if self.vcs.version >= (5, 0, 0) and keep:
                args.append("--keep")
            args.append("-v")

            if isinstance(name, list):
                self.vcs.addArguments(args, name)
            else:
                args.append(name)

            dia = HgDialog(
                self.tr("Shelve current changes"), hg=self.vcs, parent=self.ui
            )
            res = dia.startProcess(args)
            if res:
                dia.exec()
                res = dia.hasAddOrDelete()
                self.vcs.checkVCSStatus()
        return res

    def hgShelveBrowser(self):
        """
        Public method to show the shelve browser dialog.
        """
        from .HgShelveBrowserDialog import HgShelveBrowserDialog

        if self.__shelveBrowserDialog is None:
            self.__shelveBrowserDialog = HgShelveBrowserDialog(self.vcs)
        self.__shelveBrowserDialog.show()
        self.__shelveBrowserDialog.start()

    def hgUnshelve(self, shelveName=""):
        """
        Public method to restore shelved changes to the project directory.

        @param shelveName name of the shelve to restore
        @type str
        @return flag indicating that the project should be reread
        @rtype bool
        """
        from .HgUnshelveDataDialog import HgUnshelveDataDialog

        res = False
        dlg = HgUnshelveDataDialog(
            self.__hgGetShelveNamesList(), shelveName=shelveName, parent=self.ui
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            shelveName, keep = dlg.getData()
            self.__unshelveKeep = keep  # store for potential continue

            args = self.vcs.initCommand("unshelve")
            if keep:
                args.append("--keep")
            if shelveName:
                args.append(shelveName)

            dia = HgDialog(
                self.tr("Restore shelved changes"), hg=self.vcs, parent=self.ui
            )
            res = dia.startProcess(args)
            if res:
                dia.exec()
                res = dia.hasAddOrDelete()
                self.vcs.checkVCSStatus()
        return res

    def hgUnshelveAbort(self):
        """
        Public method to abort the ongoing restore operation.

        @return flag indicating that the project should be reread
        @rtype bool
        """
        args = self.vcs.initCommand("unshelve")
        args.append("--abort")

        dia = HgDialog(self.tr("Abort restore operation"), hg=self.vcs, parent=self.ui)
        res = dia.startProcess(args)
        if res:
            dia.exec()
            res = dia.hasAddOrDelete()
            self.vcs.checkVCSStatus()
        return res

    def hgUnshelveContinue(self):
        """
        Public method to continue the ongoing restore operation.

        @return flag indicating that the project should be reread
        @rtype bool
        """
        args = self.vcs.initCommand("unshelve")
        if self.__unshelveKeep:
            args.append("--keep")
        args.append("--continue")

        dia = HgDialog(
            self.tr("Continue restore operation"), hg=self.vcs, parent=self.ui
        )
        res = dia.startProcess(args)
        if res:
            dia.exec()
            res = dia.hasAddOrDelete()
            self.vcs.checkVCSStatus()
        return res

    def hgDeleteShelves(self, shelveNames=None):
        """
        Public method to delete named shelves.

        @param shelveNames name of shelves to delete
        @type list of str
        """
        from .HgShelvesSelectionDialog import HgShelvesSelectionDialog

        if not shelveNames:
            dlg = HgShelvesSelectionDialog(
                self.tr("Select the shelves to be deleted:"),
                self.__hgGetShelveNamesList(),
                parent=self.ui,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                shelveNames = dlg.getSelectedShelves()
            else:
                return

        dlg = DeleteFilesConfirmationDialog(
            self.ui,
            self.tr("Delete shelves"),
            self.tr("Do you really want to delete these shelves?"),
            shelveNames,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            args = self.vcs.initCommand("shelve")
            args.append("--delete")
            args.extend(shelveNames)

            dia = HgDialog(self.tr("Delete shelves"), hg=self.vcs, parent=self.ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()

    def hgCleanupShelves(self):
        """
        Public method to delete all shelves.
        """
        res = EricMessageBox.yesNo(
            None,
            self.tr("Delete all shelves"),
            self.tr("""Do you really want to delete all shelved changes?"""),
        )
        if res:
            args = self.vcs.initCommand("shelve")
            args.append("--cleanup")

            dia = HgDialog(self.tr("Delete all shelves"), hg=self.vcs, parent=self.ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()
