# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a JSON based writer class.
"""

import json
import socket


class EricJsonWriter:
    """
    Class implementing a JSON based writer class.
    """

    def __init__(self, host, port):
        """
        Constructor

        @param host IP address the reader is listening on
        @type str
        @param port port the reader is listening on
        @type int
        """
        self.__connection = socket.create_connection((host, port))

    def write(self, data):
        """
        Public method to send JSON serializable data.

        @param data JSON serializable object to be sent
        @type object
        """
        dataStr = json.dumps(data) + "\n"
        self.__connection.sendall(dataStr.encode("utf8", "backslashreplace"))

    def close(self):
        """
        Public method to close the stream.
        """
        self.__connection.close()
