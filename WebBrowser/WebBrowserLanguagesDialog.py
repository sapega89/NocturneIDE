# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to configure the preferred languages.
"""

from PyQt6.QtCore import QLocale, QModelIndex, QStringListModel, pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7 import EricUtilities, Preferences

from .Ui_WebBrowserLanguagesDialog import Ui_WebBrowserLanguagesDialog


class WebBrowserLanguagesDialog(QDialog, Ui_WebBrowserLanguagesDialog):
    """
    Class implementing a dialog to configure the preferred languages.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__model = QStringListModel()
        self.languagesList.setModel(self.__model)
        self.languagesList.selectionModel().currentChanged.connect(
            self.__currentChanged
        )

        languages = EricUtilities.toList(
            Preferences.getSettings().value(
                "WebBrowser/AcceptLanguages", self.defaultAcceptLanguages()
            )
        )
        self.__model.setStringList(languages)

        allLanguages = []
        for language in QLocale.Language:
            if language == QLocale.Language.C:
                continue
            allLanguages += self.expand(language)
        self.__allLanguagesModel = QStringListModel()
        self.__allLanguagesModel.setStringList(allLanguages)
        self.addCombo.setModel(self.__allLanguagesModel)

    @pyqtSlot(QModelIndex, QModelIndex)
    def __currentChanged(self, current, _previous):
        """
        Private slot to handle a change of the current selection.

        @param current index of the currently selected item
        @type QModelIndex
        @param _previous index of the previously selected item (unused)
        @type QModelIndex
        """
        self.removeButton.setEnabled(current.isValid())
        row = current.row()
        self.upButton.setEnabled(row > 0)
        self.downButton.setEnabled(row != -1 and row < self.__model.rowCount() - 1)

    @pyqtSlot()
    def on_upButton_clicked(self):
        """
        Private slot to move a language up.
        """
        currentRow = self.languagesList.currentIndex().row()
        data = self.languagesList.currentIndex().data()
        self.__model.removeRow(currentRow)
        self.__model.insertRow(currentRow - 1)
        self.__model.setData(self.__model.index(currentRow - 1), data)
        self.languagesList.setCurrentIndex(self.__model.index(currentRow - 1))

    @pyqtSlot()
    def on_downButton_clicked(self):
        """
        Private slot to move a language down.
        """
        currentRow = self.languagesList.currentIndex().row()
        data = self.languagesList.currentIndex().data()
        self.__model.removeRow(currentRow)
        self.__model.insertRow(currentRow + 1)
        self.__model.setData(self.__model.index(currentRow + 1), data)
        self.languagesList.setCurrentIndex(self.__model.index(currentRow + 1))

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove a language from the list of acceptable
        languages.
        """
        currentRow = self.languagesList.currentIndex().row()
        self.__model.removeRow(currentRow)

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a language to the list of acceptable languages.
        """
        language = self.addCombo.currentText()
        if language in self.__model.stringList():
            return

        self.__model.insertRow(self.__model.rowCount())
        self.__model.setData(self.__model.index(self.__model.rowCount() - 1), language)
        self.languagesList.setCurrentIndex(
            self.__model.index(self.__model.rowCount() - 1)
        )

    def accept(self):
        """
        Public method to accept the data entered.
        """
        result = self.__model.stringList()
        if result == self.defaultAcceptLanguages():
            Preferences.getSettings().remove("WebBrowser/AcceptLanguages")
        else:
            Preferences.getSettings().setValue("WebBrowser/AcceptLanguages", result)
        super().accept()

    @classmethod
    def httpString(cls, languages):
        """
        Class method to convert a list of acceptable languages into a
        byte array.

        The byte array can be sent along with the Accept-Language http header
        (see RFC 2616).

        @param languages list of acceptable languages
        @type list of str
        @return converted list
        @rtype QByteArray
        """
        processed = []
        qvalue = 1.0
        for language in languages:
            leftBracket = language.find("[")
            rightBracket = language.find("]")
            tag = language[leftBracket + 1 : rightBracket]
            if not processed:
                processed.append(tag)
            else:
                processed.append("{0};q={1:.1f}".format(tag, qvalue))
            if qvalue > 0.1:
                qvalue -= 0.1

        return ", ".join(processed)

    @classmethod
    def defaultAcceptLanguages(cls):
        """
        Class method to get the list of default accept languages.

        @return list of acceptable languages
        @rtype list of str
        """
        language = QLocale.system().name()
        if not language:
            return []
        else:
            return cls.expand(QLocale(language).language())

    @classmethod
    def expand(cls, language):
        """
        Class method to expand a language enum to a readable languages
        list.

        @param language language number
        @type QLocale.Language
        @return list of expanded language names
        @rtype list of str
        """
        allLanguages = []
        countries = [
            loc.country()
            for loc in QLocale.matchingLocales(
                language, QLocale.Script.AnyScript, QLocale.Country.AnyCountry
            )
        ]
        languageString = ("{0} [{1}]").format(
            QLocale.languageToString(language), QLocale(language).name().split("_")[0]
        )
        allLanguages.append(languageString)
        for country in countries:
            languageString = ("{0}/{1} [{2}]").format(
                QLocale.languageToString(language),
                QLocale.countryToString(country),
                "-".join(QLocale(language, country).name().split("_")).lower(),
            )
            if languageString not in allLanguages:
                allLanguages.append(languageString)

        return allLanguages
