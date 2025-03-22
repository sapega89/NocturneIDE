# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a new property.
"""

from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_SvnPropSetDialog import Ui_SvnPropSetDialog


class SvnPropSetDialog(QDialog, Ui_SvnPropSetDialog):
    """
    Class implementing a dialog to enter the data for a new property.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.propFilePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)

    def getData(self):
        """
        Public slot used to retrieve the data entered into the dialog.

        @return tuple containing the property name, a flag indicating a file was
            selected and the text of the property or the selected filename
        @rtype tuple of (str, bool, str)
        """
        if self.fileRadioButton.isChecked():
            return (self.propNameEdit.text(), True, self.propFilePicker.text())
        else:
            return (self.propNameEdit.text(), False, self.propTextEdit.toPlainText())
