# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the JavaScript external object being the endpoint of
a web channel.
"""

#
# This code was ported from QupZilla and modified.
# Copyright (C) David Rosca <nowrep@gmail.com>
#

from PyQt6.QtCore import QObject, pyqtProperty

from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .PasswordManagerJsObject import PasswordManagerJsObject
from .StartPageJsObject import StartPageJsObject


class ExternalJsObject(QObject):
    """
    Class implementing the endpoint of our web channel.
    """

    extraObjects = {}

    def __init__(self, page):
        """
        Constructor

        @param page reference to the web page object
        @type WebBrowserPage
        """
        super().__init__(page)

        self.__page = page

        self.__startPage = None
        self.__passwordManager = None

    def page(self):
        """
        Public method returning a reference to the web page object.

        @return reference to the web page object
        @rtype WebBrowserPage
        """
        return self.__page

    @pyqtProperty(QObject, constant=True)
    def passwordManager(self):
        """
        Public method to get a reference to the password manager JavaScript
        object.

        @return reference to the password manager JavaScript object
        @rtype StartPageJsObject
        """
        if self.__passwordManager is None:
            self.__passwordManager = PasswordManagerJsObject(self)

        return self.__passwordManager

    @pyqtProperty(QObject, constant=True)
    def speedDial(self):
        """
        Public method returning a reference to a speed dial object.

        @return reference to a speed dial object
        @rtype SpeedDial
        """
        if self.__page.url().toString() != "eric:speeddial":
            return None

        return WebBrowserWindow.speedDial()

    @pyqtProperty(QObject, constant=True)
    def startPage(self):
        """
        Public method to get a reference to the start page JavaScript object.

        @return reference to the start page JavaScript object
        @rtype StartPageJsObject
        """
        if self.__startPage is None:
            self.__startPage = StartPageJsObject(self)

        return self.__startPage

    @classmethod
    def setupWebChannel(cls, channel, page):
        """
        Class method to setup the web channel.

        @param channel reference to the channel
        @type QWebChannel
        @param page reference to the web page
        @type QWebEnginePage
        """
        channel.registerObject("eric_object", ExternalJsObject(page))
        for jsObject in cls.extraObjects:
            channel.registerObject(
                "eric_{0}".format(jsObject), cls.extraObjects[jsObject]
            )

    @classmethod
    def registerExtraObject(cls, name, jsObject):
        """
        Class method to register extra JavaScript objects.

        @param name name for the object
        @type str
        @param jsObject reference to the JavaScript object to be registered
        @type QObject
        """
        cls.extraObjects[name] = jsObject

    @classmethod
    def unregisterExtraObject(cls, name):
        """
        Class method to unregister extra JavaScript objects.

        @param name name of the object
        @type str
        """
        if name in cls.extraObjects:
            del cls.extraObjects[name]
