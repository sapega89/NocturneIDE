# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to define guards for patches.
"""

from PyQt6.QtCore import QCoreApplication, Qt, pyqtSlot
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox, QListWidgetItem

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox

from .Ui_HgQueuesDefineGuardsDialog import Ui_HgQueuesDefineGuardsDialog


class HgQueuesDefineGuardsDialog(QDialog, Ui_HgQueuesDefineGuardsDialog):
    """
    Class implementing a dialog to define guards for patches.
    """

    def __init__(self, vcs, extension, patchesList, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Hg
        @param extension reference to the extension module
        @type Queues
        @param patchesList list of patches
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.vcs = vcs
        self.extension = extension
        self.__hgClient = vcs.getClient()

        self.__patches = patchesList[:]
        self.patchSelector.addItems([""] + self.__patches)

        self.plusButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.minusButton.setIcon(EricPixmapCache.getIcon("minus"))

        self.__dirtyList = False
        self.__currentPatch = ""

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

        if self.__dirtyList:
            res = EricMessageBox.question(
                self,
                self.tr("Unsaved Changes"),
                self.tr(
                    """The guards list has been changed."""
                    """ Shall the changes be applied?"""
                ),
                EricMessageBox.Apply | EricMessageBox.Discard,
                EricMessageBox.Apply,
            )
            if res == EricMessageBox.Apply:
                self.__applyGuards()
            else:
                self.__dirtyList = False

        e.accept()

    def start(self):
        """
        Public slot to start the list command.
        """
        self.on_patchSelector_activated(0)

    @pyqtSlot(int)
    def on_patchSelector_activated(self, index):
        """
        Private slot to get the list of guards defined for the given patch
        name.

        @param index index of the selected entry
        @type int
        """
        patch = self.patchSelector.itemText(index)
        if self.__dirtyList:
            res = EricMessageBox.question(
                self,
                self.tr("Unsaved Changes"),
                self.tr(
                    """The guards list has been changed."""
                    """ Shall the changes be applied?"""
                ),
                EricMessageBox.Apply | EricMessageBox.Discard,
                EricMessageBox.Apply,
            )
            if res == EricMessageBox.Apply:
                self.__applyGuards()
            else:
                self.__dirtyList = False

        self.guardsList.clear()
        self.patchNameLabel.setText("")

        self.guardCombo.clear()
        guardsList = self.extension.getGuardsList()
        self.guardCombo.addItems(guardsList)
        self.guardCombo.setEditText("")

        args = self.vcs.initCommand("qguard")
        if patch:
            args.append(patch)

        output = self.__hgClient.runcommand(args)[0]

        if output:
            patchName, guards = output.split(":", 1)
            self.patchNameLabel.setText(patchName)
            guardsList = guards.strip().split()
            for guard in guardsList:
                if guard.startswith("+"):
                    icon = EricPixmapCache.getIcon("plus")
                    guard = guard[1:]
                    sign = "+"
                elif guard.startswith("-"):
                    icon = EricPixmapCache.getIcon("minus")
                    guard = guard[1:]
                    sign = "-"
                else:
                    continue
                itm = QListWidgetItem(icon, guard, self.guardsList)
                itm.setData(Qt.ItemDataRole.UserRole, sign)

        self.on_guardsList_itemSelectionChanged()

    @pyqtSlot()
    def on_guardsList_itemSelectionChanged(self):
        """
        Private slot to handle changes of the selection of guards.
        """
        self.removeButton.setEnabled(len(self.guardsList.selectedItems()) > 0)

    def __getGuard(self, guard):
        """
        Private method to get a reference to a named guard.

        @param guard name of the guard
        @type str
        @return reference to the guard item
        @rtype QListWidgetItem
        """
        items = self.guardsList.findItems(guard, Qt.MatchFlag.MatchCaseSensitive)
        if items:
            return items[0]
        else:
            return None

    @pyqtSlot(str)
    def on_guardCombo_editTextChanged(self, txt):
        """
        Private slot to handle changes of the text of the guard combo.

        @param txt contents of the guard combo line edit
        @type str
        """
        self.addButton.setEnabled(txt != "")

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a guard definition to the list or change it.
        """
        guard = self.guardCombo.currentText()
        if self.plusButton.isChecked():
            sign = "+"
            icon = EricPixmapCache.getIcon("plus")
        else:
            sign = "-"
            icon = EricPixmapCache.getIcon("minus")

        guardItem = self.__getGuard(guard)
        if guardItem:
            # guard already exists, remove it first
            row = self.guardsList.row(guardItem)
            itm = self.guardsList.takeItem(row)
            del itm

        itm = QListWidgetItem(icon, guard, self.guardsList)
        itm.setData(Qt.ItemDataRole.UserRole, sign)
        self.guardsList.sortItems()

        self.__dirtyList = True

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove guard definitions from the list.
        """
        res = EricMessageBox.yesNo(
            self,
            self.tr("Remove Guards"),
            self.tr("""Do you really want to remove the selected guards?"""),
        )
        if res:
            for guardItem in self.guardsList.selectedItems():
                row = self.guardsList.row(guardItem)
                itm = self.guardsList.takeItem(row)  # __IGNORE_WARNING__
                del itm

        self.__dirtyList = True

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Apply):
            self.__applyGuards()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()

    @pyqtSlot()
    def __applyGuards(self):
        """
        Private slot to apply the defined guards to the current patch.
        """
        if self.__dirtyList:
            guardsList = []
            for row in range(self.guardsList.count()):
                itm = self.guardsList.item(row)
                guard = itm.data(Qt.ItemDataRole.UserRole) + itm.text()
                guardsList.append(guard)

            args = self.vcs.initCommand("qguard")
            args.append(self.patchNameLabel.text())
            if guardsList:
                args.append("--")
                args.extend(guardsList)
            else:
                args.append("--none")

            error = self.__hgClient.runcommand(args)[1]

            if error:
                EricMessageBox.warning(
                    self,
                    self.tr("Apply Guard Definitions"),
                    self.tr(
                        """<p>The defined guards could not be"""
                        """ applied.</p><p>Reason: {0}</p>"""
                    ).format(error),
                )
            else:
                self.__dirtyList = False
                index = self.patchSelector.findText(self.patchNameLabel.text())
                if index == -1:
                    index = 0
                self.on_patchSelector_activated(index)
