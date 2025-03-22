# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some utility functions and the MicroPythonDevice base
class.
"""

import ast
import contextlib
import copy
import os
import time

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QInputDialog

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp


class BaseDevice(QObject):
    """
    Base class for the more specific MicroPython devices.

    It includes a list of commands for general use on the various boards.
    If a board needs special treatment, the command should be overwritten
    in the board specific subclass. Commands are provided to perform operations
    on the file system of a connected MicroPython device, for getting and setting
    the time on the board and getting board related data.

    Supported file system commands are:
    <ul>
    <li>cd: change directory</li>
    <li>exists: test the existence of a file or directory on the device</li>
    <li>fileSystemInfo: get information about the file system</li>
    <li>get: get a file from the connected device</li>
    <li>getData: read data of a file of the connected device</li>
    <li>lls: directory listing with meta data</li>
    <li>ls: directory listing</li>
    <li>mkdir: create a new directory</li>
    <li>put: copy a file to the connected device</li>
    <li>putData: write data to a file of the connected device</li>
    <li>pwd: get the current directory</li>
    <li>rm: remove a file from the connected device</li>
    <li>rmdir: remove an empty directory</li>
    <li>rmrf: remove a file/directory recursively (like 'rm -rf' in bash)</li>
    </ul>

    Supported non file system commands are:
    <ul>
    <li>getBoardData: get information about the connected board</li>
    <li>getDeviceData: get version info about MicroPython and some implementation
        information</li>
    <li>getModules: get a list of built-in modules</li>
    <li>getTime: get the current time</li>
    <li>showTime: show the current time of the connected device</li>
    <li>syncTime: synchronize the time of the connected device</li>
    <li>mipInstall: install a MicroPython package with 'mip'</li>
    <li>upipInstall: install a MicroPython package with 'upip'</li>
    <li>getLibPaths: get a list of library paths contained in sys.path</li>
    </ul>

    Supported WiFi commands are:
    <ul>
    <li>hasWifi: check, if the board has WiFi functionality</li>
    <li>getWifiData: get WiFi status data</li>
    <li>connectWifi: connect to a WiFi network</li>
    <li>disconnectWifi: disconnect from a WiFi network</li>
    <li>isWifiClientConnected: check the WiFi connection status as client</li>
    <li>isWifiApConnected: check the WiFi connection status as access point</li>
    <li>writeCredentials: save the WiFi credentials to the board and create
        functionality to auto-connect at boot time</li>
    <li>removeCredentials: remove the saved credentials</li>
    <li>checkInternet: check, if internet access is possible</li>
    <li>scanNetworks: scan for available WiFi networks</li>
    <li>deactivateInterface: deactivate a WiFi interface</li>
    <li>startAccessPoint: start an access point</li>
    <li>stopAccessPoint: stop the access point</li>
    <li>getConnectedClients: get a list of connected WiFi clients</li>
    </ul>

    Supported Bluetooth commands are:
    <ul>
    <li>hasBluetooth: check, if the board has Bluetooth functionality</li>
    <li>getBluetoothStatus: get Bluetooth status data</li>
    <li>activateBluetoothInterface: activate a Bluetooth interface</li>
    <li>deactivateBluetoothInterface: deactivate a Bluetooth interface</li>
    <li>getDeviceScan: scan for visible Bluetooth devices</li>
    </ul>

    Supported Ethernet commands are:
    <ul>
    <li>hasEthernet: check, if the board has Ethernet functionality</li>
    <li>getEthernetStatus: get Ethernet status data</li>
    <li>connectToLan: connect to an Ethernet network</li>
    <li>disconnectFromLan: disconnect from an Ethernet network</li>
    <li>isLanConnected: check the LAN connection status</li>
    <li>checkInternetViaLan: check, if internet access via LAN is possible</li>
    <li>deactivateEthernet: deactivate the Ethernet interface</li>
    <li>writeLanAutoConnect: save IPv4 parameters to the board and create a script
        to connect the board to the LAN</li>
    <li>removeLanAutoConnect: remove the IPv4 parameters and script from the board</li>
    </ul>
    """

    def __init__(self, microPythonWidget, deviceType, parent=None):
        """
        Constructor

        @param microPythonWidget reference to the main MicroPython widget
        @type MicroPythonWidget
        @param deviceType device type assigned to this device interface
        @type str
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self._deviceType = deviceType
        self._interface = None
        self.microPython = microPythonWidget
        self._deviceData = {}  # dictionary with essential device data

        self._submitMode = "raw"  # default is 'raw' mode to submit commands

    def setConnected(self, connected):
        """
        Public method to set the connection state.

        Note: This method can be overwritten to perform actions upon connect
        or disconnect of the device.

        @param connected connection state
        @type bool
        """
        self._deviceData = {}

        if connected:
            self._interface = self.microPython.deviceInterface()
            with contextlib.suppress(OSError):
                data = self.__getDeviceData()
                if "mpy_name" in data:
                    self._deviceData = data
                    self._deviceData["local_mip"] = (
                        not self._deviceData["mip"]
                        and not self._deviceData["upip"]
                        and not self.hasCircuitPython()
                    )
                    (
                        self._deviceData["wifi"],
                        self._deviceData["wifi_type"],
                    ) = self.hasWifi()
                    self._deviceData["bluetooth"] = self.hasBluetooth()
                    (
                        self._deviceData["ethernet"],
                        self._deviceData["ethernet_type"],
                    ) = self.hasEthernet()
                else:
                    self._deviceData = {}
        else:
            self._interface = None

    def getDeviceType(self):
        """
        Public method to get the device type.

        @return type of the device
        @rtype str
        """
        return self._deviceType

    def getDeviceData(self, key=None):
        """
        Public method to get a copy of the determined device data or part of them.

        @param key name or a list of names of the data to get (None to get all data)
            (defaults to None)
        @type str or list of str (optional)
        @return dictionary containing the essential device data
        @rtype dict or Any
        """
        if key is None:
            return copy.deepcopy(self._deviceData)
        elif isinstance(key, list):
            res = {}
            for name in key:
                try:
                    res[name] = self._deviceData[name]
                except KeyError:
                    res[name] = None
            return res
        else:
            try:
                return self._deviceData[key]
            except KeyError:
                return None

    def checkDeviceData(self, quiet=True):
        """
        Public method to check the validity of the device data determined during
        connecting the device.

        @param quiet flag indicating to not show an info message, if the data is
            not available (defaults to True)
        @type bool (optional)
        @return flag indicating valid device data
        @rtype bool
        """
        if bool(self._deviceData):
            return True
        else:
            if not quiet:
                EricMessageBox.critical(
                    None,
                    self.tr("Device Data Not Available"),
                    self.tr(
                        """<p>The device data is not available. Try to connect to the"""
                        """ device again. Aborting...</p>"""
                    ).format(self.getDeviceType()),
                )
            return False

    def hasCircuitPython(self):
        """
        Public method to check, if the connected device is flashed with CircuitPython.

        @return flag indicating CircuitPython
        @rtype bool
        """
        try:
            return (
                self.checkDeviceData()
                and self._deviceData["mpy_name"].lower() == "circuitpython"
            )
        except KeyError:
            return False

    def submitMode(self):
        """
        Public method to get the submit mode of the device.

        @return submit mode
        @rtype str (one of 'raw', 'paste')
        """
        return self._submitMode

    def setButtons(self):
        """
        Public method to enable the supported action buttons.
        """
        self.microPython.setActionButtons(
            run=False, repl=False, files=False, chart=False
        )

    def forceInterrupt(self):
        """
        Public method to determine the need for an interrupt when opening the
        serial connection.

        @return flag indicating an interrupt is needed
        @rtype bool
        """
        return True

    def deviceName(self):
        """
        Public method to get the name of the device.

        @return name of the device
        @rtype str
        """
        return self.tr("Unsupported Device")

    def canStartRepl(self):
        """
        Public method to determine, if a REPL can be started.

        @return tuple containing a flag indicating it is safe to start a REPL
            and a reason why it cannot.
        @rtype tuple of (bool, str)
        """
        return False, self.tr("REPL is not supported by this device.")

    def setRepl(self, on):
        """
        Public method to set the REPL status and dependent status.

        @param on flag indicating the active status
        @type bool
        """
        pass

    def canStartPlotter(self):
        """
        Public method to determine, if a Plotter can be started.

        @return tuple containing a flag indicating it is safe to start a
            Plotter and a reason why it cannot.
        @rtype tuple of (bool, str)
        """
        return False, self.tr("Plotter is not supported by this device.")

    def setPlotter(self, on):
        """
        Public method to set the Plotter status and dependent status.

        @param on flag indicating the active status
        @type bool
        """
        pass

    def canRunScript(self):
        """
        Public method to determine, if a script can be executed.

        @return tuple containing a flag indicating it is safe to start a
            Plotter and a reason why it cannot.
        @rtype tuple of (bool, str)
        """
        return False, self.tr("Running scripts is not supported by this device.")

    def runScript(self, script):
        """
        Public method to run the given Python script.

        @param script script to be executed
        @type str
        """
        pass

    def canStartFileManager(self):
        """
        Public method to determine, if a File Manager can be started.

        @return tuple containing a flag indicating it is safe to start a
            File Manager and a reason why it cannot.
        @rtype tuple of (bool, str)
        """
        return False, self.tr("File Manager is not supported by this device.")

    def setFileManager(self, on):
        """
        Public method to set the File Manager status and dependent status.

        @param on flag indicating the active status
        @type bool
        """
        pass

    def supportsLocalFileAccess(self):
        """
        Public method to indicate file access via a local directory.

        @return flag indicating file access via local directory
        @rtype bool
        """
        return False  # default

    def getWorkspace(self):
        """
        Public method to get the workspace directory.

        @return workspace directory used for saving files
        @rtype str
        """
        return (
            Preferences.getMicroPython("MpyWorkspace")
            or Preferences.getMultiProject("Workspace")
            or os.path.expanduser("~")
        )

    def setWorkspace(self, workspacePath):
        """
        Public method to set the device workspace directory.

        @param workspacePath directory to be used for saving files
        @type str
        """
        # nothing to do here
        pass

    def selectDeviceDirectory(self, deviceDirectories):
        """
        Public method to select the device directory from a list of detected
        ones.

        @param deviceDirectories list of directories to select from
        @type list of str
        @return selected directory or an empty string
        @rtype str
        """
        deviceDirectory, ok = QInputDialog.getItem(
            None,
            self.tr("Select Device Directory"),
            self.tr("Select the directory for the connected device:"),
            [""] + deviceDirectories,
            0,
            False,
        )
        if ok:
            return deviceDirectory
        else:
            # user cancelled
            return ""

    def executeCommands(self, commands, *, mode="raw", timeout=0):
        """
        Public method to send commands to the connected device and return the
        result.

        If no connected interface is available, empty results will be returned.

        @param commands list of commands to be executed
        @type str or list of str
        @keyparam mode submit mode to be used (one of 'raw' or 'paste') (defaults to
            'raw')
        @type str
        @keyparam timeout per command timeout in milliseconds (0 for configured default)
            (defaults to 0)
        @type int (optional)
        @return tuple containing stdout and stderr output of the device
        @rtype tuple of (bytes, bytes)
        """
        if self._interface is None:
            return b"", b""

        return self._interface.execute(commands, mode=mode, timeout=timeout)

    def sendCommands(self, commandsList):
        """
        Public method to send a list of commands to the device.

        @param commandsList list of commands to be sent to the device
        @type list of str
        """
        if self._interface is not None:
            self._interface.executeAsync(commandsList, self._submitMode)

    @pyqtSlot()
    def handleDataFlood(self):
        """
        Public slot handling a data floof from the device.
        """
        pass

    def addDeviceMenuEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        pass

    def hasFlashMenuEntry(self):
        """
        Public method to check, if the device has its own flash menu entry.

        @return flag indicating a specific flash menu entry
        @rtype bool
        """
        return False

    def hasTimeCommands(self):
        """
        Public method to check, if the device supports time commands.

        The default returns True.

        @return flag indicating support for time commands
        @rtype bool
        """
        return True

    def hasDocumentationUrl(self):
        """
        Public method to check, if the device has a configured documentation
        URL.

        @return flag indicating a configured documentation URL
        @rtype bool
        """
        return bool(self.getDocumentationUrl())

    def getDocumentationUrl(self):
        """
        Public method to get the device documentation URL.

        @return documentation URL of the device
        @rtype str
        """
        return ""

    def hasFirmwareUrl(self):
        """
        Public method to check, if the device has a configured firmware
        download URL.

        @return flag indicating a configured firmware download URL
        @rtype bool
        """
        return bool(self.getFirmwareUrl())

    def getFirmwareUrl(self):
        """
        Public method to get the device firmware download URL.

        @return firmware download URL of the device
        @rtype str
        """
        return ""

    def downloadFirmware(self):
        """
        Public method to download the device firmware.
        """
        url = self.getFirmwareUrl()
        if url:
            ericApp().getObject("UserInterface").launchHelpViewer(url)

    def getDownloadMenuEntries(self):
        """
        Public method to retrieve the entries for the downloads menu.

        @return list of tuples with menu text and URL to be opened for each
            entry
        @rtype list of tuple of (str, str)
        """
        return []

    def _shortError(self, error):
        """
        Protected method to create a shortened error message.

        @param error verbose error message
        @type bytes
        @return shortened error message
        @rtype str
        """
        if error:
            decodedError = error.decode("utf-8")
            try:
                return decodedError.split["\r\n"][-2]
            except Exception:
                return decodedError

        return self.tr("Detected an error without indications.")

    ##################################################################
    ## Methods below implement the file system commands
    ##################################################################

    def exists(self, pathname):
        """
        Public method to check the existence of a file or directory.

        @param pathname name of the path to check
        @type str
        @return flag indicating the existence
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        command = """
import os as __os_
try:
    __os_.stat({0})
    print(True)
