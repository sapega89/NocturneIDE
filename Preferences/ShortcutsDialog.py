# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for the configuration of eric's keyboard
shortcuts.
"""

import re

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QDialog, QHeaderView, QTreeWidgetItem

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Preferences import Shortcuts

from .ShortcutDialog import ShortcutDialog
from .Ui_ShortcutsDialog import Ui_ShortcutsDialog


class ShortcutsDialog(QDialog, Ui_ShortcutsDialog):
    """
    Class implementing a dialog for the configuration of eric's keyboard
    shortcuts.

    @signal updateShortcuts() emitted when the user pressed the dialogs OK
        button
    """

    updateShortcuts = pyqtSignal()

    objectNameRole = Qt.ItemDataRole.UserRole
    noCheckRole = Qt.ItemDataRole.UserRole + 1
    objectTypeRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__webBrowser = None

        self.shortcutsList.headerItem().setText(self.shortcutsList.columnCount(), "")
        self.shortcutsList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.shortcutDialog = ShortcutDialog()
        self.shortcutDialog.shortcutChanged.connect(self.__shortcutChanged)

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.shortcutsList.sortItems(
            self.shortcutsList.sortColumn(),
            self.shortcutsList.header().sortIndicatorOrder(),
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.shortcutsList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.shortcutsList.header().setStretchLastSection(True)

    def __generateCategoryItem(self, title):
        """
        Private method to generate a category item.

        @param title title for the item
        @type str
        @return reference to the category item
        @rtype QTreeWidgetItem
        """
        itm = QTreeWidgetItem(self.shortcutsList, [title])
        itm.setExpanded(True)
        return itm

    def __generateShortcutItem(self, category, action, noCheck=False, objectType=""):
        """
        Private method to generate a keyboard shortcut item.

        @param category reference to the category item
        @type QTreeWidgetItem
        @param action reference to the keyboard action
        @type EricAction
        @param noCheck flag indicating that no uniqueness check should
            be performed
        @type bool
        @param objectType type of the object. Objects of the same
            type are not checked for duplicate shortcuts.
        @type str
        """
        itm = QTreeWidgetItem(
            category,
            [
                action.iconText(),
                action.shortcut().toString(),
                action.alternateShortcut().toString(),
            ],
        )
        itm.setIcon(0, action.icon())
        itm.setData(0, self.objectNameRole, action.objectName())
        itm.setData(0, self.noCheckRole, noCheck)
        if objectType:
            itm.setData(0, self.objectTypeRole, objectType)
        else:
            itm.setData(0, self.objectTypeRole, None)

    def populate(self, webBrowser=None):
        """
        Public method to populate the dialog.

        @param webBrowser reference to the web browser window object
        @type WebBrowserWindow
        """
        self.searchEdit.clear()
        self.searchEdit.setFocus()
        self.shortcutsList.clear()
        self.actionButton.setChecked(True)

        self.__webBrowser = webBrowser

        if webBrowser is None:
            # let the plugin manager create on demand plugin objects
            pm = ericApp().getObject("PluginManager")
            pm.initOnDemandPlugins()

            # populate the various lists
            self.projectItem = self.__generateCategoryItem(self.tr("Project"))
            for act in ericApp().getObject("Project").getActions():
                self.__generateShortcutItem(self.projectItem, act)

            self.uiItem = self.__generateCategoryItem(self.tr("General"))
            for act in ericApp().getObject("UserInterface").getActions("ui"):
                self.__generateShortcutItem(self.uiItem, act)

            self.wizardsItem = self.__generateCategoryItem(self.tr("Wizards"))
            for act in ericApp().getObject("UserInterface").getActions("wizards"):
                self.__generateShortcutItem(self.wizardsItem, act)

            self.debugItem = self.__generateCategoryItem(self.tr("Debug"))
            for act in ericApp().getObject("DebugUI").getActions():
                self.__generateShortcutItem(self.debugItem, act)

            self.editItem = self.__generateCategoryItem(self.tr("Edit"))
            for act in ericApp().getObject("ViewManager").getActions("edit"):
                self.__generateShortcutItem(self.editItem, act)

            self.fileItem = self.__generateCategoryItem(self.tr("File"))
            for act in ericApp().getObject("ViewManager").getActions("file"):
                self.__generateShortcutItem(self.fileItem, act)

            self.searchItem = self.__generateCategoryItem(self.tr("Search"))
            for act in ericApp().getObject("ViewManager").getActions("search"):
                self.__generateShortcutItem(self.searchItem, act)

            self.viewItem = self.__generateCategoryItem(self.tr("View"))
            for act in ericApp().getObject("ViewManager").getActions("view"):
                self.__generateShortcutItem(self.viewItem, act)

            self.macroItem = self.__generateCategoryItem(self.tr("Macro"))
            for act in ericApp().getObject("ViewManager").getActions("macro"):
                self.__generateShortcutItem(self.macroItem, act)

            self.bookmarkItem = self.__generateCategoryItem(self.tr("Bookmarks"))
            for act in ericApp().getObject("ViewManager").getActions("bookmark"):
                self.__generateShortcutItem(self.bookmarkItem, act)

            self.spellingItem = self.__generateCategoryItem(self.tr("Spelling"))
            for act in ericApp().getObject("ViewManager").getActions("spelling"):
                self.__generateShortcutItem(self.spellingItem, act)

            actions = ericApp().getObject("ViewManager").getActions("window")
            if actions:
                self.windowItem = self.__generateCategoryItem(self.tr("Window"))
                for act in actions:
                    self.__generateShortcutItem(self.windowItem, act)

            self.pluginCategoryItems = []
            for category, ref in ericApp().getPluginObjects():
                if hasattr(ref, "getActions"):
                    categoryItem = self.__generateCategoryItem(category)
                    objectType = ericApp().getPluginObjectType(category)
                    for act in ref.getActions():
                        self.__generateShortcutItem(
                            categoryItem, act, objectType=objectType
                        )
                    self.pluginCategoryItems.append(categoryItem)

        else:
            self.__webBrowserItem = self.__generateCategoryItem(
                self.tr("eric Web Browser")
            )
            for act in webBrowser.getActions():
                self.__generateShortcutItem(self.__webBrowserItem, act, True)

        self.__resort()
        self.__resizeColumns()

        self.__editTopItem = None

    @pyqtSlot(QTreeWidgetItem, int)
    def on_shortcutsList_itemDoubleClicked(self, itm, column):
        """
        Private slot to handle a double click in the shortcuts list.

        @param itm the list item that was double clicked
        @type QTreeWidgetItem
        @param column the list item was double clicked in
        @type int
        """
        if itm.childCount():
            return

        self.__editTopItem = itm.parent()

        self.shortcutDialog.setKeys(
            QKeySequence(itm.text(1)),
            QKeySequence(itm.text(2)),
            itm.data(0, self.noCheckRole),
            itm.data(0, self.objectTypeRole),
        )
        self.shortcutDialog.show()

    def on_shortcutsList_itemClicked(self, itm, column):
        """
        Private slot to handle a click in the shortcuts list.

        @param itm the list item that was clicked
        @type QTreeWidgetItem
        @param column the list item was clicked in
        @type int
        """
        if itm.childCount() or column not in [1, 2]:
            return

        self.shortcutsList.openPersistentEditor(itm, column)

    def on_shortcutsList_itemChanged(self, itm, column):
        """
        Private slot to handle the edit of a shortcut key.

        @param itm reference to the item changed
        @type QTreeWidgetItem
        @param column column changed
        @type int
        """
        if column != 0:
            keystr = itm.text(column).title()
            if not itm.data(0, self.noCheckRole) and not self.__checkShortcut(
                QKeySequence(keystr), itm.data(0, self.objectTypeRole), itm.parent()
            ):
                itm.setText(column, "")
            else:
                itm.setText(column, keystr)
            self.shortcutsList.closePersistentEditor(itm, column)

    def __shortcutChanged(self, keysequence, altKeysequence, noCheck, objectType):
        """
        Private slot to handle the shortcutChanged signal of the shortcut
        dialog.

        @param keysequence the keysequence of the changed action
        @type QKeySequence
        @param altKeysequence the alternative keysequence of the changed action
        @type QKeySequence
        @param noCheck flag indicating that no uniqueness check should be performed
        @type bool
        @param objectType type of the object
        @type str
        """
        if not noCheck and (
            not self.__checkShortcut(keysequence, objectType, self.__editTopItem)
            or not self.__checkShortcut(altKeysequence, objectType, self.__editTopItem)
        ):
            return

        self.shortcutsList.currentItem().setText(1, keysequence.toString())
        self.shortcutsList.currentItem().setText(2, altKeysequence.toString())

        self.__resort()
        self.__resizeColumns()

    def __checkShortcut(self, keysequence, objectType, origTopItem):
        """
        Private method to check a keysequence for uniqueness.

        @param keysequence the keysequence to check
        @type QKeySequence
        @param objectType type of the object. Entries with the same
            object type are not checked for uniqueness.
        @type str
        @param origTopItem refrence to the parent of the item to be checked
        @type QTreeWidgetItem
        @return flag indicating uniqueness
        @rtype bool
        """
        if keysequence.isEmpty():
            return True

        keystr = keysequence.toString()
        keyname = self.shortcutsList.currentItem().text(0)
        for topIndex in range(self.shortcutsList.topLevelItemCount()):
            topItem = self.shortcutsList.topLevelItem(topIndex)
            for index in range(topItem.childCount()):
                itm = topItem.child(index)

                # 1. shall a check be performed?
                if itm.data(0, self.noCheckRole):
                    continue

                # 2. check object type
                itmObjectType = itm.data(0, self.objectTypeRole)
                if (
                    itmObjectType
                    and itmObjectType == objectType
                    and topItem != origTopItem
                ):
                    continue

                # 3. check key name
                if itm.text(0) != keyname:
                    for col in [1, 2]:
                        # check against primary, then alternative binding
                        itmseq = itm.text(col)
                        # step 1: check if shortcut is already allocated
                        if keystr == itmseq:
                            res = EricMessageBox.yesNo(
                                self,
                                self.tr("Edit shortcuts"),
                                self.tr(
                                    """<p><b>{0}</b> has already been"""
                                    """ allocated to the <b>{1}</b> action. """
                                    """Remove this binding?</p>"""
                                ).format(keystr, itm.text(0)),
                                icon=EricMessageBox.Warning,
                            )
                            if res:
                                itm.setText(col, "")
                                return True
                            else:
                                return False

                        if not itmseq:
                            continue

                        # step 2: check if shortcut hides an already allocated
                        if itmseq.startswith("{0}+".format(keystr)):
                            res = EricMessageBox.yesNo(
                                self,
                                self.tr("Edit shortcuts"),
                                self.tr(
                                    """<p><b>{0}</b> hides the <b>{1}</b>"""
                                    """ action. Remove this binding?</p>"""
                                ).format(keystr, itm.text(0)),
                                icon=EricMessageBox.Warning,
                            )
                            if res:
                                itm.setText(col, "")
                                return True
                            else:
                                return False

                        # step 3: check if shortcut is hidden by an
                        #         already allocated
                        if keystr.startswith("{0}+".format(itmseq)):
                            res = EricMessageBox.yesNo(
                                self,
                                self.tr("Edit shortcuts"),
                                self.tr(
                                    """<p><b>{0}</b> is hidden by the """
                                    """<b>{1}</b> action. """
                                    """Remove this binding?</p>"""
                                ).format(keystr, itm.text(0)),
                                icon=EricMessageBox.Warning,
                            )
                            if res:
                                itm.setText(col, "")
                                return True
                            else:
                                return False

        return True

    def __saveCategoryActions(self, category, actions):
        """
        Private method to save the actions for a category.

        @param category reference to the category item
        @type QTreeWidgetItem
        @param actions list of actions for the category
        @type list of EricAction
        """
        for index in range(category.childCount()):
            itm = category.child(index)
            txt = itm.data(0, self.objectNameRole)
            for act in actions:
                if txt == act.objectName():
                    act.setShortcut(QKeySequence(itm.text(1)))
                    act.setAlternateShortcut(
                        QKeySequence(itm.text(2)), removeEmpty=True
                    )
                    break

    def on_buttonBox_accepted(self):
        """
        Private slot to handle the OK button press.
        """
        if self.__webBrowser is None:
            self.__saveCategoryActions(
                self.projectItem, ericApp().getObject("Project").getActions()
            )
            self.__saveCategoryActions(
                self.uiItem, ericApp().getObject("UserInterface").getActions("ui")
            )
            self.__saveCategoryActions(
                self.wizardsItem,
                ericApp().getObject("UserInterface").getActions("wizards"),
            )
            self.__saveCategoryActions(
                self.debugItem, ericApp().getObject("DebugUI").getActions()
            )
            self.__saveCategoryActions(
                self.editItem, ericApp().getObject("ViewManager").getActions("edit")
            )
            self.__saveCategoryActions(
                self.fileItem, ericApp().getObject("ViewManager").getActions("file")
            )
            self.__saveCategoryActions(
                self.searchItem, ericApp().getObject("ViewManager").getActions("search")
            )
            self.__saveCategoryActions(
                self.viewItem, ericApp().getObject("ViewManager").getActions("view")
            )
            self.__saveCategoryActions(
                self.macroItem, ericApp().getObject("ViewManager").getActions("macro")
            )
            self.__saveCategoryActions(
                self.bookmarkItem,
                ericApp().getObject("ViewManager").getActions("bookmark"),
            )
            self.__saveCategoryActions(
                self.spellingItem,
                ericApp().getObject("ViewManager").getActions("spelling"),
            )

            actions = ericApp().getObject("ViewManager").getActions("window")
            if actions:
                self.__saveCategoryActions(self.windowItem, actions)

            for categoryItem in self.pluginCategoryItems:
                category = categoryItem.text(0)
                ref = ericApp().getPluginObject(category)
                if ref is not None and hasattr(ref, "getActions"):
                    self.__saveCategoryActions(categoryItem, ref.getActions())

            Shortcuts.saveShortcuts()

        else:
            self.__saveCategoryActions(
                self.__webBrowserItem, self.__webBrowser.getActions()
            )
            Shortcuts.saveShortcuts(webBrowser=self.__webBrowser)

        Preferences.syncPreferences()

        self.updateShortcuts.emit()
        self.hide()

    @pyqtSlot(str)
    def on_searchEdit_textChanged(self, txt):
        """
        Private slot called, when the text in the search edit changes.

        @param txt text of the search edit
        @type str
        """
        rx = re.compile(re.escape(txt), re.IGNORECASE)
        for topIndex in range(self.shortcutsList.topLevelItemCount()):
            topItem = self.shortcutsList.topLevelItem(topIndex)
            childHiddenCount = 0
            for index in range(topItem.childCount()):
                itm = topItem.child(index)
                if txt and (
                    (self.actionButton.isChecked() and rx.search(itm.text(0)) is None)
                    or (
                        self.shortcutButton.isChecked()
                        and txt.lower() not in itm.text(1).lower()
                        and txt.lower() not in itm.text(2).lower()
                    )
                ):
                    itm.setHidden(True)
                    childHiddenCount += 1
                else:
                    itm.setHidden(False)
            topItem.setHidden(childHiddenCount == topItem.childCount())

    @pyqtSlot(bool)
    def on_actionButton_toggled(self, checked):
        """
        Private slot called, when the action radio button is toggled.

        @param checked state of the action radio button
        @type bool
        """
        if checked:
            self.on_searchEdit_textChanged(self.searchEdit.text())

    @pyqtSlot(bool)
    def on_shortcutButton_toggled(self, checked):
        """
        Private slot called, when the shortcuts radio button is toggled.

        @param checked state of the shortcuts radio button
        @type bool
        """
        if checked:
            self.on_searchEdit_textChanged(self.searchEdit.text())
