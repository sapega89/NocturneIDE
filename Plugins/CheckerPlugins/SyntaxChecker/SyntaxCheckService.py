# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#
# pylint: disable=C0103

"""
Module implementing an interface to add different languages to do a syntax
check.
"""

from PyQt6.QtCore import QObject, pyqtSignal

from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import PythonUtilities


class SyntaxCheckService(QObject):
    """
    Implement the syntax check service.

    Plugins can add other languages to the syntax check by calling addLanguage
    and support of an extra checker module on the client side which has to
    connect directly to the background service.

    @signal syntaxChecked(str, dict) emitted when the syntax check was done for
        one file
    @signal batchFinished() emitted when a syntax check batch is done
    @signal error(str, str) emitted in case of an error
    """

    syntaxChecked = pyqtSignal(str, dict)
    batchFinished = pyqtSignal()
    error = pyqtSignal(str, str)

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.backgroundService = ericApp().getObject("BackgroundService")
        self.__supportedLanguages = {}

        self.queuedBatches = []
        self.batchesFinished = True

    def __determineLanguage(self, filename, source):
        """
        Private method to determine the language of the file.

        @param filename of the sourcefile
        @type str
        @param source code of the file
        @type str
        @return language of the file or None if not found
        @rtype str or None
        """
        if PythonUtilities.isPythonSource(filename, source):
            return "Python3"

        for lang, (_env, _getArgs, getExt) in self.__supportedLanguages.items():
            if filename.endswith(tuple(getExt())):
                return lang

        return None

    def addLanguage(self, lang, env, path, module, getArgs, getExt, callback, onError):
        """
        Public method to register a new language to the supported languages.

        @param lang new language to check syntax
        @type str
        @param env the environment in which the checker is implemented
        @type str
        @param path full path to the module
        @type str
        @param module name to import
        @type str
        @param getArgs function to collect the required arguments to call the
            syntax checker on client side
        @type function
        @param getExt function that returns the supported file extensions of
            the syntax checker
        @type function
        @param callback function on service response
        @type function
        @param onError callback function if client or service isn't available
        @type function
        """
        self.__supportedLanguages[lang] = env, getArgs, getExt
        # Connect to the background service
        self.backgroundService.serviceConnect(
            "{0}Syntax".format(lang),
            env,
            path,
            module,
            callback,
            onError,
            onBatchDone=self.batchJobDone,
        )

    def getLanguages(self):
        """
        Public method to return the supported language names.

        @return list of languanges supported
        @rtype list of str
        """
        return list(self.__supportedLanguages) + ["MicroPython"]

    def removeLanguage(self, lang):
        """
        Public method to remove the language from syntax check.

        @param lang language to remove
        @type str
        """
        self.__supportedLanguages.pop(lang, None)
        self.backgroundService.serviceDisconnect("{0}Syntax".format(lang), lang)

    def getExtensions(self):
        """
        Public method to return all supported file extensions for the
        syntax checker dialog.

        @return set of all supported file extensions
        @rtype set of str
        """
        extensions = set()
        for _env, _getArgs, getExt in self.__supportedLanguages.values():
            for ext in getExt():
                extensions.add(ext)
        return extensions

    def syntaxCheck(self, lang, filename, source, *args):
        """
        Public method to prepare a syntax check of one source file.

        @param lang language of the file or None to determine by internal
            algorithm
        @type str or None
        @param filename source filename
        @type str
        @param source string containing the code to check
        @type str
        @param args tuple containing additional positional arguments
        @type tuple
        """
        if not lang:
            lang = self.__determineLanguage(filename, source)
        if lang not in self.getLanguages():
            return
        if lang == "MicroPython":
            lang = "Python3"

        data = [source]
        # Call the getArgs function to get the required arguments
        env, getArgs, getExt = self.__supportedLanguages[lang]
        data.extend(getArgs())
        if args:
            data.extend(args)
        self.backgroundService.enqueueRequest(
            "{0}Syntax".format(lang), env, filename, data
        )

    def syntaxBatchCheck(self, argumentsList):
        """
        Public method to prepare a syntax check on multiple source files.

        @param argumentsList list of argument tuples with each tuple
            containing filename and source
        @type list of tuples of (str, str)
        """
        data = {}
        for lang in self.getLanguages():
            data[lang] = []

        for arguments in argumentsList:
            # ~ arguments[0]: file name
            # ~ arguments[1]: source
            # ~ arguments[2:]: additional arguments
            lang = self.__determineLanguage(arguments[0], arguments[1])
            if lang not in self.getLanguages():
                continue
            else:
                jobData = [arguments[1]]
                # Call the getArgs function to get the required arguments
                getArgs = self.__supportedLanguages[lang][1]
                jobData.extend(getArgs())
                jobData.extend(arguments[2:])
                data[lang].append((arguments[0], jobData))

        self.queuedBatches = []
        for lang in self.getLanguages():
            if data[lang]:
                self.queuedBatches.append(lang)
                env = self.__supportedLanguages[lang][0]
                self.backgroundService.enqueueRequest(
                    "batch_{0}Syntax".format(lang), env, "", data[lang]
                )
                self.batchesFinished = False

    def cancelSyntaxBatchCheck(self):
        """
        Public method to cancel all batch jobs.
        """
        for lang in self.getLanguages():
            try:
                env = self.__supportedLanguages[lang][0]
                self.backgroundService.requestCancel(
                    "batch_{0}Syntax".format(lang), env
                )
            except KeyError:
                continue

    def __serviceError(self, fn, msg):
        """
        Private slot handling service errors.

        @param fn file name
        @type str
        @param msg message text
        @type str
        """
        self.error.emit(fn, msg)

    def serviceErrorPy3(self, fx, lang, fn, msg):
        """
        Public method handling service errors for Python 3.

        @param fx service name
        @type str
        @param lang language
        @type str
        @param fn file name
        @type str
        @param msg message text
        @type str
        """
        if fx in ["Python3Syntax", "batch_Python3Syntax"]:
            if fx == "Python3Syntax":
                self.__serviceError(fn, msg)
            else:
                self.__serviceError(self.tr("Python 3 batch check"), msg)
                self.batchJobDone(fx, lang)

    def serviceErrorJavaScript(self, fx, lang, fn, msg):
        """
        Public method handling service errors for JavaScript.

        @param fx service name
        @type str
        @param lang language
        @type str
        @param fn file name
        @type str
        @param msg message text
        @type str
        """
        if fx in ["JavaScriptSyntax", "batch_JavaScriptSyntax"]:
            if fx == "JavaScriptSyntax":
                self.__serviceError(fn, msg)
            else:
                self.__serviceError(self.tr("JavaScript batch check"), msg)
                self.batchJobDone(fx, lang)

    def serviceErrorYAML(self, fx, lang, fn, msg):
        """
        Public method handling service errors for YAML.

        @param fx service name
        @type str
        @param lang language
        @type str
        @param fn file name
        @type str
        @param msg message text
        @type str
        """
        if fx in ["YAMLSyntax", "batch_YAMLSyntax"]:
            if fx == "YAMLSyntax":
                self.__serviceError(fn, msg)
            else:
                self.__serviceError(self.tr("YAML batch check"), msg)
                self.batchJobDone(fx, lang)

    def serviceErrorJSON(self, fx, lang, fn, msg):
        """
        Public method handling service errors for JSON.

        @param fx service name
        @type str
        @param lang language
        @type str
        @param fn file name
        @type str
        @param msg message text
        @type str
        """
        if fx in ["JSONSyntax", "batch_JSONSyntax"]:
            if fx == "JSONSyntax":
                self.__serviceError(fn, msg)
            else:
                self.__serviceError(self.tr("JSON batch check"), msg)
                self.batchJobDone(fx, lang)

    def serviceErrorTOML(self, fx, lang, fn, msg):
        """
        Public method handling service errors for TOML.

        @param fx service name
        @type str
        @param lang language
        @type str
        @param fn file name
        @type str
        @param msg message text
        @type str
        """
        if fx in ["TOMLSyntax", "batch_TOMLSyntax"]:
            if fx == "TOMLSyntax":
                self.__serviceError(fn, msg)
            else:
                self.__serviceError(self.tr("TOML batch check"), msg)
                self.batchJobDone(fx, lang)

    def batchJobDone(self, fx, lang):
        """
        Public slot handling the completion of a batch job.

        @param fx service name
        @type str
        @param lang language
        @type str
        """
        if fx in [
            "Python3Syntax",
            "batch_Python3Syntax",
            "JavaScriptSyntax",
            "batch_JavaScriptSyntax",
            "YAMLSyntax",
            "batch_YAMLSyntax",
            "JSONSyntax",
            "batch_JSONSyntax",
            "TOMLSyntax",
            "batch_TOMLSyntax",
        ]:
            if lang in self.queuedBatches:
                self.queuedBatches.remove(lang)
            # prevent sending the signal multiple times
            if len(self.queuedBatches) == 0 and not self.batchesFinished:
                self.batchFinished.emit()
                self.batchesFinished = True
