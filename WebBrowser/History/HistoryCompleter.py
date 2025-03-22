# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a special completer for the history.
"""

import re

from PyQt6.QtCore import QSortFilterProxyModel, Qt, QTimer
from PyQt6.QtWidgets import QAbstractItemView, QCompleter, QTableView

from .HistoryFilterModel import HistoryFilterModel
from .HistoryModel import HistoryModel


class HistoryCompletionView(QTableView):
    """
    Class implementing a special completer view for history based completions.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.horizontalHeader().hide()
        self.verticalHeader().hide()

        self.setShowGrid(False)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)

        metrics = self.fontMetrics()
        self.verticalHeader().setDefaultSectionSize(metrics.height())

    def resizeEvent(self, evt):
        """
        Protected method handling resize events.

        @param evt reference to the resize event
        @type QResizeEvent
        """
        self.horizontalHeader().resizeSection(0, int(0.65 * self.width()))
        self.horizontalHeader().setStretchLastSection(True)

        super().resizeEvent(evt)

    def sizeHintForRow(self, _row):
        """
        Public method to give a size hint for rows.

        @param _row row number (unused)
        @type int
        @return desired row height
        @rtype int
        """
        metrics = self.fontMetrics()
        return metrics.height()


class HistoryCompletionModel(QSortFilterProxyModel):
    """
    Class implementing a special model for history based completions.
    """

    HistoryCompletionRole = HistoryFilterModel.MaxRole + 1

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__searchString = ""
        self.__searchMatcher = None
        self.__wordMatcher = None
        self.__isValid = False

        self.setDynamicSortFilter(True)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get data from the model.

        @param index index of history entry to get data for
        @type QModelIndex
        @param role data role
        @type int
        @return history entry data
        @rtype Any
        """
        # If the model is valid, tell QCompleter that everything we have
        # filtered matches what the user typed; if not, nothing matches
        if role == self.HistoryCompletionRole and index.isValid():
            if self.isValid():
                return "t"
            else:
                return "f"

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                role = HistoryModel.UrlStringRole
            else:
                role = HistoryModel.TitleRole

        return QSortFilterProxyModel.data(self, index, role)

    def searchString(self):
        """
        Public method to get the current search string.

        @return current search string
        @rtype str
        """
        return self.__searchString

    def setSearchString(self, sstring):
        """
        Public method to set the current search string.

        @param sstring new search string
        @type str
        """
        if sstring != self.__searchString:
            self.__searchString = sstring
            self.__searchMatcher = re.compile(
                re.escape(self.__searchString), re.IGNORECASE
            )
            self.__wordMatcher = re.compile(
                r"\b" + re.escape(self.__searchString), re.IGNORECASE
            )
            self.invalidateFilter()

    def isValid(self):
        """
        Public method to check the model for validity.

        @return flag indicating a valid status
        @rtype bool
        """
        return self.__isValid

    def setValid(self, valid):
        """
        Public method to set the model's validity.

        @param valid flag indicating the new valid status
        @type bool
        """
        if valid == self.__isValid:
            return

        self.__isValid = valid

        # tell the history completer that the model has changed
        self.dataChanged.emit(self.index(0, 0), self.index(0, self.rowCount() - 1))

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
        if self.__searchMatcher is not None:
            # Do a case-insensitive substring match against both the url and
            # title. It's already ensured, that the user doesn't accidentally
            # use regexp metacharacters (s. setSearchString()).
            idx = self.sourceModel().index(sourceRow, 0, sourceParent)

            url = self.sourceModel().data(idx, HistoryModel.UrlStringRole)
            if self.__searchMatcher.search(url) is not None:
                return True

            title = self.sourceModel().data(idx, HistoryModel.TitleRole)
            if self.__searchMatcher.search(title) is not None:
                return True

        return False

    def lessThan(self, left, right):
        """
        Public method used to sort the displayed items.

        It implements a special sorting function based on the history entry's
        frequency giving a bonus to hits that match on a word boundary so that
        e.g. "dot.python-projects.org" is a better result for typing "dot" than
        "slashdot.org". However, it only looks for the string in the host name,
        not the entire URL, since while it makes sense to e.g. give
        "www.phoronix.com" a bonus for "ph", it does NOT make sense to give
        "www.yadda.com/foo.php" the bonus.

        @param left index of left item
        @type QModelIndex
        @param right index of right item
        @type QModelIndex
        @return true, if left is less than right
        @rtype bool
        """
        frequency_L = self.sourceModel().data(left, HistoryFilterModel.FrequencyRole)
        url_L = self.sourceModel().data(left, HistoryModel.UrlRole).host()
        title_L = self.sourceModel().data(left, HistoryModel.TitleRole)

        if self.__wordMatcher is not None and (
            bool(self.__wordMatcher.search(url_L))
            or bool(self.__wordMatcher.search(title_L))
        ):
            frequency_L *= 2

        frequency_R = self.sourceModel().data(right, HistoryFilterModel.FrequencyRole)
        url_R = self.sourceModel().data(right, HistoryModel.UrlRole).host()
        title_R = self.sourceModel().data(right, HistoryModel.TitleRole)

        if self.__wordMatcher is not None and (
            bool(self.__wordMatcher.search(url_R))
            or bool(self.__wordMatcher.search(title_R))
        ):
            frequency_R *= 2

        # Sort results in descending frequency-derived score.
        return frequency_R < frequency_L


class HistoryCompleter(QCompleter):
    """
    Class implementing a completer for the browser history.
    """

    def __init__(self, model, parent=None):
        """
        Constructor

        @param model reference to the model
        @type QAbstractItemModel
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(model, parent)

        self.setPopup(HistoryCompletionView())

        # Completion should be against the faked role.
        self.setCompletionRole(HistoryCompletionModel.HistoryCompletionRole)

        # Since the completion role is faked, advantage of the sorted-model
        # optimizations in QCompleter can be taken.
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        self.setModelSorting(QCompleter.ModelSorting.CaseSensitivelySortedModel)

        self.__searchString = ""
        self.__filterTimer = QTimer(self)
        self.__filterTimer.setSingleShot(True)
        self.__filterTimer.timeout.connect(self.__updateFilter)

    def pathFromIndex(self, idx):
        """
        Public method to get a path for a given index.

        @param idx reference to the index
        @type QModelIndex
        @return the actual URL from the history
        @rtype str
        """
        return self.model().data(idx, HistoryModel.UrlStringRole)

    def splitPath(self, path):
        """
        Public method to split the given path into strings, that are used to
        match at each level in the model.

        @param path path to be split
        @type str
        @return list of path elements
        @rtype list of str
        """
        if path == self.__searchString:
            return ["t"]

        # Queue an update to the search string. Wait a bit, so that if the user
        # is quickly typing, the completer doesn't try to complete until they
        # pause.
        if self.__filterTimer.isActive():
            self.__filterTimer.stop()
        self.__filterTimer.start(150)

        # If the previous search results are not a superset of the current
        # search results, tell the model that it is not valid yet.
        if not path.startswith(self.__searchString):
            self.model().setValid(False)

        self.__searchString = path

        # The actual filtering is done by the HistoryCompletionModel. Just
        # return a short dummy here so that QCompleter thinks everything
        # matched.
        return ["t"]

    def __updateFilter(self):
        """
        Private slot to update the search string.
        """
        completionModel = self.model()

        # Tell the HistoryCompletionModel about the new search string.
        completionModel.setSearchString(self.__searchString)

        # Sort the model.
        completionModel.sort(0)

        # Mark it valid.
        completionModel.setValid(True)

        # Now update the QCompleter widget, but only if the user is still
        # typing a URL.
        if self.widget() is not None and self.widget().hasFocus():
            self.complete()
