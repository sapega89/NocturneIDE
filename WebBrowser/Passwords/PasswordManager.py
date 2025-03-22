# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the password manager.
"""

import os

from PyQt6.QtCore import (
    QByteArray,
    QCoreApplication,
    QObject,
    QUrl,
    QXmlStreamReader,
    pyqtSignal,
)
from PyQt6.QtWebEngineCore import QWebEngineScript
from PyQt6.QtWidgets import QApplication

from eric7 import EricUtilities, Preferences
from eric7.EricUtilities import crypto
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricProgressDialog import EricProgressDialog
from eric7.Utilities.AutoSaver import AutoSaver
from eric7.WebBrowser.Tools import Scripts
from eric7.WebBrowser.WebBrowserPage import WebBrowserPage
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class PasswordManager(QObject):
    """
    Class implementing the password manager.

    @signal changed() emitted to indicate a change
    @signal passwordsSaved() emitted after the passwords were saved
    """

    changed = pyqtSignal()
    passwordsSaved = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        # setup userscript to monitor forms
        script = QWebEngineScript()
        script.setName("_eric_passwordmonitor")
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setWorldId(WebBrowserPage.SafeJsWorld)
        script.setRunsOnSubFrames(True)
        script.setSourceCode(Scripts.setupFormObserver())
        profile = WebBrowserWindow.webProfile()
        profile.scripts().insert(script)

        self.__logins = {}
        self.__loginForms = {}
        self.__never = []
        self.__loaded = False
        self.__saveTimer = AutoSaver(self, self.save)

        self.changed.connect(self.__saveTimer.changeOccurred)

    def clear(self):
        """
        Public slot to clear the saved passwords.
        """
        if not self.__loaded:
            self.__load()

        self.__logins = {}
        self.__loginForms = {}
        self.__never = []
        self.__saveTimer.changeOccurred()
        self.__saveTimer.saveIfNeccessary()

        self.changed.emit()

    def getLogin(self, url, realm):
        """
        Public method to get the login credentials.

        @param url URL to get the credentials for
        @type QUrl
        @param realm realm to get the credentials for
        @type str
        @return tuple containing the user name (string) and password
        @rtype str
        """
        if not self.__loaded:
            self.__load()

        key = self.__createKey(url, realm)
        try:
            return self.__logins[key][0], crypto.pwConvert(
                self.__logins[key][1], encode=False
            )
        except KeyError:
            return "", ""

    def setLogin(self, url, realm, username, password):
        """
        Public method to set the login credentials.

        @param url URL to set the credentials for
        @type QUrl
        @param realm realm to set the credentials for
        @type str
        @param username username for the login
        @type str
        @param password password for the login
        @type str
        """
        if not self.__loaded:
            self.__load()

        key = self.__createKey(url, realm)
        self.__logins[key] = (
            username,
            crypto.pwConvert(password, encode=True),
        )
        self.changed.emit()

    def __createKey(self, url, realm):
        """
        Private method to create the key string for the login credentials.

        @param url URL to get the credentials for
        @type QUrl
        @param realm realm to get the credentials for
        @type str
        @return key string
        @rtype str
        """
        authority = url.authority()
        if authority.startswith("@"):
            authority = authority[1:]
        key = (
            "{0}://{1} ({2})".format(url.scheme(), authority, realm)
            if realm
            else "{0}://{1}".format(url.scheme(), authority)
        )
        return key

    def getFileName(self):
        """
        Public method to get the file name of the passwords file.

        @return name of the passwords file
        @rtype str
        """
        return os.path.join(EricUtilities.getConfigDir(), "web_browser", "logins.xml")

    def save(self):
        """
        Public slot to save the login entries to disk.
        """
        from .PasswordWriter import PasswordWriter

        if not self.__loaded:
            return

        if not WebBrowserWindow.isPrivate():
            loginFile = self.getFileName()
            writer = PasswordWriter()
            if not writer.write(
                loginFile, self.__logins, self.__loginForms, self.__never
            ):
                EricMessageBox.critical(
                    None,
                    self.tr("Saving login data"),
                    self.tr(
                        """<p>Login data could not be saved to <b>{0}</b></p>"""
                    ).format(loginFile),
                )
            else:
                self.passwordsSaved.emit()

    def __load(self):
        """
        Private method to load the saved login credentials.
        """
        from .PasswordReader import PasswordReader

        if self.__loaded:
            return

        loginFile = self.getFileName()
        if os.path.exists(loginFile):
            reader = PasswordReader()
            self.__logins, self.__loginForms, self.__never = reader.read(loginFile)
            if reader.error() != QXmlStreamReader.Error.NoError:
                EricMessageBox.warning(
                    None,
                    self.tr("Loading login data"),
                    self.tr(
                        """Error when loading login data on"""
                        """ line {0}, column {1}:\n{2}"""
                    ).format(
                        reader.lineNumber(), reader.columnNumber(), reader.errorString()
                    ),
                )

        self.__loaded = True

    def reload(self):
        """
        Public method to reload the login data.
        """
        if not self.__loaded:
            return

        self.__loaded = False
        self.__load()

    def close(self):
        """
        Public method to close the passwords manager.
        """
        self.__saveTimer.saveIfNeccessary()

    def removePassword(self, site):
        """
        Public method to remove a password entry.

        @param site web site name
        @type str
        """
        if site in self.__logins:
            del self.__logins[site]
            if site in self.__loginForms:
                del self.__loginForms[site]
            self.changed.emit()

    def allSiteNames(self):
        """
        Public method to get a list of all site names.

        @return sorted list of all site names
        @rtype list of str
        """
        if not self.__loaded:
            self.__load()

        return sorted(self.__logins)

    def sitesCount(self):
        """
        Public method to get the number of available sites.

        @return number of sites
        @rtype int
        """
        if not self.__loaded:
            self.__load()

        return len(self.__logins)

    def siteInfo(self, site):
        """
        Public method to get a reference to the named site.

        @param site web site name
        @type str
        @return tuple containing the user name (string) and password
        @rtype str
        """
        if not self.__loaded:
            self.__load()

        if site not in self.__logins:
            return None

        return self.__logins[site][0], crypto.pwConvert(
            self.__logins[site][1], encode=False
        )

    def formSubmitted(self, urlStr, userName, password, data, page):
        """
        Public method to record login data.

        @param urlStr form submission URL
        @type str
        @param userName name of the user
        @type str
        @param password user password
        @type str
        @param data data to be submitted
        @type QByteArray
        @param page reference to the calling page
        @type QWebEnginePage
        """
        from .LoginForm import LoginForm

        # shall passwords be saved?
        if not Preferences.getUser("SavePasswords"):
            return

        if WebBrowserWindow.isPrivate():
            return

        if not self.__loaded:
            self.__load()

        if urlStr in self.__never:
            return

        if userName and password:
            url = QUrl(urlStr)
            url = self.__stripUrl(url)
            key = self.__createKey(url, "")
            if key not in self.__loginForms:
                mb = EricMessageBox.EricMessageBox(
                    EricMessageBox.Question,
                    self.tr("Save password"),
                    self.tr(
                        """<b>Would you like to save this password?</b><br/>"""
                        """To review passwords you have saved and remove"""
                        """ them, use the password management dialog of the"""
                        """ Settings menu."""
                    ),
                    modal=True,
                    parent=page.view(),
                )
                neverButton = mb.addButton(
                    self.tr("Never for this site"), EricMessageBox.DestructiveRole
                )
                noButton = mb.addButton(self.tr("Not now"), EricMessageBox.RejectRole)
                mb.addButton(EricMessageBox.Yes)
                mb.exec()
                if mb.clickedButton() == neverButton:
                    self.__never.append(url.toString())
                    return
                elif mb.clickedButton() == noButton:
                    return

            self.__logins[key] = (
                userName,
                crypto.pwConvert(password, encode=True),
            )
            form = LoginForm()
            form.url = url
            form.name = userName
            form.postData = crypto.pwConvert(bytes(data).decode("utf-8"), encode=True)
            self.__loginForms[key] = form
            self.changed.emit()

    def __stripUrl(self, url):
        """
        Private method to strip off all unneeded parts of a URL.

        @param url URL to be stripped
        @type QUrl
        @return stripped URL
        @rtype QUrl
        """
        cleanUrl = QUrl(url)
        cleanUrl.setQuery("")
        cleanUrl.setUserInfo("")

        authority = cleanUrl.authority()
        if authority.startswith("@"):
            authority = authority[1:]
        cleanUrl = QUrl(
            "{0}://{1}{2}".format(cleanUrl.scheme(), authority, cleanUrl.path())
        )
        cleanUrl.setFragment("")
        return cleanUrl

    def completePage(self, page):
        """
        Public slot to complete login forms with saved data.

        @param page reference to the web page
        @type WebBrowserPage
        """
        if page is None:
            return

        if not self.__loaded:
            self.__load()

        url = page.url()
        url = self.__stripUrl(url)
        key = self.__createKey(url, "")
        if key not in self.__loginForms or key not in self.__logins:
            return

        form = self.__loginForms[key]
        if form.url != url:
            return

        postData = QByteArray(
            crypto.pwConvert(form.postData, encode=False).encode("utf-8")
        )
        script = Scripts.completeFormData(postData)
        page.runJavaScript(script, WebBrowserPage.SafeJsWorld)

    def mainPasswordChanged(self, oldPassword, newPassword):
        """
        Public slot to handle the change of the main password.

        @param oldPassword current main password
        @type str
        @param newPassword new main password
        @type str
        """
        if not self.__loaded:
            self.__load()

        progress = EricProgressDialog(
            self.tr("Re-encoding saved passwords..."),
            None,
            0,
            len(self.__logins) + len(self.__loginForms),
            self.tr("%v/%m Passwords"),
            QApplication.activeModalWidget(),
        )
        progress.setMinimumDuration(0)
        progress.setWindowTitle(self.tr("Passwords"))
        count = 0  # noqa: Y113

        # step 1: do the logins
        for key in self.__logins:
            progress.setValue(count)
            QCoreApplication.processEvents()
            username, pwHash = self.__logins[key]
            pwHash = crypto.pwRecode(pwHash, oldPassword, newPassword)
            self.__logins[key] = (username, pwHash)
            count += 1

        # step 2: do the login forms
        for key in self.__loginForms:
            progress.setValue(count)
            QCoreApplication.processEvents()
            postData = self.__loginForms[key].postData
            postData = crypto.pwRecode(postData, oldPassword, newPassword)
            self.__loginForms[key].postData = postData
            count += 1

        progress.setValue(len(self.__logins) + len(self.__loginForms))
        QCoreApplication.processEvents()
        self.changed.emit()
