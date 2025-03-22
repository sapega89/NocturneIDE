# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a modified QSortFilterProxyModel.
"""

from PyQt6.QtCore import QModelIndex, QSortFilterProxyModel, Qt


class EricTreeSortFilterProxyModel(QSortFilterProxyModel):
    """
    Class implementing a modified QSortFilterProxyModel.

    It always accepts the root nodes in the tree so filtering is only done
    on the children.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """
        Public method to determine, if the row is acceptable.

        @param sourceRow row number in the source model
        @type int
        @param sourceParent index of the source item
        @type QModelIndex
        @return flag indicating acceptance
        @rtype bool
        """
        idx = self.sourceModel().index(sourceRow, 0, sourceParent)
        if self.sourceModel().hasChildren(idx):
            return True

        return QSortFilterProxyModel.filterAcceptsRow(self, sourceRow, sourceParent)

    def hasChildren(self, parent=None):
        """
        Public method to check, if a parent node has some children.

        @param parent index of the parent node
        @type QModelIndex
        @return flag indicating the presence of children
        @rtype bool
        """
        if parent is None:
            parent = QModelIndex()
        sindex = self.mapToSource(parent)
        return self.sourceModel().hasChildren(sindex)
