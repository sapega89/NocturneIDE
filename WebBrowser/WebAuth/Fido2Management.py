# -*- coding: utf-8 -*-
# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a manager for FIDO2 security keys.
"""

import time

from fido2.ctap import CtapError
from fido2.ctap2 import ClientPin, Config, CredentialManagement, Ctap2
from fido2.hid import CtapHidDevice
from fido2.webauthn import PublicKeyCredentialUserEntity
from PyQt6.QtCore import QCoreApplication, QObject, QThread, pyqtSignal


class Fido2PinError(Exception):
    """
    Class signaling an issue with the PIN.
    """

    pass


class Fido2DeviceError(Exception):
    """
    Class signaling an issue with the device.
    """

    pass


class Fido2Management(QObject):
    """
    Class implementing a manager for FIDO2 security keys.

    @signal deviceConnected() emitted to indicate a connect to the security key
    @signal deviceDisconnected() emitted to indicate a disconnect from the security key
    """

    deviceConnected = pyqtSignal()
    deviceDisconnected = pyqtSignal()

    FidoVersion2Str = {
        "FIDO_2_1": "CTAP 2.1 / FIDO2",
        "FIDO_2_0": "CTAP 2.0 / FIDO2",
        "FIDO_2_1_PRE": QCoreApplication.translate(
            "Fido2Management", "CTAP2.1 Preview Features"
        ),
        "U2F_V2": "CTAP 1 / U2F",
    }

    FidoExtension2Str = {
        "credBlob": QCoreApplication.translate("Fido2Management", "Credential BLOB"),
        "credProtect": QCoreApplication.translate(
            "Fido2Management", "Credential Protection"
        ),
        "hmac-secret": QCoreApplication.translate("Fido2Management", "HMAC Secret"),
        "largeBlobKey": QCoreApplication.translate("Fido2Management", "Large Blob Key"),
        "minPinLength": QCoreApplication.translate(
            "Fido2Management", "Minimum PIN Length"
        ),
    }

    FidoInfoCategories2Str = {
        "pin": QCoreApplication.translate("Fido2Management", "PIN"),
        "security_key": QCoreApplication.translate("Fido2Management", "Security Key"),
        "options": QCoreApplication.translate("Fido2Management", "Options"),
        "extensions": QCoreApplication.translate("Fido2Management", "Extensions"),
    }

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.disconnectFromDevice()

    def connectToDevice(self, device):
        """
        Public method to connect to a given security key.

        @param device reference to the security key device class
        @type CtapHidDevice
        """
        if self.__ctap2 is not None:
            self.disconnectFromDevice()

        self.__ctap2 = Ctap2(device)
        self.__clientPin = ClientPin(self.__ctap2)
        self.__pin = None

        self.deviceConnected.emit()

    def disconnectFromDevice(self):
        """
        Public method to disconnect from the current device.
        """
        self.__ctap2 = None
        self.__clientPin = None
        self.__pin = None

        self.deviceDisconnected.emit()

    def reconnectToDevice(self):
        """
        Public method to reconnect the current security key.
        """
        if self.__ctap2 is not None:
            self.connectToDevice(self.__ctap2.device)

    def unlockDevice(self, pin):
        """
        Public method to unlock the device (i.e. store the PIN for later use).

        @param pin PIN to be stored
        @type str
        """
        self.__pin = pin

    def lockDevice(self):
        """
        Public method to lock the device (i.e. delete the stored PIN).
        """
        self.__pin = None

    def isDeviceLocked(self):
        """
        Public method to check, if the device is in locked state (i.e. the stored PIN
        is None).

        @return flag indicating the locked state
        @rtype bool
        """
        return self.__pin is None

    def getDevices(self):
        """
        Public method to get a list of connected security keys.

        @return list of connected security keys
        @rtype list of CtapHidDevice
        """
        return list(CtapHidDevice.list_devices())

    def getSecurityKeyInfo(self):
        """
        Public method to get information about the connected security key.

        @return dictionary containing the info data
        @rtype dict[str, list[tuple[str, str]]]
        """
        if self.__ctap2 is None:
            return {}

        # each entry is a list of tuples containing the display name and the value
        data = {
            "pin": [],
            "security_key": [],
            "options": [],
            "extensions": [],
        }

        # PIN related data
        if self.__ctap2.info.options["clientPin"]:
            msg1 = (
                self.tr("PIN is disabled and must be changed before it can be used!")
                if self.__ctap2.info.force_pin_change
                else ""
            )
            pinRetries, powerCycle = self.getPinRetries()
            if pinRetries:
                if powerCycle:
                    msg = self.tr(
                        "PIN is temporarily blocked. Remove and re-insert the"
                        " security keyto unblock it."
                    )
                else:
                    msg = self.tr("%n attempts remaining", "", pinRetries)
            else:
                msg = self.tr("PIN is blocked. The security key needs to be reset.")
            if msg1:
                msg += "\n" + msg1
        else:
            msg = self.tr("A PIN has not been set.")
        data["pin"].append((self.tr("PIN Status"), msg))

        data["pin"].append(
            (self.tr("Minimum PIN length"), str(self.__ctap2.info.min_pin_length))
        )

        alwaysUv = self.__ctap2.info.options.get("alwaysUv")
        msg = (
            self.tr("not supported")
            if alwaysUv is None
            else self.tr("switched on") if alwaysUv else self.tr("switched off")
        )
        data["pin"].append((self.tr("Always require User Verification"), msg))

        remainingPasskeys = self.__ctap2.info.remaining_disc_creds
        if remainingPasskeys is not None:
            data["pin"].append(
                (self.tr("Passkeys storage remaining"), str(remainingPasskeys))
            )

        enterprise = self.__ctap2.info.options.get("ep")
        if enterprise is not None:
            data["pin"].append(
                (
                    self.tr("Enterprise Attestation"),
                    self.tr("enabled") if enterprise else self.tr("disabled"),
                )
            )

        # security key related data
        data["security_key"].extend(
            [
                (self.tr("Name"), self.__ctap2.device.product_name),
                (self.tr("Path"), self.__ctap2.device.descriptor.path),
                (
                    self.tr("Version"),
                    ".".join(str(p) for p in self.__ctap2.device.device_version),
                ),
                (self.tr("Vendor ID"), f"0x{self.__ctap2.device.descriptor.vid:04x}"),
                (self.tr("Product ID"), f"0x{self.__ctap2.device.descriptor.pid:04x}"),
            ]
        )
        serial = self.__ctap2.device.serial_number
        if serial is not None:
            data["security_key"].append((self.tr("Serial Number"), serial))
        data["security_key"].append(
            (
                self.tr("Supported Versions"),
                "\n".join(
                    self.FidoVersion2Str.get(v, v) for v in self.__ctap2.info.versions
                ),
            )
        )
        data["security_key"].append(
            (self.tr("Supported Transports"), "\n".join(self.__ctap2.info.transports))
        )

        # extensions data
        if self.__ctap2.info.extensions:
            for ext in self.FidoExtension2Str:
                data["extensions"].append(
                    (
                        self.FidoExtension2Str[ext],
                        (
                            self.tr("supported")
                            if ext in self.__ctap2.info.extensions
                            else self.tr("not supported")
                        ),
                    )
                )

        # options data
        options = self.__ctap2.info.options
        data["options"].append(
            (
                self.tr("Is Platform Device"),
                self.tr("yes") if options.get("plat", False) else self.tr("no"),
            )
        )
        data["options"].append(
            (
                self.tr("Resident Passkeys"),
                (
                    self.tr("supported")
                    if options.get("rk", False)
                    else self.tr("not supported")
                ),
            )
        )
        cp = options.get("clientPin")
        data["options"].append(
            (
                self.tr("Client PIN"),
                (
                    self.tr("not supported")
                    if cp is None
                    else (
                        self.tr("supported, PIN set")
                        if cp is True
                        else self.tr("supported, PIN not set")
                    )
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Detect User Presence"),
                (
                    self.tr("supported")
                    if options.get("up", True)
                    else self.tr("not supported")
                ),
            )
        )
        uv = options.get("uv")
        data["options"].append(
            (
                self.tr("User Verification"),
                (
                    self.tr("not supported")
                    if uv is None
                    else (
                        self.tr("supported, configured")
                        if uv is True
                        else self.tr("supported, not configured")
                    )
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Verify User with Client PIN"),
                (
                    self.tr("available")
                    if options.get("pinUvAuthToken", False)
                    else self.tr("not available")
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Make Credential / Get Assertion"),
                (
                    self.tr("available")
                    if options.get("noMcGaPermissionsWithClientPin", False)
                    else self.tr("not available")
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Large BLOBs"),
                (
                    self.tr("supported")
                    if options.get("largeBlobs", False)
                    else self.tr("not supported")
                ),
            )
        )
        ep = options.get("ep")
        data["options"].append(
            (
                self.tr("Enterprise Attestation"),
                (
                    self.tr("not supported")
                    if ep is None
                    else (
                        self.tr("supported, enabled")
                        if ep is True
                        else self.tr("supported, disabled")
                    )
                ),
            )
        )
        be = options.get("bioEnroll")
        data["options"].append(
            (
                self.tr("Fingerprint"),
                (
                    self.tr("not supported")
                    if be is None
                    else (
                        self.tr("supported, registered")
                        if be is True
                        else self.tr("supported, not registered")
                    )
                ),
            )
        )
        uvmp = options.get("userVerificationMgmtPreview")
        data["options"].append(
            (
                self.tr("CTAP2.1 Preview Fingerprint"),
                (
                    self.tr("not supported")
                    if uvmp is None
                    else (
                        self.tr("supported, registered")
                        if uvmp is True
                        else self.tr("supported, not registered")
                    )
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Verify User for Fingerprint Registration"),
                (
                    self.tr("supported")
                    if options.get("uvBioEnroll", False)
                    else self.tr("not supported")
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Security Key Configuration"),
                (
                    self.tr("supported")
                    if options.get("authnrCfg", False)
                    else self.tr("not supported")
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Verify User for Security Key Configuration"),
                (
                    self.tr("supported")
                    if options.get("uvAcfg", False)
                    else self.tr("not supported")
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Credential Management"),
                (
                    self.tr("supported")
                    if options.get("credMgmt", False)
                    else self.tr("not supported")
                ),
            )
        )
        data["options"].append(
            (
                self.tr("CTAP2.1 Preview Credential Management"),
                (
                    self.tr("supported")
                    if options.get("credentialMgmtPreview", False)
                    else self.tr("not supported")
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Set Minimum PIN Length"),
                (
                    self.tr("supported")
                    if options.get("setMinPINLength", False)
                    else self.tr("not supported")
                ),
            )
        )
        data["options"].append(
            (
                self.tr("Make Non-Resident Passkey without User Verification"),
                (
                    self.tr("allowed")
                    if options.get("makeCredUvNotRqd", False)
                    else self.tr("not allowed")
                ),
            )
        )
        auv = options.get("alwaysUv")
        data["options"].append(
            (
                self.tr("Always Require User Verification"),
                (
                    self.tr("not supported")
                    if auv is None
                    else (
                        self.tr("supported, enabled")
                        if auv is True
                        else self.tr("supported, disabled")
                    )
                ),
            )
        )

        return data

    def resetDevice(self):
        """
        Public method to reset the connected security key.

        @return flag indicating success and a message
        @rtype tuple of (bool, str)
        """
        if self.__ctap2 is None:
            return False, self.tr("No security key connected.")

        removed = False
        startTime = time.monotonic()
        while True:
            QThread.msleep(500)
            try:
                securityKeys = self.getDevices()
            except OSError:
                securityKeys = []
            if not securityKeys:
                removed = True
            if removed and len(securityKeys) == 1:
                ctap2 = Ctap2(securityKeys[0])
                break
            if time.monotonic() - startTime >= 30:
                return False, self.tr(
                    "Reset failed. The security key was not removed and re-inserted"
                    " within 30 seconds."
                )

        try:
            ctap2.reset()
            return True, "The security key has been reset."
        except CtapError as err:
            if err.code == CtapError.ERR.ACTION_TIMEOUT:
                msg = self.tr(
                    "You need to touch your security key to confirm the reset."
                )
            elif err.code in (
                CtapError.ERR.NOT_ALLOWED,
                CtapError.ERR.PIN_AUTH_BLOCKED,
            ):
                msg = self.tr(
                    "Reset must be triggered within 5 seconds after the security"
                    " key is inserted."
                )
            else:
                msg = str(err)

            return False, self.tr("Reset failed. {0}").format(msg)
        except Exception:
            return False, self.tr("Reset failed.")

    ############################################################################
    ## methods related to PIN handling
    ############################################################################

    def getMinimumPinLength(self):
        """
        Public method to get the minimum PIN length defined by the security key.

        @return minimum length for the PIN
        @rtype int
        """
        if self.__ctap2 is None:
            return None
        else:
            return self.__ctap2.info.min_pin_length

    def hasPin(self):
        """
        Public method to check, if the connected security key has a PIN set.

        @return flag indicating that a PIN has been set or None in case no device
            was connected yet or it does not support PIN
        @rtype bool or None
        """
        if self.__ctap2 is None:
            return None

        return self.__ctap2.info.options.get("clientPin")

    def pinChangeRequired(self):
        """
        Public method to check for a forced PIN change.

        @return flag indicating a forced PIN change is required
        @rtype bool
        """
        if self.__ctap2 is None:
            return False

        return self.__ctap2.info.force_pin_change

    def getPinRetries(self):
        """
        Public method to get the number of PIN retries left and an indication for the
        need of a power cycle.

        @return tuple containing the number of retries left and a flag indicating a
            power cycle is required. A retry value of -1 indicates, that no PIN was
            set yet.
        @rtype tuple of (int, bool)
        """
        if self.__ctap2 is None or self.__clientPin is None:
            return (None, None)

        try:
            return self.__clientPin.get_pin_retries()
        except CtapError as err:
            if err.code == CtapError.ERR.PIN_NOT_SET:
                # return -1 retries to indicate a missing PIN
                return (-1, False)

    def changePin(self, oldPin, newPin):
        """
        Public method to change the PIN of the connected security key.

        @param oldPin current PIN
        @type str
        @param newPin new PIN
        @type str
        @return flag indicating success and a message
        @rtype tuple of (bool, str)
        """
        if self.__ctap2 is None or self.__clientPin is None:
            return False, self.tr("No security key connected.")

        try:
            self.__clientPin.change_pin(old_pin=oldPin, new_pin=newPin)
            self.reconnectToDevice()
            return True, self.tr("PIN was changed successfully.")
        except CtapError as err:
            return (
                False,
                self.tr("<p>Failed to change the PIN.</p><p>Reason: {0}</p>").format(
                    self.__pinErrorMessage(err)
                ),
            )

    def setPin(self, pin):
        """
        Public method to set a PIN for the connected security key.

        @param pin PIN to be set
        @type str
        @return flag indicating success and a message
        @rtype tuple of (bool, str)
        """
        if self.__ctap2 is None or self.__clientPin is None:
            return False, self.tr("No security key connected.")

        try:
            self.__clientPin.set_pin(pin=pin)
            self.reconnectToDevice()
            return True, self.tr("PIN was set successfully.")
        except CtapError as err:
            return (
                False,
                self.tr("<p>Failed to set the PIN.</p><p>Reason: {0}</p>").format(
                    self.__pinErrorMessage(err)
                ),
            )

    def verifyPin(self, pin):
        """
        Public method to verify a given PIN.

        A successful verification of the PIN will reset the "retries" counter.

        @param pin PIN to be verified
        @type str
        @return flag indicating successful verification and a verification message
        @rtype tuple of (bool, str)
        """
        if self.__ctap2 is None or self.__clientPin is None:
            return False, self.tr("No security key connected.")

        try:
            self.__clientPin.get_pin_token(
                pin, ClientPin.PERMISSION.GET_ASSERTION, "eric-ide.python-projects.org"
            )
            return True, self.tr("PIN was verified.")
        except CtapError as err:
            return (
                False,
                self.tr("<p>PIN verification failed.</p><p>Reason: {0}</p>").format(
                    self.__pinErrorMessage(err)
                ),
            )

    def __pinErrorMessage(self, err):
        """
        Private method to get a message for a PIN error.

        @param err reference to the exception object
        @type CtapError
        @return message for the given PIN error
        @rtype str
        """
        errorCode = err.code
        if errorCode == CtapError.ERR.PIN_INVALID:
            msg = self.tr("Invalid PIN")
        elif errorCode == CtapError.ERR.PIN_BLOCKED:
            msg = self.tr("PIN is blocked.")
        elif errorCode == CtapError.ERR.PIN_NOT_SET:
            msg = self.tr("No PIN set.")
        elif errorCode == CtapError.ERR.PIN_POLICY_VIOLATION:
            msg = self.tr("New PIN doesn't meet complexity requirements.")
        else:
            msg = str(err)
        return msg

    ############################################################################
    ## methods related to passkey (credential) handling
    ############################################################################

    def getPasskeys(self, pin):
        """
        Public method to get all stored passkeys.

        @param pin PIN to unlock the connected security key
        @type str
        @return tuple containing a dictionary containing the stored passkeys grouped
            by Relying Party ID, the count of used credential slots and the count
            of available credential slots
        @rtype tuple of [dict[str, list[dict[str, Any]]], int, int]
        """
        credentials = {}

        credentialManager = self.__initializeCredentialManager(pin)
        data = credentialManager.get_metadata()
        if data.get(CredentialManagement.RESULT.EXISTING_CRED_COUNT) > 0:
            for relyingParty in credentialManager.enumerate_rps():
                relyingPartyId = relyingParty[CredentialManagement.RESULT.RP]["id"]
                credentials[relyingPartyId] = []
                for credential in credentialManager.enumerate_creds(
                    relyingParty[CredentialManagement.RESULT.RP_ID_HASH]
                ):
                    credentials[relyingPartyId].append(
                        {
                            "credentialId": credential[
                                CredentialManagement.RESULT.CREDENTIAL_ID
                            ],
                            "userId": credential[CredentialManagement.RESULT.USER][
                                "id"
                            ],
                            "userName": credential[
                                CredentialManagement.RESULT.USER
                            ].get("name", ""),
                            "displayName": credential[
                                CredentialManagement.RESULT.USER
                            ].get("displayName", ""),
                        }
                    )

        return (
            credentials,
            data.get(CredentialManagement.RESULT.EXISTING_CRED_COUNT),
            data.get(CredentialManagement.RESULT.MAX_REMAINING_COUNT),
        )

    def deletePasskey(self, pin, credentialId):
        """
        Public method to delete the passkey of the given ID.

        @param pin PIN to unlock the connected security key
        @type str
        @param credentialId ID of the passkey to be deleted
        @type fido2.webauthn.PublicKeyCredentialDescriptor
        """
        credentialManager = self.__initializeCredentialManager(pin)
        credentialManager.delete_cred(cred_id=credentialId)

    def changePasskeyUserInfo(self, pin, credentialId, userId, userName, displayName):
        """
        Public method to change the user info of a stored passkey.

        @param pin PIN to unlock the connected security key
        @type str
        @param credentialId ID of the passkey to change
        @type fido2.webauthn.PublicKeyCredentialDescriptor
        @param userId ID of the user
        @type bytes
        @param userName user name to set
        @type str
        @param displayName display name to set
        @type str
        """
        userInfo = PublicKeyCredentialUserEntity(
            name=userName, id=userId, display_name=displayName
        )
        credentialManager = self.__initializeCredentialManager(pin)
        credentialManager.update_user_info(cred_id=credentialId, user_info=userInfo)

    def __initializeCredentialManager(self, pin):
        """
        Private method to initialize a credential manager object.

        @param pin PIN to unlock the connected security key
        @type str
        @return reference to the credential manager object
        @rtype CredentialManagement
        @exception Fido2DeviceError raised to indicate an issue with the selected
            security key
        @exception Fido2PinError raised to indicate an issue with the PIN
        """
        if self.__clientPin is None:
            self.__clientPin = ClientPin(self.__ctap2)

        if pin == "":
            pin = self.__pin
        if pin is None:
            # Error
            raise Fido2PinError(
                self.tr(
                    "The selected security key is not unlocked or no PIN was entered."
                )
            )

        try:
            pinToken = self.__clientPin.get_pin_token(
                pin, ClientPin.PERMISSION.CREDENTIAL_MGMT
            )
        except CtapError as err:
            raise Fido2PinError(
                self.tr("PIN error: {0}").format(self.__pinErrorMessage(err))
            )
        except OSError:
            raise Fido2DeviceError(
                self.tr("Connected security key unplugged. Reinsert and try again.")
            )

        return CredentialManagement(self.__ctap2, self.__clientPin.protocol, pinToken)

    ############################################################################
    ## methods related to configuration handling
    ############################################################################

    def __initConfig(self, pin):
        """
        Private method to initialize a configuration object.

        @param pin PIN to unlock the connected security key
        @type str
        @return reference to the configuration object
        @rtype Config
        @exception Fido2DeviceError raised to indicate an issue with the selected
            security key
        @exception Fido2PinError raised to indicate an issue with the PIN
        """
        if self.__clientPin is None:
            self.__clientPin = ClientPin(self.__ctap2)

        if pin == "":
            pin = self.__pin
        if pin is None:
            # Error
            raise Fido2PinError(
                self.tr(
                    "The selected security key is not unlocked or no PIN was entered."
                )
            )

        if not Config.is_supported(self.__ctap2.info):
            raise Fido2DeviceError(
                self.tr("The selected security key does not support configuration.")
            )

        try:
            pinToken = self.__clientPin.get_pin_token(
                pin, ClientPin.PERMISSION.AUTHENTICATOR_CFG
            )
        except CtapError as err:
            raise Fido2PinError(
                self.tr("PIN error: {0}").format(self.__pinErrorMessage(err))
            )
        except OSError:
            raise Fido2DeviceError(
                self.tr("Connected security key unplugged. Reinsert and try again.")
            )

        return Config(self.__ctap2, self.__clientPin.protocol, pinToken)

    def forcePinChangeSupported(self):
        """
        Public method to check, if the 'forcePinChange' function is supported by the
        selected security key.

        @return flag indicating support
        @rtype bool
        """
        return not (
            self.__ctap2 is None
            or self.__ctap2.info is None
            or not self.__ctap2.info.options.get("setMinPINLength")
        )

    def forcePinChange(self, pin):
        """
        Public method to force the PIN to be changed to a new value before use.

        @param pin PIN to unlock the connected security key
        @type str
        """
        config = self.__initConfig(pin)
        config.set_min_pin_length(force_change_pin=True)
        self.reconnectToDevice()

    def canSetMinimumPinLength(self):
        """
        Public method to check, if the 'setMinPINLength' function is available.

        @return flag indicating availability
        @rtype bool
        """
        return not (
            self.__ctap2 is None
            or self.__ctap2.info is None
            or not self.__ctap2.info.options.get("setMinPINLength")
            or (
                self.__ctap2.info.options.get("alwaysUv")
                and not self.__ctap2.info.options.get("clientPin")
            )
        )

    def setMinimumPinLength(self, pin, minLength):
        """
        Public method to set the minimum PIN length.

        @param pin PIN to unlock the connected security key
        @type str
        @param minLength minimum PIN length
        @type int
        @exception Fido2PinError raised to indicate an issue with the PIN length
        """
        if minLength < 4 or minLength > 63:
            raise Fido2PinError(
                self.tr("The minimum PIN length must be between 4 and 63.")
            )
        if minLength < self.__ctap2.info.min_pin_length:
            raise Fido2PinError(
                self.tr("The minimum PIN length must be at least {0}.").format(
                    self.__ctap2.info.min_pin_length
                )
            )

        config = self.__initConfig(pin)
        config.set_min_pin_length(min_pin_length=minLength)
        self.reconnectToDevice()

    def canToggleAlwaysUv(self):
        """
        Public method to check, if the 'toggleAlwaysUv' function is available.

        @return flag indicating availability
        @rtype bool
        """
        return not (
            self.__ctap2 is None
            or self.__ctap2.info is None
            or "alwaysUv" not in self.__ctap2.info.options
        )

    def getAlwaysUv(self):
        """
        Public method to get the value of the 'alwaysUv' flag of the current security
        key.

        @return return value of the 'alwaysUv' flag
        @rtype bool
        """
        if self.__ctap2 is None:
            return False

        info = self.__ctap2.get_info()
        return info is not None and info.options.get("alwaysUv", False)

    def toggleAlwaysUv(self, pin):
        """
        Public method to toggle the 'alwaysUv' flag of the selected security key.

        @param pin PIN to unlock the connected security key
        @type str
        """
        config = self.__initConfig(pin)
        config.toggle_always_uv()
        self.reconnectToDevice()
