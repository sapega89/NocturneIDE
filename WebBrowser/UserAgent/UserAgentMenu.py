# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a menu to select the user agent string.
"""

import functools
import os

from PyQt6.QtCore import QFile, QIODevice, QXmlStreamReader
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMenu

from eric7.EricWidgets import EricMessageBox
from eric7.WebBrowser.WebBrowserPage import WebBrowserPage
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class UserAgentMenu(QMenu):
    """
    Class implementing a menu to select the user agent string.
    """

    def __init__(self, title, url=None, parent=None):
        """
        Constructor

        @param title title of the menu
        @type str
        @param url URL to set user agent for
        @type QUrl
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(title, parent)

        self.__manager = None
        self.__url = url
        if self.__url:
            if self.__url.isValid():
                self.__manager = WebBrowserWindow.userAgentsManager()
            else:
                self.__url = None

        self.aboutToShow.connect(self.__populateMenu)

    def __populateMenu(self):
        """
        Private slot to populate the menu.
        """
        self.aboutToShow.disconnect(self.__populateMenu)

        self.__actionGroup = QActionGroup(self)

        # add default action
        self.__defaultUserAgent = QAction(self)
        self.__defaultUserAgent.setText(self.tr("Default"))
        self.__defaultUserAgent.setCheckable(True)
        self.__defaultUserAgent.triggered.connect(self.__switchToDefaultUserAgent)
        if self.__url:
            self.__defaultUserAgent.setChecked(
                self.__manager.userAgentForUrl(self.__url) == ""
            )
        else:
            self.__defaultUserAgent.setChecked(WebBrowserPage.userAgent() == "")
        self.addAction(self.__defaultUserAgent)
        self.__actionGroup.addAction(self.__defaultUserAgent)
        isChecked = self.__defaultUserAgent.isChecked()

        # add default extra user agents
        isChecked = self.__addDefaultActions() or isChecked

        # add other action
        self.addSeparator()
        self.__otherUserAgent = QAction(self)
        self.__otherUserAgent.setText(self.tr("Other..."))
        self.__otherUserAgent.setCheckable(True)
        self.__otherUserAgent.triggered.connect(self.__switchToOtherUserAgent)
        self.addAction(self.__otherUserAgent)
        self.__actionGroup.addAction(self.__otherUserAgent)
        self.__otherUserAgent.setChecked(not isChecked)

    def __switchToDefaultUserAgent(self):
        """
        Private slot to set the default user agent.
        """
        if self.__url:
            self.__manager.removeUserAgent(self.__url.host())
        else:
            WebBrowserPage.setUserAgent("")

    def __switchToOtherUserAgent(self):
        """
        Private slot to set a custom user agent string.
        """
        from eric7.WebBrowser.WebBrowserPage import WebBrowserPage

        userAgent, ok = QInputDialog.getText(
            self,
            self.tr("Custom user agent"),
            self.tr("User agent:"),
            QLineEdit.EchoMode.Normal,
            WebBrowserPage.userAgent(resolveEmpty=True),
        )
        if ok:
            if self.__url:
                self.__manager.setUserAgentForUrl(self.__url, userAgent)
            else:
                WebBrowserPage.setUserAgent(userAgent)

    def __changeUserAgent(self, act):
        """
        Private slot to change the user agent.

        @param act reference to the action that triggered
        @type QAction
        """
        if self.__url:
            self.__manager.setUserAgentForUrl(self.__url, act.data())
        else:
            WebBrowserPage.setUserAgent(act.data())

    def __addDefaultActions(self):
        """
        Private slot to add the default user agent entries.

        @return flag indicating that a user agent entry is checked
        @rtype bool
        """
        defaultUserAgents = QFile(
            os.path.join(os.path.dirname(__file__), "UserAgentDefaults.xml")
        )
        defaultUserAgents.open(QIODevice.OpenModeFlag.ReadOnly)

        menuStack = []
        isChecked = False

        currentUserAgentString = (
            self.__manager.userAgentForUrl(self.__url)
            if self.__url
            else WebBrowserPage.userAgent()
        )
        xml = QXmlStreamReader(defaultUserAgents)
        while not xml.atEnd():
            xml.readNext()
            if xml.isStartElement() and xml.name() == "separator":
                if menuStack:
                    menuStack[-1].addSeparator()
                else:
                    self.addSeparator()
                continue

            if xml.isStartElement() and xml.name() == "useragent":
                attributes = xml.attributes()
                title = attributes.value("description")
                userAgent = attributes.value("useragent")

                act = QAction(self)
                act.setText(title)
                act.setData(userAgent)
                act.setToolTip(userAgent)
                act.setCheckable(True)
                act.setChecked(userAgent == currentUserAgentString)
                act.triggered.connect(functools.partial(self.__changeUserAgent, act))
                if menuStack:
                    menuStack[-1].addAction(act)
                else:
                    self.addAction(act)
                self.__actionGroup.addAction(act)
                isChecked = isChecked or act.isChecked()

            if xml.isStartElement() and xml.name() == "useragentmenu":
                attributes = xml.attributes()
                title = attributes.value("title")
                if title == "v_a_r_i_o_u_s":
                    title = self.tr("Various")

                menu = QMenu(self)
                menu.setTitle(title)
                self.addMenu(menu)
                menuStack.append(menu)

            if xml.isEndElement() and xml.name() == "useragentmenu":
                menuStack.pop()

        if xml.hasError():
            EricMessageBox.critical(
                self,
                self.tr("Parsing default user agents"),
                self.tr(
                    """<p>Error parsing default user agents.</p><p>{0}</p>"""
                ).format(xml.errorString()),
            )

        return isChecked
