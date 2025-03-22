# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the debugger request handler of the eric-ide server.
"""

import contextlib
import json
import os
import selectors
import socket
import subprocess  # secok
import sys
import types

from .EricRequestCategory import EricRequestCategory
from .EricServerBaseRequestHandler import EricServerBaseRequestHandler


class EricServerDebuggerRequestHandler(EricServerBaseRequestHandler):
    """
    Class implementing the debugger request handler of the eric-ide server.
    """

    def __init__(self, server):
        """
        Constructor

        @param server reference to the eric-ide server object
        @type EricServer
        """
        super().__init__(server)

        self._category = EricRequestCategory.Debugger

        self._requestMethodMapping = {
            "StartClient": self.__startClient,
            "StopClient": self.__stopClient,
            "DebugClientCommand": self.__relayDebugClientCommand,
        }

        self.__mainClientId = None
        self.__client = None
        self.__inStartClient = False
        self.__pendingConnections = []
        self.__connections = {}

        address = ("127.0.0.1", 0)
        self.__socket = socket.create_server(address, family=socket.AF_INET)

        self.__originalPathString = os.getenv("PATH")

    def sendError(self, request, reqestUuid="", errorMessage=None):
        """
        Public method to send an error report to the IDE.

        @param request request name
        @type str
        @param reqestUuid UUID of the associated request as sent by the eric IDE
            (defaults to "", i.e. no UUID received)
        @type str
        @param errorMessage error message to be sent back (defaults to None)
        @type str (optional)
        """
        if errorMessage:
            self._server.sendJson(
                category=self._category,
                reply=request,
                params={
                    "Error": f"Error during request type '{request}': {errorMessage}"
                },
                reqestUuid=reqestUuid,
            )
        else:
            super().sendError(request=request, reqestUuid=reqestUuid)

    def initServerSocket(self):
        """
        Public method to initialize the server socket listening for debug client
        connections.
        """
        # listen on the debug server socket
        self.__socket.listen()
        self.__socket.setblocking(False)
        address = self.__socket.getsockname()
        print(  # noqa: M801
            f"Listening for 'Debug Client' connections on"
            f" {address[0]}, port {address[1]}"
        )
        data = types.SimpleNamespace(
            name="server", acceptHandler=self.__acceptDbgClientConnection
        )
        self._server.getSelector().register(
            self.__socket, selectors.EVENT_READ, data=data
        )

    #######################################################################
    ## DebugServer like methods.
    #######################################################################

    def __acceptDbgClientConnection(self, sock):
        """
        Private method to accept the connection on the listening debug server socket.

        @param sock reference to the listening socket
        @type socket.socket
        """
        connection, address = sock.accept()  # Should be ready to read
        print(f"'Debug Client' connection from {address[0]}, port {address[1]}")
        # noqa: M801
        connection.setblocking(False)
        self.__pendingConnections.append(connection)

        data = types.SimpleNamespace(
            name="debug_client",
            address=address,
            handler=self.__serviceDbgClientConnection,
        )
        self._server.getSelector().register(connection, selectors.EVENT_READ, data=data)

    def __serviceDbgClientConnection(self, key):
        """
        Private method to service the debug client connection.

        @param key reference to the SelectorKey object associated with the connection
            to be serviced
        @type selectors.SelectorKey
        """
        sock = key.fileobj
        data = self._server.receiveJsonCommand(sock)

        if data is None:
            # socket was closed by debug client
            self.__clientSocketDisconnected(sock)
        elif data:
            method = data["method"]

            # 1. process debug client messages before relaying
            if method == "DebuggerId" and sock in self.__pendingConnections:
                debuggerId = data["params"]["debuggerId"]
                self.__connections[debuggerId] = sock
                self.__pendingConnections.remove(sock)
                if self.__mainClientId is None:
                    self.__mainClientId = debuggerId

            elif method == "ResponseBanner":
                # add an indicator for the eric-ide server
                data["params"]["platform"] += " (eric-ide Server)"

            # 2. pass on the data to the eric-ide
            jsonStr = json.dumps(data)
            # - print("Client Response:", jsonStr)
            self._server.sendJson(
                category=EricRequestCategory.Debugger,
                reply="DebugClientResponse",
                params={"response": jsonStr},
            )

            # 3. process debug client messages after relaying
            if method == "ResponseExit":
                for sock in list(self.__connections.values()):
                    if not self._server.isSocketClosed(sock):
                        self.__clientSocketDisconnected(sock)

                if data["params"]["debuggerId"] == self.__mainClientId:
                    self.__mainClientExited()

    def __clientSocketDisconnected(self, sock):
        """
        Private method handling a socket disconnecting.

        @param sock reference to the disconnected socket
        @type socket.socket
        """
        with contextlib.suppress(KeyError):
            self._server.getSelector().unregister(sock)

        with contextlib.suppress(OSError):
            address = sock.getpeername()
            print(  # noqa: M801
                f"'Debug Client' connection from {address[0]}, port {address[1]}"
                f" closed."
            )

        for debuggerId in list(self.__connections):
            if self.__connections[debuggerId] is sock:
                del self.__connections[debuggerId]
                self._server.sendJson(
                    category=EricRequestCategory.Debugger,
                    reply="DebugClientDisconnected",
                    params={"debugger_id": debuggerId},
                )

                if debuggerId == self.__mainClientId:
                    self.__mainClientId = None

                break
        else:
            if sock in self.__pendingConnections:
                self.__pendingConnections.remove(sock)

        with contextlib.suppress(OSError):
            sock.close()

        if not self.__connections:
            # no active connections anymore
            self.__lastClientExited()

    def __mainClientExited(self):
        """
        Private method to handle exiting of the main debug client.
        """
        self._server.sendJson(
            category=EricRequestCategory.Debugger,
            reply="MainClientExited",
            params={"debugger_id": self.__mainClientId if self.__mainClientId else ""},
        )

    def __lastClientExited(self):
        """
        Private method to handle exiting of the last debug client.
        """
        self._server.sendJson(
            category=EricRequestCategory.Debugger,
            reply="LastDebugClientExited",
            params={},
        )

    def shutdownClients(self):
        """
        Public method to shut down all connected clients.
        """
        if not self.__client:
            # no client started yet
            return

        while self.__pendingConnections:
            sock = self.__pendingConnections.pop()
            commandDict = self.__prepareClientCommand("RequestShutdown", {})
            self._server.sendJsonCommand(commandDict, sock)
            self.__shutdownSocket("", sock)

        while self.__connections:
            debuggerId, sock = self.__connections.popitem()
            commandDict = self.__prepareClientCommand("RequestShutdown", {})
            self._server.sendJsonCommand(commandDict, sock)
            self.__shutdownSocket(debuggerId, sock)

        # reinitialize
        self.__mainClientId = None
        if self.__client:
            self.__client.kill()
        self.__client = None

    def __shutdownSocket(self, debuggerId, sock):
        """
        Private method to shut down a socket.

        @param debuggerId ID of the debugger the socket belongs to
        @type str
        @param sock reference to the socket
        @type socket.socket
        """
        with contextlib.suppress(KeyError, OSError):
            # Socket might have been unregister automatically (e.g. due to a crash of
            # the script being debugged).
            self._server.getSelector().unregister(sock)
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()

        if debuggerId:
            self._server.sendJson(
                category=EricRequestCategory.Debugger,
                reply="DebugClientDisconnected",
                params={"debugger_id": debuggerId},
            )

    def __prepareClientCommand(self, command, params):
        """
        Private method to prepare a command dictionary for the debug client.

        @param command command to be sent
        @type str
        @param params dictionary containing the command parameters
        @type dict
        @return completed command dictionary to be sent to the debug client
        @rtype dict
        """
        return {
            "jsonrpc": "2.0",
            "method": command,
            "params": params,
        }

    #######################################################################
    ## Individual request handler methods.
    #######################################################################

    def __startClient(self, params):
        """
        Private method to start a debug client process.

        @param params dictionary containing the request data
        @type dict
        """
        self.shutdownClients()  # stop all running clients first (just in case)

        self.__inStartClient = True

        # start a debug client
        debugClient = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "DebugClients",
                "Python",
                "DebugClient.py",
            )
        )
        ipaddr, port = self.__socket.getsockname()
        args = [
            params["interpreter"] if params["interpreter"] else sys.executable,
            debugClient,
        ]
        args.extend(params["arguments"])
        args.extend([str(port), "True", ipaddr])

        workingDir = params["working_dir"] if params["working_dir"] else None

        clientEnv = os.environ.copy()
        if self.__originalPathString:
            clientEnv["PATH"] = self.__originalPathString

        try:
            self.__client = subprocess.Popen(  # secok
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workingDir,
                env=clientEnv,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as err:
            self.sendError(request="StartClientError", errorMessage=str(err))

    def __stopClient(self, params):  # noqa: U100
        """
        Private method to stop the current debug client process.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        self.shutdownClients()

        return {"ok": True}

    def __relayDebugClientCommand(self, params):
        """
        Private method to relay a debug client command to the client.

        @param params dictionary containing the request data
        @type dict
        """
        debuggerId = params["debugger_id"]
        jsonStr = params["command"]

        if not debuggerId and self.__mainClientId and "RequestBanner" in jsonStr:
            # modify the target for the 'RequestBanner' request
            debuggerId = self.__mainClientId

        if debuggerId == "<<all>>":
            # broadcast to all connected debug clients
            for sock in self.__connections.values():
                self._server.sendJsonCommand(jsonStr, sock)
        else:
            try:  # noqa: Y105
                sock = self.__connections[debuggerId]
                self._server.sendJsonCommand(jsonStr, sock)
            except KeyError:
                # - print(f"Command for unknown debugger ID '{debuggerId}' received.")
                pass
