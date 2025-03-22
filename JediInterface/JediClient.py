# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Jedi client of eric7.
"""

import contextlib
import os
import sys

SuppressedException = Exception

modulePath = sys.argv[-1]  # it is always the last parameter
sys.path.insert(1, modulePath)

try:
    import jedi
except ImportError:
    sys.exit(42)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from eric7.EricNetwork.EricJsonClient import EricJsonClient


class JediClient(EricJsonClient):
    """
    Class implementing the Jedi client of eric7.
    """

    def __init__(self, host, port, idString):
        """
        Constructor

        @param host ip address the background service is listening
        @type str
        @param port port of the background service
        @type int
        @param idString assigned client id to be sent back to the server in
            order to identify the connection
        @type str
        """
        super().__init__(host, port, idString)

        self.__methodMapping = {
            "openProject": self.__openProject,
            "closeProject": self.__closeProject,
            "getCompletions": self.__getCompletions,
            "getCallTips": self.__getCallTips,
            "getDocumentation": self.__getDocumentation,
            "hoverHelp": self.__getHoverHelp,
            "gotoDefinition": self.__getAssignment,
            "gotoReferences": self.__getReferences,
            "renameVariable": self.__renameVariable,
            "extractVariable": self.__extractVariable,
            "inlineVariable": self.__inlineVariable,
            "extractFunction": self.__extractFunction,
            "applyRefactoring": self.__applyRefactoring,
            "cancelRefactoring": self.__cancelRefactoring,
        }

        self.__id = idString

        self.__project = None

        self.__refactorings = {}

    def handleCall(self, method, params):
        """
        Public method to handle a method call from the server.

        @param method requested method name
        @type str
        @param params dictionary with method specific parameters
        @type dict
        """
        self.__methodMapping[method](params)

    def __handleError(self, err):
        """
        Private method to process an error.

        @param err exception object
        @type Exception or Warning
        @return dictionary containing the error information
        @rtype dict
        """
        error = str(type(err)).split()[-1]
        error = error[1:-2].split(".")[-1]
        errorDict = {
            "Error": error,
            "ErrorString": str(err),
        }

        return errorDict

    def __openProject(self, params):
        """
        Private method to create a jedi project and load its saved data.

        @param params dictionary containing the method parameters
        @type dict
        """
        projectPath = params["ProjectPath"]
        self.__project = jedi.Project(projectPath)

    def __closeProject(self, _params):
        """
        Private method to save a jedi project's data.

        @param _params dictionary containing the method parameters (unused)
        @type dict
        """
        if self.__project is not None:
            self.__project.save()

        self.__project = None

    def __completionType(self, completion):
        """
        Private method to assemble the completion type depending on the
        visibility indicated by the completion name.

        @param completion reference to the completion object
        @type jedi.api.classes.Completion
        @return modified completion type
        @rtype str
        """
        if completion.name.startswith("__"):
            compType = "__" + completion.type
        elif completion.name.startswith("_"):
            compType = "_" + completion.type
        else:
            compType = completion.type

        return compType

    def __completionFullName(self, completion):
        """
        Private method to extract the full completion name.

        @param completion reference to the completion object
        @type jedi.api.classes.Completion
        @return full completion name
        @rtype str
        """
        fullName = completion.full_name
        fullName = (
            fullName.replace("__main__", completion.module_name)
            if fullName
            else completion.module_name
        )

        return fullName

    def __getCompletions(self, params):
        """
        Private method to calculate possible completions.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]
        fuzzy = params["Fuzzy"]

        errorDict = {}
        response = []

        script = jedi.Script(source, path=filename, project=self.__project)

        try:
            completions = script.complete(line, index, fuzzy=fuzzy)
            response = [
                {
                    "ModulePath": str(completion.module_path),
                    "Name": completion.name,
                    "FullName": self.__completionFullName(completion),
                    "CompletionType": self.__completionType(completion),
                }
                for completion in completions
                if not (
                    completion.name.startswith("__") and completion.name.endswith("__")
                )
            ]
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "Completions": response,
            "CompletionText": params["CompletionText"],
            "FileName": filename,
        }
        result.update(errorDict)

        self.sendJson("CompletionsResult", result)

    def __getCallTips(self, params):
        """
        Private method to calculate possible calltips.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]

        errorDict = {}
        calltips = []

        script = jedi.Script(source, path=filename, project=self.__project)

        try:
            signatures = script.get_signatures(line, index)
            for signature in signatures:
                name = signature.name
                params = self.__extractParameters(signature)
                calltips.append("{0}{1}".format(name, params))
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "CallTips": calltips,
        }
        result.update(errorDict)

        self.sendJson("CallTipsResult", result)

    def __extractParameters(self, signature):
        """
        Private method to extract the call parameter descriptions.

        @param signature a jedi signature object
        @type object
        @return a string with comma seperated parameter names and default
            values
        @rtype str
        """
        try:
            params = ", ".join(
                [param.description.split("param ", 1)[-1] for param in signature.params]
            )
            return "({0})".format(params)
        except AttributeError:
            # Empty strings as argspec suppress display of "definition"
            return " "

    def __getDocumentation(self, params):
        """
        Private method to get some source code documentation.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]

        errorDict = {}
        docu = {}

        script = jedi.Script(source, path=filename, project=self.__project)

        try:
            definitions = script.infer(line, index)
            definition = definitions[0]  # use the first one only
            docu = {
                "name": definition.full_name,
                "module": definition.module_name,
                "argspec": self.__extractParameters(definition),
                "docstring": definition.docstring(),
            }
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "DocumentationDict": docu,
        }
        result.update(errorDict)

        self.sendJson("DocumentationResult", result)

    def __getHoverHelp(self, params):
        """
        Private method to get some source code documentation.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]
        uid = params["Uuid"]

        script = jedi.Script(source, path=filename, project=self.__project)

        errorDict = {}
        helpText = ""

        try:
            helpText = script.help(line, index)[0].docstring()
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "Line": line,
            "Index": index,
            "HoverHelp": helpText,
            "Uuid": uid,
        }
        result.update(errorDict)

        self.sendJson("HoverHelpResult", result)

    def __getAssignment(self, params):
        """
        Private method to get the place a parameter is defined.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]
        uid = params["Uuid"]

        errorDict = {}
        gotoDefinition = {}

        script = jedi.Script(source, path=filename, project=self.__project)

        try:
            assignments = script.goto(
                line, index, follow_imports=True, follow_builtin_imports=True
            )
            for assignment in assignments:
                if bool(assignment.module_path):
                    gotoDefinition = {
                        "ModulePath": str(assignment.module_path),
                        "Line": (0 if assignment.line is None else assignment.line),
                        "Column": assignment.column,
                    }

                    if (
                        gotoDefinition["ModulePath"] == filename
                        and gotoDefinition["Line"] == line
                    ):
                        # user called for the definition itself
                        # => send the references instead
                        self.__getReferences(params)
                        return
                break
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "GotoDefinitionDict": gotoDefinition,
            "Uuid": uid,
        }
        result.update(errorDict)

        self.sendJson("GotoDefinitionResult", result)

    def __getReferences(self, params):
        """
        Private method to get the places a parameter is referenced.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]
        uid = params["Uuid"]

        errorDict = {}
        gotoReferences = []

        script = jedi.Script(source, path=filename, project=self.__project)

        try:
            references = script.get_references(line, index, include_builtins=False)
            for reference in references:
                if bool(reference.module_path):
                    if (
                        reference.line == line
                        and str(reference.module_path) == filename
                    ):
                        continue
                    gotoReferences.append(
                        {
                            "ModulePath": str(reference.module_path),
                            "Line": (0 if reference.line is None else reference.line),
                            "Column": reference.column,
                            "Code": reference.get_line_code(),
                        }
                    )
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "GotoReferencesList": gotoReferences,
            "Uuid": uid,
        }
        result.update(errorDict)

        self.sendJson("GotoReferencesResult", result)

    def __renameVariable(self, params):
        """
        Private method to rename the variable under the cursor.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]
        uid = params["Uuid"]
        newName = params["NewName"]

        errorDict = {}
        diff = ""

        script = jedi.Script(source, path=filename, project=self.__project)

        try:
            refactoring = script.rename(line, index, new_name=newName)
            self.__refactorings[uid] = refactoring
            diff = refactoring.get_diff()
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "Diff": diff,
            "Uuid": uid,
        }
        result.update(errorDict)

        self.sendJson("RefactoringDiff", result)

    def __extractVariable(self, params):
        """
        Private method to extract a statement to a new variable.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]
        endLine = params["EndLine"]
        endIndex = params["EndIndex"]
        uid = params["Uuid"]
        newName = params["NewName"]

        errorDict = {}
        diff = ""

        script = jedi.Script(source, path=filename, project=self.__project)

        try:
            refactoring = script.extract_variable(
                line, index, new_name=newName, until_line=endLine, until_column=endIndex
            )
            self.__refactorings[uid] = refactoring
            diff = refactoring.get_diff()
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "Diff": diff,
            "Uuid": uid,
        }
        result.update(errorDict)

        self.sendJson("RefactoringDiff", result)

    def __inlineVariable(self, params):
        """
        Private method to inline a variable statement.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]
        uid = params["Uuid"]

        errorDict = {}
        diff = ""

        script = jedi.Script(source, path=filename, project=self.__project)

        try:
            refactoring = script.inline(line, index)
            self.__refactorings[uid] = refactoring
            diff = refactoring.get_diff()
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "Diff": diff,
            "Uuid": uid,
        }
        result.update(errorDict)

        self.sendJson("RefactoringDiff", result)

    def __extractFunction(self, params):
        """
        Private method to extract an expression to a new function.

        @param params dictionary containing the method parameters
        @type dict
        """
        filename = params["FileName"]
        source = params["Source"]
        line = params["Line"]
        index = params["Index"]
        endLine = params["EndLine"]
        endIndex = params["EndIndex"]
        uid = params["Uuid"]
        newName = params["NewName"]

        errorDict = {}
        diff = ""

        script = jedi.Script(source, path=filename, project=self.__project)

        try:
            refactoring = script.extract_function(
                line, index, new_name=newName, until_line=endLine, until_column=endIndex
            )
            self.__refactorings[uid] = refactoring
            diff = refactoring.get_diff()
        except SuppressedException as err:
            errorDict = self.__handleError(err)

        result = {
            "Diff": diff,
            "Uuid": uid,
        }
        result.update(errorDict)

        self.sendJson("RefactoringDiff", result)

    def __applyRefactoring(self, params):
        """
        Private method to apply a refactoring.

        @param params dictionary containing the method parameters
        @type dict
        """
        uid = params["Uuid"]

        errorDict = {}

        try:
            refactoring = self.__refactorings[uid]
            refactoring.apply()
            ok = True
        except KeyError:
            ok = False
        except SuppressedException as err:
            errorDict = self.__handleError(err)
            ok = False

        result = {
            "result": ok,
            "Uuid": uid,
        }
        result.update(errorDict)

        self.sendJson("RefactoringApplyResult", result)

        with contextlib.suppress(KeyError):
            del self.__refactorings[uid]

    def __cancelRefactoring(self, params):
        """
        Private method to cancel a refactoring.

        @param params dictionary containing the method parameters
        @type dict
        """
        uid = params["Uuid"]
        with contextlib.suppress(KeyError):
            del self.__refactorings[uid]


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Host, port, id and module path parameters are missing. Abort.")
        sys.exit(1)

    host, port, idString = sys.argv[1:-1]

    client = JediClient(host, int(port), idString)
    # Start the main loop
    client.run()

    sys.exit(0)

#
# eflag: noqa = M801
