# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the identities management dialog.
"""

import copy

from PyQt6.QtCore import QEvent, QItemSelectionModel, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QInputDialog, QLineEdit

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.SystemUtilities import OSUtilities

from .IrcNetworkManager import IrcIdentity
from .Ui_IrcIdentitiesEditDialog import Ui_IrcIdentitiesEditDialog


class IrcIdentitiesEditDialog(QDialog, Ui_IrcIdentitiesEditDialog):
    """
    Class implementing the identities management dialog.
    """

    def __init__(self, manager, identityName, parent=None):
        """
        Constructor

        @param manager reference to the IRC network manager object
        @type IrcNetworkManager
        @param identityName name of the identity to be selected
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.addButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.copyButton.setIcon(EricPixmapCache.getIcon("editCopy"))
        self.renameButton.setIcon(EricPixmapCache.getIcon("editRename"))
        self.deleteButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.nicknameAddButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.nicknameDeleteButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.nicknameUpButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.nicknameDownButton.setIcon(EricPixmapCache.getIcon("1downarrow"))
        self.showPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))

        self.__manager = manager

        self.__identities = self.__manager.getIdentities()
        self.__currentIdentity = None

        identities = sorted(self.__manager.getIdentityNames())
        identities[identities.index(IrcIdentity.DefaultIdentityName)] = (
            IrcIdentity.DefaultIdentityDisplay
        )
        self.identitiesCombo.addItems(identities)
        if identityName == IrcIdentity.DefaultIdentityName:
            identityName = IrcIdentity.DefaultIdentityDisplay
        index = self.identitiesCombo.findText(identityName)
        if index == -1:
            index = 0
            identityName = self.identitiesCombo.itemText(0)
        self.identitiesCombo.setCurrentIndex(index)

        self.on_identitiesCombo_currentIndexChanged(index)

        self.nicknameEdit.installEventFilter(self)

    def eventFilter(self, obj, evt):
        """
        Public method to handle events for other objects.

        @param obj reference to the object
        @type QObject
        @param evt reference to the event
        @type QEvent
        @return flag indicating that the event should be filtered out
        @rtype bool
        """
        if (
            obj == self.nicknameEdit
            and evt.type() == QEvent.Type.KeyPress
            and evt.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]
        ):
            self.on_nicknameAddButton_clicked()
            return True

        return super().eventFilter(obj, evt)

    def __updateIdentitiesButtons(self):
        """
        Private slot to update the status of the identity related buttons.
        """
        enable = (
            self.identitiesCombo.currentText() != IrcIdentity.DefaultIdentityDisplay
        )
        self.renameButton.setEnabled(enable)
        self.deleteButton.setEnabled(enable)

    @pyqtSlot(int)
    def on_identitiesCombo_currentIndexChanged(self, index):
        """
        Private slot to handle the selection of an identity.

        @param index index of the selected entry
        @type int
        """
        identity = self.identitiesCombo.itemText(index)
        if identity == IrcIdentity.DefaultIdentityDisplay:
            identity = IrcIdentity.DefaultIdentityName
        self.__updateIdentitiesButtons()

        if self.__currentIdentity and not self.__checkCurrentIdentity():
            return

        self.__refreshCurrentIdentity()

        self.__currentIdentity = self.__identities[identity]

        # General Tab
        self.realnameEdit.setText(self.__currentIdentity.getRealName())
        self.nicknamesList.clear()
        self.nicknamesList.addItems(self.__currentIdentity.getNickNames())
        self.serviceEdit.setText(self.__currentIdentity.getServiceName())
        self.passwordEdit.setText(self.__currentIdentity.getPassword())

        # Away Tab
        self.rememberPosOnAwayCheckBox.setChecked(
            self.__currentIdentity.rememberAwayPosition()
        )
        self.awayEdit.setText(self.__currentIdentity.getAwayMessage())

        # Advanced Tab
        self.identEdit.setText(self.__currentIdentity.getIdent())
        self.quitEdit.setText(self.__currentIdentity.getQuitMessage())
        self.partEdit.setText(self.__currentIdentity.getPartMessage())

        self.__updateIdentitiesButtons()
        self.__updateNicknameUpDownButtons()
        self.__updateNicknameButtons()

        self.identityTabWidget.setCurrentIndex(0)

    def __refreshCurrentIdentity(self):
        """
        Private method to read back the data for the current identity.
        """
        if self.__currentIdentity is None:
            return

        # General Tab
        self.__currentIdentity.setRealName(self.realnameEdit.text())
        self.__currentIdentity.setNickNames(
            [
                self.nicknamesList.item(row).text()
                for row in range(self.nicknamesList.count())
            ]
        )
        self.__currentIdentity.setServiceName(self.serviceEdit.text())
        self.__currentIdentity.setPassword(self.passwordEdit.text())

        # Away Tab
        self.__currentIdentity.setRememberAwayPosition(
            self.rememberPosOnAwayCheckBox.isChecked()
        )
        self.__currentIdentity.setAwayMessage(self.awayEdit.text())

        # Advanced Tab
        self.__currentIdentity.setIdent(self.identEdit.text())
        self.__currentIdentity.setQuitMessage(self.quitEdit.text())
        self.__currentIdentity.setPartMessage(self.partEdit.text())

    def __checkCurrentIdentity(self):
        """
        Private method to check the data for the current identity.

        @return flag indicating a successful check
        @rtype bool
        """
        if self.nicknamesList.count() == 0:
            EricMessageBox.critical(
                self,
                self.tr("Edit Identity"),
                self.tr("""The identity must contain at least one nick name."""),
            )
            block = self.identitiesCombo.blockSignals(True)
            identity = self.__currentIdentity.getName()
            if identity == IrcIdentity.DefaultIdentityName:
                identity = IrcIdentity.DefaultIdentityDisplay
            self.identitiesCombo.setCurrentIndex(
                self.identitiesCombo.findText(identity)
            )
            self.identitiesCombo.blockSignals(block)
            self.identityTabWidget.setCurrentIndex(0)
            self.nicknameEdit.setFocus()
            return False

        if not self.realnameEdit.text():
            EricMessageBox.critical(
                self,
                self.tr("Edit Identity"),
                self.tr("""The identity must have a real name."""),
            )
            block = self.identitiesCombo.blockSignals(True)
            identity = self.__currentIdentity.getName()
            if identity == IrcIdentity.DefaultIdentityName:
                identity = IrcIdentity.DefaultIdentityDisplay
            self.identitiesCombo.setCurrentIndex(
                self.identitiesCombo.findText(identity)
            )
            self.identitiesCombo.blockSignals(block)
            self.identityTabWidget.setCurrentIndex(0)
            self.realnameEdit.setFocus()
            return False

        return True

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a new idntity.
        """
        name, ok = QInputDialog.getText(
            self,
            self.tr("Add Identity"),
            self.tr("Identity Name:"),
            QLineEdit.EchoMode.Normal,
        )

        if ok:
            if name:
                if name in self.__identities:
                    EricMessageBox.critical(
                        self,
                        self.tr("Add Identity"),
                        self.tr(
                            """An identity named <b>{0}</b> already exists."""
                            """ You must provide a different name."""
                        ).format(name),
                    )
                    self.on_addButton_clicked()
                else:
                    identity = IrcIdentity(name)
                    identity.setIdent(OSUtilities.getUserName())
                    identity.setRealName(OSUtilities.getRealName())
                    self.__identities[name] = identity
                    self.identitiesCombo.addItem(name)
                    self.identitiesCombo.setCurrentIndex(
                        self.identitiesCombo.count() - 1
                    )
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Add Identity"),
                    self.tr("""The identity has to have a name."""),
                )
                self.on_addButton_clicked()

    @pyqtSlot()
    def on_copyButton_clicked(self):
        """
        Private slot to copy the selected identity.
        """
        currentIdentity = self.identitiesCombo.currentText()
        name, ok = QInputDialog.getText(
            self,
            self.tr("Copy Identity"),
            self.tr("Identity Name:"),
            QLineEdit.EchoMode.Normal,
            currentIdentity,
        )

        if ok:
            if name:
                if name in self.__identities:
                    EricMessageBox.critical(
                        self,
                        self.tr("Copy Identity"),
                        self.tr(
                            """An identity named <b>{0}</b> already exists."""
                            """ You must provide a different name."""
                        ).format(name),
                    )
                    self.on_copyButton_clicked()
                else:
                    identity = copy.deepcopy(self.__currentIdentity)
                    identity.setName(name)
                    self.__identities[name] = identity
                    self.identitiesCombo.addItem(name)
                    self.identitiesCombo.setCurrentIndex(
                        self.identitiesCombo.count() - 1
                    )
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Copy Identity"),
                    self.tr("""The identity has to have a name."""),
                )
                self.on_copyButton_clicked()

    @pyqtSlot()
    def on_renameButton_clicked(self):
        """
        Private slot to rename the selected identity.
        """
        currentIdentity = self.identitiesCombo.currentText()
        name, ok = QInputDialog.getText(
            self,
            self.tr("Rename Identity"),
            self.tr("Identity Name:"),
            QLineEdit.EchoMode.Normal,
            currentIdentity,
        )

        if ok and name != currentIdentity:
            if name:
                if name in self.__identities:
                    EricMessageBox.critical(
                        self,
                        self.tr("Rename Identity"),
                        self.tr(
                            """An identity named <b>{0}</b> already exists."""
                            """ You must provide a different name."""
                        ).format(name),
                    )
                    self.on_renameButton_clicked()
                else:
                    del self.__identities[currentIdentity]
                    self.__currentIdentity.setName(name)
                    self.__identities[name] = self.__currentIdentity
                    self.identitiesCombo.setItemText(
                        self.identitiesCombo.currentIndex(), name
                    )
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Copy Identity"),
                    self.tr("""The identity has to have a name."""),
                )
                self.on_renameButton_clicked()

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to rename the selected identity.
        """
        currentIdentity = self.identitiesCombo.currentText()
        if currentIdentity == IrcIdentity.DefaultIdentityDisplay:
            return

        inUse = False
        for networkName in self.__manager.getNetworkNames():
            inUse = (
                self.__manager.getNetwork(networkName).getIdentityName()
                == currentIdentity
            )
            if inUse:
                break

        msg = (
            self.tr(
                "This identity is in use. If you remove it, the network"
                " settings using it will fall back to the default"
                " identity. Should it be deleted anyway?"
            )
            if inUse
            else self.tr(
                "Do you really want to delete all information for this identity?"
            )
        )
        res = EricMessageBox.yesNo(
            self, self.tr("Delete Identity"), msg, icon=EricMessageBox.Warning
        )
        if res:
            del self.__identities[currentIdentity]
            self.identitiesCombo.removeItem(
                self.identitiesCombo.findText(currentIdentity)
            )

    def __updateNicknameUpDownButtons(self):
        """
        Private method to set the enabled state of the nick name up and
        down buttons.
        """
        if len(self.nicknamesList.selectedItems()) == 0:
            self.nicknameUpButton.setEnabled(False)
            self.nicknameDownButton.setEnabled(False)
        else:
            if self.nicknamesList.currentRow() == 0:
                self.nicknameUpButton.setEnabled(False)
                self.nicknameDownButton.setEnabled(True)
            elif self.nicknamesList.currentRow() == self.nicknamesList.count() - 1:
                self.nicknameUpButton.setEnabled(True)
                self.nicknameDownButton.setEnabled(False)
            else:
                self.nicknameUpButton.setEnabled(True)
                self.nicknameDownButton.setEnabled(True)

    def __updateNicknameButtons(self):
        """
        Private slot to update the nick name buttons except the up and
        down buttons.
        """
        self.nicknameDeleteButton.setEnabled(
            len(self.nicknamesList.selectedItems()) != 0
        )

        self.nicknameAddButton.setEnabled(self.nicknameEdit.text() != "")

    @pyqtSlot(str)
    def on_nicknameEdit_textEdited(self, nick):
        """
        Private slot handling a change of the nick name.

        @param nick new nick name
        @type str
        """
        sel = self.nicknamesList.selectedItems()
        if sel:
            sel[0].setText(nick)

        self.__updateNicknameButtons()

    @pyqtSlot()
    def on_nicknamesList_itemSelectionChanged(self):
        """
        Private slot handling the selection of a nick name.
        """
        items = self.nicknamesList.selectedItems()
        if items:
            self.nicknameEdit.setText(items[0].text())

        self.__updateNicknameUpDownButtons()
        self.__updateNicknameButtons()

        self.nicknameEdit.setFocus()

    @pyqtSlot()
    def on_nicknameAddButton_clicked(self):
        """
        Private slot to add a new nickname.
        """
        nick = self.nicknameEdit.text()
        if nick not in [
            self.nicknamesList.item(row).text()
            for row in range(self.nicknamesList.count())
        ]:
            self.nicknamesList.insertItem(0, nick)
        self.nicknamesList.setCurrentRow(0, QItemSelectionModel.SelectionFlag.Clear)
        self.nicknameEdit.clear()
        self.__updateNicknameButtons()

    @pyqtSlot()
    def on_nicknameDeleteButton_clicked(self):
        """
        Private slot to delete a nick name.
        """
        itm = self.nicknamesList.takeItem(self.nicknamesList.currentRow())
        del itm
        self.__updateNicknameButtons()

    @pyqtSlot()
    def on_nicknameUpButton_clicked(self):
        """
        Private slot to move the selected entry up one row.
        """
        row = self.nicknamesList.currentRow()
        if row > 0:
            itm = self.nicknamesList.takeItem(row)
            row -= 1
            self.nicknamesList.insertItem(row, itm)
            self.nicknamesList.setCurrentItem(itm)

    @pyqtSlot()
    def on_nicknameDownButton_clicked(self):
        """
        Private slot to move the selected entry down one row.
        """
        row = self.nicknamesList.currentRow()
        if row < self.nicknamesList.count() - 1:
            itm = self.nicknamesList.takeItem(row)
            row += 1
            self.nicknamesList.insertItem(row, itm)
            self.nicknamesList.setCurrentItem(itm)

    @pyqtSlot(bool)
    def on_showPasswordButton_clicked(self, checked):
        """
        Private slot to show or hide the password.

        @param checked state of the button
        @type bool
        """
        if checked:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.showPasswordButton.setIcon(EricPixmapCache.getIcon("hidePassword"))
            self.showPasswordButton.setToolTip(self.tr("Press to hide the password"))
        else:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)
            self.showPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))
            self.showPasswordButton.setToolTip(self.tr("Press to show the password"))

    def accept(self):
        """
        Public slot handling the acceptance of the dialog.
        """
        if not self.__checkCurrentIdentity():
            return

        self.__refreshCurrentIdentity()
        self.__manager.setIdentities(self.__identities)

        super().accept()
