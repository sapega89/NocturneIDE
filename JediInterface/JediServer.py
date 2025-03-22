# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the autocompletion interface to jedi.
"""

import contextlib
import os
import uuid

from PyQt6.QtCore import QCoreApplication, QThread, QTimer, pyqtSlot
from PyQt6.QtWidgets import QDialog, QInputDialog, QLineEdit

from eric7 import Preferences
from eric7.EricNetwork.EricJsonServer import EricJsonServer
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.QScintilla.Editor import EditorIconId, ReferenceItem
from eric7.SystemUtilities import FileSystemUtilities, PythonUtilities

from .RefactoringPreviewDialog import RefactoringPreviewDialog


class JediServer(EricJsonServer):
    """
    Class implementing the interface to the jedi library.
    """

    IdProject = "Project"

    PictureIDs = {
        "class": "?{0}".format(EditorIconId.Class),
        "_class": "?{0}".format(EditorIconId.ClassProtected),
        "__class": "?{0}".format(EditorIconId.ClassPrivate),
        "instance": "?{0}".format(EditorIconId.Class),
        "_instance": "?{0}".format(EditorIconId.ClassProtected),
        "__instance": "?{0}".format(EditorIconId.ClassPrivate),
        "function": "?{0}".format(EditorIconId.Method),
        "_function": "?{0}".format(EditorIconId.MethodProtected),
        "__function": "?{0}".format(EditorIconId.MethodPrivate),
        "module": "?{0}".format(EditorIconId.Module),
        "_module": "?{0}".format(EditorIconId.Module),
        "__module": "?{0}".format(EditorIconId.Module),
        "param": "?{0}".format(EditorIconId.Attribute),
        "_param": "?{0}".format(EditorIconId.AttributeProtected),
        "__param": "?{0}".format(EditorIconId.AttributePrivate),
        "statement": "?{0}".format(EditorIconId.Attribute),
        "_statement": "?{0}".format(EditorIconId.AttributeProtected),
        "__statement": "?{0}".format(EditorIconId.AttributePrivate),
        "import": "",
        "None": "",
    }

    def __init__(self, viewManager, project, ui):
        """
        Constructor

        @param viewManager reference to the viewmanager object
        @type ViewManager
        @param project reference to the project object
        @type Project
        @param ui reference to the user interface
        @type UserInterface
        """
        super().__init__(
            name="JediServer",
            interface=Preferences.getDebugger("NetworkInterface"),
            multiplex=True,
            parent=ui,
        )

        self.__ui = ui
        self.__vm = viewManager
        self.__ericProject = project

        self.__editorLanguageMapping = {}

        self.__documentationViewer = None

        # attributes to store the resuls of the client side
        self.__completions = None
        self.__calltips = None

        self.__methodMapping = {
            "CompletionsResult": self.__processCompletionsResult,
            "CallTipsResult": self.__processCallTipsResult,
            "DocumentationResult": self.__processDocumentationResult,
            "HoverHelpResult": self.__processHoverHelpResult,
            "GotoDefinitionResult": self.__processGotoDefinitionResult,
            "GotoReferencesResult": self.__processGotoReferencesResult,
            "RefactoringDiff": self.__showRefactoringDiff,
            "RefactoringApplyResult": self.__checkRefactoringResult,
            "ClientException": self.__processClientException,
        }

        # temporary store for editor references indexed by UUID
        self.__editors = {}

        # Python 3
        self.__ensureActive("Python3")

    def __updateEditorLanguageMapping(self):
        """
        Private method to update the editor language to connection mapping.
        """
        self.__editorLanguageMapping = {}
        for name in self.connectionNames():
            if name == "Python3":
                self.__editorLanguageMapping.update(
                    {
                        "Python3": "Python3",
                        "MicroPython": "Python3",
                        "Pygments|Python": "Python3",
                        "Pygments|Python 2.x": "Python3",
                        "Cython": "Python3",
                    }
                )

    def isSupportedLanguage(self, language):
        """
        Public method to check, if the given language is supported.

        @param language editor programming language to check
        @type str
        @return flag indicating the support status
        @rtype bool
        """
        return language in self.__editorLanguageMapping

    def __idString(self, editor):
        """
        Private method to determine the ID string for the back-end.

        @param editor reference to the editor to determine the ID string for
        @type Editor
        @return ID string
        @rtype str
        """
        idString = ""

        language = editor.getLanguage()
        if (
            self.__ericProject.isOpen()
            and self.__ericProject.getProjectLanguage() == language
        ):
            filename = editor.getFileName()
            if self.__ericProject.isProjectCategory(filename, "SOURCES"):
                idString = JediServer.IdProject

        if not idString and language in self.__editorLanguageMapping:
            idString = self.__editorLanguageMapping[language]

        return idString

    def __prepareData(self, editor):
        """
        Private method to gather data about current cursor position.

        @param editor reference to the editor object, that called this method
        @type Editor
        @return tuple of filename, line, index, source
        @rtype tuple (str, int, int, str)
        """
        filename = editor.getFileName()
        line, index = editor.getCursorPosition()
        line += 1  # jedi line numbers are 1 based
        source = editor.text()
        return filename, line, index, source

    def requestCompletions(self, editor, _context, acText):
        """
        Public method to request a list of possible completions.

        @param editor reference to the editor object, that called this method
        @type Editor
        @param _context flag indicating to autocomplete a context (unused)
        @type bool
        @param acText text to be completed
        @type str
        """
        if not Preferences.getJedi("JediCompletionsEnabled"):
            return

        idString = self.__idString(editor)
        if not idString:
            return

        filename, line, index, source = self.__prepareData(editor)
        fuzzy = Preferences.getJedi("JediFuzzyCompletionsEnabled")

        self.__ensureActive(idString)

        self.sendJson(
            "getCompletions",
            {
                "FileName": filename,
                "Source": source,
                "Line": line,
                "Index": index,
                "Fuzzy": fuzzy,
                "CompletionText": acText,
            },
            idString=idString,
        )

    def __processCompletionsResult(self, result):
        """
        Private method to process the completions sent by the client.

        @param result dictionary containing the result sent by the client
        @type dict
        """
        names = []
        for completion in result["Completions"]:
            name = completion["Name"]
            context = completion["FullName"]
            if context:
                if context.endswith(".{0}".format(name)):
                    context = context.rsplit(".", 1)[0]
                name = "{0} ({1})".format(name, context)

            name += JediServer.PictureIDs.get(completion["CompletionType"], "")
            names.append(name)

        if "Error" not in result:
            editor = self.__vm.getOpenEditor(result["FileName"])
            if editor is not None:
                editor.completionsListReady(names, result["CompletionText"])

    def getCallTips(self, editor, _pos, _commas):
        """
        Public method to calculate calltips.

        @param editor reference to the editor object, that called this method
        @type Editor
        @param _pos position in the text for the calltip (unused)
        @type int
        @param _commas minimum number of commas contained in the calltip (unused)
        @type int
        @return list of possible calltips
        @rtype list of str
        """
        if not Preferences.getJedi("JediCalltipsEnabled"):
            return []

        # reset the calltips buffer
        self.__calltips = None

        idString = self.__idString(editor)
        if not idString:
            return []

        filename, line, index, source = self.__prepareData(editor)

        self.__ensureActive(idString)
        self.sendJson(
            "getCallTips",
            {
                "FileName": filename,
                "Source": source,
                "Line": line,
                "Index": index,
            },
            idString=idString,
        )

        # emulate the synchronous behaviour
        timer = QTimer()
        timer.setSingleShot(True)
        timer.start(5000)  # 5s timeout
        while self.__calltips is None and timer.isActive():
            QCoreApplication.processEvents()
            QThread.msleep(100)

        return [] if self.__calltips is None else self.__calltips

    def __processCallTipsResult(self, result):
        """
        Private method to process the calltips sent by the client.

        @param result dictionary containing the result sent by the client
        @type dict
        """
        if "Error" in result:
            self.__calltips = []
        else:
            self.__calltips = result["CallTips"]

    def requestCodeDocumentation(self, editor):
        """
        Public method to request source code documentation for the given
        editor.

        @param editor reference to the editor to get source code documentation
            for
        @type Editor
        """
        if self.__documentationViewer is None:
            return

        idString = self.__idString(editor)

        if not idString:
            language = editor.getLanguage()
            warning = self.tr("Language <b>{0}</b> is not supported.").format(language)
            self.__documentationViewer.documentationReady(warning, isWarning=True)
            return

        filename, line, index, source = self.__prepareData(editor)
        sourceLines = source.splitlines()
        # Correct index if cursor is standing after an opening bracket
        if line > 0 and index > 0 and sourceLines[line - 1][index - 1] == "(":
            index -= 1

        self.__ensureActive(idString)
        self.sendJson(
            "getDocumentation",
            {
                "FileName": filename,
                "Source": source,
                "Line": line,
                "Index": index,
            },
            idString=idString,
        )

    def __processDocumentationResult(self, result):
        """
        Private method to process the documentation sent by the client.

        @param result dictionary containing the result sent by the client
        @type dict with keys 'name', 'module', 'argspec', 'docstring'
        """
        if self.__documentationViewer is None:
            return

        docu = None

        if "Error" not in result:
            docu = result["DocumentationDict"]
            docu["note"] = self.tr("Present in <i>{0}</i> module").format(
                docu["module"]
            )

        if docu is None:
            msg = self.tr("No documentation available.")
            self.__documentationViewer.documentationReady(msg, isDocWarning=True)
        else:
            self.__documentationViewer.documentationReady(docu)

    def gotoDefinition(self, editor):
        """
        Public slot to find the definition for the word at the cursor position
        and go to it.

        Note: This is executed upon a mouse click sequence.

        @param editor reference to the calling editor
        @type Editor
        """
        if not Preferences.getJedi("MouseClickEnabled"):
            return

        idString = self.__idString(editor)
        if not idString:
            return

        filename, line, index, source = self.__prepareData(editor)

        self.__ensureActive(idString)

        euuid = str(uuid.uuid4())
        self.__editors[euuid] = editor

        self.sendJson(
            "gotoDefinition",
            {
                "FileName": filename,
                "Source": source,
                "Line": line,
                "Index": index,
                "Uuid": euuid,
            },
            idString=idString,
        )

    def __processGotoDefinitionResult(self, result):
        """
        Private method callback for the goto definition result.

        @param result dictionary containing the result data
        @type dict
        """
        euuid = result["Uuid"]
        if "Error" not in result:
            # ignore errors silently
            location = result["GotoDefinitionDict"]
            if location:
                self.__vm.openSourceFile(
                    location["ModulePath"], location["Line"], addNext=True
                )
            else:
                ericApp().getObject("UserInterface").statusBar().showMessage(
                    self.tr("Jedi: No definition found"), 5000
                )

        with contextlib.suppress(KeyError):
            del self.__editors[euuid]

    def __processGotoReferencesResult(self, result):
        """
        Private method callback for the goto references result.

        @param result dictionary containing the result data
        @type dict
        """
        euuid = result["Uuid"]
        with contextlib.suppress(ImportError):
            if "Error" not in result:
                # ignore errors silently
                references = result["GotoReferencesList"]
                if references:
                    try:
                        editor = self.__editors[euuid]
                    except KeyError:
                        editor = None
                    if editor is not None:
                        referenceItemsList = [
                            ReferenceItem(
                                modulePath=ref["ModulePath"],
                                codeLine=ref["Code"],
                                line=ref["Line"],
                                column=ref["Column"],
                            )
                            for ref in references
                        ]
                        editor.gotoReferenceHandler(referenceItemsList)

        with contextlib.suppress(KeyError):
            del self.__editors[euuid]

    def hoverHelp(self, editor, line, index):
        """
        Public method to initiate the display of mouse hover help.

        @param editor reference to the calling editor
        @type Editor
        @param line line number (zero based)
        @type int
        @param index index within the line (zero based)
        @type int
        """
        idString = self.__idString(editor)
        if not idString:
            return

        filename = editor.getFileName()
        line += 1  # jedi line numbers are 1 based
        source = editor.text()

        self.__ensureActive(idString)

        euuid = str(uuid.uuid4())
        self.__editors[euuid] = editor

        self.sendJson(
            "hoverHelp",
            {
                "FileName": filename,
                "Source": source,
                "Line": line,
                "Index": index,
                "Uuid": euuid,
            },
            idString=idString,
        )

    def __processHoverHelpResult(self, result):
        """
        Private method callback for the goto definition result.

        @param result dictionary containing the result data
        @type dict
        """
        euuid = result["Uuid"]
        if "Error" not in result:
            # ignore errors silently
            helpText = result["HoverHelp"]
            if helpText:
                with contextlib.suppress(KeyError):
                    self.__editors[euuid].showMouseHoverHelpData(
                        result["Line"] - 1, result["Index"], helpText
                    )
            else:
                ericApp().getObject("UserInterface").statusBar().showMessage(
                    self.tr("Jedi: No mouse hover help found"), 5000
                )

        with contextlib.suppress(KeyError):
            del self.__editors[euuid]

    #######################################################################
    ## Refactoring methods below
    #######################################################################

    @pyqtSlot()
    def refactoringRenameVariable(self):
        """
        Public slot to rename the selected variable.
        """
        editor = self.__vm.activeWindow()
        if editor:
            idString = self.__idString(editor)
            if not idString:
                return

            newName, ok = QInputDialog.getText(
                None,
                self.tr("Rename Variable"),
                self.tr("Enter the new name for the variable:"),
                QLineEdit.EchoMode.Normal,
                editor.selectedText(),
            )

            if ok and newName and self.__vm.checkAllDirty():
                filename = editor.getFileName()
                line, index = editor.getCursorPosition()
                source = editor.text()

                self.__ensureActive(idString)

                euuid = str(uuid.uuid4())
                self.__editors[euuid] = editor

                self.sendJson(
                    "renameVariable",
                    {
                        "FileName": filename,
                        "Source": source,
                        "Line": line + 1,
                        "Index": index,
                        "Uuid": euuid,
                        "NewName": newName,
                    },
                    idString=idString,
                )

    @pyqtSlot()
    def refactoringExtractNewVariable(self):
        """
        Public slot to extract a statement to a new variable.
        """
        editor = self.__vm.activeWindow()
        if editor:
            idString = self.__idString(editor)
            if not idString:
                return

            newName, ok = QInputDialog.getText(
                None,
                self.tr("Extract Variable"),
                self.tr("Enter the name for the new variable:"),
                QLineEdit.EchoMode.Normal,
            )

            if ok and newName and editor.checkDirty():
                filename = editor.getFileName()
                sLine, sIndex, eLine, eIndex = editor.getSelection()
                source = editor.text()

                self.__ensureActive(idString)

                euuid = str(uuid.uuid4())
                self.__editors[euuid] = editor

                self.sendJson(
                    "extractVariable",
                    {
                        "FileName": filename,
                        "Source": source,
                        "Line": sLine + 1,
                        "Index": sIndex,
                        "EndLine": eLine + 1,
                        "EndIndex": eIndex,
                        "Uuid": euuid,
                        "NewName": newName,
                    },
                    idString=idString,
                )

    @pyqtSlot()
    def refactoringInlineVariable(self):
        """
        Public slot to inline the selected variable.

        Note: This is the opposite to Extract New Variable.
        """
        editor = self.__vm.activeWindow()
        if editor:
            idString = self.__idString(editor)
            if not idString:
                return

            if editor.checkDirty():
                filename = editor.getFileName()
                line, index = editor.getCursorPosition()
                source = editor.text()

                self.__ensureActive(idString)

                euuid = str(uuid.uuid4())
                self.__editors[euuid] = editor

                self.sendJson(
                    "inlineVariable",
                    {
                        "FileName": filename,
                        "Source": source,
                        "Line": line + 1,
                        "Index": index,
                        "Uuid": euuid,
                    },
                    idString=idString,
                )

    @pyqtSlot()
    def refactoringExtractFunction(self):
        """
        Public slot to extract an expression to a function.
        """
        editor = self.__vm.activeWindow()
        if editor:
            idString = self.__idString(editor)
            if not idString:
                return

            newName, ok = QInputDialog.getText(
                None,
                self.tr("Extract Function"),
                self.tr("Enter the name for the function:"),
                QLineEdit.EchoMode.Normal,
            )

            if ok and newName and editor.checkDirty():
                filename = editor.getFileName()
                sLine, sIndex, eLine, eIndex = editor.getSelection()
                source = editor.text()

                self.__ensureActive(idString)

                euuid = str(uuid.uuid4())
                self.__editors[euuid] = editor

                self.sendJson(
                    "extractFunction",
                    {
                        "FileName": filename,
                        "Source": source,
                        "Line": sLine + 1,
                        "Index": sIndex,
                        "EndLine": eLine + 1,
                        "EndIndex": eIndex,
                        "Uuid": euuid,
                        "NewName": newName,
                    },
                    idString=idString,
                )

    def __showRefactoringDiff(self, result):
        """
        Private method to show the diff of a refactoring.

        @param result dictionary containing the result data
        @type dict
        """
        if "Error" not in result:
            euuid = result["Uuid"]
            diff = result["Diff"]
            dlg = RefactoringPreviewDialog(
                self.tr("Rename Variable"), diff, parent=self.__ui
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.__applyRefactoring(euuid)
            else:
                self.__cancelRefactoring(euuid)
        else:
            EricMessageBox.critical(
                None,
                self.tr("Refactoring"),
                self.tr(
                    "<p>The refactoring could not be performed.</p>"
                    "<p>Reason: {0}</p>"
                ).format(result["ErrorString"]),
            )

    def __applyRefactoring(self, uid):
        """
        Private method to apply a given refactoring.

        @param uid UID of the calculated refactoring
        @type str
        """
        with contextlib.suppress(KeyError):
            editor = self.__editors[uid]
            idString = self.__idString(editor)

            editor.setCheckExternalModificationEnabled(False)

            self.sendJson(
                "applyRefactoring",
                {
                    "Uuid": uid,
                },
                idString=idString,
            )

    def __cancelRefactoring(self, uid):
        """
        Private method to cancel a given refactoring.

        @param uid UID of the calculated refactoring
        @type str
        """
        with contextlib.suppress(KeyError):
            editor = self.__editors[uid]
            idString = self.__idString(editor)

            self.sendJson(
                "cancelRefactoring",
                {
                    "Uuid": uid,
                },
                idString=idString,
            )

            del self.__editors[uid]

    def __checkRefactoringResult(self, result):
        """
        Private method to check the refactoring result for errors.

        @param result dictionary containing the result data
        @type dict
        """
        if "Error" in result:
            EricMessageBox.critical(
                None,
                self.tr("Apply Refactoring"),
                self.tr(
                    "<p>The refactoring could not be applied.</p><p>Reason: {0}</p>"
                ).format(result["ErrorString"]),
            )
        else:
            with contextlib.suppress(KeyError):
                self.__editors[result["Uuid"]].reload()
                self.__editors[result["Uuid"]].setCheckExternalModificationEnabled(True)

        with contextlib.suppress(KeyError):
            del self.__editors[result["Uuid"]]

    #######################################################################
    ## Methods below handle the network connection
    #######################################################################

    def handleCall(self, method, params):
        """
        Public method to handle a method call from the client.

        @param method requested method name
        @type str
        @param params dictionary with method specific parameters
        @type dict
        """
        self.__methodMapping[method](params)

    def __processClientException(self, params):
        """
        Private method to handle exceptions of the refactoring client.

        @param params dictionary containing the exception data
        @type dict
        """
        if params["ExceptionType"] == "ProtocolError":
            self.__ui.appendToStderr(
                self.tr(
                    "The data received from the Jedi server could not be"
                    " decoded. Please report this issue with the received"
                    " data to the eric bugs email address.\n"
                    "Error: {0}\n"
                    "Data:\n{1}\n"
                ).format(params["ExceptionValue"], params["ProtocolData"])
            )
        else:
            self.__ui.appendToStderr(
                self.tr(
                    "An exception happened in the Jedi client. Please"
                    " report it to the eric bugs email address.\n"
                    "Exception: {0}\n"
                    "Value: {1}\n"
                    "Traceback: {2}\n"
                ).format(
                    params["ExceptionType"],
                    params["ExceptionValue"],
                    params["Traceback"],
                )
            )

    def __startJediClient(self, interpreter, idString, clientEnv):
        """
        Private method to start the Jedi client with the given interpreter.

        @param interpreter interpreter to be used for the Jedi client
        @type str
        @param idString id of the client to be started
        @type str
        @param clientEnv dictionary with environment variables to run the
            interpreter with
        @type dict
        @return flag indicating a successful start of the client
        @rtype bool
        """
        ok = False

        if interpreter:
            client = os.path.join(os.path.dirname(__file__), "JediClient.py")
            ok, exitCode = self.startClient(
                interpreter,
                client,
                [PythonUtilities.getPythonLibraryDirectory()],
                idString=idString,
                environment=clientEnv,
            )
            if not ok:
                if exitCode == 42:
                    self.__ui.appendToStderr(
                        "JediServer: "
                        + self.tr("The jedi and/or parso library is not installed.\n")
                    )
                else:
                    self.__ui.appendToStderr(
                        "JediServer: "
                        + self.tr(
                            "'{0}' is not supported because the configured"
                            " interpreter could not be started.\n"
                        ).format(idString)
                    )
        else:
            self.__ui.appendToStderr(
                "JediServer: "
                + self.tr(
                    "'{0}' is not supported because no suitable interpreter is"
                    " configured.\n"
                ).format(idString)
            )

        return ok

    def __ensureActive(self, idString):
        """
        Private method to ensure, that the requested client is active.

        A non-active client will be started.

        @param idString id of the client to be checked
        @type str
        @return flag indicating an active client
        @rtype bool
        """
        ok = idString in self.connectionNames()
        if not ok:
            # client is not running
            if idString == JediServer.IdProject:
                interpreter, clientEnv = self.__interpreterForProject()
            else:
                interpreter = ""
                venvName = ""
                clientEnv = os.environ.copy()
                if "PATH" in clientEnv:
                    clientEnv["PATH"] = self.__ui.getOriginalPathString()
                # new code using virtual environments
                venvManager = ericApp().getObject("VirtualEnvManager")
                if idString == "Python3":
                    venvName = Preferences.getDebugger("Python3VirtualEnv")
                    if not venvName:
                        venvName, _ = venvManager.getDefaultEnvironment()
                if venvName:
                    interpreter = venvManager.getVirtualenvInterpreter(venvName)
                    execPath = venvManager.getVirtualenvExecPath(venvName)

                    # build a suitable environment
                    if execPath:
                        if "PATH" in clientEnv:
                            clientEnv["PATH"] = os.pathsep.join(
                                [execPath, clientEnv["PATH"]]
                            )
                        else:
                            clientEnv["PATH"] = execPath
            if interpreter:
                ok = self.__startJediClient(interpreter, idString, clientEnv)
            else:
                ok = False
        return ok

    def __interpreterForProject(self):
        """
        Private method to determine the interpreter for the current project and
        the environment to run it.

        @return tuple containing the interpreter of the current project and the
            environment variables
        @rtype tuple of (str, dict)
        """
        projectLanguage = self.__ericProject.getProjectLanguage()
        interpreter = ""
        clientEnv = os.environ.copy()
        if "PATH" in clientEnv:
            clientEnv["PATH"] = self.__ui.getOriginalPathString()

        if projectLanguage in ("Python3", "MicroPython", "Cython"):
            interpreter = self.__ericProject.getProjectInterpreter()
            if interpreter:
                execPath = self.__ericProject.getProjectExecPath()

                # build a suitable environment
                if execPath:
                    if "PATH" in clientEnv:
                        clientEnv["PATH"] = os.pathsep.join(
                            [execPath, clientEnv["PATH"]]
                        )
                    else:
                        clientEnv["PATH"] = execPath

        return interpreter, clientEnv

    @pyqtSlot()
    def handleNewConnection(self):
        """
        Public slot for new incoming connections from a client.
        """
        super().handleNewConnection()

        self.__updateEditorLanguageMapping()

    def activate(self):
        """
        Public method to activate the Jedi server.
        """
        self.__documentationViewer = self.__ui.documentationViewer()
        if self.__documentationViewer is not None:
            self.__documentationViewer.registerProvider(
                "jedi",
                self.tr("Jedi"),
                self.requestCodeDocumentation,
                self.isSupportedLanguage,
            )

        self.__ericProject.projectOpened.connect(self.__projectOpened)
        self.__ericProject.projectClosed.connect(self.__projectClosed)

    def deactivate(self):
        """
        Public method to deactivate the code assist server.
        """
        """
        Public method to shut down the code assist server.
        """
        if self.__documentationViewer is not None:
            self.__documentationViewer.unregisterProvider("jedi")

        with contextlib.suppress(TypeError):
            self.__ericProject.projectOpened.disconnect(self.__projectOpened)
            self.__ericProject.projectClosed.disconnect(self.__projectClosed)

        self.stopAllClients()

    @pyqtSlot()
    def __projectOpened(self):
        """
        Private slot to handle the projectOpened signal.
        """
        if not FileSystemUtilities.isRemoteFileName(
            self.__ericProject.getProjectFile()
        ):
            self.__ensureActive(JediServer.IdProject)
            self.sendJson(
                "openProject",
                {
                    "ProjectPath": self.__ericProject.getProjectPath(),
                },
                idString=JediServer.IdProject,
            )

    @pyqtSlot()
    def __projectClosed(self):
        """
        Private slot to handle the projectClosed signal.
        """
        self.__ensureActive(JediServer.IdProject)
        self.sendJson("closeProject", {}, idString=JediServer.IdProject)

        self.stopClient(idString=JediServer.IdProject)

    def forgetEditor(self, editor):
        """
        Public method to forget about the given editor.

        @param editor reference to the editor to forget about
        @type Editor
        """
        for uid in list(self.__editors):
            if self.__editors[uid] is editor:
                with contextlib.suppress(KeyError):
                    del self.__editors[uid]
                break
