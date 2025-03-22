# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a personal information manager used to complete form
fields.
"""

import enum
import functools

from PyQt6.QtCore import QObject, QPoint, Qt
from PyQt6.QtWidgets import QDialog, QMenu

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache

from ..WebBrowserPage import WebBrowserPage


class PersonalInformationType(enum.Enum):
    """
    Class defining the personal information types.
    """

    FullName = 0
    LastName = 1
    FirstName = 2
    Email = 3
    Mobile = 4
    Phone = 5
    Address = 6
    City = 7
    Zip = 8
    State = 9
    Country = 10
    HomePage = 11
    Special1 = 12
    Special2 = 13
    Special3 = 14
    Special4 = 15

    Max = 16
    Invalid = 256


class PersonalInformationManager(QObject):
    """
    Class implementing the personal information manager used to complete form
    fields.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__loaded = False
        self.__allInfo = {}
        self.__infoMatches = {}
        self.__translations = {}

        self.__view = None
        self.__clickedPos = QPoint()

    def __loadSettings(self):
        """
        Private method to load the settings.
        """
        self.__allInfo[PersonalInformationType.FullName] = Preferences.getWebBrowser(
            "PimFullName"
        )
        self.__allInfo[PersonalInformationType.LastName] = Preferences.getWebBrowser(
            "PimLastName"
        )
        self.__allInfo[PersonalInformationType.FirstName] = Preferences.getWebBrowser(
            "PimFirstName"
        )
        self.__allInfo[PersonalInformationType.Email] = Preferences.getWebBrowser(
            "PimEmail"
        )
        self.__allInfo[PersonalInformationType.Mobile] = Preferences.getWebBrowser(
            "PimMobile"
        )
        self.__allInfo[PersonalInformationType.Phone] = Preferences.getWebBrowser(
            "PimPhone"
        )
        self.__allInfo[PersonalInformationType.Address] = Preferences.getWebBrowser(
            "PimAddress"
        )
        self.__allInfo[PersonalInformationType.City] = Preferences.getWebBrowser(
            "PimCity"
        )
        self.__allInfo[PersonalInformationType.Zip] = Preferences.getWebBrowser(
            "PimZip"
        )
        self.__allInfo[PersonalInformationType.State] = Preferences.getWebBrowser(
            "PimState"
        )
        self.__allInfo[PersonalInformationType.Country] = Preferences.getWebBrowser(
            "PimCountry"
        )
        self.__allInfo[PersonalInformationType.HomePage] = Preferences.getWebBrowser(
            "PimHomePage"
        )
        self.__allInfo[PersonalInformationType.Special1] = Preferences.getWebBrowser(
            "PimSpecial1"
        )
        self.__allInfo[PersonalInformationType.Special2] = Preferences.getWebBrowser(
            "PimSpecial2"
        )
        self.__allInfo[PersonalInformationType.Special3] = Preferences.getWebBrowser(
            "PimSpecial3"
        )
        self.__allInfo[PersonalInformationType.Special4] = Preferences.getWebBrowser(
            "PimSpecial4"
        )

        self.__translations[PersonalInformationType.FullName] = self.tr("Full Name")
        self.__translations[PersonalInformationType.LastName] = self.tr("Last Name")
        self.__translations[PersonalInformationType.FirstName] = self.tr("First Name")
        self.__translations[PersonalInformationType.Email] = self.tr("E-mail")
        self.__translations[PersonalInformationType.Mobile] = self.tr("Mobile")
        self.__translations[PersonalInformationType.Phone] = self.tr("Phone")
        self.__translations[PersonalInformationType.Address] = self.tr("Address")
        self.__translations[PersonalInformationType.City] = self.tr("City")
        self.__translations[PersonalInformationType.Zip] = self.tr("ZIP Code")
        self.__translations[PersonalInformationType.State] = self.tr("State/Region")
        self.__translations[PersonalInformationType.Country] = self.tr("Country")
        self.__translations[PersonalInformationType.HomePage] = self.tr("Home Page")
        self.__translations[PersonalInformationType.Special1] = self.tr("Custom 1")
        self.__translations[PersonalInformationType.Special2] = self.tr("Custom 2")
        self.__translations[PersonalInformationType.Special3] = self.tr("Custom 3")
        self.__translations[PersonalInformationType.Special4] = self.tr("Custom 4")

        self.__infoMatches[PersonalInformationType.FullName] = ["fullname", "realname"]
        self.__infoMatches[PersonalInformationType.LastName] = ["lastname", "surname"]
        self.__infoMatches[PersonalInformationType.FirstName] = ["firstname", "name"]
        self.__infoMatches[PersonalInformationType.Email] = ["email", "e-mail", "mail"]
        self.__infoMatches[PersonalInformationType.Mobile] = ["mobile", "mobilephone"]
        self.__infoMatches[PersonalInformationType.Phone] = ["phone", "telephone"]
        self.__infoMatches[PersonalInformationType.Address] = ["address"]
        self.__infoMatches[PersonalInformationType.City] = ["city"]
        self.__infoMatches[PersonalInformationType.Zip] = ["zip"]
        self.__infoMatches[PersonalInformationType.State] = ["state", "region"]
        self.__infoMatches[PersonalInformationType.Country] = ["country"]
        self.__infoMatches[PersonalInformationType.HomePage] = ["homepage", "www"]

        self.__loaded = True

    def showConfigurationDialog(self, parent=None):
        """
        Public method to show the configuration dialog.

        @param parent reference to the parent widget
        @type QWidget
        """
        from .PersonalDataDialog import PersonalDataDialog

        dlg = PersonalDataDialog(parent=parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.storeData()
            self.__loadSettings()

    def createSubMenu(self, menu, view, hitTestResult):
        """
        Public method to create the personal information sub-menu.

        @param menu reference to the main menu
        @type QMenu
        @param view reference to the view
        @type WebBrowserView
        @param hitTestResult reference to the hit test result
        @type WebHitTestResult
        """
        self.__view = view
        self.__clickedPos = hitTestResult.pos()

        if not hitTestResult.isContentEditable():
            return

        if not self.__loaded:
            self.__loadSettings()

        submenu = QMenu(self.tr("Insert Personal Information"), menu)
        submenu.setIcon(EricPixmapCache.getIcon("pim"))

        for key, info in sorted(self.__allInfo.items()):
            if info:
                act = submenu.addAction(self.__translations[key])
                act.setData(info)
                act.triggered.connect(functools.partial(self.__insertData, act))

        submenu.addSeparator()
        submenu.addAction(
            self.tr("Edit Personal Information"), self.showConfigurationDialog
        )

        menu.addMenu(submenu)
        menu.addSeparator()

    def __insertData(self, act):
        """
        Private slot to insert the selected personal information.

        @param act reference to the action that triggered
        @type QAction
        """
        if self.__view is None or self.__clickedPos.isNull():
            return

        info = act.data()
        info = info.replace('"', '\\"')

        source = """
            var e = document.elementFromPoint({0}, {1});
            if (e) {{
                var v = e.value.substring(0, e.selectionStart);
                v += "{2}" + e.value.substring(e.selectionEnd);
                e.value = v;
            }}""".format(
            self.__clickedPos.x(), self.__clickedPos.y(), info
        )
        self.__view.page().runJavaScript(source, WebBrowserPage.SafeJsWorld)

    def viewKeyPressEvent(self, view, evt):
        """
        Protected method to handle key press events we are interested in.

        @param view reference to the view
        @type WebBrowserView
        @param evt reference to the key event
        @type QKeyEvent
        @return flag indicating handling of the event
        @rtype bool
        """
        if view is None:
            return False

        isEnter = evt.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]
        isControlModifier = evt.modifiers() & Qt.KeyboardModifier.ControlModifier
        if not isEnter or not isControlModifier:
            return False

        if not self.__loaded:
            self.__loadSettings()

        source = """
            var inputs = document.getElementsByTagName('input');
            var table = {0};
            for (var i = 0; i < inputs.length; ++i) {{
                var input = inputs[i];
                if (input.type != 'text' || input.name == '')
                    continue;
                for (var key in table) {{
                    if (!table.hasOwnProperty(key))
                        continue;
                    if (key == input.name || input.name.indexOf(key) != -1) {{
                        input.value = table[key];
                        break;
                    }}
                }}
            }}""".format(
            self.__matchingJsTable()
        )
        view.page().runJavaScript(source, WebBrowserPage.SafeJsWorld)

        return True

    def connectPage(self, page):
        """
        Public method to allow the personal information manager to connect to
        the page.

        @param page reference to the web page
        @type WebBrowserPage
        """
        page.loadFinished.connect(lambda ok: self.__pageLoadFinished(ok, page))

    def __pageLoadFinished(self, ok, page):
        """
        Private slot to handle the completion of a page load.

        @param ok flag indicating a successful load
        @type bool
        @param page reference to the web page object
        @type WebBrowserPage
        """
        if page is None or not ok:
            return

        if not self.__loaded:
            self.__loadSettings()

        source = """
            var inputs = document.getElementsByTagName('input');
            var table = {0};
            for (var i = 0; i < inputs.length; ++i) {{
                var input = inputs[i];
                if (input.type != 'text' || input.name == '')
                    continue;
                for (var key in table) {{
                    if (!table.hasOwnProperty(key) || table[key] == '')
                        continue;
                    if (key == input.name || input.name.indexOf(key) != -1) {{
                        input.style['-webkit-appearance'] = 'none';
                        input.style['-webkit-box-shadow'] =
                            'inset 0 0 2px 1px #000EEE';
                        break;
                    }}
                }}
            }}""".format(
            self.__matchingJsTable()
        )
        page.runJavaScript(source, WebBrowserPage.SafeJsWorld)

    def __matchingJsTable(self):
        """
        Private method to create the common part of the JavaScript sources.

        @return JavaScript source
        @rtype str
        """
        values = []
        for key, names in self.__infoMatches.items():
            for name in names:
                value = self.__allInfo[key].replace('"', '\\"')
                values.append('"{0}":"{1}"'.format(name, value))
        return "{{ {0} }}".format(",".join(values))
