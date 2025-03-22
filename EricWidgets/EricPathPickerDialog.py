# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter a file system path using a file picker.
"""

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from .EricPathPicker import EricPathPicker, EricPathPickerModes


class EricPathPickerDialog(QDialog):
    """
    Class implementing a dialog to enter a file system path using a file
    picker.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setMinimumWidth(400)

        self.__layout = QVBoxLayout(self)

        self.__label = QLabel(self)
        self.__label.setWordWrap(True)

        self.__pathPicker = EricPathPicker(self)
        self.__buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok,
            self,
        )

        self.__layout.addWidget(self.__label)
        self.__layout.addWidget(self.__pathPicker)
        self.__layout.addWidget(self.__buttonBox)

        self.__buttonBox.accepted.connect(self.accept)
        self.__buttonBox.rejected.connect(self.reject)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def setLabelText(self, text):
        """
        Public method to set the label text.

        @param text label text
        @type str
        """
        self.__label.setText(text)

    def setTitle(self, title):
        """
        Public method to set the window title.

        @param title window title
        @type str
        """
        self.setWindowTitle(title)
        self.__pathPicker.setWindowTitle(title)

    def setPickerMode(self, mode):
        """
        Public method to set the mode of the path picker.

        @param mode picker mode
        @type EricPathPickerModes
        """
        self.__pathPicker.setMode(mode)

    def setPickerRemote(self, remote):
        """
        Public method to set the remote mode of the path picker.

        @param remote flag indicating the remote mode
        @type bool
        """
        self.__pathPicker.setRemote(remote)

    def setPickerFilters(self, filters):
        """
        Public method to set the filters of the path picker.

        Note: Multiple filters must be separated by ';;'.

        @param filters string containing the file filters
        @type str
        """
        self.__pathPicker.setFilters(filters)

    def setPickerPath(self, fpath):
        """
        Public method to set the path of the path picker.

        @param fpath path to be set
        @type str or pathlib.Path
        """
        self.__pathPicker.setText(str(fpath))

    def setDefaultDirectory(self, directory):
        """
        Public method to set the default directory of the path picker.

        @param directory default directory
        @type str or pathlib.Path
        """
        self.__pathPicker.setDefaultDirectory(str(directory))

    def getText(self):
        """
        Public method to get the current path as text.

        @return current path
        @rtype str
        """
        return self.__pathPicker.text()

    def getPath(self):
        """
        Public method to get the current path as a pathlib.Path object.

        @return current path
        @rtype pathlib.Path
        """
        return self.__pathPicker.path()


def getStrPath(
    parent,
    title,
    label,
    mode=EricPathPickerModes.OPEN_FILE_MODE,
    strPath=None,
    defaultDirectory=None,
    filters=None,
    remote=False,
):
    """
    Function to get a file or directory path from the user.

    @param parent reference to the parent widget
    @type QWidget
    @param title title of the dialog
    @type str
    @param label text to be shown above the path picker
    @type str
    @param mode mode of the path picker (defaults to EricPathPickerModes.OPEN_FILE_MODE)
    @type EricPathPickerModes (optional)
    @param strPath initial path to be shown (defaults to None)
    @type str (optional)
    @param defaultDirectory default directory of the path picker selection
        dialog (defaults to None)
    @type str (optional)
    @param filters list of file filters (defaults to None)
    @type list of str (optional)
    @param remote flag indicating the remote mode (defaults to False)
    @type bool (optional)
    @return tuple containing the entered path and a flag indicating that the
        user pressed the OK button
    @rtype tuple of (str, bool)
    """
    if parent is None:
        parent = QCoreApplication.instance().getMainWindow()

    # step 1: setup of the dialog
    dlg = EricPathPickerDialog(parent)
    if title:
        dlg.setTitle(title)
    if label:
        dlg.setLabelText(label)
    dlg.setPickerMode(mode)
    dlg.setPickerRemote(remote)
    if strPath:
        dlg.setPickerPath(strPath)
    if defaultDirectory:
        dlg.setDefaultDirectory(defaultDirectory)
    if filters is not None and len(filters) > 0:
        dlg.setPickerFilters(";;".join(filters))

    # step 2: show the dialog and get the result
    if dlg.exec() == QDialog.DialogCode.Accepted:
        ok = True
        fpath = dlg.getText().strip()
    else:
        ok = False
        fpath = ""

    # step 3: return the result
    return fpath, ok


def getPath(
    parent,
    title,
    label,
    mode=EricPathPickerModes.OPEN_FILE_MODE,
    pathlibPath=None,
    defaultDirectory=None,
    filters=None,
):
    """
    Function to get a file or directory path from the user.

    @param parent reference to the parent widget
    @type QWidget
    @param title title of the dialog
    @type str
    @param label text to be shown above the path picker
    @type str
    @param mode mode of the path picker (defaults to EricPathPickerModes.OPEN_FILE_MODE)
    @type EricPathPickerModes (optional)
    @param pathlibPath initial path to be shown (defaults to None)
    @type pathlib.Path (optional)
    @param defaultDirectory default directory of the path picker selection
        dialog (defaults to None)
    @type pathlib.Path (optional)
    @param filters list of file filters (defaults to None)
    @type list of str (optional)
    @return tuple containing the entered path and a flag indicating that the
        user pressed the OK button
    @rtype tuple of (pathlib.Path, bool)
    """
    if parent is None:
        parent = QCoreApplication.instance().getMainWindow()

    # step 1: setup of the dialog
    dlg = EricPathPickerDialog(parent)
    if title:
        dlg.setTitle(title)
    if label:
        dlg.setLabelText(label)
    dlg.setPickerMode(mode)
    if pathlibPath:
        dlg.setPickerPath(pathlibPath)
    if defaultDirectory:
        dlg.setDefaultDirectory(defaultDirectory)
    if filters is not None and len(filters) > 0:
        dlg.setPickerFilters(";;".join(filters))

    # step 2: show the dialog and get the result
    if dlg.exec() == QDialog.DialogCode.Accepted:
        ok = True
        fpath = dlg.getText().strip()
    else:
        ok = False
        fpath = ""

    # step 3: return the result
    return fpath, ok
