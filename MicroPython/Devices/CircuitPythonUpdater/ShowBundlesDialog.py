# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing the available bundles and their modules.
"""

import circup

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from .Ui_ShowBundlesDialog import Ui_ShowBundlesDialog


class ShowBundlesDialog(QDialog, Ui_ShowBundlesDialog):
    """
    Class implementing a dialog showing the available bundles and their modules.
    """

    def __init__(self, withModules, parent=None):
        """
        Constructor

        @param withModules flag indicating to list the modules and their version
        @type bool
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.header.setText(
            self.tr("Available Bundles and Modules")
            if withModules
            else self.tr("Available Bundles")
        )
        self.bundlesWidget.setColumnCount(2)

        localBundles = circup.get_bundles_local_dict().values()
        bundles = circup.get_bundles_list()
        availableModules = circup.get_bundle_versions(bundles)

        for bundle in bundles:
            topItm = QTreeWidgetItem(
                self.bundlesWidget, [bundle.key, bundle.current_tag]
            )
            topItm.setExpanded(True)
            if bundle.key in localBundles:
                font = topItm.font(0)
                font.setUnderline(True)
                topItm.setFont(0, font)
            itm = QTreeWidgetItem(topItm, [bundle.url])
            itm.setFirstColumnSpanned(True)

            if withModules:
                modulesHeader = QTreeWidgetItem(topItm, [self.tr("Modules")])
                modulesHeader.setExpanded(True)
                for name, mod in sorted(availableModules.items()):
                    if mod["bundle"] == bundle:
                        QTreeWidgetItem(
                            modulesHeader,
                            [name, mod.get("__version__", self.tr("unknown"))],
                        )

        self.bundlesWidget.resizeColumnToContents(0)
        self.bundlesWidget.resizeColumnToContents(1)
        self.bundlesWidget.sortItems(0, Qt.SortOrder.AscendingOrder)
