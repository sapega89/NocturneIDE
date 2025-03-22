# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Table of Contents viewer widget.
"""

from PyQt6.QtCore import QModelIndex, QSortFilterProxyModel, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtPdf import QPdfBookmarkModel, QPdfDocument
from PyQt6.QtWidgets import QLabel, QLineEdit, QTreeView, QVBoxLayout, QWidget


class PdfToCModel(QPdfBookmarkModel):
    """
    Class implementing a TOC model with page numbers.
    """

    def __init__(self, parent):
        """
        Constructor

        @param parent DESCRIPTION
        @type TYPE
        """
        super().__init__(parent)

    def columnCount(self, _index):
        """
        Public method to define the number of columns to be shown.

        @param _index index of the element (unused)
        @type QModelIndex
        @return column count (always 2)
        @rtype int
        """
        return 2

    def data(self, index, role):
        """
        Public method to return the requested data.

        @param index index of the element
        @type QModelIndex
        @param role data role
        @type Qt.ItemDataRole
        @return requested data
        @rtype Any
        """
        if not index.isValid():
            return None

        if index.column() == 1:
            if role == Qt.ItemDataRole.DisplayRole:
                page = index.data(QPdfBookmarkModel.Role.Page.value)
                return self.document().pageLabel(page)
            elif role == Qt.ItemDataRole.TextAlignmentRole:
                return Qt.AlignmentFlag.AlignRight

        return super().data(index, role)


class PdfToCWidget(QWidget):
    """
    Class implementing a Table of Contents viewer widget.

    @signal topicActivated(page, zoomFactor) emitted to navigate to the selected topic
    """

    topicActivated = pyqtSignal(int, float)

    def __init__(self, document, parent=None):
        """
        Constructor

        @param document reference to the PDF document object
        @type QPdfDocument
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.__layout = QVBoxLayout(self)

        self.__header = QLabel("<h2>{0}</h2>".format(self.tr("Contents")))
        self.__header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.__layout.addWidget(self.__header)

        self.__searchEdit = QLineEdit(self)
        self.__searchEdit.setPlaceholderText(self.tr("Search ..."))
        self.__searchEdit.setClearButtonEnabled(True)
        self.__layout.addWidget(self.__searchEdit)

        self.__tocWidget = QTreeView(self)
        self.__tocWidget.setHeaderHidden(True)
        self.__tocWidget.setExpandsOnDoubleClick(False)
        self.__tocModel = PdfToCModel(self)
        self.__tocModel.setDocument(document)
        self.__tocFilterModel = QSortFilterProxyModel(self)
        self.__tocFilterModel.setRecursiveFilteringEnabled(True)
        self.__tocFilterModel.setFilterCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self.__tocFilterModel.setSourceModel(self.__tocModel)
        self.__tocWidget.setModel(self.__tocFilterModel)
        self.__layout.addWidget(self.__tocWidget)

        self.setLayout(self.__layout)

        self.__searchEdit.setEnabled(False)
        self.__tocWidget.setEnabled(False)

        self.__tocWidget.activated.connect(self.__topicSelected)
        document.statusChanged.connect(self.__handleDocumentStatus)
        self.__searchEdit.textEdited.connect(self.__searchTextChanged)

    @pyqtSlot(QModelIndex)
    def __topicSelected(self, index):
        """
        Private slot to handle the selection of a ToC entry.

        @param index index of the activated entry
        @type QModelIndex
        """
        if not index.isValid():
            return

        page = index.data(QPdfBookmarkModel.Role.Page.value)
        zoomFactor = index.data(QPdfBookmarkModel.Role.Zoom.value)

        self.topicActivated.emit(page, zoomFactor)

    @pyqtSlot(QPdfDocument.Status)
    def __handleDocumentStatus(self, status):
        """
        Private slot to handle a change of the document status.

        @param status document status
        @type QPdfDocument.Status
        """
        ready = status == QPdfDocument.Status.Ready
        if ready:
            self.__tocWidget.expandAll()
            for column in range(self.__tocModel.columnCount(QModelIndex())):
                self.__tocWidget.resizeColumnToContents(column)

        self.__searchEdit.setEnabled(ready)
        self.__tocWidget.setEnabled(ready)

    @pyqtSlot(str)
    def __searchTextChanged(self, text):
        """
        Private slot to handle a change of the search text.

        @param text search text
        @type str
        """
        self.__tocFilterModel.setFilterWildcard("*{0}*".format(text))
        self.__tocWidget.expandAll()
