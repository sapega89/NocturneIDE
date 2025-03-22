# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a VCS Status widget for the sidebar/toolbar.
"""

import contextlib
import os

from PyQt6.QtCore import QEvent, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences, Utilities
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricListSelectionDialog import EricListSelectionDialog
from eric7.EricWidgets.EricSpellCheckedTextEdit import EricSpellCheckedTextEdit


class StatusWidget(QWidget):
    """
    Class implementing a VCS Status widget for the sidebar/toolbox.
    """

    StatusDataRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, project, viewmanager, parent=None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param viewmanager reference to the viewmanager object
        @type ViewManager
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setObjectName("VcsStatusWidget")

        self.__project = project
        self.__vm = viewmanager

        self.__layout = QVBoxLayout()
        self.__layout.setObjectName("MainLayout")
        self.__layout.setContentsMargins(0, 3, 0, 0)

        # Create the info label part
        self.__infoLabel = QLabel(self)
        self.__infoLabel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.__layout.addWidget(self.__infoLabel)

        # Create the top area
        self.__topLayout = QHBoxLayout()
        self.__topLayout.setObjectName("topLayout")

        self.__topLayout.addStretch()

        self.__commitToggleButton = QToolButton(self)
        self.__commitToggleButton.setIcon(EricPixmapCache.getIcon("check"))
        self.__commitToggleButton.setToolTip(
            self.tr("Press to toggle the commit markers")
        )
        self.__commitToggleButton.clicked.connect(self.__toggleCheckMark)
        self.__topLayout.addWidget(self.__commitToggleButton)

        self.__commitButton = QToolButton(self)
        self.__commitButton.setIcon(EricPixmapCache.getIcon("vcsCommit"))
        self.__commitButton.setToolTip(
            self.tr("Press to commit the marked entries with options")
        )
        self.__commitButton.clicked.connect(self.__commit)
        self.__topLayout.addWidget(self.__commitButton)

        self.__addButton = QToolButton(self)
        self.__addButton.setIcon(EricPixmapCache.getIcon("vcsAdd"))
        self.__addButton.setToolTip(
            self.tr("Press to add the selected, untracked entries")
        )
        self.__addButton.clicked.connect(self.__addUntracked)
        self.__topLayout.addWidget(self.__addButton)

        self.__reloadButton = QToolButton(self)
        self.__reloadButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.__reloadButton.setToolTip(self.tr("Press to reload the status list"))
        self.__reloadButton.clicked.connect(self.__reload)
        self.__topLayout.addWidget(self.__reloadButton)

        self.__actionsButton = QToolButton(self)
        self.__actionsButton.setIcon(EricPixmapCache.getIcon("actionsToolButton"))
        self.__actionsButton.setToolTip(self.tr("Select action from menu"))
        self.__actionsButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.__topLayout.addWidget(self.__actionsButton)

        self.__topLayout.addStretch()

        self.__layout.addLayout(self.__topLayout)
        ###################################################################

        # Create the status part
        self.__statusList = QListWidget(self)
        self.__statusList.setAlternatingRowColors(True)
        self.__statusList.setSortingEnabled(True)
        self.__statusList.setViewMode(QListView.ViewMode.ListMode)
        self.__statusList.setTextElideMode(Qt.TextElideMode.ElideLeft)
        self.__statusList.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.__statusList.itemSelectionChanged.connect(self.__updateEnabledStates)
        self.__statusList.itemDoubleClicked.connect(self.__itemDoubleClicked)
        self.__statusList.itemChanged.connect(self.__updateEnabledStates)
        ###################################################################

        # create the Quick Commit area
        self.__quickCommitGroup = QGroupBox(self.tr("Quick Commit"), self)
        self.__quickCommitGroup.setMaximumHeight(300)
        self.__quickCommitLayout = QVBoxLayout()
        self.__quickCommitEdit = EricSpellCheckedTextEdit(self)
        self.__quickCommitEdit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.__quickCommitEdit.setTabChangesFocus(True)
        self.__quickCommitEdit.installEventFilter(self)
        self.__quickCommitEdit.textChanged.connect(self.__quickCommitEditTextChanged)
        self.__quickCommitLayout.addWidget(self.__quickCommitEdit)

        self.__quickCommitLayout2 = QHBoxLayout()
        self.__quickCommitLayout2.addStretch()

        self.__quickCommitHistoryButton = QToolButton(self)
        self.__quickCommitHistoryButton.setIcon(EricPixmapCache.getIcon("history"))
        self.__quickCommitHistoryButton.setToolTip(
            self.tr("Select commit message from previous commits")
        )
        self.__quickCommitHistoryButton.clicked.connect(self.__selectQuickCommitMessage)
        self.__quickCommitLayout2.addWidget(self.__quickCommitHistoryButton)

        self.__quickCommitHistoryClearButton = QToolButton(self)
        self.__quickCommitHistoryClearButton.setIcon(
            EricPixmapCache.getIcon("historyClear")
        )
        self.__quickCommitHistoryClearButton.setToolTip(
            self.tr("Clear the list of saved commit messages")
        )
        self.__quickCommitHistoryClearButton.clicked.connect(self.__clearCommitMessages)
        self.__quickCommitLayout2.addWidget(self.__quickCommitHistoryClearButton)

        self.__quickCommitButton = QToolButton(self)
        self.__quickCommitButton.setIcon(EricPixmapCache.getIcon("vcsCommit"))
        self.__quickCommitButton.setToolTip(
            self.tr("Press to commit the marked entries")
        )
        self.__quickCommitButton.clicked.connect(self.__quickCommit)
        self.__quickCommitLayout2.addWidget(self.__quickCommitButton)

        self.__quickCommitLayout2.addStretch()

        self.__quickCommitLayout.addLayout(self.__quickCommitLayout2)
        self.__quickCommitGroup.setLayout(self.__quickCommitLayout)
        ###################################################################

        # create the splitter
        self.__splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.__splitter.addWidget(self.__statusList)
        self.__splitter.addWidget(self.__quickCommitGroup)
        self.__splitter.setSizes([600, 100])
        self.__splitter.setCollapsible(0, False)
        self.__layout.addWidget(self.__splitter)
        ###################################################################

        self.setLayout(self.__layout)

        self.__statusIcons = {
            "A": "vcs-added",  # added
            "M": "vcs-modified",  # modified
            "O": "vcs-removed",  # removed
            "R": "vcs-renamed",  # renamed
            "U": "vcs-update-required",  # update needed
            "Z": "vcs-conflicting",  # conflict
            "?": "vcs-untracked",  # not tracked
            "!": "vcs-missing",  # missing
        }
        self.__statusTexts = {
            "A": self.tr("added"),
            "M": self.tr("modified"),
            "O": self.tr("removed"),
            "R": self.tr("renamed"),
            "U": self.tr("needs update"),
            "Z": self.tr("conflict"),
            "?": self.tr("not tracked"),
            "!": self.tr("missing"),
        }

        self.__initActionsMenu()

        self.__reset()

        if self.__project.isOpen():
            self.__projectOpened()
        else:
            self.__projectClosed()

        self.__addedItemsText = []

        self.__project.projectOpened.connect(self.__projectOpened)
        self.__project.projectClosed.connect(self.__projectClosed)
        self.__project.projectPropertiesChanged.connect(self.__setProjectSpellCheckData)
        self.__project.vcsCommitted.connect(self.__committed)
        self.__project.vcsStatusMonitorInfo.connect(self.__setInfoText)
        self.__project.vcsStatusMonitorAllData.connect(self.__processStatusData)

    def __initActionsMenu(self):
        """
        Private method to initialize the actions menu.
        """
        self.__actionsMenu = QMenu()
        self.__actionsMenu.setToolTipsVisible(True)
        self.__actionsMenu.aboutToShow.connect(self.__showActionsMenu)

        self.__commitAct = self.__actionsMenu.addAction(
            EricPixmapCache.getIcon("vcsCommit"), self.tr("Commit"), self.__commit
        )
        self.__commitAct.setToolTip(self.tr("Commit the marked entries with options"))
        self.__commitSelectAct = self.__actionsMenu.addAction(
            self.tr("Select all for commit"), self.__commitSelectAll
        )
        self.__commitDeselectAct = self.__actionsMenu.addAction(
            self.tr("Unselect all from commit"), self.__commitDeselectAll
        )

        self.__actionsMenu.addSeparator()

        self.__addAct = self.__actionsMenu.addAction(
            EricPixmapCache.getIcon("vcsAdd"), self.tr("Add"), self.__addUntracked
        )
        self.__addAct.setToolTip(self.tr("Add the selected, untracked entries"))
        self.__addAllAct = self.__actionsMenu.addAction(
            self.tr("Add All"), self.__addAllUntracked
        )
        self.__addAllAct.setToolTip(self.tr("Add all untracked entries"))

        self.__actionsMenu.addSeparator()

        self.__diffAct = self.__actionsMenu.addAction(
            EricPixmapCache.getIcon("vcsDiff"), self.tr("Differences"), self.__diff
        )
        self.__diffAct.setToolTip(
            self.tr("Shows the differences of the selected entry in a separate dialog")
        )
        self.__sbsDiffAct = self.__actionsMenu.addAction(
            EricPixmapCache.getIcon("vcsSbsDiff"),
            self.tr("Differences Side-By-Side"),
            self.__sbsDiff,
        )
        self.__sbsDiffAct.setToolTip(
            self.tr(
                "Shows the differences of the selected entry side-by-side in"
                " a separate dialog"
            )
        )
        self.__diffAllAct = self.__actionsMenu.addAction(
            self.tr("All Differences"), self.__diffAll
        )
        self.__diffAllAct.setToolTip(
            self.tr("Shows the differences of all entries in a separate dialog")
        )

        self.__actionsMenu.addSeparator()

        self.__revertAct = self.__actionsMenu.addAction(
            EricPixmapCache.getIcon("vcsRevert"), self.tr("Revert"), self.__revert
        )
        self.__revertAct.setToolTip(
            self.tr("Reverts the changes of the selected files")
        )

        self.__actionsMenu.addSeparator()

        self.__forgetAct = self.__actionsMenu.addAction(
            self.tr("Forget Missing"), self.__forgetMissing
        )
        self.__forgetAct.setToolTip(self.tr("Forgets about the selected missing files"))
        self.__restoreAct = self.__actionsMenu.addAction(
            self.tr("Restore Missing"), self.__restoreMissing
        )
        self.__restoreAct.setToolTip(self.tr("Restores the selected missing files"))
        self.__actionsMenu.addSeparator()

        self.__editAct = self.__actionsMenu.addAction(
            EricPixmapCache.getIcon("open"),
            self.tr("Edit Conflict"),
            self.__editConflict,
        )
        self.__editAct.setToolTip(self.tr("Edit the selected conflicting file"))
        self.__resolvedAct = self.__actionsMenu.addAction(
            EricPixmapCache.getIcon("vcsResolved"),
            self.tr("Conflict Resolved"),
            self.__conflictResolved,
        )
        self.__resolvedAct.setToolTip(
            self.tr("Mark the selected conflicting file as resolved")
        )

        self.__actionsButton.setMenu(self.__actionsMenu)

    @pyqtSlot()
    def __projectOpened(self):
        """
        Private slot to handle the opening of a project.
        """
        self.__reloadButton.setEnabled(True)
        self.__setProjectSpellCheckData()

    @pyqtSlot()
    def __setProjectSpellCheckData(self):
        """
        Private slot to set the spell check properties of the
        quick commit area.
        """
        pwl, pel = self.__project.getProjectDictionaries()
        language = self.__project.getProjectSpellLanguage()
        self.__quickCommitEdit.setLanguageWithPWL(language, pwl or None, pel or None)

    @pyqtSlot()
    def __projectClosed(self):
        """
        Private slot to handle the closing of a project.
        """
        self.__infoLabel.setText(self.tr("No project open."))

        self.__reloadButton.setEnabled(False)

        self.__reset()

    @pyqtSlot(str)
    def __setInfoText(self, info):
        """
        Private slot to set the info label text.

        @param info text to be shown
        @type str
        """
        self.__infoLabel.setText(info)

    @pyqtSlot()
    def __reload(self):
        """
        Private slot to reload the status list.
        """
        self.__project.checkVCSStatus()

    def __reset(self):
        """
        Private method to reset the widget to default.
        """
        self.__statusList.clear()

        self.__commitToggleButton.setEnabled(False)
        self.__commitButton.setEnabled(False)
        self.__addButton.setEnabled(False)

        self.__quickCommitEdit.clear()
        self.__quickCommitGroup.setEnabled(False)

    def __updateEnabledStates(self):
        """
        Private method to set the enabled states depending on the list state.
        """
        modified = len(self.__getModifiedItems())
        unversioned = len(self.__getSelectedUnversionedItems())
        commitable = len(self.__getCommitableItems())

        self.__commitToggleButton.setEnabled(modified)
        self.__commitButton.setEnabled(commitable)
        self.__addButton.setEnabled(unversioned)

        self.__quickCommitGroup.setEnabled(commitable)

    @pyqtSlot(dict)
    def __processStatusData(self, data):
        """
        Private slot to process the status data emitted by the project.

        Each entry of the status data consists of a status flag and and the
        path relative to the project directory starting with the third column.
        The known status flags are:
        <ul>
            <li>"A" path was added but not yet committed</li>
            <li>"M" path has local changes</li>
            <li>"O" path was removed</li>
            <li>"R" path was deleted and then re-added</li>
            <li>"U" path needs an update</li>
            <li>"Z" path contains a conflict</li>
            <li>"?" path is not tracked</li>
            <li>"!" path is missing</li>
            <li>" " path is back at normal</li>
        </ul>

        @param data dictionary containing the status data
        @type dict
        """
        # step 1: remember all currently checked entries
        checkedEntries = [itm.text() for itm in self.__getCommitableItems()]
        selectedEntries = [itm.text() for itm in self.__statusList.selectedItems()]
        knownEntries = [
            self.__statusList.item(row).text()
            for row in range(self.__statusList.count())
        ]

        # step 2: clear the list and re-populate it with new data
        self.__statusList.clear()

        block = self.__statusList.blockSignals(True)
        for name, status in data.items():
            if status:
                itm = QListWidgetItem(name, self.__statusList)
                with contextlib.suppress(KeyError):
                    itm.setToolTip(self.__statusTexts[status])
                    itm.setIcon(EricPixmapCache.getIcon(self.__statusIcons[status]))
                itm.setData(self.StatusDataRole, status)
                if status in "AMOR":
                    itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    if (
                        name in checkedEntries
                        or name not in knownEntries
                        or name in self.__addedItemsText
                    ):
                        itm.setCheckState(Qt.CheckState.Checked)
                    else:
                        itm.setCheckState(Qt.CheckState.Unchecked)
                else:
                    itm.setFlags(itm.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                itm.setSelected(name in selectedEntries)

        self.__statusList.sortItems(Qt.SortOrder.AscendingOrder)
        self.__statusList.blockSignals(block)

        self.__updateEnabledStates()

    @pyqtSlot()
    def __toggleCheckMark(self):
        """
        Private slot to toggle the check marks.
        """
        itemList = (
            self.__statusList.selectedItems()
            if len(self.__statusList.selectedItems())
            else [
                self.__statusList.item(row) for row in range(self.__statusList.count())
            ]
        )
        for itm in itemList:
            if (
                itm.flags() & Qt.ItemFlag.ItemIsUserCheckable
                == Qt.ItemFlag.ItemIsUserCheckable
            ):
                if itm.checkState() == Qt.CheckState.Unchecked:
                    itm.setCheckState(Qt.CheckState.Checked)
                else:
                    itm.setCheckState(Qt.CheckState.Unchecked)

    def __setCheckMark(self, checked):
        """
        Private method to set or unset all check marks.

        @param checked check mark state to be set
        @type bool
        """
        for row in range(self.__statusList.count()):
            itm = self.__statusList.item(row)
            if (
                itm.flags() & Qt.ItemFlag.ItemIsUserCheckable
                == Qt.ItemFlag.ItemIsUserCheckable
            ):
                if checked:
                    itm.setCheckState(Qt.CheckState.Checked)
                else:
                    itm.setCheckState(Qt.CheckState.Unchecked)

    @pyqtSlot()
    def __commit(self):
        """
        Private slot to handle the commit button.
        """
        projectPath = self.__project.getProjectPath()
        names = []

        for row in range(self.__statusList.count()):
            itm = self.__statusList.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                names.append(os.path.join(projectPath, itm.text()))

        if not names:
            EricMessageBox.information(
                self,
                self.tr("Commit"),
                self.tr("""There are no entries selected to be committed."""),
            )
            return

        if Preferences.getVCS("AutoSaveFiles"):
            vm = ericApp().getObject("ViewManager")
            for name in names:
                vm.saveEditor(name)
        vcs = self.__project.getVcs()
        vcs and vcs.vcsCommit(names, "")

    @pyqtSlot()
    def __committed(self):
        """
        Private slot called after the commit has been completed.
        """
        self.__reload()

    @pyqtSlot()
    def __commitSelectAll(self):
        """
        Private slot to select all entries for commit.
        """
        self.__setCheckMark(True)

    @pyqtSlot()
    def __commitDeselectAll(self):
        """
        Private slot to deselect all entries from commit.
        """
        self.__setCheckMark(False)

    @pyqtSlot()
    def __addUntracked(self, allItems=False):
        """
        Private slot to add the selected untracked entries.

        @param allItems flag indicating to show the differences of all files
            (defaults to False)
        @type bool (optional)
        """
        projectPath = self.__project.getProjectPath()

        names = (
            [
                os.path.join(projectPath, itm.text())
                for itm in self.__getUnversionedItems()
            ]
            if allItems
            else [
                os.path.join(projectPath, itm.text())
                for itm in self.__getSelectedUnversionedItems()
            ]
        )

        if not names:
            EricMessageBox.information(
                self,
                self.tr("Add"),
                self.tr("""There are no unversioned entries available/selected."""),
            )
            return

        self.__addedItemsText = (
            [itm.text() for itm in self.__getUnversionedItems()]
            if allItems
            else [itm.text() for itm in self.__getSelectedUnversionedItems()]
        )

        vcs = self.__project.getVcs()
        vcs and vcs.vcsAdd(names)
        self.__reload()

    @pyqtSlot(QListWidgetItem)
    def __itemDoubleClicked(self, itm):
        """
        Private slot to handle double clicking an item.

        @param itm reference to the double clicked item
        @type QListWidgetItem
        """
        projectPath = self.__project.getProjectPath()

        if itm.data(self.StatusDataRole) in "MZ":
            # modified and conflicting items
            name = os.path.join(projectPath, itm.text())
            vcs = self.__project.getVcs()
            vcs and vcs.vcsDiff(name)

    ###########################################################################
    ## Menu handling methods
    ###########################################################################

    def __showActionsMenu(self):
        """
        Private slot to prepare the actions button menu before it is shown.
        """
        modified = len(self.__getSelectedModifiedItems())
        allModified = len(self.__getModifiedItems())
        unversioned = len(self.__getSelectedUnversionedItems())
        allUnversioned = len(self.__getUnversionedItems())
        missing = len(self.__getMissingItems())
        commitable = len(self.__getCommitableItems())
        commitableUnselected = len(self.__getCommitableUnselectedItems())
        conflicting = len(self.__getSelectedConflictingItems())

        self.__addAct.setEnabled(unversioned)
        self.__addAllAct.setEnabled(allUnversioned)
        self.__diffAct.setEnabled(modified)
        self.__sbsDiffAct.setEnabled(modified == 1)
        self.__diffAllAct.setEnabled(allModified)
        self.__revertAct.setEnabled(modified)
        self.__forgetAct.setEnabled(missing)
        self.__restoreAct.setEnabled(missing)
        self.__commitAct.setEnabled(commitable)
        self.__commitSelectAct.setEnabled(commitableUnselected)
        self.__commitDeselectAct.setEnabled(commitable)
        self.__editAct.setEnabled(conflicting == 1)
        self.__resolvedAct.setEnabled(conflicting)

    def __getCommitableItems(self):
        """
        Private method to retrieve all entries the user wants to commit.

        @return list of all items, the user has checked
        @rtype list of QListWidgetItem
        """
        commitableItems = []
        for row in range(self.__statusList.count()):
            itm = self.__statusList.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                commitableItems.append(itm)
        return commitableItems

    def __getCommitableUnselectedItems(self):
        """
        Private method to retrieve all entries the user may commit but hasn't
        selected.

        @return list of all items, the user has checked
        @rtype list of QListWidgetItem
        """
        items = []
        for row in range(self.__statusList.count()):
            itm = self.__statusList.item(row)
            if (
                itm.flags() & Qt.ItemFlag.ItemIsUserCheckable
                == Qt.ItemFlag.ItemIsUserCheckable
            ) and itm.checkState() == Qt.CheckState.Unchecked:
                items.append(itm)
        return items

    def __getModifiedItems(self):
        """
        Private method to retrieve all entries, that have a modified status.

        @return list of all items with a modified status
        @rtype list of QListWidgetItem
        """
        items = []
        for row in range(self.__statusList.count()):
            itm = self.__statusList.item(row)
            if itm.data(self.StatusDataRole) in "AMOR":
                items.append(itm)
        return items

    def __getSelectedModifiedItems(self):
        """
        Private method to retrieve all selected entries, that have a modified
        status.

        @return list of all selected entries with a modified status
        @rtype list of QListWidgetItem
        """
        return [
            itm
            for itm in self.__statusList.selectedItems()
            if itm.data(self.StatusDataRole) in "AMOR"
        ]

    def __getUnversionedItems(self):
        """
        Private method to retrieve all entries, that have an unversioned
        status.

        @return list of all items with an unversioned status
        @rtype list of QListWidgetItem
        """
        items = []
        for row in range(self.__statusList.count()):
            itm = self.__statusList.item(row)
            if itm.data(self.StatusDataRole) == "?":
                items.append(itm)
        return items

    def __getSelectedUnversionedItems(self):
        """
        Private method to retrieve all selected entries, that have an
        unversioned status.

        @return list of all items with an unversioned status
        @rtype list of QListWidgetItem
        """
        return [
            itm
            for itm in self.__statusList.selectedItems()
            if itm.data(self.StatusDataRole) == "?"
        ]

    def __getMissingItems(self):
        """
        Private method to retrieve all entries, that have a missing status.

        @return list of all items with a missing status
        @rtype list of QListWidgetItem
        """
        return [
            itm
            for itm in self.__statusList.selectedItems()
            if itm.data(self.StatusDataRole) == "!"
        ]

    def __getSelectedConflictingItems(self):
        """
        Private method to retrieve all selected entries, that have a conflict
        status.

        @return list of all selected entries with a conflict status
        @rtype list of QListWidgetItem
        """
        return [
            itm
            for itm in self.__statusList.selectedItems()
            if itm.data(self.StatusDataRole) == "Z"
        ]

    @pyqtSlot()
    def __addAllUntracked(self):
        """
        Private slot to handle the Add All action menu entry.
        """
        self.__addUntracked(allItems=True)

    @pyqtSlot()
    def __diff(self, allItems=False):
        """
        Private slot to handle the Differences action menu entry.

        @param allItems flag indicating to show the differences of all files
            (defaults to False)
        @type bool (optional)
        """
        projectPath = self.__project.getProjectPath()

        names = (
            [os.path.join(projectPath, itm.text()) for itm in self.__getModifiedItems()]
            if allItems
            else [
                os.path.join(projectPath, itm.text())
                for itm in self.__getSelectedModifiedItems()
            ]
        )
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Differences"),
                self.tr("""There are no uncommitted changes available/selected."""),
            )
            return

        vcs = self.__project.getVcs()
        vcs and vcs.vcsDiff(names)

    @pyqtSlot()
    def __diffAll(self):
        """
        Private slot to handle the All Differences action menu entry.
        """
        self.__diff(allItems=True)

    @pyqtSlot()
    def __sbsDiff(self):
        """
        Private slot to handle the Side-By-Side Differences action menu entry.
        """
        projectPath = self.__project.getProjectPath()

        names = [
            os.path.join(projectPath, itm.text())
            for itm in self.__getSelectedModifiedItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Differences Side-By-Side"),
                self.tr("""There are no uncommitted changes available/selected."""),
            )
            return
        elif len(names) > 1:
            EricMessageBox.information(
                self,
                self.tr("Differences Side-By-Side"),
                self.tr(
                    """Only one file with uncommitted changes"""
                    """ must be selected."""
                ),
            )
            return

        vcs = self.__project.getVcs()
        vcs and vcs.vcsSbsDiff(names[0])

    @pyqtSlot()
    def __revert(self):
        """
        Private slot to handle the Revert action menu entry.
        """
        projectPath = self.__project.getProjectPath()

        names = [
            os.path.join(projectPath, itm.text())
            for itm in self.__getSelectedModifiedItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Revert"),
                self.tr("""There are no uncommitted changes available/selected."""),
            )
            return

        vcs = self.__project.getVcs()
        vcs and vcs.vcsRevert(names)
        self.__reload()

    @pyqtSlot()
    def __forgetMissing(self):
        """
        Private slot to handle the Forget action menu entry.
        """
        projectPath = self.__project.getProjectPath()

        names = [
            os.path.join(projectPath, itm.text()) for itm in self.__getMissingItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Forget Missing"),
                self.tr("""There are no missing entries available/selected."""),
            )
            return

        vcs = self.__project.getVcs()
        vcs and vcs.vcsForget(names)
        self.__reload()

    @pyqtSlot()
    def __restoreMissing(self):
        """
        Private slot to handle the Restore Missing context menu entry.
        """
        projectPath = self.__project.getProjectPath()

        names = [
            os.path.join(projectPath, itm.text()) for itm in self.__getMissingItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Restore Missing"),
                self.tr("""There are no missing entries available/selected."""),
            )
            return

        vcs = self.__project.getVcs()
        vcs and vcs.vcsRevert(names)
        self.__reload()

    @pyqtSlot()
    def __editConflict(self):
        """
        Private slot to handle the Edit Conflict action menu entry.
        """
        projectPath = self.__project.getProjectPath()

        itm = self.__getSelectedConflictingItems()[0]
        filename = os.path.join(projectPath, itm.text())
        if Utilities.MimeTypes.isTextFile(filename):
            self.__vm.getEditor(filename)

    @pyqtSlot()
    def __conflictResolved(self):
        """
        Private slot to handle the Conflict Resolved action menu entry.
        """
        projectPath = self.__project.getProjectPath()

        names = [
            os.path.join(projectPath, itm.text())
            for itm in self.__getSelectedConflictingItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Conflict Resolved"),
                self.tr("""There are no conflicting entries available/selected."""),
            )
            return

        vcs = self.__project.getVcs()
        vcs and vcs.vcsResolved(names)
        self.__reload()

    #######################################################################
    ## Quick Commit handling methods
    #######################################################################

    @pyqtSlot()
    def __selectQuickCommitMessage(self):
        """
        Private slot to select a commit message from the list of
        saved messages.
        """
        vcs = self.__project.getVcs()
        if vcs:
            commitMessages = vcs.vcsCommitMessages()
            dlg = EricListSelectionDialog(
                commitMessages,
                selectionMode=QAbstractItemView.SelectionMode.SingleSelection,
                title=self.tr("Quick Commit"),
                message=self.tr("Select your commit message:"),
                doubleClickOk=True,
                parent=self,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                selection = dlg.getSelection()
                if selection:
                    self.__quickCommitEdit.setPlainText(selection[0])

    @pyqtSlot()
    def __clearCommitMessages(self):
        """
        Private slot to clear the list of saved commit messages.
        """
        vcs = self.__project.getVcs()
        vcs and vcs.vcsClearCommitMessages()

    @pyqtSlot()
    def __quickCommit(self):
        """
        Private slot to commit all marked entries with the entered
        commit message.
        """
        projectPath = self.__project.getProjectPath()
        names = []

        for row in range(self.__statusList.count()):
            itm = self.__statusList.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                names.append(os.path.join(projectPath, itm.text()))

        if not names:
            EricMessageBox.information(
                self,
                self.tr("Commit"),
                self.tr("""There are no entries selected to be committed."""),
            )
            return

        if Preferences.getVCS("AutoSaveFiles"):
            vm = ericApp().getObject("ViewManager")
            for name in names:
                vm.saveEditor(name)

        commitMessage = self.__quickCommitEdit.toPlainText()
        vcs = self.__project.getVcs()
        if vcs:
            vcs.vcsCommit(names, commitMessage, noDialog=True)
            vcs.vcsAddCommitMessage(commitMessage)
            self.__quickCommitEdit.clear()

    @pyqtSlot()
    def __quickCommitEditTextChanged(self):
        """
        Private slot to react upon changes of the quick commit text.
        """
        self.__quickCommitButton.setEnabled(bool(self.__quickCommitEdit.toPlainText()))

    def eventFilter(self, obj, evt):
        """
        Public method to process some events for the Commit edit.

        @param obj reference to the object the event was meant for
        @type QObject
        @param evt reference to the event object
        @type QEvent
        @return flag to indicate that the event was handled
        @rtype bool
        """
        if (
            obj is self.__quickCommitEdit
            and evt.type() == QEvent.Type.KeyPress
            and evt.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and evt.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            # Ctrl-Enter or Ctrl-Return => commit
            self.__quickCommitButton.animateClick()
            return True
        else:
            # standard event processing
            return super().eventFilter(obj, evt)
