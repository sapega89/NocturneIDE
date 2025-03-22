# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the interface to the eric remote server.
"""

import collections
import json
import logging
import struct
import time
import uuid
import zlib

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtNetwork import QAbstractSocket, QTcpSocket
from PyQt6.QtWidgets import QDialog, QMenu, QToolBar, QToolButton

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.RemoteServer.EricRequestCategory import EricRequestCategory


class EricServerInterface(QObject):
    """
    Class implementing the interface to the eric remote server.

    @signal showMenu(name:str, menu:QMenu) emitted when a menu is about to be shown.
        The name of the menu and a reference to the menu are given.

    @signal connectionStateChanged(state:bool) emitted to indicate a change of the
        connection state
    @signal aboutToDisconnect() emitted just befor the remote server is disconnected

    @signal remoteReply(category:int, request:str, params:dict) emitted to deliver the
        reply of an unknown category
    @signal remoteCoverageReply(request:str, params:dict) emitted to deliver the reply
        of a remote server code coverage request
    @signal remoteDebuggerReply(request:str, params:dict) emitted to deliver the reply
        of a remote server debugger request
    @signal remoteEchoReply(request:str, params:dict) emitted to deliver the reply of
        a remote server echo request
    @signal remoteEditorConfig(request:str, params:dict) emitted to deliver the reply
        of a remote server  editor config request
    @signal remoteFileSystemReply(request:str, params:dict) emitted to deliver the
        reply of a remote server file system request
    @signal remoteProjectReply(request:str, params:dict) emitted to deliver the reply
        of a remote server project related request
    @signal remoteServerReply(request:str, params:dict) emitted to deliver the reply
        of a remote server control request
    """

    showMenu = pyqtSignal(str, QMenu)

    aboutToDisconnect = pyqtSignal()
    connectionStateChanged = pyqtSignal(bool)

    remoteReply = pyqtSignal(int, str, dict)

    remoteCoverageReply = pyqtSignal(str, dict)
    remoteDebuggerReply = pyqtSignal(str, dict)
    remoteEchoReply = pyqtSignal(str, dict)
    remoteEditorConfig = pyqtSignal(str, dict)
    remoteFileSystemReply = pyqtSignal(str, dict)
    remoteProjectReply = pyqtSignal(str, dict)
    remoteServerReply = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent=parent)

        self.__ui = parent

        self.__categorySignalMapping = {
            EricRequestCategory.Coverage: self.remoteCoverageReply,
            EricRequestCategory.Debugger: self.remoteDebuggerReply,
            EricRequestCategory.Echo: self.remoteEchoReply,
            EricRequestCategory.EditorConfig: self.remoteEditorConfig,
            EricRequestCategory.FileSystem: self.remoteFileSystemReply,
            EricRequestCategory.Project: self.remoteProjectReply,
            EricRequestCategory.Server: self.remoteServerReply,
        }
        self.__serviceFactory = {
            # key: lower case service name; value method to create the service interface
            "coverage": self.__createCoverageInterface,
            "debugger": self.__createDebuggerInterface,
            "editorconfig": self.__createEditorConfigInterface,
            "filesystem": self.__createFilesystemInterface,
        }
        self.__serviceInterfaces = {}
        # no specific service interfaces have been created yet

        self.__connection = None
        self.__clientId = b""  # prepended to each messge for validity checking
        self.__callbacks = {}  # callback references indexed by UUID
        self.__messageQueue = collections.deque()
        self.__connected = False

        self.connectionStateChanged.connect(self.__connectionStateChanged)

    def getServiceInterface(self, name):
        """
        Public method to get a references to a specific service interface by
        service name.

        @param name service name
        @type str
        @return reference to the service interface
        @rtype QObject
        @exception ValueError raised to indicate an unsupported server interface
            was requested
        """
        lname = name.lower()
        try:
            return self.__serviceInterfaces[lname]
        except KeyError:
            try:
                # instantiate the service interface
                self.__serviceFactory[lname]()
            except KeyError:
                raise ValueError(f"no such service supported ({name})")

            return self.__serviceInterfaces[lname]

    def __createCoverageInterface(self):
        """
        Private method to create and register the 'Coverage' eric-ide server interface.
        """
        from .EricServerCoverageInterface import EricServerCoverageInterface

        self.__serviceInterfaces["coverage"] = EricServerCoverageInterface(self)

    def __createDebuggerInterface(self):
        """
        Private method to create and register the 'Debugger' eric-ide server interface.
        """
        from .EricServerDebuggerInterface import EricServerDebuggerInterface

        self.__serviceInterfaces["debugger"] = EricServerDebuggerInterface(self)

    def __createEditorConfigInterface(self):
        """
        Private method to create and register the 'EditorConfig' eric-ide server
        interface.
        """
        from .EricServerEditorConfigInterface import EricServerEditorConfigInterface

        self.__serviceInterfaces["editorconfig"] = EricServerEditorConfigInterface(self)

    def __createFilesystemInterface(self):
        """
        Private method to create and register the 'Filesystem' eric-ide server
        interface.
        """
        from .EricServerFileSystemInterface import EricServerFileSystemInterface

        self.__serviceInterfaces["filesystem"] = EricServerFileSystemInterface(self)

    #######################################################################
    ## Methods for handling the server connection.
    #######################################################################

    def connectToServer(self, host, port=None, timeout=None, clientId=""):
        """
        Public method to connect to the given host and port.

        @param host host name or IP address of the eric remote server
        @type str
        @param port port number to connect to (defaults to None)
        @type int (optional)
        @param timeout timeout im seconds for the connection attempt
            (defaults to None)
        @type int (optional)
        @param clientId string prepended to each message for validity checking
            (defaults to "")
        @type str (optional)
        @return flag indicating success
        @rtype bool
        """
        if not bool(port):  # None or 0
            # use default port
            port = 42024

        if not bool(timeout):  # None or 0
            # use configured default timeout
            timeout = Preferences.getEricServer("ConnectionTimeout")
        timeout *= 1000  # convert to milliseconds

        if self.__connection is not None:
            self.disconnectFromServer()

        self.__connection = QTcpSocket(self)
        self.__connection.connectToHost(host, port)
        if not self.__connection.waitForConnected(timeout):
            EricMessageBox.critical(
                None,
                self.tr("Connect to eric-ide Server"),
                self.tr(
                    "<p>The connection to the eric-ide server {0}:{1} could not be"
                    " established.</p><p>Reason: {2}</p>"
                ).format(
                    host if ":" not in host else f"[{host}]",
                    port,
                    self.__connection.errorString(),
                ),
            )

            self.__connection = None
            return False

        self.__clientId = clientId.encode("utf-8")

        self.__connection.readyRead.connect(self.__receiveJson)
        self.__connection.disconnected.connect(self.__handleDisconnect)

        self.connectionStateChanged.emit(True)

        return True

    @pyqtSlot()
    def disconnectFromServer(self):
        """
        Public method to disconnect from the eric remote server.
        """
        if self.__connection is not None and self.__connection.isValid():
            # signal we are about to disconnect
            self.aboutToDisconnect.emit()

            # disconnect from the eric-ide server
            self.__connection.disconnectFromHost()
            if self.__connection is not None:
                # may have disconnected already
                self.__connection.waitForDisconnected(
                    Preferences.getEricServer("ConnectionTimeout") * 1000
                )

                self.connectionStateChanged.emit(False)
                self.__connection = None
                self.__callbacks.clear()

        self.__clientId = b""

    def isServerConnected(self):
        """
        Public method to check, if a connection to an eric-ide server has been
        established.

        @return flag indicating the interface connection state
        @rtype bool
        """
        return (
            self.__connection is not None
            and self.__connection.state() == QAbstractSocket.SocketState.ConnectedState
        )

    @pyqtSlot()
    def __handleDisconnect(self):
        """
        Private slot handling a disconnect of the client.
        """
        if self.__connection is not None:
            self.__connection.close()

        self.connectionStateChanged.emit(False)
        self.__connection = None
        self.__callbacks.clear()
        self.__clientId = b""

    def getHost(self):
        """
        Public method to get the connected host as "host name:port".

        @return connected host as "host name:port" or an empty string, if there is no
            valid connection
        @rtype str
        """
        if self.isServerConnected():
            peerName = self.__connection.peerName()
            return "{0}:{1}".format(
                f"[{peerName}]" if ":" in peerName else peerName,
                self.__connection.peerPort(),
            )
        else:
            return ""

    def getHostName(self):
        """
        Public method to get the name of the connected host.

        @return name of the connected host or an empty string, if there is no
            valid connection
        @rtype str
        """
        if self.isServerConnected():
            return self.__connection.peerName()
        else:
            return ""

    def parseHost(self, host):
        """
        Public method to parse a host string generated with 'getHost()'.

        @param host host string
        @type str
        @return tuple containing the host name and the port
        @rtype tuple of (str, int)
        """
        host = host.strip()
        if "]" in host:
            # IPv6 address
            hostname, rest = host.split("]")
            hostname = hostname[1:]
            if rest and rest[0] == ":":
                port = int(rest[1:])
            else:
                port = None
        else:
            if ":" in host:
                hostname, port = host.split(":")
                port = int(port)
            else:
                hostname = host
                port = None

        return hostname, port

    #######################################################################
    ## Methods for sending requests and receiving the replies.
    #######################################################################

    @pyqtSlot()
    def __receiveJson(self):
        """
        Private slot handling received data from the eric remote server.
        """
        headerSize = struct.calcsize(b"!II")

        while self.__connection and self.__connection.bytesAvailable():
            now = time.monotonic()
            while self.__connection.bytesAvailable() < headerSize:
                self.__connection.waitForReadyRead(50)
                if time.monotonic() - now > 2.0:  # 2 seconds timeout
                    return
            header = self.__connection.read(struct.calcsize(b"!II"))
            length, datahash = struct.unpack(b"!II", header)

            data = bytearray()
            while len(data) < length:
                maxSize = length - len(data)
                if self.__connection.bytesAvailable() < maxSize:
                    self.__connection.waitForReadyRead(50)
                if not self.__connection:
                    # connection to server is gone uncontrolled
                    break
                newData = self.__connection.read(maxSize)
                if newData:
                    data += newData

            if zlib.adler32(data) & 0xFFFFFFFF != datahash:
                # corrupted data -> discard and continue
                continue

            jsonString = data.decode("utf-8", "backslashreplace")

            logging.getLogger(__name__).debug(
                f"<Remote Server Interface Rx> {jsonString}"
            )
            # - print("Remote Server Interface Receive: {0}".format(jsonString))
            # - this is for debugging only

            try:
                serverDataDict = json.loads(jsonString.strip())
            except (TypeError, ValueError) as err:
                EricMessageBox.critical(
                    None,
                    self.tr("JSON Protocol Error"),
                    self.tr(
                        """<p>The response received from the remote server"""
                        """ could not be decoded. Please report"""
                        """ this issue with the received data to the"""
                        """ eric bugs email address.</p>"""
                        """<p>Error: {0}</p>"""
                        """<p>Data:<br/>{1}</p>"""
                    ).format(str(err), EricUtilities.html_encode(jsonString.strip())),
                    EricMessageBox.Ok,
                )
                return

            reqUuid = serverDataDict["uuid"]
            if reqUuid:
                # It is a response to a synchronous request -> handle the call back
                # immediately.
                self.__callbacks[reqUuid](
                    serverDataDict["reply"], serverDataDict["params"]
                )
                del self.__callbacks[reqUuid]
            else:
                self.__messageQueue.append(serverDataDict)

        while self.__messageQueue:
            serverDataDict = self.__messageQueue.popleft()  # get the first message
            try:
                self.__categorySignalMapping[serverDataDict["category"]].emit(
                    serverDataDict["reply"], serverDataDict["params"]
                )
            except KeyError:
                if serverDataDict["category"] == EricRequestCategory.Error:
                    # handle server errors in here
                    self.__handleServerError(
                        serverDataDict["reply"], serverDataDict["params"]
                    )
                else:
                    self.remoteReply.emit(
                        serverDataDict["category"],
                        serverDataDict["reply"],
                        serverDataDict["params"],
                    )

    def sendJson(self, category, request, params, callback=None, flush=False):
        """
        Public method to send a single command to a client.

        @param category service category
        @type EricRequestCategory
        @param request request name to be sent
        @type str
        @param params dictionary of named parameters for the request
        @type dict
        @param callback callback function for the reply from the eric remote server
            (defaults to None)
        @type function (optional)
        @param flush flag indicating to flush the data to the socket
            (defaults to False)
        @type bool (optional)
        """
        if callback:
            reqUuid = str(uuid.uuid4())
            self.__callbacks[reqUuid] = callback
        else:
            reqUuid = ""

        serviceDict = {
            "jsonrpc": "2.0",
            "category": category,
            "request": request,
            "params": params,
            "uuid": reqUuid,
        }
        jsonString = json.dumps(serviceDict) + "\n"

        logging.getLogger(__name__).debug(f"<Remote Server Interface Tx> {jsonString}")
        # - print("Remote Server Interface Send: {0}".format(jsonString))
        # - this is for debugging only

        if self.__connection is not None:
            data = jsonString.encode("utf8", "backslashreplace")
            header = struct.pack(b"!II", len(data), zlib.adler32(data) & 0xFFFFFFFF)
            if self.__clientId:
                self.__connection.write(self.__clientId)
            self.__connection.write(header)
            self.__connection.write(data)
            if flush:
                self.__connection.flush()

    def shutdownServer(self):
        """
        Public method shutdown the currebtly connected eric-ide remote server.
        """
        if self.__connection:
            self.sendJson(
                category=EricRequestCategory.Server,
                request="Shutdown",
                params={},
            )

    @pyqtSlot()
    def serverVersions(self):
        """
        Public slot to request the eric-ide version of the server.
        """
        if self.__connection:
            self.sendJson(
                category=EricRequestCategory.Server,
                request="Versions",
                params={},
                callback=self.__handleServerVersionReply,
            )

    #######################################################################
    ## Callback methods
    #######################################################################

    def __handleServerVersionReply(self, reply, params):
        """
        Private method to handle the reply of a 'Version' request.

        @param reply name of the eric-ide server reply
        @type str
        @param params dictionary containing the reply data
        @type dict
        @exception ValueError raised in case of an unsupported reply
        """
        if reply != "Versions":
            raise ValueError(f"unsupported reply received ({reply})")

        else:
            hostname = params["hostname"]
            versionInfo = [
                "<h2>",
                self.tr("{0}Version Numbers").format(
                    self.tr("{0} - ").format(hostname) if hostname else ""
                ),
                "</h2><table>",
            ]

            # eric7 server version
            versionInfo.extend(
                [
                    "<tr><td></td><td></td></tr>",
                    f"<tr><td><b>eric7_server</b></td>"
                    f"<td>{params['version']} </td></tr>",
                    "<tr><td></td><td></td></tr>",
                ]
            )

            # Python version
            versionInfo.append(
                f"<tr><td><b>Python</b></td>"
                f"<td>{params['python']}, {params['py_bitsize']}</td></tr>"
            )

            versionInfo.append("</table>")

            EricMessageBox.about(
                None,
                self.tr("eric-ide Server Versions"),
                "".join(versionInfo),
            )

    #######################################################################
    ## Reply handler methods
    #######################################################################

    def __handleServerError(self, reply, params):
        """
        Private method handling server error replies.

        @param reply name of the error reply
        @type str
        @param params dictionary containing the specific reply data
        @type dict
        """
        if reply == "ClientChecksumException":
            self.__ui.appendToStderr(
                self.tr(
                    "eric-ide Server Checksum Error\nError: {0}\nData:\n{1}\n"
                ).format(params["ExceptionValue"], params["ProtocolData"])
            )

        elif reply == "ClientException":
            self.__ui.appendToStderr(
                self.tr("eric-ide Server Data Error\nError: {0}\nData:\n{1}\n").format(
                    params["ExceptionValue"], params["ProtocolData"]
                )
            )

        elif reply == "UnsupportedServiceCategory":
            self.__ui.appendToStderr(
                self.tr(
                    "eric-ide Server Unsupported Category\n"
                    "Error: The server received the unsupported request category '{0}'."
                ).format(params["Category"])
            )

    #######################################################################
    ## User interface related methods
    #######################################################################

    def initActions(self):
        """
        Public slot to initialize the eric-ide server actions.
        """
        self.actions = []

        self.connectServerAct = EricAction(
            self.tr("Connect"),
            EricPixmapCache.getIcon("linkConnect"),
            self.tr("Connect..."),
            QKeySequence(self.tr("Meta+Shift+C")),
            0,
            self,
            "remote_server_connect",
        )
        self.connectServerAct.setStatusTip(
            self.tr("Show a dialog to connect to an 'eric-ide' server")
        )
        self.connectServerAct.setWhatsThis(
            self.tr(
                """<b>Connect...</b>"""
                """<p>This opens a dialog to enter the connection parameters to"""
                """ connect to a remote 'eric-ide' server.</p>"""
            )
        )
        self.connectServerAct.triggered.connect(self.__connectToServer)
        self.actions.append(self.connectServerAct)

        self.disconnectServerAct = EricAction(
            self.tr("Disconnect"),
            EricPixmapCache.getIcon("linkDisconnect"),
            self.tr("Disconnect"),
            QKeySequence(self.tr("Meta+Shift+D")),
            0,
            self,
            "remote_server_disconnect",
        )
        self.disconnectServerAct.setStatusTip(
            self.tr("Disconnect from the currently connected 'eric-ide' server")
        )
        self.disconnectServerAct.setWhatsThis(
            self.tr(
                """<b>Disconnect</b>"""
                """<p>This disconnects from the currently connected 'eric-ide'"""
                """ server.</p>"""
            )
        )
        self.disconnectServerAct.triggered.connect(self.disconnectFromServer)
        self.actions.append(self.disconnectServerAct)

        self.stopServerAct = EricAction(
            self.tr("Stop Server"),
            EricPixmapCache.getIcon("stopScript"),
            self.tr("Stop Server"),
            QKeySequence(self.tr("Meta+Shift+S")),
            0,
            self,
            "remote_server_shutdown",
        )
        self.stopServerAct.setStatusTip(
            self.tr("Stop the currently connected 'eric-ide' server")
        )
        self.stopServerAct.setWhatsThis(
            self.tr(
                """<b>Stop Server</b>"""
                """<p>This stops the currently connected 'eric-ide server.</p>"""
            )
        )
        self.stopServerAct.triggered.connect(self.__shutdownServer)
        self.actions.append(self.stopServerAct)

        self.serverVersionsAct = EricAction(
            self.tr("Show Server Versions"),
            EricPixmapCache.getIcon("helpAbout"),
            self.tr("Show Server Versions"),
            0,
            0,
            self,
            "remote_server_versions",
        )
        self.serverVersionsAct.setStatusTip(
            self.tr("Show the eric-ide server versions")
        )
        self.serverVersionsAct.setWhatsThis(
            self.tr(
                """<b>Show Server Versions</b>"""
                """<p>This opens a dialog to show the eric-ide server versions.</p>"""
            )
        )
        self.serverVersionsAct.triggered.connect(self.serverVersions)
        self.actions.append(self.serverVersionsAct)

        self.disconnectServerAct.setEnabled(False)
        self.stopServerAct.setEnabled(False)
        self.serverVersionsAct.setEnabled(False)

    def initMenus(self):
        """
        Public slot to initialize the eric-ide server menus.

        @return reference to the main eric-ide server menu
        @rtype QMenu
        """
        self.__serverProfilesMenu = QMenu(self.tr("Connect to"))
        self.__serverProfilesMenu.aboutToShow.connect(self.__showServerProfilesMenu)
        self.__serverProfilesMenu.triggered.connect(self.__serverProfileTriggered)

        menu = QMenu(self.tr("eric-ide Server"), self.__ui)
        menu.setTearOffEnabled(True)
        menu.aboutToShow.connect(self.__showEricServerMenu)
        menu.addAction(self.connectServerAct)
        menu.addMenu(self.__serverProfilesMenu)
        menu.addSeparator()
        menu.addAction(self.disconnectServerAct)
        menu.addSeparator()
        menu.addAction(self.stopServerAct)
        menu.addSeparator()
        menu.addAction(self.serverVersionsAct)

        self.__menus = {
            "Main": menu,
            "ServerProfiles": self.__serverProfilesMenu,
        }

        return menu

    def initToolbar(self, toolbarManager):
        """
        Public slot to initialize the eric-ide server toolbar.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return the toolbar generated
        @rtype QToolBar
        """
        self.__connectButton = QToolButton()
        self.__connectButton.setIcon(self.connectServerAct.icon())
        self.__connectButton.setToolTip(self.connectServerAct.toolTip())
        self.__connectButton.setWhatsThis(self.connectServerAct.whatsThis())
        self.__connectButton.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup
        )
        self.__connectButton.setMenu(self.__serverProfilesMenu)
        self.connectServerAct.enabledChanged.connect(self.__connectButton.setEnabled)
        self.__connectButton.clicked.connect(self.connectServerAct.triggered)

        tb = QToolBar(self.tr("eric-ide Server"), self.__ui)
        tb.setObjectName("EricServerToolbar")
        tb.setToolTip(self.tr("eric-ide Server"))

        self.__connectButtonAct = tb.addWidget(self.__connectButton)
        self.__connectButtonAct.setText(self.connectServerAct.iconText())
        self.__connectButtonAct.setIcon(self.connectServerAct.icon())
        tb.addAction(self.disconnectServerAct)
        tb.addSeparator()
        tb.addAction(self.stopServerAct)
        tb.addSeparator()
        tb.addAction(self.serverVersionsAct)

        toolbarManager.addToolBar(tb, tb.windowTitle())

        return tb

    @pyqtSlot()
    def __showEricServerMenu(self):
        """
        Private slot to display the server menu.
        """
        connected = self.isServerConnected()
        self.connectServerAct.setEnabled(not connected)
        self.disconnectServerAct.setEnabled(connected)
        self.stopServerAct.setEnabled(connected)
        self.serverVersionsAct.setEnabled(connected)

        self.showMenu.emit("Main", self.__menus["Main"])

    @pyqtSlot()
    def __showServerProfilesMenu(self):
        """
        Private slot to prepare the eric server profiles menu.
        """
        serverProfiles = Preferences.getEricServer("ConnectionProfiles")

        self.__serverProfilesMenu.clear()

        if not self.isServerConnected():
            for serverProfile in sorted(serverProfiles):
                act = self.__serverProfilesMenu.addAction(serverProfile)
                data = serverProfiles[serverProfile]
                if len(data) == 3:
                    # profile generated before eric-ide 24.12
                    data.append("")
                act.setData(data)
            self.__serverProfilesMenu.addSeparator()

        self.__serverProfilesMenu.addAction(
            self.tr("Manage Server Connections"), self.__manageServerProfiles
        )

        self.showMenu.emit("ServerProfiles", self.__menus["ServerProfiles"])

    @pyqtSlot(bool)
    def __connectionStateChanged(self, connected):
        """
        Private slot to handle the connection state change.

        @param connected flag indicating the connection state
        @type bool
        """
        if connected != self.__connected:  # prevent executing it twice in succession
            self.__connected = connected

            self.connectServerAct.setEnabled(not connected)
            self.disconnectServerAct.setEnabled(connected)
            self.stopServerAct.setEnabled(connected)
            self.serverVersionsAct.setEnabled(connected)

            if connected:
                peerName = self.__connection.peerName()
                EricMessageBox.information(
                    None,
                    self.tr("Connect to eric-ide Server"),
                    self.tr(
                        "<p>The eric-ide server at <b>{0}:{1}</b> was connected"
                        " successfully.</p>"
                    ).format(
                        f"[{peerName}]" if ":" in peerName else peerName,
                        self.__connection.peerPort(),
                    ),
                )
            else:
                EricMessageBox.information(
                    None,
                    self.tr("Disconnect from eric-ide Server"),
                    self.tr("""The eric-ide server was disconnected."""),
                )

    @pyqtSlot()
    def __connectToServer(self):
        """
        Private slot to connect to a remote eric-ide server.
        """
        from .EricServerConnectionDialog import EricServerConnectionDialog

        dlg = EricServerConnectionDialog(parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            hostname, port, timeout, clientId = dlg.getData()
            self.connectToServer(
                hostname, port=port, timeout=timeout, clientId=clientId
            )

    @pyqtSlot()
    def __shutdownServer(self):
        """
        Private slot to shut down the currently connected eric-ide server.
        """
        ok = EricMessageBox.yesNo(
            None,
            self.tr("Stop Server"),
            self.tr(
                "<p>Do you really want to stop the currently connected eric-ide server"
                " <b>{0}</b>? No further connections will be possible without"
                " restarting the server.</p>"
            ).format(self.getHost()),
        )
        if ok:
            self.shutdownServer()

    @pyqtSlot(QAction)
    def __serverProfileTriggered(self, act):
        """
        Private slot to handle the selection of a remote server connection.

        @param act reference to the triggered profile action
        @type QAction
        """
        data = act.data()
        if data is not None:
            # handle the connection
            hostname, port, timeout, clientId = data
            self.connectToServer(
                hostname, port=port, timeout=timeout, clientId=clientId
            )

    @pyqtSlot()
    def __manageServerProfiles(self):
        """
        Private slot to show a dialog to manage the eric-ide server connection
        profiles.
        """
        from .EricServerProfilesDialog import EricServerProfilesDialog

        dlg = EricServerProfilesDialog(
            Preferences.getEricServer("ConnectionProfiles"), parent=self.__ui
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            profiles = dlg.getConnectionProfiles()
            Preferences.setEricServer("ConnectionProfiles", profiles)