except OSError:
    print(False)
del __os_
""".format(
            repr(pathname)
        )
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))
        return out.strip() == b"True"

    def ls(self, dirname=""):
        """
        Public method to get a directory listing of the connected device.

        @param dirname name of the directory to be listed
        @type str
        @return tuple containg the directory listing
        @rtype tuple of str
        @exception OSError raised to indicate an issue with the device
        """
        command = """
import os as __os_
print(__os_.listdir('{0}'))
del __os_
""".format(
            dirname
        )
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))
        return ast.literal_eval(out.decode("utf-8"))

    def lls(self, dirname="", fullstat=False, showHidden=False):
        """
        Public method to get a long directory listing of the connected device
        including meta data.

        @param dirname name of the directory to be listed
        @type str
        @param fullstat flag indicating to return the full stat() tuple
        @type bool
        @param showHidden flag indicating to show hidden files as well
        @type bool
        @return list containing the directory listing with tuple entries of
            the name and and a tuple of mode, size and time (if fullstat is
            false) or the complete stat() tuple. 'None' is returned in case the
            directory doesn't exist.
        @rtype tuple of (str, tuple)
        @exception OSError raised to indicate an issue with the device
        """
        command = """
import os as __os_

def is_visible(filename, showHidden):
    return showHidden or (filename[0] != '.' and filename[-1] != '~')

