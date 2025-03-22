# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the eric remote server.
"""

import io
import json
import selectors
import socket
import struct
import sys
import traceback
import types
import zlib

from eric7.__version__ import Version

from .EricRequestCategory import EricRequestCategory
from .EricServerCoverageRequestHandler import EricServerCoverageRequestHandler
from .EricServerDebuggerRequestHandler import EricServerDebuggerRequestHandler
from .EricServerEditorConfigRequestHandler import EricServerEditorConfigRequestHandler
from .EricServerFileSystemRequestHandler import EricServerFileSystemRequestHandler


class EricServer:
    """
    Class implementing the eric remote server.
    """

    def __init__(self, port=42024, useIPv6=False, clientId=""):
        """
        Constructor

        @param port port to listen on (defaults to 42024)
        @type int (optional)
        @param useIPv6 flag indicating to use IPv6 protocol (defaults to False)
        @type bool (optional)
        @param clientId ID string used to check each received message for being
            sent by a valid eric IDE (defaults to "")
        @type str (optional)
        """
        self.__clientId = clientId
        self.__address = ("", port)
        self.__useIPv6 = useIPv6

        self.__requestCategoryHandlerRegistry = {}
        # Dictionary containing the defined and registered request category
        # handlers. The key is the request category and the value is the respective
        # handler method. This method must have the signature:
        #     handler(request:str, params:dict, reqestUuid:str) -> None
        self.__registerInternalHandlers()

        self.__connection = None

        self.__selector = selectors.DefaultSelector()

        # create and register the 'Debugger' request handler
        self.__debuggerRequestHandler = EricServerDebuggerRequestHandler(self)
        self.registerRequestHandler(
            EricRequestCategory.Debugger,
            self.__debuggerRequestHandler.handleRequest,
        )

        # create and register the 'File System' request handler
        self.__fileSystemRequestHandler = EricServerFileSystemRequestHandler(self)
        self.registerRequestHandler(
            EricRequestCategory.FileSystem,
            self.__fileSystemRequestHandler.handleRequest,
        )

        # create and register the 'Coverage' request handler
        self.__coverageRequestHandler = EricServerCoverageRequestHandler(self)
        self.registerRequestHandler(
            EricRequestCategory.Coverage,
            self.__coverageRequestHandler.handleRequest,
        )

        # create and register the 'Editor Config' request handler
        self.__editorConfigRequestHandler = EricServerEditorConfigRequestHandler(self)
        self.registerRequestHandler(
            EricRequestCategory.EditorConfig,
            self.__editorConfigRequestHandler.handleRequest,
        )

    def getSelector(self):
        """
        Public method to get a reference to the selector object.

        @return reference to the selector object
        @rtype selectors.BaseSelector
        """
        return self.__selector

    #######################################################################
    ## Methods for receiving requests and sending the results.
    #######################################################################

    def sendJson(self, category, reply, params, reqestUuid=""):
        """
        Public method to send a single refactoring command to the server.

        @param category service category
        @type EricRequestCategory
        @param reply reply name to be sent
        @type str
        @param params dictionary of named parameters for the request
        @type dict
        @param reqestUuid UUID of the associated request as sent by the eric IDE
            (defaults to "", i.e. no UUID received)
        @type str
        """
        if self.__connection is not None:
            commandDict = {
                "jsonrpc": "2.0",
                "category": category,
                "reply": reply,
                "params": params,
                "uuid": reqestUuid,
            }
            self.sendJsonCommand(commandDict, self.__connection)

    def sendJsonCommand(self, jsonCommand, sock):
        """
        Public method to send a JSON encoded command/response via a given socket.

        @param jsonCommand dictionary containing the command data or a JSON encoded
            command string
        @type dict or str
        @param sock reference to the socket to send the data to
        @type socket.socket
        @return flag indicating a successful transmission
        @rtype bool
        """
        if isinstance(jsonCommand, dict):
            jsonCommand = json.dumps(jsonCommand)
        # - print("Eric Server Send:", jsonCommand)  # for debugging

        data = jsonCommand.encode("utf8", "backslashreplace")
        header = struct.pack(b"!II", len(data), zlib.adler32(data) & 0xFFFFFFFF)
        try:
            sock.sendall(header)
            sock.sendall(data)
            return True
        except BrokenPipeError:
            return False

    def __receiveBytes(self, length, sock):
        """
        Private method to receive the given length of bytes.

        @param length bytes to receive
        @type int
        @param sock reference to the socket to receive the data from
        @type socket.socket
        @return received bytes or None if connection closed
        @rtype bytes
        """
        data = bytearray()
        while sock is not None and len(data) < length:
            try:
                newData = sock.recv(length - len(data))
                if not newData:
                    return None

                data += newData
            except OSError as err:
                if err.errno != 11:
                    data = None  # in case some data was received already
                    break
            except MemoryError:
                data = None  # in case some data was received already
                break
        return data

    def receiveJsonCommand(self, sock):
        """
        Public method to receive a JSON encoded command and data.

        @param sock reference to the socket to receive the data from
        @type socket.socket
        @return dictionary containing the JSON command data or None to signal
            an issue while receiving data
        @rtype dict
        """
        if self.isSocketClosed(sock):
            return None

        if self.__clientId and sock == self.__connection:
            msgClientIdBytes = self.__receiveBytes(len(self.__clientId), sock)
            try:
                msgClientId = str(msgClientIdBytes, encoding="utf-8")
            except UnicodeDecodeError:
                msgClientId = str(bytes(msgClientIdBytes))
            if msgClientId != self.__clientId:
                print(f"Received illegal client ID '{msgClientId}'.")  # noqa: M801
                return {}

        header = self.__receiveBytes(struct.calcsize(b"!II"), sock)
        if not header:
            return {}

        length, datahash = struct.unpack(b"!II", header)

        length = int(length)
        data = self.__receiveBytes(length, sock)
        if data is None:
            return None

        if not data or zlib.adler32(data) & 0xFFFFFFFF != datahash:
            self.sendJson(
                category=EricRequestCategory.Error,
                reply="EricServerChecksumException",
                params={
                    "ExceptionType": "ProtocolChecksumError",
                    "ExceptionValue": "The checksum of the data does not match.",
                    "ProtocolData": data.decode("utf8", "backslashreplace"),
                },
            )
            return {}

        jsonStr = data.decode("utf8", "backslashreplace")
        # - print("Eric Server Receive:", jsonStr)  # for debugging  # noqa: M801
        try:
            return json.loads(jsonStr.strip())
        except (TypeError, ValueError) as err:
            self.sendJson(
                category=EricRequestCategory.Error,
                reply="EricServerException",
                params={
                    "ExceptionType": "ProtocolError",
                    "ExceptionValue": str(err),
                    "ProtocolData": jsonStr.strip(),
                },
            )
            return {}

    def __receiveJson(self):
        """
        Private method to receive a JSON encoded command and data from the
        server.

        @return tuple containing the received service category, the command,
            a dictionary containing the associated data and the UUID of the
            request
        @rtype tuple of (int, str, dict, str)
        """
        requestDict = self.receiveJsonCommand(self.__connection)

        if not requestDict:
            return EricRequestCategory.Error, None, None, None

        category = requestDict["category"]
        request = requestDict["request"]
        params = requestDict["params"]
        reqestUuid = requestDict["uuid"]

        return category, request, params, reqestUuid

    def isSocketClosed(self, sock):
        """
        Public method to check, if a given socket is closed.

        @param sock reference to the socket to be checked
        @type socket.socket
        @return flag indicating a closed state
        @rtype bool
        """
        try:
            # this will try to read bytes without removing them from buffer (peek only)
            data = sock.recv(16, socket.MSG_PEEK)
            if len(data) == 0:
                return True
        except BlockingIOError:
            return False  # socket is open and reading from it would block
        except ConnectionError:
            return True  # socket was closed for some other reason
        except Exception:
            return False
        return False

    #######################################################################
    ## Methods for the server main loop.
    #######################################################################

    def __initializeIdeSocket(self):
        """
        Private method to initialize and register the eric-ide server socket.
        """
        if socket.has_dualstack_ipv6() and self.__useIPv6:
            self.__socket = socket.create_server(
                self.__address, family=socket.AF_INET6, backlog=0, dualstack_ipv6=True
            )
        else:
            self.__socket = socket.create_server(
                self.__address, family=socket.AF_INET, backlog=0
            )

        self.__socket.listen(0)
        self.__socket.setblocking(False)
        address = self.__socket.getsockname()
        print(  # noqa: M801
            f"Listening for 'eric-ide' connections on {address[0]}, port {address[1]}"
        )
        data = types.SimpleNamespace(
            name="server", acceptHandler=self.__acceptIdeConnection
        )
        self.__selector.register(self.__socket, selectors.EVENT_READ, data=data)

    def __unregisterIdeSocket(self):
        """
        Private method to unregister the eric-ide server socket because only one
        connection is allowed.
        """
        self.__selector.unregister(self.__socket)
        self.__socket.shutdown(socket.SHUT_RDWR)
        self.__socket.close()
        self.__socket = None

    def __shutdown(self):
        """
        Private method to shut down the server.
        """
        self.__closeIdeConnection(shutdown=True)

        print("Stop listening for 'eric-ide' connections.")  # noqa: M801
        if self.__socket is not None:
            self.__socket.shutdown(socket.SHUT_RDWR)
            self.__socket.close()

        self.__selector.close()

    def __acceptIdeConnection(self, sock):
        """
        Private method to accept the connection on the listening IDE server socket.

        @param sock reference to the listening socket
        @type socket.socket
        """
        connection, address = sock.accept()  # Should be ready to read.
        if self.__connection is None:
            print(f"'eric-ide' connection from {address[0]}, port {address[1]}")
            # noqa: M801
            self.__connection = connection
            self.__connection.settimeout(10)
            data = types.SimpleNamespace(
                name="eric-ide", address=address, handler=self.__serviceIdeConnection
            )
            events = selectors.EVENT_READ
            self.__selector.register(self.__connection, events, data=data)

            self.__unregisterIdeSocket()
        else:
            print(  # noqa: M801
                f"'eric-ide' connection from {address[0]}, port {address[1]} rejected"
            )
            connection.close()

    def __closeIdeConnection(self, shutdown=False):
        """
        Private method to close the connection to an eric-ide.

        @param shutdown flag indicating a shutdown process
        @type bool
        """
        if self.__connection is not None:
            self.__selector.unregister(self.__connection)
            try:
                address = self.__connection.getpeername()
                print(  # noqa: M801
                    f"Closing 'eric-ide' connection to {address[0]}, port {address[1]}."
                )
                self.__connection.shutdown(socket.SHUT_RDWR)
                self.__connection.close()
            except OSError:
                print("'eric-ide' connection gone.")  # noqa: M801
            self.__connection = None

            self.__debuggerRequestHandler.shutdownClients()

        if not shutdown:
            self.__initializeIdeSocket()

    def __serviceIdeConnection(self, key):
        """
        Private method to service the eric-ide connection.

        @param key reference to the SelectorKey object associated with the connection
            to be serviced
        @type selectors.SelectorKey
        """
        if key.data.name == "eric-ide":
            category, request, params, reqestUuid = self.__receiveJson()
            if category == EricRequestCategory.Error or request is None:
                self.__closeIdeConnection()
                return

            if category == EricRequestCategory.Server and request.lower() == "shutdown":
                self.__shouldStop = True
                return

            self.__handleRequest(category, request, params, reqestUuid)

    def run(self):
        """
        Public method implementing the remote server main loop.

        Exiting the inner loop, that receives and dispatches the requests, will
        cause the server to stop and exit. The main loop handles these requests.
        <ul>
        <li>exit - exit the handler loop and wait for the next connection</li>
        <li>shutdown - exit the handler loop and perform a clean shutdown</li>
        </ul>

        @return flag indicating a clean shutdown
        @rtype bool
        """
        cleanExit = True
        self.__shouldStop = False

        # initialize the eric-ide server socket and listen for new connections
        self.__initializeIdeSocket()

        # initialize the debug client server socket
        self.__debuggerRequestHandler.initServerSocket()

        while True:
            try:
                events = self.__selector.select(timeout=None)
                for key, _mask in events:
                    if key.data.name == "server":
                        # it is an event for a server socket
                        key.data.acceptHandler(key.fileobj)
                    else:
                        key.data.handler(key)

            except KeyboardInterrupt:
                # intercept user pressing Ctrl+C
                self.__shouldStop = True

            except Exception:
                exctype, excval, exctb = sys.exc_info()
                tbinfofile = io.StringIO()
                traceback.print_tb(exctb, None, tbinfofile)
                tbinfofile.seek(0)
                tbinfo = tbinfofile.read()

                print("Stopping due to an exception.\nDetails:")  # noqa: M801
                print(f"{str(exctype)} / {str(excval)} / {tbinfo}")  # noqa: M801

                self.__shouldStop = True
                cleanExit = False

            if self.__shouldStop:
                # exit the outer loop and shut down the server
                self.__shutdown()
                break

        return cleanExit

    #######################################################################
    ## Methods for registering and unregistering handlers.
    #######################################################################

    def registerRequestHandler(self, requestCategory, handler):
        """
        Public method to register a request handler method for the given request
        category.

        @param requestCategory request category to be registered
        @type EricRequestCategory or int (>= EricRequestCategory.UserCategory)
        @param handler reference to the handler method. This handler must accept
            the parameters 'request', 'params', and 'requestUuid'
        @type function(request:str, params:dict, requestUuid:str)
        @exception ValueError raised to signal a request category collision
        """
        if requestCategory in self.__requestCategoryHandlerRegistry:
            raise ValueError(f"Request category '{requestCategory} already registered.")

        self.__requestCategoryHandlerRegistry[requestCategory] = handler

    def unregisterRequestHandler(self, requestCategory, ignoreError=False):
        """
        Public method to unregister a handler for the given request category.

        Note: This method will raise a KeyError exception in case the request
        category has not been registered and ignoreError is False (the default).

        @param requestCategory request category to be unregistered
        @type EricRequestCategory or int (>= EricRequestCategory.UserCategory)
        @param ignoreError flag indicating to ignore errors (defaults to False)
        @type bool (optional)
        """
        try:
            del self.__requestCategoryHandlerRegistry[requestCategory]
        except KeyError:
            if not ignoreError:
                raise

    def __registerInternalHandlers(self):
        """
        Private method to register request handler categories of this class.
        """
        self.registerRequestHandler(EricRequestCategory.Echo, self.__handleEchoRequest)
        self.registerRequestHandler(
            EricRequestCategory.Server, self.__handleServerRequest
        )
        self.registerRequestHandler(EricRequestCategory.Error, None)
        # Register a None handler to indicate we are not expecting a request of the
        # 'Error' category.

    #######################################################################
    ## Request handler methods.
    #######################################################################

    def __handleRequest(self, category, request, params, reqestUuid):
        """
        Private method handling or dispatching the received requests.

        @param category category of the request
        @type EricRequestCategory
        @param request request name
        @type str
        @param params request parameters
        @type dict
        @param reqestUuid UUID of the associated request as sent by the eric IDE
        @type str
        """
        try:
            handler = self.__requestCategoryHandlerRegistry[category]
            handler(request=request, params=params, reqestUuid=reqestUuid)
        except KeyError:
            self.sendJson(
                category=EricRequestCategory.Error,
                reply="UnsupportedServiceCategory",
                params={"Category": category},
            )

    def __handleEchoRequest(self, request, params, reqestUuid):  # noqa: U100
        """
        Private method to handle an 'Echo' request.

        @param request request name
        @type str
        @param params request parameters
        @type dict
        @param reqestUuid UUID of the associated request as sent by the eric IDE
            (defaults to "", i.e. no UUID received)
        @type str
        """
        self.sendJson(
            category=EricRequestCategory.Echo,
            reply="Echo",
            params=params,
            reqestUuid=reqestUuid,
        )

    def __handleServerRequest(self, request, params, reqestUuid):  # noqa: U100
        """
        Private method to handle a 'Server' request.

        @param request request name
        @type str
        @param params request parameters
        @type dict
        @param reqestUuid UUID of the associated request as sent by the eric IDE
            (defaults to "", i.e. no UUID received)
        @type str
        """
        # 'Exit' and 'Shutdown' are handled in the 'run()' method.

        if request.lower() == "versions":
            self.sendJson(
                category=EricRequestCategory.Server,
                reply="Versions",
                params={
                    "python": sys.version.split()[0],
                    "py_bitsize": "64-Bit" if sys.maxsize > 2**32 else "32-Bit",
                    "version": Version,
                    "hostname": socket.gethostname(),
                },
                reqestUuid=reqestUuid,
            )
