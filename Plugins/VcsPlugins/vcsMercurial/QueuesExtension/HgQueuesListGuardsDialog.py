# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the guards of a selected patch.
"""

from PyQt6.QtCore import QCoreApplication, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QListWidgetItem

from eric7.EricGui import EricPixmapCache

from .Ui_HgQueuesListGuardsDialog import Ui_HgQueuesListGuardsDialog


class HgQueuesListGuardsDialog(QDialog, Ui_HgQueuesListGuardsDialog):
    """
    Class implementing a dialog to show the guards of a selected patch.
    """

    def __init__(self, vcs, patchesList, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Hg
        @param patchesList list of patches
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.vcs = vcs
        self.__hgClient = vcs.getClient()

        self.patchSelector.addItems([""] + patchesList)

        self.show()
        QCoreApplication.processEvents()

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if self.__hgClient.isExecuting():
            self.__hgClient.cancel()

        e.accept()

    def start(self):
        """
        Public slot to start the list command.
        """
        self.on_patchSelector_activated(0)

    @pyqtSlot(int)
    def on_patchSelector_activated(self, index):
        """
        Private slot to get the list of guards for the given patch name.

        @param index index of the selected entry
        @type int
        """
        patch = self.patchSelector.itemText(index)
        self.guardsList.clear()
        self.patchNameLabel.setText("")

        args = self.vcs.initCommand("qguard")
        if patch:
            args.append(patch)

        output = self.__hgClient.runcommand(args)[0].strip()

        if output:
            patchName, guards = output.split(":", 1)
            self.patchNameLabel.setText(patchName)
            guardsList = guards.strip().split()
            for guard in guardsList:
                if guard.startswith("+"):
                    icon = EricPixmapCache.getIcon("plus")
                    guard = guard[1:]
                elif guard.startswith("-"):
                    icon = EricPixmapCache.getIcon("minus")
                    guard = guard[1:]
                else:
                    icon = None
                    guard = self.tr("Unguarded")
                itm = QListWidgetItem(guard, self.guardsList)
                if icon:
                    itm.setIcon(icon)
