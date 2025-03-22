# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing some special network related objects and functions.
"""

from PyQt6.QtNetwork import QAbstractSocket, QHostAddress


def isValidAddress(address):
    """
    Public function to check, if the given address is valid.

    @param address IPv4 or IPv6 address string
    @type str
    @return flag indicating validity
    @rtype bool
    """
    h = QHostAddress(address)
    return not h.isNull()


def isValidIPv4Address(address):
    """
    Public function to check, if the given address is a valid IPv4 address.

    @param address IPv4 address string
    @type str
    @return flag indicating validity
    @rtype bool
    """
    h = QHostAddress(address)
    return (
        not h.isNull()
        and h.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol
    )


def isValidIPv6Address(address):
    """
    Public function to check, if the given address is a valid IPv6 address.

    @param address IPv6 address string
    @type str
    @return flag indicating validity
    @rtype bool
    """
    h = QHostAddress(address)
    return (
        not h.isNull()
        and h.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv6Protocol
    )
