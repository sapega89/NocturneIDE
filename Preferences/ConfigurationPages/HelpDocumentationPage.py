# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Help Documentation configuration page.
"""

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_HelpDocumentationPage import Ui_HelpDocumentationPage


class HelpDocumentationPage(ConfigurationPageBase, Ui_HelpDocumentationPage):
    """
    Class implementing the Help Documentation configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("HelpDocumentationPage")

        self.ericDocDirPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.ericDocDirPicker.setFilters(
            self.tr("HTML Files (*.html *.htm);;All Files (*)")
        )
        self.pythonDocDirPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pythonDocDirPicker.setFilters(
            self.tr(
                "HTML Files (*.html *.htm);;"
                "Compressed Help Files (*.chm);;"
                "All Files (*)"
            )
        )
        self.qt5DocDirPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.qt5DocDirPicker.setFilters(
            self.tr("HTML Files (*.html *.htm);;All Files (*)")
        )
        self.qt6DocDirPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.qt6DocDirPicker.setFilters(
            self.tr("HTML Files (*.html *.htm);;All Files (*)")
        )
        self.pyqt5DocDirPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pyqt5DocDirPicker.setFilters(
            self.tr("HTML Files (*.html *.htm);;All Files (*)")
        )
        self.pyqt6DocDirPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pyqt6DocDirPicker.setFilters(
            self.tr("HTML Files (*.html *.htm);;All Files (*)")
        )
        self.pyside2DocDirPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pyside2DocDirPicker.setFilters(
            self.tr("HTML Files (*.html *.htm);;All Files (*)")
        )
        self.pyside6DocDirPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pyside6DocDirPicker.setFilters(
            self.tr("HTML Files (*.html *.htm);;All Files (*)")
        )

        # set initial values
        self.searchQtHelpCheckBox.setChecked(
            Preferences.getHelp("QtHelpSearchNewOnStart")
        )
        self.ericDocDirPicker.setText(Preferences.getHelp("EricDocDir"), toNative=False)
        self.pythonDocDirPicker.setText(
            Preferences.getHelp("PythonDocDir"), toNative=False
        )
        self.qt5DocDirPicker.setText(Preferences.getHelp("Qt5DocDir"), toNative=False)
        self.qt6DocDirPicker.setText(Preferences.getHelp("Qt6DocDir"), toNative=False)
        self.pyqt5DocDirPicker.setText(
            Preferences.getHelp("PyQt5DocDir"), toNative=False
        )
        self.pyqt6DocDirPicker.setText(
            Preferences.getHelp("PyQt6DocDir"), toNative=False
        )
        self.pyside2DocDirPicker.setText(
            Preferences.getHelp("PySide2DocDir"), toNative=False
        )
        self.pyside6DocDirPicker.setText(
            Preferences.getHelp("PySide6DocDir"), toNative=False
        )

    def save(self):
        """
        Public slot to save the Help Documentation configuration.
        """
        Preferences.setHelp(
            "QtHelpSearchNewOnStart", self.searchQtHelpCheckBox.isChecked()
        )
        Preferences.setHelp("EricDocDir", self.ericDocDirPicker.text(toNative=False))
        Preferences.setHelp(
            "PythonDocDir", self.pythonDocDirPicker.text(toNative=False)
        )
        Preferences.setHelp("Qt5DocDir", self.qt5DocDirPicker.text(toNative=False))
        Preferences.setHelp("Qt6DocDir", self.qt6DocDirPicker.text(toNative=False))
        Preferences.setHelp("PyQt5DocDir", self.pyqt5DocDirPicker.text(toNative=False))
        Preferences.setHelp("PyQt6DocDir", self.pyqt6DocDirPicker.text(toNative=False))
        Preferences.setHelp(
            "PySide2DocDir", self.pyside2DocDirPicker.text(toNative=False)
        )
        Preferences.setHelp(
            "PySide6DocDir", self.pyside6DocDirPicker.text(toNative=False)
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = HelpDocumentationPage()
    return page
