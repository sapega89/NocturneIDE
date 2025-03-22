# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a specialized error message dialog.
"""

import contextlib
import sys

from PyQt6.QtCore import (
    Q_ARG,
    QCoreApplication,
    QMetaObject,
    QSettings,
    Qt,
    QThread,
    QtMsgType,
    qInstallMessageHandler,
)
from PyQt6.QtWidgets import QDialog, QErrorMessage

from eric7 import EricUtilities
from eric7.EricCore import EricPreferences
from eric7.EricWidgets.EricApplication import ericApp

_msgHandlerDialog = None
_msgHandlerMinSeverity = None
_origMsgHandler = None

_filterSettings = QSettings(
    QSettings.Format.IniFormat,
    QSettings.Scope.UserScope,
    EricPreferences.settingsNameOrganization,
    "eric7messagefilters",
)
_defaultFilters = [
    "QFont::",
    "QCocoaMenu::removeMenuItem",
    "QCocoaMenu::insertNative",
    ",type id:",
    "Remote debugging server started successfully",
    "Uncaught SecurityError:",
    "Content Security Policy",
    "QXcbClipboard:",
    "QXcbConnection: XCB error",
    "libpng warning: iCCP:",
    "Uncaught ReferenceError: $ is not defined",
    "Refused to execute script from",
]


def filterMessage(message):
    """
    Module function to filter messages.

    @param message message to be checked
    @type str
    @return flag indicating that the message should be filtered out
    @rtype bool
    """
    return any(
        filterStr in message
        for filterStr in EricUtilities.toList(
            _filterSettings.value("MessageFilters", [])
        )
        + _defaultFilters
    )


class EricErrorMessage(QErrorMessage):
    """
    Class implementing a specialized error message dialog.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        if parent is None:
            parent = QCoreApplication.instance().getMainWindow()

        super().__init__(parent)

    def showMessage(self, message, msgType=""):
        """
        Public method to show a message.

        @param message error message to be shown
        @type str
        @param msgType type of the error message
        @type str
        """
        if not filterMessage(message):
            if msgType:
                super().showMessage(message, msgType)
            else:
                super().showMessage(message)

    def editMessageFilters(self):
        """
        Public method to edit the list of message filters.
        """
        from .EricErrorMessageFilterDialog import EricErrorMessageFilterDialog

        dlg = EricErrorMessageFilterDialog(
            EricUtilities.toList(_filterSettings.value("MessageFilters", [])),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            filters = dlg.getFilters()
            _filterSettings.setValue("MessageFilters", filters)


def messageHandler(msgType, context, message):
    """
    Module function handling messages.

    @param msgType type of the message
    @type  int, QtMsgType
    @param context context information
    @type QMessageLogContext
    @param message message to be shown
    @type bytes
    """
    if _msgHandlerDialog:
        if msgType.value < _msgHandlerMinSeverity:
            # severity is lower than configured
            # just ignore the message
            return

        with contextlib.suppress(RuntimeError):
            if msgType == QtMsgType.QtDebugMsg:
                messageType = "Debug Message:"
            elif msgType == QtMsgType.QtInfoMsg:
                messageType = "Info Message:"
            elif msgType == QtMsgType.QtWarningMsg:
                messageType = "Warning:"
            elif msgType == QtMsgType.QtCriticalMsg:
                messageType = "Critical:"
            elif msgType == QtMsgType.QtFatalMsg:
                messageType = "Fatal Error:"
            if isinstance(message, bytes):
                message = EricUtilities.decodeBytes(message)
            if filterMessage(message):
                return
            message = (
                message.replace("\r\n", "<br/>")
                .replace("\n", "<br/>")
                .replace("\r", "<br/>")
            )
            msg = (
                (
                    "<p><b>{0}</b></p><p>{1}</p><p>File: {2}</p>"
                    "<p>Line: {3}</p><p>Function: {4}</p>"
                ).format(
                    messageType,
                    EricUtilities.html_uencode(message),
                    context.file,
                    context.line,
                    context.function,
                )
                if context.file is not None
                else "<p><b>{0}</b></p><p>{1}</p>".format(
                    messageType, EricUtilities.html_uencode(message)
                )
            )
            if QThread.currentThread() == ericApp().thread():
                _msgHandlerDialog.showMessage(msg)
            else:
                QMetaObject.invokeMethod(
                    _msgHandlerDialog,
                    "showMessage",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, msg),
                )
            return
    elif _origMsgHandler:
        _origMsgHandler(msgType, message)
        return

    if msgType == QtMsgType.QtDebugMsg:
        messageType = "Debug Message"
    elif msgType == QtMsgType.QtInfoMsg:
        messageType = "Info Message:"
    elif msgType == QtMsgType.QtWarningMsg:
        messageType = "Warning"
    elif msgType == QtMsgType.QtCriticalMsg:
        messageType = "Critical"
    elif msgType == QtMsgType.QtFatalMsg:
        messageType = "Fatal Error"
    if isinstance(message, bytes):
        message = message.decode()
    output = "{0}: {1} in {2} at line {3} ({4})".format(
        messageType, message, context.file, context.line, context.function
    )
    try:
        print(output)
    except RuntimeError:
        # The wrapped redirector object might be gone. Write an error message
        # to the original stdout channel.
        # Note: This can happen during shutdown of an applicaton.
        if sys.__stdout__ is not None:
            sys.__stdout__.write(output)
            sys.__stdout__.flush()


def qtHandler(minSeverity):
    """
    Module function to install an EricErrorMessage dialog as the global
    message handler.

    @param minSeverity minimum severity of messages to be shown
    @type int
    @return reference to the message handler dialog
    @rtype EricErrorMessage
    """
    global _msgHandlerDialog, _msgHandlerMinSeverity, _origMsgHandler

    if _msgHandlerDialog is None:
        # Install an EricErrorMessage dialog as the global message handler.
        _msgHandlerDialog = EricErrorMessage()
        _origMsgHandler = qInstallMessageHandler(messageHandler)

    _msgHandlerMinSeverity = minSeverity

    return _msgHandlerDialog


def editMessageFilters():
    """
    Module function to edit the list of message filters.
    """
    if _msgHandlerDialog:
        _msgHandlerDialog.editMessageFilters()
    else:
        print("No message handler installed.")


def messageHandlerInstalled():
    """
    Module function to check, if a message handler was installed.

    @return flag indicating an installed message handler
    @rtype bool
    """
    return _msgHandlerDialog is not None


#
# eflag: noqa = M801
