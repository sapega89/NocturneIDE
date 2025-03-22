# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to configure the various view profiles.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_ViewProfileSidebarsDialog import Ui_ViewProfileSidebarsDialog
from .Ui_ViewProfileToolboxesDialog import Ui_ViewProfileToolboxesDialog


class ViewProfileDialog(QDialog):
    """
    Class implementing a dialog to configure the various view profiles.
    """

    def __init__(self, layout, editVisibilities, debugVisibilities, parent=None):
        """
        Constructor

        @param layout type of the window layout
        @type str
        @param editVisibilities list  of flags giving the visibilities
            of the various parts for the 'edit' view profile
        @type list of bool
        @param debugVisibilities list  of flags giving the visibilities
            of the various parts for the 'debug' view profile
        @type list of bool
        @param parent parent widget of this dialog
        @type QWidget
        @exception ValueError raised to indicate an invalid layout
        """
        super().__init__(parent)

        if layout not in ("Toolboxes", "Sidebars"):
            raise ValueError("Illegal layout given ({0}).".format(self.__layout))

        self.__layout = layout
        if self.__layout == "Toolboxes":
            self.ui = Ui_ViewProfileToolboxesDialog()
        else:
            self.ui = Ui_ViewProfileSidebarsDialog()
        self.ui.setupUi(self)

        if self.__layout in ["Toolboxes", "Sidebars"]:
            # set the edit profile
            self.ui.epltCheckBox.setChecked(editVisibilities[0])
            self.ui.ephtCheckBox.setChecked(editVisibilities[1])
            self.ui.eprtCheckBox.setChecked(editVisibilities[2])

            # set the debug profile
            self.ui.dpltCheckBox.setChecked(debugVisibilities[0])
            self.ui.dphtCheckBox.setChecked(debugVisibilities[1])
            self.ui.dprtCheckBox.setChecked(debugVisibilities[2])

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getVisibilities(self):
        """
        Public method to retrieve the visibilities configuration.

        @return tuple of two lists giving the visibilities of the
            various parts
        @rtype list
        """
        if self.__layout in ["Toolboxes", "Sidebars"]:
            return (
                # edit profile
                [
                    self.ui.epltCheckBox.isChecked(),
                    self.ui.ephtCheckBox.isChecked(),
                    self.ui.eprtCheckBox.isChecked(),
                ],
                # debug profile
                [
                    self.ui.dpltCheckBox.isChecked(),
                    self.ui.dphtCheckBox.isChecked(),
                    self.ui.dprtCheckBox.isChecked(),
                ],
            )

        return (
            [True, True, True],  # edit profile
            [True, True, True],  # debug profile
        )