def stat(filename):
    try:
        rstat = __os_.lstat(filename)
    except:
        rstat = __os_.stat(filename)
    return tuple(rstat)

def listdir_stat(dirname, showHidden):
    try:
        files = __os_.listdir(dirname)
    except OSError:
        return []
    if dirname in ('', '/'):
        return list((f, stat(dirname + f)) for f in files if is_visible(f, showHidden))
    return list(
        (f, stat(dirname + '/' + f)) for f in files if is_visible(f, showHidden)
    )

print(listdir_stat('{0}', {1}))
del __os_, stat, listdir_stat, is_visible
""".format(
            dirname, showHidden
        )
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))
        fileslist = ast.literal_eval(out.decode("utf-8"))
        if fileslist is None:
            return None
        else:
            if fullstat:
                return fileslist
            else:
                return [(f, (s[0], s[6], s[8])) for f, s in fileslist]

    def cd(self, dirname):
        """
        Public method to change the current directory on the connected device.

        @param dirname directory to change to
        @type str
        @exception OSError raised to indicate an issue with the device
        """
        if dirname:
            command = """
import os as __os_
__os_.chdir('{0}')
del __os_
""".format(
                dirname
            )
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))

    def pwd(self):
        """
        Public method to get the current directory of the connected device.

        @return current directory
        @rtype str
        @exception OSError raised to indicate an issue with the device
        """
        command = """
import os as __os_
print(__os_.getcwd())
del __os_
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))
        return out.decode("utf-8").strip()

    def rm(self, filename):
        """
        Public method to remove a file from the connected device.

        @param filename name of the file to be removed
        @type str
        @exception OSError raised to indicate an issue with the device
        """
        if filename:
            command = """
import os as __os_
try:
    __os_.remove('{0}')
except OSError as err:
    if err.errno != 2:
        raise err
del __os_
""".format(
                filename
            )
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))

    def rmrf(self, name, recursive=False, force=False):
        """
        Public method to remove a file or directory recursively.

        @param name of the file or directory to remove
        @type str
        @param recursive flag indicating a recursive deletion
        @type bool
        @param force flag indicating to ignore errors
        @type bool
        @return flag indicating success
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        if name:
            command = """
