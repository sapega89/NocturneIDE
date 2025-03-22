# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show all guards for all patches.
"""

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from eric7.EricGui import EricPixmapCache

from .Ui_HgQueuesListAllGuardsDialog import Ui_HgQueuesListAllGuardsDialog


class HgQueuesListAllGuardsDialog(QDialog, Ui_HgQueuesListAllGuardsDialog):
    """
    Class implementing a dialog to show all guards for all patches.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the VCS object (Hg)
        @type Hg
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.vcs = vcs
        self.__hgClient = vcs.getClient()

        self.show()
        QCoreApplication.processEvents()

    def start(self):
        """
        Public slot to start the list command.
        """
        args = self.vcs.initCommand("qguard")
        args.append("--list")

        output = self.__hgClient.runcommand(args)[0]

        if output:
            guardsDict = {}
            for line in output.splitlines():
                if line:
                    patchName, guards = line.strip().split(":", 1)
                    guardsDict[patchName] = guards.strip().split()
            for patchName in sorted(guardsDict):
                patchItm = QTreeWidgetItem(self.guardsTree, [patchName])
                patchItm.setExpanded(True)
                for guard in guardsDict[patchName]:
                    if guard.startswith("+"):
                        icon = EricPixmapCache.getIcon("plus")
                        guard = guard[1:]
                    elif guard.startswith("-"):
                        icon = EricPixmapCache.getIcon("minus")
                        guard = guard[1:]
                    else:
                        icon = None
                        guard = self.tr("Unguarded")
                    itm = QTreeWidgetItem(patchItm, [guard])
                    if icon:
                        itm.setIcon(0, icon)
        else:
            QTreeWidgetItem(self.guardsTree, [self.tr("no patches found")])
