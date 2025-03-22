# -*- coding: utf-8 -*-
# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to manage FIDO2 security keys.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QMenu,
    QToolButton,
    QTreeWidgetItem,
)

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox

from .Fido2Management import Fido2DeviceError, Fido2Management, Fido2PinError
from .Fido2PinDialog import Fido2PinDialog, Fido2PinDialogMode
from .Ui_Fido2ManagementDialog import Ui_Fido2ManagementDialog


class Fido2ManagementDialog(QDialog, Ui_Fido2ManagementDialog):
    """
    Class implementing a dialog to manage FIDO2 security keys.
    """

    CredentialIdRole = Qt.ItemDataRole.UserRole
    UserIdRole = Qt.ItemDataRole.UserRole + 1

    RelyingPartyColumn = 0
    CredentialIdColumn = 1
    DisplayNameColumn = 2
    UserNameColumn = 3

    def __init__(self, standalone=False, parent=None):
        """
        Constructor

        @param standalone flag indicating the standalone management application
            (defaults to False)
        @type bool (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.reloadButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.lockButton.setIcon(EricPixmapCache.getIcon("locked"))

        self.menuButton.setObjectName("fido2_supermenu_button")
        self.menuButton.setIcon(EricPixmapCache.getIcon("superMenu"))
        self.menuButton.setToolTip(self.tr("Security Key Management Menu"))
        self.menuButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menuButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.menuButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.menuButton.setShowMenuInside(True)

        self.__initManagementMenu()

        if standalone:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setText(
                self.tr("Quit")
            )

        self.reloadButton.clicked.connect(self.__populateDeviceSelector)

        self.__manager = Fido2Management(parent=self)
        self.__manager.deviceConnected.connect(self.__deviceConnected)
        self.__manager.deviceDisconnected.connect(self.__deviceDisconnected)

        QTimer.singleShot(0, self.__populateDeviceSelector)

    def __initManagementMenu(self):
        """
        Private method to initialize the security key management menu with
        actions not needed so much.
        """
        self.__mgmtMenu = QMenu()
        self.__mgmtMenu.addAction(self.tr("Show Info"), self.__showSecurityKeyInfo)
        self.__mgmtMenu.addSeparator()
        self.__mgmtMenu.addAction(
            self.tr("Reset Security Key"), self.__resetSecurityKey
        )
        self.__mgmtMenu.addSeparator()
        self.__forcePinChangeAct = self.__mgmtMenu.addAction(
            self.tr("Force PIN Change"), self.__forcePinChange
        )
        self.__minPinLengthAct = self.__mgmtMenu.addAction(
            self.tr("Set Minimum PIN Length"), self.__setMinimumPinLength
        )
        self.__toggleAlwaysUvAct = self.__mgmtMenu.addAction(
            self.tr("Toggle 'Always Require User Verification'"), self.__toggleAlwaysUv
        )

        self.__mgmtMenu.aboutToShow.connect(self.__aboutToShowManagementMenu)

        self.menuButton.setMenu(self.__mgmtMenu)

    @pyqtSlot()
    def __aboutToShowManagementMenu(self):
        """
        Private slot to prepare the security key management menu before it is shown.
        """
        self.__forcePinChangeAct.setEnabled(
            self.__manager.forcePinChangeSupported()
            and not self.__manager.pinChangeRequired()
        )
        self.__minPinLengthAct.setEnabled(
            self.__manager.canSetMinimumPinLength()
            and not self.__manager.pinChangeRequired()
        )
        self.__toggleAlwaysUvAct.setEnabled(
            self.__manager.canToggleAlwaysUv()
            and not self.__manager.pinChangeRequired()
        )

    ############################################################################
    ## methods related to device handling
    ############################################################################

    @pyqtSlot()
    def __populateDeviceSelector(self):
        """
        Private slot to populate the device selector combo box.
        """
        self.__manager.disconnectFromDevice()
        self.securityKeysComboBox.clear()

        securityKeys = self.__manager.getDevices()

        if len(securityKeys) != 1:
            self.securityKeysComboBox.addItem("")
        for securityKey in securityKeys:
            self.securityKeysComboBox.addItem(
                self.tr("{0} ({1})").format(
                    securityKey.product_name, securityKey.descriptor.path
                ),
                securityKey,
            )

        if len(securityKeys) == 0:
            EricMessageBox.information(
                self,
                self.tr("FIDO2 Security Key Management"),
                self.tr(
                    """No security key could be detected. Attach a key and press"""
                    """ the "Reload" button."""
                ),
            )

    @pyqtSlot(int)
    def on_securityKeysComboBox_currentIndexChanged(self, index):
        """
        Private slot handling the selection of security key.

        @param index index of the selected security key
        @type int
        """
        self.__manager.disconnectFromDevice()

        securityKey = self.securityKeysComboBox.itemData(index)
        if securityKey is not None:
            self.__manager.connectToDevice(securityKey)

    @pyqtSlot()
    def __deviceConnected(self):
        """
        Private slot handling the device connected signal.
        """
        self.lockButton.setEnabled(True)
        self.pinButton.setEnabled(True)
        self.menuButton.setEnabled(True)
        self.loadPasskeysButton.setEnabled(True)

        hasPin = self.__manager.hasPin()
        forcedPinChange = self.__manager.pinChangeRequired()
        if hasPin is True:
            self.pinButton.setText(self.tr("Change PIN"))
        elif hasPin is False:
            self.pinButton.setText(self.tr("Set PIN"))
        else:
            self.pinButton.setEnabled(False)
        if forcedPinChange or hasPin is False:
            self.lockButton.setEnabled(False)
            self.loadPasskeysButton.setEnabled(False)
            msg = (
                self.tr("A PIN change is required.")
                if forcedPinChange
                else self.tr("You must set a PIN first.")
            )
            EricMessageBox.information(
                self,
                self.tr("FIDO2 Security Key Management"),
                msg,
            )

        self.passkeysList.clear()
        self.on_passkeysList_itemSelectionChanged()

    @pyqtSlot()
    def __deviceDisconnected(self):
        """
        Private slot handling the device disconnected signal.
        """
        self.lockButton.setChecked(False)
        self.passkeysList.clear()
        self.on_passkeysList_itemSelectionChanged()

        self.lockButton.setEnabled(False)
        self.pinButton.setEnabled(False)
        self.menuButton.setEnabled(False)
        self.loadPasskeysButton.setEnabled(False)

        self.passkeysList.clear()
        self.on_passkeysList_itemSelectionChanged()

    @pyqtSlot(bool)
    def on_lockButton_toggled(self, checked):
        """
        Private slot to handle the toggling of the device locked status.

        @param checked state of the lock/unlock button
        @type bool
        """
        if checked:
            # unlock the selected security key
            pin = self.__getRequiredPin(self.tr("Unlock Security Key"))
            if pin:
                ok, msg = self.__manager.verifyPin(pin=pin)
                if ok:
                    self.lockButton.setIcon(EricPixmapCache.getIcon("unlocked"))
                    self.__manager.unlockDevice(pin)
                else:
                    EricMessageBox.critical(
                        self,
                        self.tr("Unlock Security Key"),
                        msg,
                    )
                    self.lockButton.setChecked(False)
            else:
                self.lockButton.setChecked(False)
        else:
            # lock the selected security key
            self.lockButton.setIcon(EricPixmapCache.getIcon("locked"))
            self.__manager.lockDevice()

    @pyqtSlot()
    def __showSecurityKeyInfo(self):
        """
        Private slot to show some info about the selected security key.
        """
        from .Fido2InfoDialog import Fido2InfoDialog

        securityKey = self.securityKeysComboBox.currentData()
        dlg = Fido2InfoDialog(
            header=securityKey.product_name, manager=self.__manager, parent=self
        )
        dlg.exec()

    @pyqtSlot()
    def __resetSecurityKey(self):
        """
        Private slot to reset the selected security key.
        """
        title = self.tr("Reset Security Key")

        yes = EricMessageBox.yesNo(
            parent=self,
            title=title,
            text=self.tr(
                "<p>Shall the selected security key really be reset?</p><p><b>WARNING"
                ":</b> This will delete all passkeys and restore factory settings.</p>"
            ),
        )
        if yes:
            if len(self.__manager.getDevices()) != 1:
                EricMessageBox.critical(
                    self,
                    title=title,
                    text=self.tr(
                        "Only one security key can be connected to perform a reset."
                        " Remove all other security keys and try again."
                    ),
                )
                return

            EricMessageBox.information(
                self,
                title=title,
                text=self.tr(
                    "Confirm this dialog then remove and re-insert the security key."
                    " Confirm the reset by touching it."
                ),
            )

            ok, msg = self.__manager.resetDevice()
            if ok:
                EricMessageBox.information(self, title, msg)
            else:
                EricMessageBox.warning(self, title, msg)

            self.__populateDeviceSelector()

    ############################################################################
    ## methods related to PIN handling
    ############################################################################

    def __checkPinStatus(self, feature):
        """
        Private method to check the PIN status of the connected security key.

        @param feature name of the feature requesting the PIN (defaults to None)
        @type str (optional)
        @return flag indicating a positive status
        @rtype bool
        """
        feature = self.tr("This feature") if feature is None else f"'{feature}'"

        hasPin = self.__manager.hasPin()
        retries, powerCycle = self.__manager.getPinRetries()

        if hasPin is None:
            msg = self.tr("{0} is not supported by the selected security key.").format(
                feature
            )
        elif not hasPin:
            msg = self.tr("{0} requires having a PIN. Set a PIN first.").format(feature)
        elif self.__manager.pinChangeRequired():
            msg = self.tr("The security key is locked. Change the PIN first.")
        elif powerCycle:
            msg = self.tr(
                "The security key is locked because the wrong PIN was entered "
                "too many times. To unlock it, remove and reinsert it."
            )
        elif retries == 0:
            msg = self.tr(
                "The security key is locked because the wrong PIN was entered too"
                " many times. You will need to reset the security key."
            )
        else:
            msg = ""

        if msg:
            EricMessageBox.critical(
                self,
                self.tr("FIDO2 Security Key Management"),
                msg,
            )
            return False
        else:
            return True

    def __getRequiredPin(self, feature=None):
        """
        Private method to check, if a pin has been set for the selected device, and
        ask the user to enter it.

        @param feature name of the feature requesting the PIN (defaults to None)
        @type str (optional)
        @return PIN of the selected security key or None in case of an issue
        @rtype str or None
        """
        if not self.__checkPinStatus(feature=feature):
            return None
        else:
            if self.__manager.isDeviceLocked():
                retries = self.__manager.getPinRetries()[0]
                title = self.tr("PIN required") if feature is None else feature
                dlg = Fido2PinDialog(
                    mode=Fido2PinDialogMode.GET,
                    title=title,
                    message=self.tr("Enter the PIN to unlock the security key."),
                    minLength=self.__manager.getMinimumPinLength(),
                    retries=retries,
                    parent=self,
                )
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    return dlg.getPins()[0]
                else:
                    return None
            else:
                return ""

    @pyqtSlot()
    def __setPin(self):
        """
        Private slot to set a PIN for the selected security key.
        """
        retries = self.__manager.getPinRetries()[0]
        title = self.tr("Set PIN")

        dlg = Fido2PinDialog(
            mode=Fido2PinDialogMode.SET,
            title=title,
            message=self.tr("Enter the PIN for the security key."),
            minLength=self.__manager.getMinimumPinLength(),
            retries=retries,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            newPin = dlg.getPins()[1]
            ok, msg = self.__manager.setPin(newPin)
            if ok:
                EricMessageBox.information(self, title, msg)
            else:
                EricMessageBox.warning(self, title, msg)

    @pyqtSlot()
    def __changePin(self):
        """
        Private slot to change the PIN of the selected security key.
        """
        retries = self.__manager.getPinRetries()[0]
        title = self.tr("Change PIN")

        dlg = Fido2PinDialog(
            mode=Fido2PinDialogMode.CHANGE,
            title=title,
            message=self.tr("Enter the current and new PINs."),
            minLength=self.__manager.getMinimumPinLength(),
            retries=retries,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            oldPin, newPin = dlg.getPins()
            ok, msg = self.__manager.changePin(oldPin, newPin)
            if ok:
                EricMessageBox.information(self, title, msg)
            else:
                EricMessageBox.warning(self, title, msg)

    @pyqtSlot()
    def on_pinButton_clicked(self):
        """
        Private slot to set or change the PIN for the selected security key.
        """
        if self.__manager.hasPin():
            self.__changePin()
        else:
            self.__setPin()

    ############################################################################
    ## methods related to passkeys handling
    ############################################################################

    @pyqtSlot()
    def __populatePasskeysList(self):
        """
        Private slot to populate the list of store passkeys of the selected security
        key.
        """
        keyIndex = self.securityKeysComboBox.currentData()
        if keyIndex is None:
            return

        pin = self.__getRequiredPin(feature=self.tr("Credential Management"))
        if pin is None:
            return

        self.passkeysList.clear()

        try:
            with EricOverrideCursor():
                passkeys, existingCount, remainingCount = self.__manager.getPasskeys(
                    pin=pin
                )
        except (Fido2DeviceError, Fido2PinError) as err:
            self.__handleError(
                error=err,
                title=self.tr("Load Passkeys"),
                message=self.tr("The stored passkeys could not be loaded."),
            )
            return

        self.existingCountLabel.setText(str(existingCount))
        self.remainingCountLabel.setText(str(remainingCount))

        for relyingParty in passkeys:
            rpItem = QTreeWidgetItem(self.passkeysList, [relyingParty])
            rpItem.setFirstColumnSpanned(True)
            rpItem.setExpanded(True)
            for passDict in passkeys[relyingParty]:
                item = QTreeWidgetItem(
                    rpItem,
                    [
                        "",
                        passDict["credentialId"]["id"].hex(),
                        passDict["displayName"],
                        passDict["userName"],
                    ],
                )
                item.setData(0, self.CredentialIdRole, passDict["credentialId"])
                item.setData(0, self.UserIdRole, passDict["userId"])

        self.passkeysList.sortItems(self.DisplayNameColumn, Qt.SortOrder.AscendingOrder)
        self.passkeysList.sortItems(
            self.RelyingPartyColumn, Qt.SortOrder.AscendingOrder
        )

    @pyqtSlot()
    def on_loadPasskeysButton_clicked(self):
        """
        Private slot to (re-)populate the passkeys list.
        """
        self.__populatePasskeysList()

    @pyqtSlot()
    def on_passkeysList_itemSelectionChanged(self):
        """
        Private slot handling the selection of a passkey.
        """
        enableButtons = (
            len(self.passkeysList.selectedItems()) == 1
            and self.passkeysList.selectedItems()[0].parent() is not None
        )
        self.editButton.setEnabled(enableButtons)
        self.deleteButton.setEnabled(enableButtons)

    @pyqtSlot()
    def on_editButton_clicked(self):
        """
        Private slot to edit the selected passkey.
        """
        from .Fido2PasskeyEditDialog import Fido2PasskeyEditDialog

        selectedItem = self.passkeysList.selectedItems()[0]
        dlg = Fido2PasskeyEditDialog(
            displayName=selectedItem.text(self.DisplayNameColumn),
            userName=selectedItem.text(self.UserNameColumn),
            relyingParty=selectedItem.parent().text(self.RelyingPartyColumn),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            displayName, userName = dlg.getData()
            if displayName != selectedItem.text(
                self.DisplayNameColumn
            ) or userName != selectedItem.text(self.UserNameColumn):
                # only change on the security key, if there is really a change
                pin = self.__getRequiredPin(feature=self.tr("Change User Info"))
                try:
                    self.__manager.changePasskeyUserInfo(
                        pin=pin,
                        credentialId=selectedItem.data(0, self.CredentialIdRole),
                        userId=selectedItem.data(0, self.UserIdRole),
                        userName=userName,
                        displayName=displayName,
                    )
                except (Fido2DeviceError, Fido2PinError) as err:
                    self.__handleError(
                        error=err,
                        title=self.tr("Change User Info"),
                        message=self.tr("The user info could not be changed."),
                    )
                    return

                selectedItem.setText(self.DisplayNameColumn, displayName)
                selectedItem.setText(self.UserNameColumn, userName)

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the selected passkey.
        """
        selectedItem = self.passkeysList.selectedItems()[0]

        ok = EricMessageBox.yesNo(
            self,
            self.tr("Delete Passkey"),
            self.tr(
                "<p>Shall the selected passkey really be deleted?</p>"
                "<ul>"
                "<li>Relying Party: {0}</li>"
                "<li>Display Name: {1}</li>"
                "<li>User Name: {2}</li>"
                "</ul>"
            ).format(
                selectedItem.parent().text(self.RelyingPartyColumn),
                selectedItem.text(self.DisplayNameColumn),
                selectedItem.text(self.UserNameColumn),
            ),
        )
        if ok:
            pin = self.__getRequiredPin(feature=self.tr("Delete Passkey"))
            try:
                self.__manager.deletePasskey(
                    pin=pin,
                    credentialId=selectedItem.data(0, self.CredentialIdRole),
                )
            except (Fido2DeviceError, Fido2PinError) as err:
                self.__handleError(
                    error=err,
                    title=self.tr("Delete Passkey"),
                    message=self.tr("The passkey could not be deleted."),
                )
                return

            rpItem = selectedItem.parent()
            index = rpItem.indexOfChild(selectedItem)
            rpItem.takeChild(index)
            del selectedItem
            if rpItem.childCount() == 0:
                index = self.passkeysList.indexOfTopLevelItem(rpItem)
                self.passkeysList.takeTopLevelItem(index)
                del rpItem

    ############################################################################
    ## methods related to device configuration
    ############################################################################

    @pyqtSlot()
    def __forcePinChange(self):
        """
        Private slot to force a PIN change before the next use.
        """
        pin = self.__getRequiredPin(feature=self.tr("Force PIN Change"))
        try:
            self.__manager.forcePinChange(pin=pin)
        except (Fido2DeviceError, Fido2PinError) as err:
            self.__handleError(
                error=err,
                title=self.tr("Force PIN Change"),
                message=self.tr("The 'Force PIN Change' flag could not be set."),
            )

    @pyqtSlot()
    def __setMinimumPinLength(self):
        """
        Private slot to set the minimum PIN length.
        """
        currMinLength = self.__manager.getMinimumPinLength()

        minPinLength, ok = QInputDialog.getInt(
            self,
            self.tr("Set Minimum PIN Length"),
            self.tr("Enter the minimum PIN length (between {0} and 63):").format(
                currMinLength
            ),
            0,
            currMinLength,
            63,
            1,
        )
        if ok and minPinLength != currMinLength:
            pin = self.__getRequiredPin(feature=self.tr("Set Minimum PIN Length"))
            try:
                self.__manager.setMinimumPinLength(pin=pin, minLength=minPinLength)
                EricMessageBox.information(
                    self,
                    self.tr("Set Minimum PIN Length"),
                    self.tr("The minimum PIN length was set to be {0}.").format(
                        minPinLength
                    ),
                )
            except (Fido2DeviceError, Fido2PinError) as err:
                self.__handleError(
                    error=err,
                    title=self.tr("Set Minimum PIN Length"),
                    message=self.tr("The minimum PIN length could not be set."),
                )

    @pyqtSlot()
    def __toggleAlwaysUv(self):
        """
        Private slot to toggle the state of the 'Always Require User Verification'
        flag.
        """
        pin = self.__getRequiredPin(
            feature=self.tr("Toggle 'Always Require User Verification'")
        )
        try:
            self.__manager.toggleAlwaysUv(pin=pin)
            EricMessageBox.information(
                self,
                self.tr("Always Require User Verification"),
                (
                    self.tr("Always Require User Verification is now enabled.")
                    if self.__manager.getAlwaysUv()
                    else self.tr("Always Require User Verification is now disabled.")
                ),
            )

        except (Fido2DeviceError, Fido2PinError) as err:
            self.__handleError(
                error=err,
                title=self.tr("Toggle 'Always Require User Verification'"),
                message=self.tr(
                    "The 'Always Require User Verification' flag could not be toggled."
                ),
            )

    ############################################################################
    ## utility methods
    ############################################################################

    def __handleError(self, error, title, message):
        """
        Private method to handle an error reported by the manager.

        @param error reference to the exception object
        @type Exception
        @param title tirle of the message box
        @type str
        @param message message to be shown
        @type str
        """
        EricMessageBox.critical(
            self,
            title,
            self.tr("<p>{0}</p><p>Reason: {1}</p>").format(message, str(error)),
        )
        if isinstance(error, Fido2DeviceError):
            self.__populateDeviceSelector()
