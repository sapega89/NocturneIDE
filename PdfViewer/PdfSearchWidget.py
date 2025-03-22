# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Search widget.
"""

from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtPdf import QPdfDocument, QPdfLink, QPdfSearchModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache


class PdfSearchResultsWidget(QTreeWidget):
    """
    Class implementing a widget to show the search results.

    @signal rowCountChanged() emitted to indicate a change of the number
        of items
    @signal searchNextAvailable(bool) emitted to indicate the availability of
        search results after the current one
    @signal searchPrevAvailable(bool) emitted to indicate the availability of
        search results before the current one
    @signal searchResult(QPdfLink) emitted to send the link of a search result
    @signal searchCleared() emitted to indicate that the search results have been
        cleared
    """

    rowCountChanged = pyqtSignal()
    searchNextAvailable = pyqtSignal(bool)
    searchPrevAvailable = pyqtSignal(bool)
    searchResult = pyqtSignal(QPdfLink)
    searchCleared = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.setColumnCount(2)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.__searchModel = QPdfSearchModel(self)
        self.__searchModel.modelReset.connect(self.__clear)
        self.__searchModel.rowsInserted.connect(self.__rowsInserted)

        self.currentItemChanged.connect(self.__handleCurrentItemChanged)

    def setSearchString(self, searchString):
        """
        Public method to set the search string.

        @param searchString search string
        @type str
        """
        self.__searchModel.setSearchString(searchString)

    def searchString(self):
        """
        Public method to get the current search string.

        @return search string
        @rtype str
        """
        return self.__searchModel.searchString()

    def setDocument(self, document):
        """
        Public method to set the PDF document object to be searched.

        @param document reference to the PDF document object
        @type QPdfDocument
        """
        self.__searchModel.setDocument(document)

    def document(self):
        """
        Public method to get the reference to the PDF document object.

        @return reference to the PDF document object
        @rtype QPdfDocument
        """
        return self.__searchModel.document()

    @pyqtSlot()
    def __clear(self):
        """
        Private slot to clear the list of search results.
        """
        self.clear()

        self.searchCleared.emit()
        self.rowCountChanged.emit()
        self.searchNextAvailable.emit(False)
        self.searchPrevAvailable.emit(False)

    @pyqtSlot(QModelIndex, int, int)
    def __rowsInserted(self, parent, first, last):
        """
        Private slot to handle the insertion of rows of the search model.

        @param parent reference to the parent index
        @type QModelIndex
        @param first first row inserted
        @type int
        @param last last row inserted
        @type int
        """
        contextLength = Preferences.getPdfViewer("PdfSearchContextLength")

        for row in range(first, last + 1):
            index = self.__searchModel.index(row, 0)
            itm = QTreeWidgetItem(
                self,
                [
                    self.tr("Page {0}").format(
                        self.__searchModel.document().pageLabel(
                            self.__searchModel.data(
                                index, QPdfSearchModel.Role.Page.value
                            )
                        )
                    ),
                    "",
                ],
            )
            contextBefore = self.__searchModel.data(
                index, QPdfSearchModel.Role.ContextBefore.value
            )
            if len(contextBefore) > contextLength:
                contextBefore = "... {0}".format(contextBefore[-contextLength:])
            contextAfter = self.__searchModel.data(
                index, QPdfSearchModel.Role.ContextAfter.value
            )
            if len(contextAfter) > contextLength:
                contextAfter = "{0} ...".format(contextAfter[:contextLength])
            resultLabel = QLabel(
                self.tr(
                    "{0}<b>{1}</b>{2}", "context before, search string, context after"
                ).format(contextBefore, self.searchString(), contextAfter)
            )
            self.setItemWidget(itm, 1, resultLabel)

            if Preferences.getPdfViewer("PdfSearchHighlightAll"):
                self.searchResult.emit(self.__searchModel.resultAtIndex(row))

        for column in range(self.columnCount()):
            self.resizeColumnToContents(column)

        self.rowCountChanged.emit()
        self.searchNextAvailable.emit(True)

    def rowCount(self):
        """
        Public method to get the number of rows.

        @return number of rows
        @rtype int
        """
        return self.topLevelItemCount()

    def currentRow(self):
        """
        Public method to get the current row.

        @return current row
        @rtype int
        """
        curItem = self.currentItem()
        if curItem is None:
            return -1
        else:
            return self.indexOfTopLevelItem(curItem)

    def setCurrentRow(self, row):
        """
        Public method to set the current row.

        @param row row number to make the current row
        @type int
        """
        if 0 <= row < self.topLevelItemCount():
            self.setCurrentItem(self.topLevelItem(row))

    def searchResultData(self, item, role):
        """
        Public method to get data of a search result item.

        @param item reference to the search result item
        @type QTreeWidgetItem
        @param role item data role
        @type QPdfSearchModel.Role or Qt.ItemDataRole
        @return requested data
        @rtype Any
        """
        row = self.indexOfTopLevelItem(item)
        index = self.__searchModel.index(row, 0)
        return self.__searchModel.data(index, role)

    def getPdfLink(self, item):
        """
        Public method to get the PDF link associated with a search result item.

        @param item reference to the search result item
        @type QTreeWidgetItem
        @return associated PDF link
        @rtype QPdfLink
        """
        row = self.indexOfTopLevelItem(item)
        return self.__searchModel.resultAtIndex(row)

    @pyqtSlot()
    def __handleCurrentItemChanged(self):
        """
        Private slot to handle a change of the current item.
        """
        hasSearchResults = bool(self.topLevelItemCount())
        currentRow = self.currentRow()
        self.searchPrevAvailable.emit(hasSearchResults and currentRow > 0)
        self.searchNextAvailable.emit(
            hasSearchResults and currentRow < self.topLevelItemCount() - 1
        )


class PdfSearchWidget(QWidget):
    """
    Class implementing a Search widget.

    @signal searchResultActivated(QPdfLink) emitted to send the activated search
        result link
    @signal searchNextAvailable(bool) emitted to indicate the availability of
        search results after the current one
    @signal searchPrevAvailable(bool) emitted to indicate the availability of
        search results before the current one
    @signal searchResult(QPdfLink) emitted to send the link of a search result
    @signal searchCleared() emitted to indicate that the search results have been
        cleared
    """

    searchResultActivated = pyqtSignal(QPdfLink)
    searchNextAvailable = pyqtSignal(bool)
    searchPrevAvailable = pyqtSignal(bool)
    searchResult = pyqtSignal(QPdfLink)
    searchCleared = pyqtSignal()

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

        # Line 1: a header label
        self.__header = QLabel("<h2>{0}</h2>".format(self.tr("Search")))
        self.__header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.__layout.addWidget(self.__header)

        # Line 2: search entry and navigation buttons
        self.__searchLineLayout = QHBoxLayout()

        self.__searchEdit = QLineEdit(self)
        self.__searchEdit.setPlaceholderText(self.tr("Search ..."))
        self.__searchEdit.setClearButtonEnabled(True)
        self.__searchLineLayout.addWidget(self.__searchEdit)

        # layout for the navigation buttons
        self.__buttonsLayout = QHBoxLayout()
        self.__buttonsLayout.setSpacing(0)

        self.__findPrevButton = QToolButton(self)
        self.__findPrevButton.setToolTip(
            self.tr("Press to move to the previous occurrence")
        )
        self.__findPrevButton.setIcon(EricPixmapCache.getIcon("1leftarrow"))
        self.__buttonsLayout.addWidget(self.__findPrevButton)

        self.__findNextButton = QToolButton(self)
        self.__findNextButton.setToolTip(
            self.tr("Press to move to the next occurrence")
        )
        self.__findNextButton.setIcon(EricPixmapCache.getIcon("1rightarrow"))
        self.__buttonsLayout.addWidget(self.__findNextButton)

        self.__searchLineLayout.addLayout(self.__buttonsLayout)
        self.__layout.addLayout(self.__searchLineLayout)

        self.__resultsWidget = PdfSearchResultsWidget(self)
        self.__resultsWidget.setDocument(document)
        self.__layout.addWidget(self.__resultsWidget)

        self.__infoLabel = QLabel(self)
        self.__infoLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.__layout.addWidget(self.__infoLabel)

        self.setLayout(self.__layout)

        self.__searchEdit.setEnabled(False)
        self.__resultsWidget.setEnabled(False)
        self.__findPrevButton.setEnabled(False)
        self.__findNextButton.setEnabled(False)

        self.__resultsWidget.itemActivated.connect(self.__entrySelected)
        document.statusChanged.connect(self.__handleDocumentStatus)
        self.__searchEdit.returnPressed.connect(self.__search)
        self.__searchEdit.textChanged.connect(self.__searchTextChanged)
        self.__resultsWidget.searchNextAvailable.connect(self.searchNextAvailable)
        self.__resultsWidget.searchPrevAvailable.connect(self.searchPrevAvailable)
        self.__resultsWidget.searchNextAvailable.connect(
            self.__findNextButton.setEnabled
        )
        self.__resultsWidget.searchPrevAvailable.connect(
            self.__findPrevButton.setEnabled
        )
        self.__findNextButton.clicked.connect(self.nextResult)
        self.__findPrevButton.clicked.connect(self.previousResult)
        self.__resultsWidget.searchCleared.connect(self.searchCleared)
        self.__resultsWidget.searchResult.connect(self.searchResult)
        self.__resultsWidget.rowCountChanged.connect(self.__updateInfoLabel)
        self.__resultsWidget.currentItemChanged.connect(self.__updateInfoLabel)

        self.__updateInfoLabel()

    @pyqtSlot(QPdfDocument.Status)
    def __handleDocumentStatus(self, status):
        """
        Private slot to handle a change of the document status.

        @param status document status
        @type QPdfDocument.Status
        """
        ready = status == QPdfDocument.Status.Ready

        self.__searchEdit.setEnabled(ready)
        self.__resultsWidget.setEnabled(ready)

        if not ready:
            self.__searchEdit.clear()

    @pyqtSlot(str)
    def __searchTextChanged(self, text):
        """
        Private slot to handle a change of the search string.

        @param text search string
        @type str
        """
        if not text:
            self.__resultsWidget.setSearchString("")

    @pyqtSlot()
    def __search(self):
        """
        Private slot to initiate a new search.
        """
        searchString = self.__searchEdit.text()
        self.__resultsWidget.setSearchString(searchString)

    @pyqtSlot(QTreeWidgetItem)
    def __entrySelected(self, item):
        """
        Private slot to handle the selection of a search result entry.

        @param item reference to the selected item
        @type QTreeWidgetItem
        """
        link = self.__resultsWidget.getPdfLink(item)
        self.searchResultActivated.emit(link)

    @pyqtSlot()
    def nextResult(self):
        """
        Public slot to activate the next result.
        """
        row = self.__resultsWidget.currentRow()
        if row < self.__resultsWidget.rowCount() - 1:
            nextItem = self.__resultsWidget.topLevelItem(row + 1)
            self.__resultsWidget.setCurrentItem(nextItem)
            self.__entrySelected(nextItem)

    @pyqtSlot()
    def previousResult(self):
        """
        Public slot to activate the previous result.
        """
        row = self.__resultsWidget.currentRow()
        if row > 0:
            prevItem = self.__resultsWidget.topLevelItem(row - 1)
            self.__resultsWidget.setCurrentItem(prevItem)
            self.__entrySelected(prevItem)

    @pyqtSlot()
    def activateSearch(self):
        """
        Public slot to 'activate' a search.
        """
        self.__searchEdit.setFocus(Qt.FocusReason.OtherFocusReason)
        self.__searchEdit.selectAll()

    @pyqtSlot()
    def __updateInfoLabel(self):
        """
        Private slot to update the data of the info label.
        """
        rowCount = self.__resultsWidget.rowCount()
        if rowCount:
            currentRow = self.__resultsWidget.currentRow()
            if currentRow == -1:  # no result selected yet
                self.__infoLabel.setText(self.tr("%n Result(s)", "", rowCount))
            else:
                self.__infoLabel.setText(
                    self.tr("{0} of %n Results", "", rowCount).format(currentRow + 1)
                )
        else:
            self.__infoLabel.setText(self.tr("No results"))