import os as __os_

def remove_file(name, recursive=False, force=False):
    try:
        mode = __os_.stat(name)[0]
        if mode & 0x4000 != 0:
            if recursive:
                for file in __os_.listdir(name):
                    success = remove_file(name + '/' + file, recursive, force)
                    if not success and not force:
                        return False
                __os_.rmdir(name)
            else:
                if not force:
                    return False
        else:
            __os_.remove(name)
    except:
        if not force:
            return False
    return True

print(remove_file('{0}', {1}, {2}))
del __os_, remove_file
""".format(
                name, recursive, force
            )
            out, err = self.executeCommands(
                command, mode=self._submitMode, timeout=20000
            )
            if err:
                raise OSError(self._shortError(err))
            return ast.literal_eval(out.decode("utf-8"))

        return False

    def mkdir(self, dirname):
        """
        Public method to create a new directory.

        @param dirname name of the directory to create
        @type str
        @exception OSError raised to indicate an issue with the device
        """
        if dirname:
            command = """
import os as __os_
__os_.mkdir('{0}')
del __os_
""".format(
                dirname
            )
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))

    def rmdir(self, dirname):
        """
        Public method to remove a directory.

        @param dirname name of the directory to be removed
        @type str
        @exception OSError raised to indicate an issue with the device
        """
        if dirname:
            command = """
import os as __os_

try:
    __os_.rmdir('{0}')
except OSError as exc:
    if exc.args[0] == 13:
        raise OSError(13, 'Access denied or directory not empty.')
    else:
        raise
del __os_
""".format(
                dirname
            )
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))

    def rename(self, oldname, newname):
        """
        Public method to rename a file on the device.

        @param oldname current name of the file
        @type str
        @param newname new name for the file
        @type str
        @exception OSError raised to indicate an issue with the device
        """
        if oldname and newname:
            command = """
import os as __os_
__os_.rename('{0}', '{1}')
del __os_
""".format(
                oldname, newname
            )
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))

    def put(self, hostFileName, deviceFileName=None):
        """
        Public method to copy a local file to the connected device.

        @param hostFileName name of the file to be copied
        @type str
        @param deviceFileName name of the file to copy to
        @type str
        @return flag indicating success
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        if not os.path.isfile(hostFileName):
            raise OSError("No such file: {0}".format(hostFileName))

        if not deviceFileName:
            deviceFileName = os.path.basename(hostFileName)

        with open(hostFileName, "rb") as hostFile:
            content = hostFile.read()

        return self.putData(deviceFileName, content)

    def putData(self, deviceFileName, content):
        """
        Public method to write the given data to the connected device.

        @param deviceFileName name of the file to write to
        @type str
        @param content data to write
        @type bytes
        @return flag indicating success
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        if not deviceFileName:
            raise OSError("Missing device file name")

        # convert eol to '\n'
        content = content.replace(b"\r\n", b"\n")
        content = content.replace(b"\r", b"\n")

        commands = [
            "fd = open('{0}', 'wb')".format(deviceFileName),
            "f = fd.write",
        ]
        while content:
            chunk = content[:64]
            commands.append("f(" + repr(chunk) + ")")
            content = content[64:]
        commands.extend(
            [
                "fd.close()",
                "del f, fd",
            ]
        )
        command = "\n".join(commands)

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))
        return True

    def get(self, deviceFileName, hostFileName=None):
        """
        Public method to copy a file from the connected device.

        @param deviceFileName name of the file to copy
        @type str
        @param hostFileName name of the file to copy to
        @type str
        @return flag indicating success
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        if not deviceFileName:
            raise OSError("Missing device file name")

        if not hostFileName:
            hostFileName = deviceFileName

        out = self.getData(deviceFileName)
        with open(hostFileName, "wb") as hostFile:
            hostFile.write(out)

        return True

    def getData(self, deviceFileName):
        """
        Public method to read data from the connected device.

        @param deviceFileName name of the file to read from
        @type str
        @return data read from the device
        @rtype bytes
        @exception OSError raised to indicate an issue with the device
        """
        if not deviceFileName:
            raise OSError("Missing device file name")

        command = """
def send_data():
    try:
        from microbit import uart as u
    except ImportError:
        try:
            from sys import stdout as u
        except ImportError:
            try:
                from machine import UART
                u = UART(0, 115200)
            except Exception:
                raise Exception('Could not find UART module in device.')
    f = open('{0}', 'rb')
    r = f.read
    result = True
    while result:
        result = r(32)
        if result:
            u.write(result)
    f.close()

send_data()
del send_data
""".format(
            deviceFileName
        )
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        # write the received bytes to the local file
        # convert eol to "\n"
        out = out.replace(b"\r\n", b"\n")
        out = out.replace(b"\r", b"\n")

        return out

    def fileSystemInfo(self):
        """
        Public method to obtain information about the currently mounted file
        systems.

        @return tuple of tuples containing the file system name, the total
            size, the used size and the free size
        @rtype tuple of tuples of (str, int, int, int)
        @exception OSError raised to indicate an issue with the device
        """
        command = """
import os as __os_

def fsinfo():
    infodict = {}
    info = __os_.statvfs('/')
    if info[0] == 0:
        fsnames = __os_.listdir('/')
        for fs in fsnames:
            fs = '/' + fs
            infodict[fs] = __os_.statvfs(fs)
    else:
        infodict['/'] = info
        fsnames = __os_.listdir('/')
        for fs in fsnames:
            fs = '/' + fs
            info = __os_.statvfs(fs)
            if info not in infodict.values():
                infodict[fs] = info
    return infodict

print(fsinfo())
del __os_, fsinfo
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))
        infodict = ast.literal_eval(out.decode("utf-8"))
        if infodict is None:
            return None
        else:
            filesystemInfos = []
            for fs, info in infodict.items():
                totalSize = info[2] * info[1]
                freeSize = info[4] * info[1]
                usedSize = totalSize - freeSize
                filesystemInfos.append((fs, totalSize, usedSize, freeSize))

        return tuple(filesystemInfos)

    def ensurePath(self, target):
        """
        Public method to ensure, that the given target path exists.

        @param target target directory
        @type str
        """
        pathParts = target.split("/")

        # handle targets starting with "/"
        if not pathParts[0]:
            pathParts.pop(0)
            pathParts[0] = "/" + pathParts[0]

        directory = ""
        for index in range(len(pathParts)):
            directory += pathParts[index]
            if not self.exists(directory):
                self.mkdir(directory)
            directory += "/"

    ##################################################################
    ## board information related methods below
    ##################################################################

    def __getDeviceData(self):
        """
        Private method to get some essential data for the connected board.

        @return dictionary containing the determined data
        @rtype dict
        @exception OSError raised to indicate an issue with the device
        """
        command = """
