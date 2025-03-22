# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Python side for GreaseMonkey scripts.
"""

from PyQt6.QtCore import QObject, QSettings, pyqtSlot
from PyQt6.QtGui import QGuiApplication


class GreaseMonkeyJsObject(QObject):
    """
    Class implementing the Python side for GreaseMonkey scripts.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__settings = None

    def setSettingsFile(self, name):
        """
        Public method to set the settings file for the GreaseMonkey parameters.

        @param name name of the settings file
        @type str
        """
        if self.__settings is not None:
            self.__settings.sync()
            self.__settings = None

        self.__settings = QSettings(name, QSettings.Format.IniFormat)

    @pyqtSlot(str, str, str)
    def getValue(self, nspace, name, dValue):
        """
        Public slot to get the value for the named variable for the identified
        script.

        @param nspace unique script id
        @type str
        @param name name of the variable
        @type str
        @param dValue default value
        @type str
        @return value for the named variable
        @rtype str
        """
        vName = "GreaseMonkey-{0}/{1}".format(nspace, name)
        sValue = self.__settings.value(vName, dValue)
        if not sValue:
            return dValue

        return sValue

    @pyqtSlot(str, str, str)
    def setValue(self, nspace, name, value):
        """
        Public slot to set the value for the named variable for the identified
        script.

        @param nspace unique script id
        @type str
        @param name name of the variable
        @type str
        @param value value to be set
        @type str
        @return flag indicating success
        @rtype bool
        """
        vName = "GreaseMonkey-{0}/{1}".format(nspace, name)
        self.__settings.setValue(vName, value)
        self.__settings.sync()
        return True

    @pyqtSlot(str, str)
    def deleteValue(self, nspace, name):
        """
        Public slot to set delete the named variable for the identified script.

        @param nspace unique script id
        @type str
        @param name name of the variable
        @type str
        @return flag indicating success
        @rtype bool
        """
        vName = "GreaseMonkey-{0}/{1}".format(nspace, name)
        self.__settings.remove(vName)
        self.__settings.sync()
        return True

    @pyqtSlot(str)
    def listValues(self, nspace):
        """
        Public slot to list the stored variables for the identified script.

        @param nspace unique script id
        @type str
        @return list of stored variables
        @rtype list of str
        """
        nspaceName = "GreaseMonkey-{0}".format(nspace)
        self.__settings.beginGroup(nspaceName)
        keys = self.__settings.allKeys()
        self.__settings.endGroup()

        return keys

    @pyqtSlot(str)
    def setClipboard(self, text):
        """
        Public slot to set some clipboard text.

        @param text text to be copied to the clipboard
        @type str
        """
        QGuiApplication.clipboard().setText(text)
