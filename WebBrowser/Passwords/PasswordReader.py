# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to read login data files.
"""

from PyQt6.QtCore import QCoreApplication, QFile, QIODevice, QUrl, QXmlStreamReader


class PasswordReader(QXmlStreamReader):
    """
    Class implementing a reader object for login data files.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

    def read(self, fileNameOrDevice):
        """
        Public method to read a login data file.

        @param fileNameOrDevice name of the file to read
        @type str
            or reference to the device to read (QIODevice)
        @return tuple containing the logins, forms and never URLs
        @rtype tuple of (dict, dict, list)
        """
        self.__logins = {}
        self.__loginForms = {}
        self.__never = []

        if isinstance(fileNameOrDevice, QIODevice):
            self.setDevice(fileNameOrDevice)
        else:
            f = QFile(fileNameOrDevice)
            if not f.exists():
                return self.__logins, self.__loginForms, self.__never
            f.open(QIODevice.OpenModeFlag.ReadOnly)
            self.setDevice(f)

        while not self.atEnd():
            self.readNext()
            if self.isStartElement():
                version = self.attributes().value("version")
                if self.name() == "Password" and (not version or version == "2.0"):
                    self.__readPasswords()
                else:
                    self.raiseError(
                        QCoreApplication.translate(
                            "PasswordReader",
                            "The file is not a Passwords version 2.0 file.",
                        )
                    )

        return self.__logins, self.__loginForms, self.__never

    def __readPasswords(self):
        """
        Private method to read and parse the login data file.
        """
        if not self.isStartElement() and self.name() != "Password":
            return

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break

            if self.isStartElement():
                if self.name() == "Logins":
                    self.__readLogins()
                elif self.name() == "Forms":
                    self.__readForms()
                elif self.name() == "Nevers":
                    self.__readNevers()
                else:
                    self.__skipUnknownElement()

    def __readLogins(self):
        """
        Private method to read the login information.
        """
        if not self.isStartElement() and self.name() != "Logins":
            return

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                if self.name() == "Login":
                    continue
                else:
                    break

            if self.isStartElement():
                if self.name() == "Login":
                    attributes = self.attributes()
                    key = attributes.value("key")
                    user = attributes.value("user")
                    password = attributes.value("password")
                    self.__logins[key] = (user, password)
                else:
                    self.__skipUnknownElement()

    def __readForms(self):
        """
        Private method to read the forms information.
        """
        from .LoginForm import LoginForm

        if not self.isStartElement() and self.name() != "Forms":
            return

        while not self.atEnd():
            self.readNext()
            if self.isStartElement():
                if self.name() == "Form":
                    attributes = self.attributes()
                    key = attributes.value("key")
                    form = LoginForm()
                    form.url = QUrl(attributes.value("url"))
                    form.name = attributes.value("name")

                elif self.name() == "PostData":
                    form.postData = self.readElementText()
                else:
                    self.__skipUnknownElement()

            if self.isEndElement():
                if self.name() == "Form":
                    self.__loginForms[key] = form
                    continue
                elif self.name() in ["PostData", "Elements", "Element"]:
                    continue
                else:
                    break

    def __readNevers(self):
        """
        Private method to read the never URLs.
        """
        if not self.isStartElement() and self.name() != "Nevers":
            return

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                if self.name() == "Never":
                    continue
                else:
                    break

            if self.isStartElement():
                if self.name() == "Never":
                    self.__never.append(self.attributes().value("url"))
                else:
                    self.__skipUnknownElement()

    def __skipUnknownElement(self):
        """
        Private method to skip over all unknown elements.
        """
        if not self.isStartElement():
            return

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break

            if self.isStartElement():
                self.__skipUnknownElement()
