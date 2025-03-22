# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class representing the session JSON file.
"""

import contextlib
import json
import time

from PyQt6.QtCore import QObject, Qt

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverridenCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities


class SessionFile(QObject):
    """
    Class representing the session JSON file.
    """

    def __init__(self, isGlobal: bool, parent: QObject = None):
        """
        Constructor

        @param isGlobal flag indicating a file for a global session
        @type bool
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.__isGlobal = isGlobal

    def writeFile(self, filename: str, withServer: bool = True) -> bool:
        """
        Public method to write the session data to a session JSON file.

        @param filename name of the session file
        @type str
        @param withServer flag indicating to save the current server connection
            (defaults to True)
        @type bool (optional)
        @return flag indicating a successful write
        @rtype bool
        """
        # get references to objects we need
        serverInterface = ericApp().getObject("EricServer")
        fsInterface = serverInterface.getServiceInterface("FileSystem")

        project = ericApp().getObject("Project")
        projectBrowser = ericApp().getObject("ProjectBrowser")
        multiProject = ericApp().getObject("MultiProject")
        vm = ericApp().getObject("ViewManager")
        dbg = ericApp().getObject("DebugUI")
        dbs = ericApp().getObject("DebugServer")

        # prepare the session data dictionary
        # step 0: header
        sessionDict = {"header": {}}
        if not self.__isGlobal:
            sessionDict["header"]["comment"] = (
                "eric session file for project {0}".format(project.getProjectName())
            )
        sessionDict["header"][
            "warning"
        ] = "This file was generated automatically, do not edit."

        if Preferences.getProject("TimestampFile") or self.__isGlobal:
            sessionDict["header"]["saved"] = time.strftime("%Y-%m-%d, %H:%M:%S")

        # step 1: eric-ide Server Connection
        # ==================================
        if withServer:
            sessionDict["RemoteServer"] = (
                serverInterface.getHost() if serverInterface.isServerConnected() else ""
            )

        # step 2: open multi project and project for global session
        # =========================================================
        sessionDict["MultiProject"] = ""
        sessionDict["Project"] = ""
        if self.__isGlobal:
            if multiProject.isOpen():
                sessionDict["MultiProject"] = multiProject.getMultiProjectFile()
            if project.isOpen():
                sessionDict["Project"] = project.getProjectFile()

        # step 3: all open (project) filenames and the active editor
        # ==========================================================
        if vm.canSplit():
            sessionDict["ViewManagerSplits"] = {
                "Count": vm.splitCount(),
                "Orientation": vm.getSplitOrientation().value,
            }
        else:
            sessionDict["ViewManagerSplits"] = {
                "Count": 0,
                "Orientation": 1,
            }

        editorsDict = {}  # remember editors by file name to detect clones
        sessionDict["Editors"] = []
        allOpenEditorLists = vm.getOpenEditorsForSession()
        for splitIndex, openEditorList in enumerate(allOpenEditorLists):
            for editorIndex, editor in enumerate(openEditorList):
                fileName = editor.getFileName()
                if self.__isGlobal or project.isProjectFile(fileName):
                    if fileName in editorsDict:
                        isClone = editorsDict[fileName].isClone(editor)
                    else:
                        isClone = False
                        editorsDict[fileName] = editor
                    editorDict = {
                        "Filename": fileName,
                        "Cursor": editor.getCursorPosition(),
                        "Folds": editor.contractedFolds(),
                        "Zoom": editor.getZoom(),
                        "Clone": isClone,
                        "Splitindex": splitIndex,
                        "Editorindex": editorIndex,
                    }
                    sessionDict["Editors"].append(editorDict)

        aw = vm.getActiveName()
        sessionDict["ActiveWindow"] = {}
        if aw and (self.__isGlobal or project.isProjectFile(aw)):
            ed = vm.getOpenEditor(aw)
            sessionDict["ActiveWindow"] = {
                "Filename": aw,
                "Cursor": ed.getCursorPosition(),
            }

        # step 4: breakpoints
        # ===================
        allBreaks = Preferences.getProject("SessionAllBreakpoints")
        projectFiles = project.getSources(True)
        bpModel = dbs.getBreakPointModel()
        if self.__isGlobal or allBreaks:
            sessionDict["Breakpoints"] = bpModel.getAllBreakpoints()
        else:
            sessionDict["Breakpoints"] = [
                bp for bp in bpModel.getAllBreakpoints() if bp[0] in projectFiles
            ]

        # step 5: watch expressions
        # =========================
        wpModel = dbs.getWatchPointModel()
        sessionDict["Watchpoints"] = wpModel.getAllWatchpoints()

        # step 6: debug info
        # ==================
        if self.__isGlobal:
            if len(dbg.scriptsHistory):
                dbgScriptName = dbg.scriptsHistory[0]
            else:
                dbgScriptName = ""
            if len(dbg.argvHistory):
                dbgCmdline = dbg.argvHistory[0]
            else:
                dbgCmdline = ""
            if len(dbg.wdHistory):
                dbgWd = dbg.wdHistory[0]
            else:
                dbgWd = ""
            if len(dbg.envHistory):
                dbgEnv = dbg.envHistory[0]
            else:
                dbgEnv = ""
            if len(dbg.multiprocessNoDebugHistory):
                dbgMultiprocessNoDebug = dbg.multiprocessNoDebugHistory[0]
            else:
                dbgMultiprocessNoDebug = ""
            sessionDict["DebugInfo"] = {
                "VirtualEnv": dbg.lastUsedVenvName,
                "ScriptName": dbgScriptName,
                "CommandLine": dbgCmdline,
                "WorkingDirectory": dbgWd,
                "Environment": dbgEnv,
                "Exceptions": dbg.excList,
                "IgnoredExceptions": dbg.excIgnoreList,
                "AutoClearShell": dbg.autoClearShell,
                "TracePython": dbg.tracePython,
                "AutoContinue": dbg.autoContinue,
                "ReportAllExceptions": dbg.reportAllExceptions,
                "EnableMultiprocess": dbg.enableMultiprocess,
                "MultiprocessNoDebug": dbgMultiprocessNoDebug,
                "GlobalConfigOverride": dbg.overrideGlobalConfig,
            }
        else:
            sessionDict["DebugInfo"] = {
                "VirtualEnv": project.dbgVirtualEnv,
                "ScriptName": "",
                "CommandLine": project.dbgCmdline,
                "WorkingDirectory": project.dbgWd,
                "Environment": project.dbgEnv,
                "Exceptions": project.dbgExcList,
                "IgnoredExceptions": project.dbgExcIgnoreList,
                "AutoClearShell": project.dbgAutoClearShell,
                "TracePython": project.dbgTracePython,
                "AutoContinue": project.dbgAutoContinue,
                "ReportAllExceptions": project.dbgReportAllExceptions,
                "EnableMultiprocess": project.dbgEnableMultiprocess,
                "MultiprocessNoDebug": project.dbgMultiprocessNoDebug,
                "GlobalConfigOverride": project.dbgGlobalConfigOverride,
            }

        # step 7: bookmarks
        # =================
        bookmarksList = []
        for fileName in editorsDict:
            if self.__isGlobal or project.isProjectFile(fileName):
                editor = editorsDict[fileName]
                bookmarks = editor.getBookmarks()
                if bookmarks:
                    bookmarksList.append(
                        {
                            "Filename": fileName,
                            "Lines": bookmarks,
                        }
                    )
        sessionDict["Bookmarks"] = bookmarksList

        # step 8: state of the various project browsers
        # =============================================
        browsersList = []
        for browserName in projectBrowser.getProjectBrowserNames():
            expandedItems = projectBrowser.getProjectBrowser(
                browserName
            ).getExpandedItemNames()
            if expandedItems:
                browsersList.append(
                    {
                        "Name": browserName,
                        "ExpandedItems": expandedItems,
                    }
                )
        sessionDict["ProjectBrowserStates"] = browsersList

        try:
            jsonString = json.dumps(sessionDict, indent=2) + "\n"
            if FileSystemUtilities.isRemoteFileName(filename):
                title = self.tr("Save Remote Session")
                fsInterface.writeFile(filename, jsonString.encode("utf-8"))
            else:
                title = self.tr("Save Session")
                with open(filename, "w") as f:
                    f.write(jsonString)
        except (OSError, TypeError) as err:
            with EricOverridenCursor():
                EricMessageBox.critical(
                    None,
                    title,
                    self.tr(
                        "<p>The session file <b>{0}</b> could not be"
                        " written.</p><p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return False

        return True

    def readFile(self, filename: str) -> bool:
        """
        Public method to read the session data from a session JSON file.

        @param filename name of the project file
        @type str
        @return flag indicating a successful read
        @rtype bool
        """
        fsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        try:
            if FileSystemUtilities.isRemoteFileName(filename):
                title = self.tr("Read Remote Session")
                jsonString = fsInterface.readFile(filename).decode("utf-8")
            else:
                title = self.tr("Read Session")
                with open(filename, "r") as f:
                    jsonString = f.read()
            sessionDict = json.loads(jsonString)
        except (OSError, json.JSONDecodeError) as err:
            EricMessageBox.critical(
                None,
                title,
                self.tr(
                    "<p>The session file <b>{0}</b> could not be read.</p>"
                    "<p>Reason: {1}</p>"
                ).format(filename, str(err)),
            )
            return False

        # get references to objects we need
        project = ericApp().getObject("Project")
        projectBrowser = ericApp().getObject("ProjectBrowser")
        multiProject = ericApp().getObject("MultiProject")
        vm = ericApp().getObject("ViewManager")
        dbg = ericApp().getObject("DebugUI")
        dbs = ericApp().getObject("DebugServer")

        serverInterface = ericApp().getObject("EricServer")

        # step 1: eric-ide Server Connection
        # ==================================
        with contextlib.suppress(KeyError):
            if sessionDict["RemoteServer"]:
                hostname, port = serverInterface.parseHost(sessionDict["RemoteServer"])
                serverInterface.connectToServer(hostname, port)

        # step 2: multi project and project
        # =================================
        if sessionDict["MultiProject"]:
            multiProject.openMultiProject(sessionDict["MultiProject"], False)
        if sessionDict["Project"]:
            project.openProject(sessionDict["Project"], False)

        # step 3: (project) filenames and the active editor
        # =================================================
        vm.setSplitOrientation(
            Qt.Orientation(sessionDict["ViewManagerSplits"]["Orientation"])
        )
        vm.setSplitCount(sessionDict["ViewManagerSplits"]["Count"])

        editorsDict = {}
        for editorDict in sessionDict["Editors"]:
            if editorDict["Clone"] and editorDict["Filename"] in editorsDict:
                editor = editorsDict[editorDict["Filename"]]
                ed = vm.newEditorView(
                    editorDict["Filename"],
                    editor,
                    editor.getFileType(),
                    indexes=(editorDict["Splitindex"], editorDict["Editorindex"]),
                )
            else:
                ed = vm.openSourceFile(
                    editorDict["Filename"],
                    indexes=(editorDict["Splitindex"], editorDict["Editorindex"]),
                )
                editorsDict[editorDict["Filename"]] = ed
            if ed is not None:
                ed.zoomTo(editorDict["Zoom"])
                if editorDict["Folds"]:
                    ed.recolor()
                    ed.setContractedFolds(editorDict["Folds"])
                ed.setCursorPosition(*editorDict["Cursor"])

        # step 4: breakpoints
        # ===================
        bpModel = dbs.getBreakPointModel()
        bpModel.addBreakPoints(sessionDict["Breakpoints"])

        # step 5: watch expressions
        # =========================
        wpModel = dbs.getWatchPointModel()
        wpModel.addWatchPoints(sessionDict["Watchpoints"])

        # step 6: debug info
        # ==================
        debugInfoDict = sessionDict["DebugInfo"]

        # adjust for newer session types
        if "GlobalConfigOverride" not in debugInfoDict:
            debugInfoDict["GlobalConfigOverride"] = {
                "enable": False,
                "redirect": True,
            }

        dbg.lastUsedVenvName = debugInfoDict["VirtualEnv"]
        dbg.setScriptsHistory(debugInfoDict.get("ScriptName", ""))
        dbg.setArgvHistory(debugInfoDict["CommandLine"])
        dbg.setWdHistory(debugInfoDict["WorkingDirectory"])
        dbg.setEnvHistory(debugInfoDict["Environment"])
        dbg.setExcList(debugInfoDict["Exceptions"])
        dbg.setExcIgnoreList(debugInfoDict["IgnoredExceptions"])
        dbg.setAutoClearShell(debugInfoDict["AutoClearShell"])
        dbg.setTracePython(debugInfoDict["TracePython"])
        dbg.setAutoContinue(debugInfoDict["AutoContinue"])
        dbg.setExceptionReporting(debugInfoDict.get("ReportAllExceptions", False))
        dbg.setEnableMultiprocess(debugInfoDict["EnableMultiprocess"])
        dbg.setMultiprocessNoDebugHistory(debugInfoDict["MultiprocessNoDebug"])
        dbg.setEnableGlobalConfigOverride(debugInfoDict["GlobalConfigOverride"])
        if not self.__isGlobal:
            project.setDbgInfo(
                debugInfoDict["VirtualEnv"],
                debugInfoDict["CommandLine"],
                debugInfoDict["WorkingDirectory"],
                debugInfoDict["Environment"],
                debugInfoDict["Exceptions"],
                debugInfoDict["IgnoredExceptions"],
                debugInfoDict["AutoClearShell"],
                debugInfoDict["TracePython"],
                debugInfoDict["AutoContinue"],
                debugInfoDict.get("ReportAllExceptions", False),
                debugInfoDict["EnableMultiprocess"],
                debugInfoDict["MultiprocessNoDebug"],
                debugInfoDict["GlobalConfigOverride"],
            )

        # step 7: bookmarks
        # =================
        for bookmark in sessionDict["Bookmarks"]:
            editor = vm.getOpenEditor(bookmark["Filename"])
            if editor is not None:
                for lineno in bookmark["Lines"]:
                    editor.toggleBookmark(lineno)

        # step 8: state of the various project browsers
        # =============================================
        for browserState in sessionDict["ProjectBrowserStates"]:
            browser = projectBrowser.getProjectBrowser(browserState["Name"])
            if browser is not None:
                browser.expandItemsByName(browserState["ExpandedItems"])

        # step 9: active window
        # =====================
        if sessionDict["ActiveWindow"]:
            vm.openFiles(sessionDict["ActiveWindow"]["Filename"])
            ed = vm.getOpenEditor(sessionDict["ActiveWindow"]["Filename"])
            if ed is not None:
                ed.setCursorPosition(*sessionDict["ActiveWindow"]["Cursor"])
                ed.ensureCursorVisible()

        return True
