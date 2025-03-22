# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit channel data.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_IrcChannelEditDialog import Ui_IrcChannelEditDialog


class IrcChannelEditDialog(QDialog, Ui_IrcChannelEditDialog):
    """
    Class implementing a dialog to edit channel data.
    """

    def __init__(self, name, key, autoJoin, edit, parent=None):
        """
        Constructor

        @param name channel name
        @type str
        @param key channel key
        @type str
        @param autoJoin flag indicating, that the channel should
            be joined automatically
        @type bool
        @param edit flag indicating an edit of an existing
            channel
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.nameEdit.setText(name)
        self.keyEdit.setText(key)
        self.autoJoinCheckBox.setChecked(autoJoin)

        self.nameEdit.setReadOnly(edit)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(name != "")

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the given name.

        @param txt text of the edit
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(txt != "")

    def getData(self):
        """
        Public method to get the channel data.

        @return tuple giving the channel name, channel key and a flag
            indicating, that the channel should be joined automatically
        @rtype tuple of (str, str, bool)
        """
        return (
            self.nameEdit.text(),
            self.keyEdit.text(),
            self.autoJoinCheckBox.isChecked(),
        )
