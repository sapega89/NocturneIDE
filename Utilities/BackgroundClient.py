# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#
# pylint: disable=C0103

"""
Module implementing a Qt free version of a background client for the various
checkers and other python interpreter dependent functions.
"""

import contextlib
import importlib
import io
import json
import multiprocessing
import socket
import struct
import sys
import time
import traceback

from zlib import adler32


class BackgroundClient:
    """
    Class implementing the main part of the background client.
    """

    def __init__(self, host, port, maxProcs):
        """
        Constructor

        @param host ip address the background service is listening
        @type str
        @param port port of the background service
        @type int
        @param maxProcs maximum number of CPUs (processes) to use
            (0 = determined automatically)
        @type int
        """
        self.services = {}
        self.batchServices = {}

        self.connection = socket.create_connection((host, port))
        ver = b"Python3"
        self.connection.sendall(ver)
        self.__maxProcs = maxProcs

    def __initClientService(self, fn, path, module):
        """
        Private method to import the given module and register it as service.

        @param fn service name to register
        @type str
        @param path contains the path to the module
        @type str
        @param module name to import
        @type str
        @return text result of the import action
        @rtype str
        """
        sys.path.insert(1, path)
        try:
            importedModule = importlib.import_module(module)
            self.services[fn] = importedModule.initService()
            with contextlib.suppress(AttributeError):
                self.batchServices["batch_" + fn] = importedModule.initBatchService()
            return "ok"
        except ImportError as err:
            return "Import Error: " + str(err)
        except Exception as err:
            return str(err)

    def __send(self, fx, fn, data):
        """
        Private method to send a job response back to the BackgroundService
        server.

        @param fx remote function name to execute
        @type str
        @param fn filename for identification
        @type str
        @param data return value(s)
        @type any basic datatype
        """
        if not isinstance(
            data,
            (
                dict,
                list,
                tuple,
                str,
                int,
                float,
                bool,
                type(None),
            ),
        ):
            # handle sending of objects of unsupported types
            data = str(data)

        packedData = json.dumps([fx, fn, data])
        packedData = bytes(packedData, "utf-8")
        header = struct.pack(b"!II", len(packedData), adler32(packedData) & 0xFFFFFFFF)
        self.connection.sendall(header)
        self.connection.sendall(packedData)

    def __receive(self, length):
        """
        Private method to receive the given length of bytes.

        @param length bytes to receive
        @type int
        @return received bytes or None if connection closed
        @rtype bytes
        """
        data = bytearray()
        while len(data) < length:
            newData = self.connection.recv(length - len(data))
            if not newData:
                return None
            data += newData
        return data

    def __peek(self, length):
        """
        Private method to peek the given length of bytes.

        @param length bytes to receive
        @type int
        @return received bytes
        @rtype bytes
        """
        data = b""
        self.connection.setblocking(False)
        try:
            with contextlib.suppress(OSError):
                data = self.connection.recv(length, socket.MSG_PEEK)
        finally:
            self.connection.setblocking(True)

        return data

    def __cancelled(self):
        """
        Private method to check for a job cancellation.

        @return flag indicating a cancellation
        @rtype bool
        """
        msg = self.__peek(struct.calcsize(b"!II") + 6)
        if msg[-6:] == b"CANCEL":
            # get rid of the message data
            self.__receive(struct.calcsize(b"!II") + 6)
            return True
        else:
            return False

    def run(self):
        """
        Public method implementing the main loop of the client.

        @exception RuntimeError raised if hashes don't match
        """
        try:
            while True:
                header = self.__receive(struct.calcsize(b"!II"))
                # Leave main loop if connection was closed.
                if not header:
                    break

                length, datahash = struct.unpack(b"!II", header)
                messageType = self.__receive(6)
                packedData = self.__receive(length)

                if messageType != b"JOB   ":
                    continue

                if adler32(packedData) & 0xFFFFFFFF != datahash:
                    raise RuntimeError("Hashes not equal")

                packedData = packedData.decode("utf-8")

                fx, fn, data = json.loads(packedData)
                if fx == "INIT":
                    ret = self.__initClientService(fn, *data)
                elif fx.startswith("batch_"):
                    callback = self.batchServices.get(fx)
                    if callback:
                        callback(
                            data,
                            self.__send,
                            fx,
                            self.__cancelled,
                            maxProcesses=self.__maxProcs,
                        )
                        ret = "__DONE__"
                    else:
                        ret = "Unknown batch service."
                else:
                    callback = self.services.get(fx)
                    if callback:
                        ret = callback(fn, *data)
                    else:
                        ret = "Unknown service."

                if isinstance(ret, Exception):
                    ret = str(ret)

                self.__send(fx, fn, ret)
        except OSError:
            pass
        except Exception:
            exctype, excval, exctb = sys.exc_info()
            tbinfofile = io.StringIO()
            traceback.print_tb(exctb, None, tbinfofile)
            tbinfofile.seek(0)
            tbinfo = tbinfofile.read()
            del exctb
            self.__send("EXCEPTION", "?", [str(exctype), str(excval), tbinfo])

        finally:
            # Give time to process latest response on server side
            time.sleep(0.5)
            with contextlib.suppress(OSError):
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Host, port, max. processes and Python library path parameters"
            " are missing. Aborting..."
        )
        sys.exit(1)

    multiprocessing.set_start_method("spawn")

    host, port, maxProcs, pyLibraryPath = sys.argv[1:]

    # insert pyLibraryPath into the search path because external stuff might
    # be installed in the eric (virtual) environment
    sys.path.insert(1, pyLibraryPath)

    backgroundClient = BackgroundClient(host, int(port), int(maxProcs))
    # Start the main loop
    backgroundClient.run()

#
# eflag: noqa = M801