def get_device_data():
    res = {}

    try:
        import os
        uname = os.uname()
        res['sysname'] = uname.sysname
        res['nodename'] = uname.nodename
        res['release'] = uname.release
        res['version'] = uname.version
        res['machine'] = uname.machine
    except AttributeError:
        import sys
        res['sysname'] = sys.platform
        res['nodename'] = sys.platform
        res['release'] = '.'.join(str(v) for v in sys.implementation.version)
        res['version'] = sys.version.split(';', 1)[-1].strip()
        res['machine'] = sys.implementation._machine

    import sys
    res['py_platform'] = sys.platform
    res['py_version'] = sys.version

    try:
        res['mpy_name'] = sys.implementation.name
    except AttributeError:
        res['mpy_name'] = 'unknown'

    try:
        res['mpy_version'] = '.'.join((str(i) for i in sys.implementation.version))
    except AttributeError:
        res['mpy_version'] = 'unknown'

    if hasattr(sys.implementation, '_mpy'):
        res['mpy_file_version'] = sys.implementation._mpy & 0xff
    elif hasattr(sys.implementation, 'mpy'):
        res['mpy_file_version'] = sys.implementation.mpy & 0xff
    else:
        res['mpy_file_version'] = 0

    try:
        import pimoroni
        res['mpy_variant'] = 'Pimoroni Pico'
        try:
            import version
            res['mpy_variant_info'] = version.BUILD
            res['mpy_variant_version'] = version.BUILD.split('-')[2][1:]
        except ImportError:
            res['mpy_variant_info'] = ''
            res['mpy_variant_version'] = ''
    except ImportError:
        res['mpy_variant'] = ''
        res['mpy_variant_info'] = ''
        res['mpy_variant_version'] = ''

    res['mip'] = False
    res['upip'] = False
    try:
        import mip
        res['mip'] = True
    except ImportError:
        try:
            import upip
            res['upip'] = True
        except ImportError:
            pass

    try:
        import time
        res['epoch_year'] = time.gmtime(0)[0]
    except AttributeError:
        res['epoch_year'] = 2000

    return res

