# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the file system interface to the eric-ide server.
"""

from PyQt6.QtCore import QEventLoop, QObject, pyqtSignal, pyqtSlot

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.RemoteServer.EricRequestCategory import EricRequestCategory
from eric7.SystemUtilities import FileSystemUtilities


class EricServerDebuggerInterface(QObject):
    """
    Class implementing the file system interface to the eric-ide server.

    @signal debugClientResponse(response:str) emitted to relay a response of
        the remote debug client
    @signal debugClientDisconnected(debuggerId:str) emitted when a remote debug
        client did disconnect from the eric-ide server
    @signal lastClientExited() emitted to indicate that the last debug client of
        the eric-ide server exited
    """

    debugClientResponse = pyqtSignal(str)
    debugClientDisconnected = pyqtSignal(str)
    lastClientExited = pyqtSignal()

    def __init__(self, serverInterface):
        """
        Constructor

        @param serverInterface reference to the eric-ide server interface
        @type EricServerInterface
        """
        super().__init__(parent=serverInterface)

        self.__serverInterface = serverInterface
        self.__clientStarted = False

        self.__replyMethodMapping = {
            "DebuggerRequestError": self.__handleDbgRequestError,
            "DebugClientResponse": self.__handleDbgClientResponse,
            "DebugClientDisconnected": self.__handleDbgClientDisconnected,
            "LastDebugClientExited": self.__handleLastDbgClientExited,
            "MainClientExited": self.__handleMainClientExited,
            "StartClientError": self.__handleStartClientError,
        }

        # connect some signals
        self.__serverInterface.remoteDebuggerReply.connect(self.__handleDebuggerReply)

    def sendClientCommand(self, debuggerId, jsonCommand):
        """
        Public method to rely a debug client command via the eric-ide server.

        @param debuggerId id of the debug client to send the command to
        @type str
        @param jsonCommand JSON encoded command dictionary to be relayed
        @type str
        """
        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.Debugger,
                request="DebugClientCommand",
                params={"debugger_id": debuggerId, "command": jsonCommand},
            )

    @pyqtSlot(str, dict)
    def __handleDebuggerReply(self, reply, params):
        """
        Private slot to handle a debugger reply from the eric-ide server.

        @param reply name of the server reply
        @type str
        @param params dictionary containing the reply data
        @type dict
        """
        if self.__serverInterface.isServerConnected():
            try:
                self.__replyMethodMapping[reply](params)
            except KeyError:
                EricMessageBox.critical(
                    None,
                    self.tr("Unknown Server Reply"),
                    self.tr(
                        "<p>The eric-ide server debugger interface sent the unknown"
                        " reply <b>{0}</b>.</p>"
                    ).format(reply),
                )

    #######################################################################
    ## Methods for handling of debug client replies.
    #######################################################################

    def __handleDbgRequestError(self, params):
        """
        Private method to handle an error reported by the debugger interface of
        the eric-ide server.

        @param params dictionary containing the reply data
        @type dict
        """
        EricMessageBox.warning(
            None,
            self.tr("Debug Client Command"),
            self.tr(
                "<p>The IDE received an error message.</p><p>Error: {0}</p>"
            ).format(params["Error"]),
        )

    def __handleDbgClientResponse(self, params):
        """
        Private method to handle a response from a debug client connected to the
        eric-ide server.

        @param params dictionary containing the reply data
        @type dict
        """
        self.debugClientResponse.emit(params["response"])

    def __handleDbgClientDisconnected(self, params):
        """
        Private method to handle a debug client disconnect report of the
        eric-ide server.

        @param params dictionary containing the reply data
        @type dict
        """
        self.debugClientDisconnected.emit(params["debugger_id"])

    def __handleLastDbgClientExited(self, params):  # noqa: U100
        """
        Private method to handle a report of the eric-ide server, that the last
        debug client has disconnected.

        @param params dictionary containing the reply data
        @type dict
        """
        self.__clientStarted = False
        self.lastClientExited.emit()

    def __handleMainClientExited(self, params):  # noqa: U100
        """
        Private method to handle the main client exiting.

        @param params dictionary containing the reply data
        @type dict
        """
        self.__clientStarted = False
        ericApp().getObject("DebugServer").signalMainClientExit()

    def __handleStartClientError(self, params):
        """
        Private method to handle an error starting the remote debug client.

        @param params dictionary containing the reply data
        @type dict
        """
        EricMessageBox.warning(
            None,
            self.tr("Start Debug Client"),
            self.tr(
                "<p>The debug client of the 'eric-ide' server could not be started.</p>"
                "<p>Error: {0}</p>"
            ).format(params["Error"]),
        )

    #######################################################################
    ## Methods for sending debug server commands to the eric-ide server.
    #######################################################################

    def startClient(self, interpreter, originalPathString, args, workingDir=""):
        """
        Public method to send a command to start a debug client.

        @param interpreter path of the remote interpreter to be used
        @type str
        @param originalPathString original PATH environment variable
        @type str
        @param args list of command line parameters for the debug client
        @type list of str
        @param workingDir directory to start the debugger client in (defaults to "")
        @type str (optional)
        """
        self.__serverInterface.sendJson(
            category=EricRequestCategory.Debugger,
            request="StartClient",
            params={
                "interpreter": FileSystemUtilities.plainFileName(interpreter),
                "path": originalPathString,
                "arguments": args,
                "working_dir": FileSystemUtilities.plainFileName(workingDir),
            },
        )
        self.__clientStarted = True

    def stopClient(self):
        """
        Public method to stop the debug client synchronously.
        """
        if self.__serverInterface.isServerConnected() and self.__clientStarted:
            loop = QEventLoop()

            def callback(reply, params):  # noqa: U100
                """
                Function to handle the server reply

                @param reply name of the server reply
                @type str
                @param params dictionary containing the reply data
                @type dict
                """
                if reply == "StopClient":
                    loop.quit()

            self.__serverInterface.sendJson(
                category=EricRequestCategory.Debugger,
                request="StopClient",
                params={},
                callback=callback,
            )

            loop.exec()
            self.__clientStarted = False
