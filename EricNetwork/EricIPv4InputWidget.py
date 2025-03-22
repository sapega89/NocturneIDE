# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to enter an IPv4 address.
"""

import ipaddress

from PyQt6.QtCore import QEvent, QRegularExpression, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QWidget

from eric7.EricGui import EricPixmapCache

from .Ui_EricIPv4InputWidget import Ui_EricIPv4InputWidget


class EricIPv4InputWidget(QWidget, Ui_EricIPv4InputWidget):
    """
    Class implementing a widget to enter an IPv4 address.

    @signal addressChanged() emitted to indicate a change of the entered IPv4 address
    """

    addressChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.clearButton.setIcon(EricPixmapCache.getIcon("clearLeft"))
        self.clearButton.clicked.connect(self.__clear)

        ipRange = r"(?:[0-1]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])"

        self.ip1Edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(ipRange))
        )
        self.ip2Edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(ipRange))
        )
        self.ip3Edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(ipRange))
        )
        self.ip4Edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(ipRange))
        )

        self.ip1Edit.installEventFilter(self)
        self.ip2Edit.installEventFilter(self)
        self.ip3Edit.installEventFilter(self)

        self.ip1Edit.textChanged.connect(self.addressChanged)
        self.ip2Edit.textChanged.connect(self.addressChanged)
        self.ip3Edit.textChanged.connect(self.addressChanged)
        self.ip4Edit.textChanged.connect(self.addressChanged)

    def eventFilter(self, obj, evt):
        """
        Public method to filter pressing '.' to give focus to the next input field.

        @param obj reference to the object
        @type QObject
        @param evt reference to the event object
        @type QEvent
        @return flag indicating, that the event was handled
        @rtype bool
        """
        if evt.type() == QEvent.Type.KeyPress and evt.text() == ".":
            if obj is self.ip1Edit:
                nextWidget = self.ip2Edit
            elif obj is self.ip2Edit:
                nextWidget = self.ip3Edit
            elif obj is self.ip3Edit:
                nextWidget = self.ip4Edit
            else:
                nextWidget = None
            if nextWidget:
                nextWidget.setFocus(Qt.FocusReason.TabFocusReason)
                return True

        return super().eventFilter(obj, evt)

    def hasAcceptableInput(self):
        """
        Public method to check, if the input is acceptable.

        @return flag indicating acceptable input
        @rtype bool
        """
        try:
            ipaddress.IPv4Address(self.text())
        except ipaddress.AddressValueError:
            # leading zeros are not allowed
            return False

        return (
            self.ip1Edit.hasAcceptableInput()
            and self.ip2Edit.hasAcceptableInput()
            and self.ip3Edit.hasAcceptableInput()
            and self.ip4Edit.hasAcceptableInput()
        )

    def text(self):
        """
        Public method to get the IPv4 address as a string.

        @return IPv4 address
        @rtype str
        """
        ip1 = self.ip1Edit.text()
        ip2 = self.ip2Edit.text()
        ip3 = self.ip3Edit.text()
        ip4 = self.ip4Edit.text()

        if not all(bool(ip) for ip in (ip1, ip2, ip3, ip4)):
            return ""

        return "{0}.{1}.{2}.{3}".format(ip1, ip2, ip3, ip4)

    def setText(self, address):
        """
        Public method to set the IPv4 address given a string.

        Note: If an invalid address is given, the input is cleared.

        @param address IPv4 address
        @type str
        """
        if address and address != "...":  # '...' is empty as well
            try:
                ipaddress.IPv4Address(address)
            except ipaddress.AddressValueError:
                self.clear()
                return

            addressParts = address.split(".")
            self.ip1Edit.setText(addressParts[0])
            self.ip2Edit.setText(addressParts[1])
            self.ip3Edit.setText(addressParts[2])
            self.ip4Edit.setText(addressParts[3])
        else:
            self.clear()

    def address(self):
        """
        Public method to get the IPv4 address as an ipaddress.IPv4Address object.

        @return IPv4 address
        @rtype ipaddress.IPv4Address
        @exception ValueError raised to indicate an invalid IPv4 address
        """
        try:
            return ipaddress.IPv4Address(self.text())
        except ipaddress.AddressValueError as err:
            raise ValueError(str(err))

    def setAddress(self, address):
        """
        Public method to set the IPv4 address given an ipaddress.IPv4Address object.

        @param address IPv4 address
        @type ipaddress.IPv4Address
        @exception ValueError raised to indicate an invalid IPv4 address
        """
        if address and address != "...":  # '...' is empty as well
            try:
                ipaddress.IPv4Address(address)
            except ipaddress.AddressValueError as err:
                raise ValueError(str(err))

            self.setText(str(address))
        else:
            self.clear()

    @pyqtSlot()
    def clear(self):
        """
        Public slot to clear the input fields.
        """
        self.ip1Edit.clear()
        self.ip2Edit.clear()
        self.ip3Edit.clear()
        self.ip4Edit.clear()

    @pyqtSlot()
    def __clear(self):
        """
        Private slot to handle the clear button press.
        """
        self.clear()
        self.ip1Edit.setFocus(Qt.FocusReason.OtherFocusReason)
