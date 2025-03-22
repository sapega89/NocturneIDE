# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter some text.
"""

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout


class EricTextInputDialog(QDialog):
    """
    Class implementing a dialog to enter some text.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setMaximumWidth(600)

        self.__layout = QVBoxLayout(self)

        self.__label = QLabel(self)
        self.__layout.addWidget(self.__label)

        self.__lineEdit = QLineEdit(self)
        self.__lineEdit.setClearButtonEnabled(True)
        self.__layout.addWidget(self.__lineEdit)

        self.__buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.__layout.addWidget(self.__buttonBox)

        self.__buttonBox.accepted.connect(self.accept)
        self.__buttonBox.rejected.connect(self.reject)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def setTextEchoMode(self, echoMode):
        """
        Public method to set the echo mode of the line edit.

        @param echoMode echo mode of the line edit
        @type QLineEdit.EchoMode
        """
        self.__lineEdit.setEchoMode(echoMode)

    def textEchoMode(self):
        """
        Public method to get the current echo mode of the line edit.

        @return echo mode of the line edit
        @rtype QLineEdit.EchoMode
        """
        return self.__lineEdit.echoMode()

    def setTextValue(self, text):
        """
        Public method to set the text of the line edit.

        @param text text for the line edit
        @type str
        """
        self.__lineEdit.setText(text)

    def textValue(self):
        """
        Public method to get the text of the line edit.

        @return text of the line edit
        @rtype str
        """
        return self.__lineEdit.text()

    def setLabelText(self, text):
        """
        Public method to set the label text.

        @param text label text
        @type str
        """
        self.__label.setText(text)

        msh = self.minimumSizeHint()
        labelSizeHint = self.__label.sizeHint()
        self.resize(max(self.width(), msh.width(), labelSizeHint.width()), msh.height())

    def labelText(self):
        """
        Public method to get the current label text.

        @return current label text
        @rtype str
        """
        return self.label.text()


def getText(
    parent, title, label, mode=QLineEdit.EchoMode.Normal, text="", minimumWidth=300
):
    """
    Function to get create a dialog to enter some text and return it.

    @param parent reference to the parent widget
    @type QWidget
    @param title title of the dialog
    @type str
    @param label label of the dialog
    @type str
    @param mode echo mode of the line edit
    @type QLineEdit.EchoMode
    @param text initial text of the line edit
    @type str
    @param minimumWidth minimum width of the dialog
    @type int
    @return tuple containing a flag indicating the dialog was accepted and the
        entered text
    @rtype tuple of (bool, str)
    """
    if parent is None:
        parent = QCoreApplication.instance().getMainWindow()

    dlg = EricTextInputDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setLabelText(label)
    dlg.setTextEchoMode(mode)
    dlg.setTextValue(text)
    dlg.setMinimumWidth(minimumWidth)

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return True, dlg.textValue()
    else:
        return False, ""