print(get_device_data())
del get_device_data
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))
        return ast.literal_eval(out.decode("utf-8"))

    def getBoardInformation(self):
        """
        Public method to get some information data of the connected board.

        @return dictionary containing the determined data
        @rtype dict
        @exception OSError raised to indicate an issue with the device
        """
        commands = [  # needs to be splitted for boards with low memory
            """def get_board_info():
    res = {}

    import gc
    gc.enable()
    gc.collect()
    mem_alloc = gc.mem_alloc()
    mem_free = gc.mem_free()
    mem_total = mem_alloc + mem_free
    res['mem_total_kb'] = mem_total / 1024.0
    res['mem_used_kb'] = mem_alloc / 1024.0
    res['mem_used_pc'] = mem_alloc / mem_total * 100.0
    res['mem_free_kb'] = mem_free / 1024.0
    res['mem_free_pc'] = mem_free / mem_total * 100.0
    del gc, mem_alloc, mem_free, mem_total

    return res

print(get_board_info())
del get_board_info
""",
            """def get_board_info():
    res = {}

    try:
        import os
        uname = os.uname()
        res['sysname'] = uname.sysname
        res['nodename'] = uname.nodename
        res['release'] = uname.release
        res['version'] = uname.version
        res['machine'] = uname.machine
    except AttributeError:
        import sys
        res['sysname'] = sys.platform
        res['nodename'] = sys.platform
        res['release'] = '.'.join(str(v) for v in sys.implementation.version)
        res['version'] = sys.version.split(';', 1)[-1].strip()
        res['machine'] = sys.implementation._machine

    return res

print(get_board_info())
del get_board_info
""",
            """def get_board_info():
    res = {}

    import sys
    res['py_platform'] = sys.platform
    res['py_version'] = sys.version

    try:
        res['mpy_name'] = sys.implementation.name
    except AttributeError:
        res['mpy_name'] = 'unknown'
    try:
        res['mpy_version'] = '.'.join((str(i) for i in sys.implementation.version))
    except AttributeError:
        res['mpy_version'] = 'unknown'
    try:
        import pimoroni
        res['mpy_variant'] = 'Pimoroni Pico'
        try:
            import version
            res['mpy_variant_info'] = version.BUILD
            res['mpy_variant_version'] = version.BUILD.split('-')[2][1:]
        except ImportError:
            res['mpy_variant_info'] = ''
            res['mpy_variant_version'] = ''
    except ImportError:
        res['mpy_variant'] = ''
        res['mpy_variant_info'] = ''
        res['mpy_variant_version'] = ''

    return res

print(get_board_info())
del get_board_info
""",
            """def get_board_info():
    res = {}

    try:
        import os
        stat_ = os.statvfs('/flash')
        res['flash_info_available'] = True
        res['flash_total_kb'] = stat_[2] * stat_[0] / 1024.0
        res['flash_free_kb'] = stat_[3] * stat_[0] / 1024.0
        res['flash_used_kb'] = res['flash_total_kb'] - res['flash_free_kb']
        res['flash_free_pc'] = res['flash_free_kb'] / res['flash_total_kb'] * 100.0
        res['flash_used_pc'] = res['flash_used_kb'] / res['flash_total_kb'] * 100.0
    except (AttributeError, OSError):
        res['flash_info_available'] = False

    return res

print(get_board_info())
del get_board_info
""",
            """def get_board_info():
    res = {}

    try:
        import machine as mc
        if isinstance(mc.freq(), tuple):
            res['mc_frequency_mhz'] = mc.freq()[0] / 1000000.0
        else:
           res['mc_frequency_mhz'] = mc.freq() / 1000000.0
        res['mc_id'] = mc.unique_id()
    except ImportError:
        try:
            import microcontroller as mc
            res['mc_frequency_mhz'] = mc.cpu.frequency / 1000000.0
            res['mc_temp_c'] = mc.cpu.temperature
            res['mc_id'] = mc.cpu.uid
        except ImportError:
            res['mc_frequency'] = None
            res['mc_temp'] = None
    if 'mc_id' in res:
        res['mc_id'] = ':'.join('{0:02X}'.format(x) for x in res['mc_id'])

    return res

print(get_board_info())
del get_board_info
""",
            """def get_board_info():
    res = {}

    try:
        import ulab
        res['ulab'] = ulab.__version__
    except ImportError:
        res['ulab'] = None

    return res

print(get_board_info())
del get_board_info
""",
        ]
        res = {}
        for command in commands:
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))
            res.update(ast.literal_eval(out.decode("utf-8")))
        return res

    def getModules(self):
        """
        Public method to show a list of modules built into the firmware.

        @return list of builtin modules
        @rtype list of str
        @exception OSError raised to indicate an issue with the device
        """
        commands = ["help('modules')"]
        out, err = self.executeCommands(commands, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        modules = []
        for line in out.decode("utf-8").splitlines()[:-1]:
            modules.extend(line.split())
        return modules

    ##################################################################
    ## time related methods below
    ##################################################################

    def getTime(self):
        """
        Public method to get the current time of the device.

        @return time of the device
        @rtype str
        @exception OSError raised to indicate an issue with the device
        """
        command = """
def get_time():
    try:
        import rtc
        print(
            '{0:04d}-{1:02d}-{2:02d} {3:02d}:{4:02d}:{5:02d}'
            .format(*rtc.RTC().datetime[:6])
        )
    except:
        import time
        try:
            print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        except AttributeError:
            tm = time.localtime()
            print(
                '{0:04d}-{1:02d}-{2:02d} {3:02d}:{4:02d}:{5:02d}'
                .format(tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])
            )

get_time()
del get_time
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            if b"NotImplementedError" in err:
                return "&lt;unsupported&gt; &lt;unsupported&gt;"
            raise OSError(self._shortError(err))
        return out.decode("utf-8").strip()

    def _getSetTimeCode(self):
        """
        Protected method to get the device code to set the time.

        Note: This method must be implemented in the various device specific
        subclasses.

        @return code to be executed on the connected device to set the time
        @rtype str
        """
        # rtc_time[0] - year    4 digit
        # rtc_time[1] - month   1..12
        # rtc_time[2] - day     1..31
        # rtc_time[3] - weekday 1..7 1=Monday
        # rtc_time[4] - hour    0..23
        # rtc_time[5] - minute  0..59
        # rtc_time[6] - second  0..59
        # rtc_time[7] - yearday 1..366
        # rtc_time[8] - isdst   0, 1, or -1
        if self.hasCircuitPython():
            # CircuitPython is handled here in order to not duplicate the code in all
            # specific boards able to be flashed with CircuitPython or MicroPython
            return """
def set_time(rtc_time):
    import rtc
    import time
    clock = rtc.RTC()
    clock_time = rtc_time[:3] + rtc_time[4:7] + (rtc_time[3], rtc_time[7], rtc_time[8])
    clock.datetime = time.struct_time(clock_time)
"""
        else:
            return ""

    def syncTime(self, _deviceType, hasCPy=False):  # noqa: U100
        """
        Public method to set the time of the connected device to the local
        computer's time.

        @param _deviceType type of board to sync time to (unused)
        @type str
        @param hasCPy flag indicating that the device has CircuitPython loadede
            (defaults to False) (unused)
        @type bool
        @exception OSError raised to indicate an issue with the device
        """
        setTimeCode = self._getSetTimeCode()
        if setTimeCode:
            now = time.localtime(time.time())
            command = """{0}
set_time({1})
del set_time
""".format(
                setTimeCode,
                (
                    now.tm_year,
                    now.tm_mon,
                    now.tm_mday,
                    now.tm_wday,
                    now.tm_hour,
                    now.tm_min,
                    now.tm_sec,
                    now.tm_yday,
                    now.tm_isdst,
                ),
            )
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))

    ##################################################################
    ## Methods below implement package management related methods
    ##################################################################

    def upipInstall(self, packages):
        """
        Public method to install packages using 'upip'.

        @param packages list of package names
        @type list of str
        @return tuple containing the command output and errors
        @rtype  tuple of (str, str)
        """
        command = """
def upip_install():
    import upip
    upip.install({0})

upip_install()
del upip_install
""".format(
            repr(packages)
        )
        return self.executeCommands(command, mode=self._submitMode, timeout=60000)

    def mipInstall(self, package, index=None, target=None, version=None, mpy=True):
        """
        Public method to install packages using 'mip'.

        @param package package name
        @type str
        @param index URL of the package index to be used (defaults to None)
        @type str (optional)
        @param target target directory on the device (defaults to None)
        @type str (optional)
        @param version package version (defaults to None)
        @type str (optional)
        @param mpy flag indicating to install as '.mpy' file (defaults to True)
        @type bool (optional)
        @return tuple containing the command output and errors
        @rtype tuple of (str, str)
        """
        parameterStr = repr(package)
        if index:
            parameterStr += ", index={0}".format(repr(index))
        if target:
            parameterStr += ", target={0}".format(repr(target))
        if version:
            parameterStr += ", version={0}".format(repr(version))
        if not mpy:
            parameterStr += ", mpy=False"

        command = """
def mip_install():
    import mip
    mip.install({0})

mip_install()
del mip_install
""".format(
            parameterStr
        )
        return self.executeCommands(command, mode=self._submitMode, timeout=60000)

    def getLibPaths(self):
        """
        Public method to get the list of library paths contained in 'sys.path'.

        @return list of library paths
        @rtype list of str
        @exception OSError raised to indicate an issue with the device
        """
        command = """
def lib_paths():
    import sys
    print([p for p in sys.path if p.endswith('/lib')])

lib_paths()
del lib_paths
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        return ast.literal_eval(out.decode("utf-8"))

    ##################################################################
    ## Methods below implement general network related methods
    ##################################################################

    def isNetworkConnected(self):
        """
        Public method to check, if the network interface (WiFi or Ethernet) is
        connected.

        @return flag indicating the network connection state
        @rtype bool
        """
        if self._deviceData:
            # Ask the device if that is true.
            if self._deviceData["ethernet"]:
                # It is an ethernet capable device.
                return self.isLanConnected()
            elif self._deviceData["wifi"]:
                # It is a WiFi capable device.
                return self.isWifiClientConnected()

        return False

    ##################################################################
    ## Methods below implement WiFi related methods
    ##################################################################

    def hasWifi(self):
        """
        Public method to check the availability of WiFi.

        @return tuple containing a flag indicating the availability of WiFi
            and the WiFi type (picow or pimoroni)
        @rtype tuple of (bool, str)
        """
        return False, ""

    def hasWifiCountry(self):
        """
        Public method to check, if the device (potentially) has support to set the
        WiFi country.

        @return flag indicating the support of WiFi country
        @rtype bool
        """
        return False

    def addDeviceWifiEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        pass

    def getWifiData(self):
        """
        Public method to get data related to the current WiFi status.

        @return tuple of three dictionaries containing the WiFi status data
            for the WiFi client, access point and overall data
        @rtype tuple of (dict, dict, dict)
        """
        return {}, {}, {}

    def connectWifi(self, ssid, password, hostname):  # noqa: U100
        """
        Public method to connect a device to a WiFi network.

        @param ssid name (SSID) of the WiFi network (unused)
        @type str
        @param password password needed to connect (unused)
        @type str
        @param hostname host name of the device (unused)
        @type str
        @return tuple containing the connection status and an error string
        @rtype tuple of (bool, str)
        """
        return False, self.tr("Operation not supported.")

    def disconnectWifi(self):
        """
        Public method to disconnect a device from the WiFi network.

        @return tuple containing a flag indicating success and an error string
        @rtype tuple of (bool, str)
        """
        return True, ""

    def isWifiClientConnected(self):
        """
        Public method to check the WiFi connection status as client.

        @return flag indicating the WiFi connection status
        @rtype bool
        """
        return False

    def isWifiApConnected(self):
        """
        Public method to check the WiFi connection status as access point.

        @return flag indicating the WiFi connection status
        @rtype bool
        """
        return False

    def writeCredentials(self, ssid, password, hostname, country):  # noqa: U100
        """
        Public method to write the given credentials to the connected device and modify
        the start script to connect automatically.

        @param ssid SSID of the network to connect to (unused)
        @type str
        @param password password needed to authenticate (unused)
        @type str
        @param hostname host name of the device (unused)
        @type str
        @param country WiFi country code (unused)
        @type str
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return False, ""

    def removeCredentials(self):
        """
        Public method to remove the saved credentials from the connected device.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return False, ""

    def checkInternet(self):
        """
        Public method to check, if the internet can be reached.

        @return tuple containing a flag indicating reachability and an error string
        @rtype tuple of (bool, str)
        """
        return False, ""

    def scanNetworks(self):
        """
        Public method to scan for available WiFi networks.

        @return tuple containing the list of available networks as a tuple of 'Name',
            'MAC-Address', 'channel', 'RSSI' and 'security' and an error string
        @rtype tuple of (list of tuple of (str, str, int, int, str), str)
        """
        return [], ""

    def deactivateInterface(self, interface):  # noqa: U100
        """
        Public method to deactivate a given WiFi interface of the connected device.

        @param interface designation of the interface to be deactivated (one of 'AP'
            or 'STA') (unused)
        @type str
        @return tuple containg a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return True, ""

    def startAccessPoint(
        self,
        ssid,  # noqa: U100
        security=None,  # noqa: U100
        password=None,  # noqa: U100
        hostname=None,  # noqa: U100
        ifconfig=None,  # noqa: U100
    ):
        """
        Public method to start the access point interface.

        @param ssid SSID of the access point (unused)
        @type str
        @param security security method (defaults to None) (unused)
        @type int (optional)
        @param password password (defaults to None) (unused)
        @type str (optional)
        @param hostname host name of the device (defaults to None) (unused)
        @type str (optional)
        @param ifconfig IPv4 configuration for the access point if not default
            (IPv4 address, netmask, gateway address, DNS server address) (unused)
        @type tuple of (str, str, str, str)
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return False, ""

    def stopAccessPoint(self):
        """
        Public method to stop the access point interface.

        @return tuple containg a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return True, ""

    def getConnectedClients(self):
        """
        Public method to get a list of connected clients.

        @return a tuple containing a list of tuples containing the client MAC-Address
            and the RSSI (if supported and available) and an error message
        @rtype tuple of ([(bytes, int)], str)
        """
        return [], ""

    def enableWebrepl(self, password):  # noqa: U100
        """
        Public method to write the given WebREPL password to the connected device and
        modify the start script to start the WebREPL server.

        @param password password needed to authenticate (unused)
        @type str
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return False, ""

    def disableWebrepl(self):
        """
        Public method to write the given WebREPL password to the connected device and
        modify the start script to start the WebREPL server.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return False, ""

    ##################################################################
    ## Methods below implement Ethernet related methods
    ##################################################################

    def hasEthernet(self):
        """
        Public method to check the availability of Ethernet.

        @return tuple containing a flag indicating the availability of Ethernet
            and the Ethernet type
        @rtype tuple of (bool, str)
        """
        return False, ""

    def addDeviceEthernetEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        pass

    def getEthernetStatus(self):
        """
        Public method to get Ethernet status data of the connected board.

        @return list of tuples containing the translated status data label and
            the associated value
        @rtype list of tuples of (str, str)
        """
        return []

    def connectToLan(self, config, hostname):  # noqa: U100
        """
        Public method to connect the connected device to the LAN.

        @param config configuration for the connection (either the string 'dhcp'
            for a dynamic address or a tuple of four strings with the IPv4 parameters.
            (unused)
        @type str or tuple of (str, str, str, str)
        @param hostname host name of the device (unused)
        @type str
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return False, ""

    def disconnectFromLan(self):
        """
        Public method  to disconnect from the LAN.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return True, ""

    def isLanConnected(self):
        """
        Public method to check the LAN connection status.

        @return flag indicating that the device is connected to the LAN
        @rtype bool
        """
        return False

    def checkInternetViaLan(self):
        """
        Public method to check, if the internet can be reached (LAN variant).

        @return tuple containing a flag indicating reachability and an error string
        @rtype tuple of (bool, str)
        """
        return False, ""

    def deactivateEthernet(self):
        """
        Public method to deactivate the Ethernet interface of the connected device.

        @return tuple containg a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return True, ""

    def writeLanAutoConnect(self, config, hostname):  # noqa: U100
        """
        Public method to generate a script and associated configuration to connect the
        device to the LAN during boot time.

        @param config configuration for the connection (either the string 'dhcp'
            for a dynamic address or a tuple of four strings with the IPv4 parameters.
            (unused)
        @type str or tuple of (str, str, str, str)
        @param hostname host name of the device (unused)
        @type str
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return False, ""

    def removeLanAutoConnect(self):
        """
        Public method to remove the saved IPv4 parameters from the connected device.

        Note: This disables the LAN auto-connect feature.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return False, ""

    ##################################################################
    ## Methods below implement Bluetooth related methods
    ##################################################################

    def hasBluetooth(self):
        """
        Public method to check the availability of Bluetooth.

        @return flag indicating the availability of Bluetooth
        @rtype bool
        """
        return False

    def addDeviceBluetoothEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        pass

    def getBluetoothStatus(self):
        """
        Public method to get Bluetooth status data of the connected board.

        @return list of tuples containing the translated status data label and
            the associated value
        @rtype list of tuples of (str, str)
        """
        return []

    def activateBluetoothInterface(self):
        """
        Public method to activate the Bluetooth interface.

        @return flag indicating the new state of the Bluetooth interface
        @rtype bool
        """
        return False

    def deactivateBluetoothInterface(self):
        """
        Public method to deactivate the Bluetooth interface.

        @return flag indicating the new state of the Bluetooth interface
        @rtype bool
        """
        return False

    def getDeviceScan(self, timeout=10):  # noqa: U100
        """
        Public method to perform a Bluetooth device scan.

        @param timeout duration of the device scan in seconds (defaults
            to 10) (unused)
        @type int (optional)
        @return tuple containing a dictionary with the scan results and
            an error string
        @rtype tuple of (dict, str)
        """
        return {}, ""

    ##################################################################
    ## Methods below implement NTP related methods
    ##################################################################

    def hasNetworkTime(self):
        """
        Public method to check the availability of network time functions.

        @return flag indicating the availability of network time functions
        @rtype bool
        """
        return False

    def setNetworkTime(
        self, server="pool.ntp.org", tzOffset=0, timeout=10  # noqa: U100
    ):
        """
        Public method to set the time to the network time retrieved from an
        NTP server.

        @param server name of the NTP server to get the network time from
            (defaults to "0.pool.ntp.org") (unused)
        @type str (optional)
        @param tzOffset offset with respect to UTC (defaults to 0) (unused)
        @type int (optional)
        @param timeout maximum time to wait for a server response in seconds
            (defaults to 10) (unused)
        @type int
        @return tuple containing a flag indicating success and an error string
        @rtype tuple of (bool, str)
        """
        return False, ""

    ##################################################################
    ## Methods below implement some utility methods
    ##################################################################

    def bool2str(self, val, capitalized=True):
        """
        Public method to generate a yes/no string given a truth value.

        @param val truth value to be converted
        @type bool
        @param capitalized flag indicating a capitalized variant
        @type bool
        @return string with 'yes' or 'no'
        @rtype str
        """
        if capitalized:
            return self.tr("Yes") if val else self.tr("No")
        else:
            return self.tr("yes") if val else self.tr("no")


#
# eflag: noqa = M613
