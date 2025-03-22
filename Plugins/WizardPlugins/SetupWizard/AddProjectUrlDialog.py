# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a project URL.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_AddProjectUrlDialog import Ui_AddProjectUrlDialog


class AddProjectUrlDialog(QDialog, Ui_AddProjectUrlDialog):
    """
    Class implementing a dialog to enter the data for a project URL.
    """

    def __init__(self, name="", url="", parent=None):
        """
        Constructor

        @param name name of the project URL (defaults to "")
        @type str (optional)
        @param url address of the project URL (defaults to "")
        @type str (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.nameComboBox.lineEdit().setClearButtonEnabled(True)
        self.nameComboBox.addItems(
            [
                "",
                "Bug Tracker",
                "Change Log",
                "Documentation",
                "Donation",
                "Download",
                "Funding",
                "Homepage",
                "Issues Tracker",
                "News",
                "Release Notes",
            ]
        )

        self.nameComboBox.editTextChanged.connect(self.__updateOK)
        self.urlEdit.textChanged.connect(self.__updateOK)

        self.nameComboBox.setEditText(name)
        self.urlEdit.setText(url)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the enabled state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.nameComboBox.currentText())
            and bool(self.urlEdit.text())
            and self.urlEdit.text().startswith(("http://", "https://"))
        )

    def getUrl(self):
        """
        Public method to get the data for the project URL.

        @return tuple containing the name and address of the project URL
        @rtype tuple of (str, str)
        """
        return (
            self.nameComboBox.currentText(),
            self.urlEdit.text(),
        )
