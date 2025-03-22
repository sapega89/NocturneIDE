# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the JSON based client base class.
"""

import contextlib
import io
import json
import select
import socket
import struct
import sys
import traceback
import zlib


class EricJsonClient:
    """
    Class implementing a JSON based client base class.
    """

    def __init__(self, host, port, idString=""):
        """
        Constructor

        @param host IP address the background service is listening
        @type str
        @param port port of the background service
        @type int
        @param idString assigned client id to be sent back to the server in
            order to identify the connection
        @type str
        """
        self.__connection = socket.create_connection((host, port))
        if idString:
            reply = idString + "\n"
            self.__connection.sendall(reply.encode("utf8", "backslashreplace"))

    def sendJson(self, command, params):
        """
        Public method to send a single refactoring command to the server.

        @param command command name to be sent
        @type str
        @param params dictionary of named parameters for the command
        @type dict
        """
        commandDict = {
            "jsonrpc": "2.0",
            "method": command,
            "params": params,
        }
        data = json.dumps(commandDict).encode("utf8", "backslashreplace")
        header = struct.pack(b"!II", len(data), zlib.adler32(data) & 0xFFFFFFFF)
        self.__connection.sendall(header)
        self.__connection.sendall(data)

    def __receiveBytes(self, length):
        """
        Private method to receive the given length of bytes.

        @param length bytes to receive
        @type int
        @return received bytes or None if connection closed
        @rtype bytes
        """
        data = bytearray()
        while len(data) < length:
            newData = self.__connection.recv(length - len(data))
            if not newData:
                return None

            data += newData
        return data

    def __receiveJson(self):
        """
        Private method to receive a JSON encoded command and data from the
        server.

        @return tuple containing the received command and a dictionary
            containing the associated data
        @rtype tuple of (str, dict)
        """
        # step 1: receive the data
        header = self.__receiveBytes(struct.calcsize(b"!II"))
        if not header:
            return None, None

        length, datahash = struct.unpack(b"!II", header)

        length = int(length)
        data = self.__receiveBytes(length)
        if not data or zlib.adler32(data) & 0xFFFFFFFF != datahash:
            self.sendJson(
                "ClientException",
                {
                    "ExceptionType": "ProtocolError",
                    "ExceptionValue": "The checksum of the data does not match.",
                    "ProtocolData": data.decode("utf8", "backslashreplace"),
                },
            )
            return None, None

        # step 2: decode and convert the data
        jsonString = data.decode("utf8", "backslashreplace")
        try:
            commandDict = json.loads(jsonString.strip())
        except (TypeError, ValueError) as err:
            self.sendJson(
                "ClientException",
                {
                    "ExceptionType": "ProtocolError",
                    "ExceptionValue": str(err),
                    "ProtocolData": jsonString.strip(),
                },
            )
            return None, None

        method = commandDict["method"]
        params = commandDict["params"]

        return method, params

    def handleCall(self, method, params):
        """
        Public method to handle a method call from the server.

        Note: This is an empty implementation that must be overridden in
        derived classes.

        @param method requested method name
        @type str
        @param params dictionary with method specific parameters
        @type dict
        """
        pass

    def run(self):
        """
        Public method implementing the main loop of the client.
        """
        try:
            selectErrors = 0
            while selectErrors <= 10:  # selected arbitrarily
                try:
                    rrdy, _wrdy, _xrdy = select.select([self.__connection], [], [])

                    # Just waiting for self.__connection. Therefore no check
                    # needed.
                    method, params = self.__receiveJson()
                    if method is None:
                        selectErrors += 1
                    elif method == "Exit":
                        break
                    else:
                        self.handleCall(method, params)

                        # reset select errors
                        selectErrors = 0

                except (KeyboardInterrupt, select.error, socket.error):
                    selectErrors += 1

        except Exception:
            exctype, excval, exctb = sys.exc_info()
            tbinfofile = io.StringIO()
            traceback.print_tb(exctb, None, tbinfofile)
            tbinfofile.seek(0)
            tbinfo = tbinfofile.read()
            del exctb
            self.sendJson(
                "ClientException",
                {
                    "ExceptionType": str(exctype),
                    "ExceptionValue": str(excval),
                    "Traceback": tbinfo,
                },
            )

        # Give time to process latest response on server side
        with contextlib.suppress(socket.error, OSError):
            self.__connection.shutdown(socket.SHUT_RDWR)
            self.__connection.close()

    def poll(self, waitMethod=""):
        """
        Public method to check and receive one message (if available).

        @param waitMethod name of a method to wait for
        @type str
        @return dictionary containing the data of the waited for method
        @rtype dict
        """
        try:
            if waitMethod:
                rrdy, _wrdy, _xrdy = select.select([self.__connection], [], [])
            else:
                rrdy, _wrdy, _xrdy = select.select([self.__connection], [], [], 0)

            if self.__connection in rrdy:
                method, params = self.__receiveJson()
                if method is not None:
                    if method == "Exit":
                        self.__exitClient = True
                    elif method == waitMethod:
                        return params
                    else:
                        self.handleCall(method, params)

        except (KeyboardInterrupt, select.error, socket.error):
            # just ignore these
            pass

        except Exception:
            exctype, excval, exctb = sys.exc_info()
            tbinfofile = io.StringIO()
            traceback.print_tb(exctb, None, tbinfofile)
            tbinfofile.seek(0)
            tbinfo = tbinfofile.read()
            del exctb
            self.sendJson(
                "ClientException",
                {
                    "ExceptionType": str(exctype),
                    "ExceptionValue": str(excval),
                    "Traceback": tbinfo,
                },
            )

        return None
