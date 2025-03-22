# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit breakpoint properties.
"""

import os.path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_EditBreakpointDialog import Ui_EditBreakpointDialog


class EditBreakpointDialog(QDialog, Ui_EditBreakpointDialog):
    """
    Class implementing a dialog to edit breakpoint properties.
    """

    def __init__(
        self,
        breakPointId,
        properties,
        condHistory,
        parent=None,
        name=None,
        modal=False,
        addMode=False,
        filenameHistory=None,
    ):
        """
        Constructor

        @param breakPointId id of the breakpoint (tuple of (filename, line number)
        @type tuple of (str, int)
        @param properties properties for the breakpoint (tuple of (condition,
            temporary flag, enabled flag, ignore count)
        @type tuple of (str, bool, bool, int)
        @param condHistory the list of conditionals history
        @type list of str
        @param parent the parent of this dialog
        @type QWidget
        @param name the widget name of this dialog
        @type str
        @param modal flag indicating a modal dialog
        @type bool
        @param addMode flag indicating the add mode
        @type bool
        @param filenameHistory list of recently used file names
        @type list of str
        """
        super().__init__(parent)
        self.setupUi(self)
        if name:
            self.setObjectName(name)
        self.setModal(modal)

        self.filenamePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.filenamePicker.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )

        fn, lineno = breakPointId

        if not addMode:
            cond, temp, enabled, count = properties

            # set the filename
            if fn is not None:
                self.filenamePicker.setEditText(fn)

            # set the line number
            self.linenoSpinBox.setValue(lineno)

            # set the condition
            if cond is None:
                cond = ""
            try:
                curr = condHistory.index(cond)
            except ValueError:
                condHistory.insert(0, cond)
                curr = 0
            self.conditionCombo.addItems(condHistory)
            self.conditionCombo.setCurrentIndex(curr)

            # set the ignore count
            self.ignoreSpinBox.setValue(count)

            # set the checkboxes
            self.temporaryCheckBox.setChecked(temp)
            self.enabledCheckBox.setChecked(enabled)

            self.filenamePicker.setEnabled(False)
            self.linenoSpinBox.setEnabled(False)
            self.conditionCombo.setFocus()
        else:
            self.setWindowTitle(self.tr("Add Breakpoint"))
            # set the filename
            if fn is None:
                fn = ""
            try:
                curr = filenameHistory.index(fn)
            except ValueError:
                filenameHistory.insert(0, fn)
                curr = 0
            self.filenamePicker.addItems(filenameHistory)
            self.filenamePicker.setCurrentIndex(curr)

            # set the condition
            cond = ""
            try:
                curr = condHistory.index(cond)
            except ValueError:
                condHistory.insert(0, cond)
                curr = 0
            self.conditionCombo.addItems(condHistory)
            self.conditionCombo.setCurrentIndex(curr)

            if not fn:
                self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                    False
                )

        # set completer of condition combobox to be case sensitive
        self.conditionCombo.completer().setCaseSensitivity(
            Qt.CaseSensitivity.CaseSensitive
        )

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def on_filenamePicker_editTextChanged(self, fn):
        """
        Private slot to handle the change of the filename.

        @param fn text of the filename edit
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(fn))

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return a tuple containing the breakpoints new properties
            (condition, temporary flag, enabled flag, ignore count)
        @rtype tuple of (str, bool, bool, int)
        """
        return (
            self.conditionCombo.currentText(),
            self.temporaryCheckBox.isChecked(),
            self.enabledCheckBox.isChecked(),
            self.ignoreSpinBox.value(),
        )

    def getAddData(self):
        """
        Public method to retrieve the entered data for an add.

        @return a tuple containing the new breakpoints properties
            (filename, lineno, condition, temporary flag, enabled flag,
            ignore count)
        @rtype tuple of (str, int, str, bool, bool, int)
        """
        fn = self.filenamePicker.currentText()
        fn = os.path.expanduser(os.path.expandvars(fn)) if fn else None

        return (
            fn,
            self.linenoSpinBox.value(),
            self.conditionCombo.currentText(),
            self.temporaryCheckBox.isChecked(),
            self.enabledCheckBox.isChecked(),
            self.ignoreSpinBox.value(),
        )
