# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing QMessageBox replacements and more convenience function.
"""

import contextlib

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

###############################################################################
##  Mappings to standard QMessageBox                                         ##
###############################################################################

# QMessageBox.Icon
NoIcon = QMessageBox.Icon.NoIcon
Critical = QMessageBox.Icon.Critical
Information = QMessageBox.Icon.Information
Question = QMessageBox.Icon.Question
Warning = QMessageBox.Icon.Warning  # __IGNORE_WARNING_M131__

# QMessageBox.StandardButton
Abort = QMessageBox.StandardButton.Abort
Apply = QMessageBox.StandardButton.Apply
Cancel = QMessageBox.StandardButton.Cancel
Close = QMessageBox.StandardButton.Close
Discard = QMessageBox.StandardButton.Discard
Help = QMessageBox.StandardButton.Help
Ignore = QMessageBox.StandardButton.Ignore
No = QMessageBox.StandardButton.No
NoToAll = QMessageBox.StandardButton.NoToAll
Ok = QMessageBox.StandardButton.Ok
Open = QMessageBox.StandardButton.Open
Reset = QMessageBox.StandardButton.Reset
RestoreDefaults = QMessageBox.StandardButton.RestoreDefaults
Retry = QMessageBox.StandardButton.Retry
Save = QMessageBox.StandardButton.Save
SaveAll = QMessageBox.StandardButton.SaveAll
Yes = QMessageBox.StandardButton.Yes
YesToAll = QMessageBox.StandardButton.YesToAll
NoButton = QMessageBox.StandardButton.NoButton

# QMessageBox.ButtonRole
AcceptRole = QMessageBox.ButtonRole.AcceptRole
ActionRole = QMessageBox.ButtonRole.ActionRole
ApplyRole = QMessageBox.ButtonRole.ApplyRole
DestructiveRole = QMessageBox.ButtonRole.DestructiveRole
InvalidRole = QMessageBox.ButtonRole.InvalidRole
HelpRole = QMessageBox.ButtonRole.HelpRole
NoRole = QMessageBox.ButtonRole.NoRole
RejectRole = QMessageBox.ButtonRole.RejectRole
ResetRole = QMessageBox.ButtonRole.ResetRole
YesRole = QMessageBox.ButtonRole.YesRole

###############################################################################
##  Replacement for the QMessageBox class                                    ##
###############################################################################


class EricMessageBox(QMessageBox):
    """
    Class implementing a replacement for QMessageBox.
    """

    def __init__(
        self,
        icon,
        title,
        text,
        modal=False,
        buttons=QMessageBox.StandardButton.NoButton,
        parent=None,
    ):
        """
        Constructor

        @param icon type of icon to be shown
        @type QMessageBox.Icon
        @param title caption of the message box
        @type str
        @param text text to be shown by the message box
        @type str
        @param modal flag indicating a modal dialog
        @type bool
        @param buttons set of standard buttons to generate
        @type StandardButtons
        @param parent parent widget of the message box
        @type QWidget
        """
        super().__init__(parent)
        self.setIcon(icon)
        if modal:
            if parent is not None:
                self.setWindowModality(Qt.WindowModality.WindowModal)
            else:
                self.setWindowModality(Qt.WindowModality.ApplicationModal)
        else:
            self.setWindowModality(Qt.WindowModality.NonModal)
        if title == "":
            self.setWindowTitle("{0}".format(QApplication.applicationName()))
        else:
            self.setWindowTitle(
                "{0} - {1}".format(QApplication.applicationName(), title)
            )
        self.setText(text)
        self.setStandardButtons(buttons)


###############################################################################
##  Replacements for QMessageBox static methods                              ##
###############################################################################


def __messageBox(
    parent,
    title,
    text,
    icon,
    buttons=QMessageBox.StandardButton.Ok,
    defaultButton=QMessageBox.StandardButton.NoButton,
    textFormat=Qt.TextFormat.AutoText,
):
    """
    Private module function to show a modal message box.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box
    @type str
    @param text text to be shown by the message box
    @type str
    @param icon type of icon to be shown
    @type QMessageBox.Icon
    @param buttons flags indicating which buttons to show
    @type QMessageBox.StandardButtons
    @param defaultButton flag indicating the default button
    @type QMessageBox.StandardButton
    @param textFormat format of the text
    @type Qt.TextFormat
    @return button pressed by the user
    @rtype QMessageBox.StandardButton
    """
    if parent is None:
        with contextlib.suppress(AttributeError):
            parent = QCoreApplication.instance().getMainWindow()

    messageBox = QMessageBox(parent)
    messageBox.setIcon(icon)
    if parent is not None:
        messageBox.setWindowModality(Qt.WindowModality.WindowModal)
    if title == "":
        messageBox.setWindowTitle("{0}".format(QApplication.applicationName()))
    else:
        messageBox.setWindowTitle(
            "{0} - {1}".format(QApplication.applicationName(), title)
        )
    messageBox.setTextFormat(textFormat)
    messageBox.setText(text)
    messageBox.setStandardButtons(buttons)
    messageBox.setDefaultButton(defaultButton)
    messageBox.exec()
    clickedButton = messageBox.clickedButton()
    if clickedButton is None:
        return QMessageBox.StandardButton.NoButton
    else:
        return messageBox.standardButton(clickedButton)


def about(parent, title, text):
    """
    Function to show a modal dialog with some text about the application.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box
    @type str
    @param text text to be shown by the message box
    @type str
    """
    if parent is None:
        parent = QCoreApplication.instance().getMainWindow()

    QMessageBox.about(parent, title, text)


def aboutQt(parent, title=""):
    """
    Function to show a modal dialog with text about Qt.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box (defaults to "")
    @type str (optional)
    """
    if parent is None:
        parent = QCoreApplication.instance().getMainWindow()

    QMessageBox.aboutQt(parent, title)


def critical(
    parent,
    title,
    text,
    buttons=QMessageBox.StandardButton.Ok,
    defaultButton=QMessageBox.StandardButton.NoButton,
):
    """
    Function to show a modal critical message box.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box
    @type str
    @param text text to be shown by the message box
    @type str
    @param buttons flags indicating which buttons to show
    @type QMessageBox.StandardButtons
    @param defaultButton flag indicating the default button
    @type QMessageBox.StandardButton
    @return button pressed by the user
    @rtype QMessageBox.StandardButton
    """
    return __messageBox(
        parent, title, text, QMessageBox.Icon.Critical, buttons, defaultButton
    )


def information(
    parent,
    title,
    text,
    buttons=QMessageBox.StandardButton.Ok,
    defaultButton=QMessageBox.StandardButton.NoButton,
):
    """
    Function to show a modal information message box.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box
    @type str
    @param text text to be shown by the message box
    @type str
    @param buttons flags indicating which buttons to show
    @type QMessageBox.StandardButtons
    @param defaultButton flag indicating the default button
    @type QMessageBox.StandardButton
    @return button pressed by the user
    @rtype QMessageBox.StandardButton
    """
    return __messageBox(
        parent, title, text, QMessageBox.Icon.Information, buttons, defaultButton
    )


def question(
    parent,
    title,
    text,
    buttons=QMessageBox.StandardButton.Ok,
    defaultButton=QMessageBox.StandardButton.NoButton,
):
    """
    Function to show a modal question message box.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box
    @type str
    @param text text to be shown by the message box
    @type str
    @param buttons flags indicating which buttons to show
    @type QMessageBox.StandardButtons
    @param defaultButton flag indicating the default button
    @type QMessageBox.StandardButton
    @return button pressed by the user
    @rtype QMessageBox.StandardButton
    """
    return __messageBox(
        parent, title, text, QMessageBox.Icon.Question, buttons, defaultButton
    )


def warning(
    parent,
    title,
    text,
    buttons=QMessageBox.StandardButton.Ok,
    defaultButton=QMessageBox.StandardButton.NoButton,
):
    """
    Function to show a modal warning message box.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box
    @type str
    @param text text to be shown by the message box
    @type str
    @param buttons flags indicating which buttons to show
    @type QMessageBox.StandardButtons
    @param defaultButton flag indicating the default button
    @type QMessageBox.StandardButton
    @return button pressed by the user
    @rtype QMessageBox.StandardButton
    """
    return __messageBox(
        parent, title, text, QMessageBox.Icon.Warning, buttons, defaultButton
    )


###############################################################################
##  Additional convenience functions                                         ##
###############################################################################


def yesNo(
    parent,
    title,
    text,
    icon=Question,
    yesDefault=False,
    textFormat=Qt.TextFormat.AutoText,
):
    """
    Function to show a model yes/no message box.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box
    @type str
    @param text text to be shown by the message box
    @type str
    @param icon icon for the dialog (Critical, Information, Question or
        Warning)
    @type QMessageBox.Icon
    @param yesDefault flag indicating that the Yes button should be the
        default button
    @type bool
    @param textFormat format of the text
    @type Qt.TextFormat
    @return flag indicating the selection of the Yes button
    @rtype bool
    @exception ValueError raised to indicate a bad parameter value
    """
    if icon not in [Critical, Information, Question, Warning]:
        raise ValueError("Bad value for 'icon' parameter.")

    res = __messageBox(
        parent,
        title,
        text,
        icon,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        yesDefault and QMessageBox.StandardButton.Yes or QMessageBox.StandardButton.No,
        textFormat,
    )
    return res == QMessageBox.StandardButton.Yes


def retryAbort(parent, title, text, icon=Question, textFormat=Qt.TextFormat.AutoText):
    """
    Function to show a model abort/retry message box.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box
    @type str
    @param text text to be shown by the message box
    @type str
    @param icon icon for the dialog (Critical, Information, Question or
        Warning)
    @type QMessageBox.Icon
    @param textFormat format of the text
    @type Qt.TextFormat
    @return flag indicating the selection of the Retry button
    @rtype bool
    @exception ValueError raised to indicate a bad parameter value
    """
    if icon not in [Critical, Information, Question, Warning]:
        raise ValueError("Bad value for 'icon' parameter.")

    res = __messageBox(
        parent,
        title,
        text,
        icon,
        QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Abort,
        QMessageBox.StandardButton.Retry,
        textFormat,
    )
    return res == QMessageBox.StandardButton.Retry


def okToClearData(parent, title, text, saveFunc, textFormat=Qt.TextFormat.AutoText):
    """
    Function to show a modal message box to ask for clearing the data.

    @param parent parent widget of the message box
    @type QWidget
    @param title caption of the message box
    @type str
    @param text text to be shown by the message box
    @type str
    @param saveFunc reference to a function performing the save action. It
        must be a parameterless function returning a flag indicating success.
    @type function
    @param textFormat format of the text
    @type Qt.TextFormat
    @return flag indicating that it is ok to clear the data
    @rtype bool
    """
    buttons = QMessageBox.StandardButton.Abort | QMessageBox.StandardButton.Discard
    if saveFunc:
        buttons |= QMessageBox.StandardButton.Save
    res = __messageBox(
        parent,
        title,
        text,
        QMessageBox.Icon.Warning,
        buttons,
        QMessageBox.StandardButton.Save,
        textFormat,
    )
    if res == QMessageBox.StandardButton.Abort:
        return False
    if res == QMessageBox.StandardButton.Save:
        return saveFunc()
    return True


#
# eflag: noqa = U200
