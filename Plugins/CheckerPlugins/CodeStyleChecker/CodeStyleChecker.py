# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the code style checker.
"""

import ast
import contextlib
import multiprocessing
import queue
import sys

import pycodestyle

from Annotations.AnnotationsChecker import AnnotationsChecker
from Async.AsyncChecker import AsyncChecker
from CodeStyleFixer import CodeStyleFixer
from Complexity.ComplexityChecker import ComplexityChecker
from DocStyle.DocStyleChecker import DocStyleChecker
from Imports.ImportsChecker import ImportsChecker
from Logging.LoggingChecker import LoggingChecker
from Miscellaneous.MiscellaneousChecker import MiscellaneousChecker
from NameOrder.NameOrderChecker import NameOrderChecker
from Naming.NamingStyleChecker import NamingStyleChecker
from PathLib.PathlibChecker import PathlibChecker
from Security.SecurityChecker import SecurityChecker
from Simplify.SimplifyChecker import SimplifyChecker
from Unused.UnusedChecker import UnusedChecker

# register the name checker
pycodestyle.register_check(NamingStyleChecker, NamingStyleChecker.Codes)


def initService():
    """
    Initialize the service and return the entry point.

    @return the entry point for the background client
    @rtype function
    """
    return codeStyleCheck


def initBatchService():
    """
    Initialize the batch service and return the entry point.

    @return the entry point for the background client
    @rtype function
    """
    return codeStyleBatchCheck


class CodeStyleCheckerReport(pycodestyle.BaseReport):
    """
    Class implementing a special report to be used with our dialog.
    """

    def __init__(self, options):
        """
        Constructor

        @param options options for the report
        @type optparse.Values
        """
        super().__init__(options)

        self.__repeat = options.repeat
        self.errors = []

    def error_args(self, line_number, offset, errorCode, check, *args):
        """
        Public method to collect the error messages.

        @param line_number line number of the issue
        @type int
        @param offset position within line of the issue
        @type int
        @param errorCode error message code
        @type str
        @param check reference to the checker function
        @type function
        @param args arguments for the message
        @type list
        @return error code
        @rtype str
        """
        errorCode = super().error_args(line_number, offset, errorCode, check, *args)
        if errorCode and (self.counters[errorCode] == 1 or self.__repeat):
            self.errors.append(
                {
                    "file": self.filename,
                    "line": line_number,
                    "offset": offset,
                    "code": errorCode,
                    "args": args,
                }
            )
        return errorCode


def extractLineFlags(line, startComment="#", endComment="", flagsLine=False):
    """
    Function to extract flags starting and ending with '__' from a line
    comment.

    @param line line to extract flags from
    @type str
    @param startComment string identifying the start of the comment
    @type str
    @param endComment string identifying the end of a comment
    @type str
    @param flagsLine flag indicating to check for a flags only line
    @type bool
    @return list containing the extracted flags
    @rtype list of str
    """
    flags = []

    if not flagsLine or (flagsLine and line.strip().startswith(startComment)):
        pos = line.rfind(startComment)
        if pos >= 0:
            comment = line[pos + len(startComment) :].strip()
            if endComment:
                endPos = line.rfind(endComment)
                if endPos >= 0:
                    comment = comment[:endPos]
            if comment.startswith(("noqa:", "NOQA:")):
                flags = [
                    "noqa:{0}".format(f.strip())
                    for f in comment[len("noqa:") :].split(",")
                ]
            else:
                flags = [
                    f
                    for f in comment.split()
                    if (f.startswith("__") and f.endswith("__"))
                ]
                flags += [
                    f.lower()
                    for f in comment.split()
                    if f in ("noqa", "NOQA", "nosec", "NOSEC", "secok", "SECOK")
                ]
    return flags


def ignoreCode(errorCode, lineFlags):
    """
    Function to check, if the given code should be ignored as per line flags.

    @param errorCode error code to be checked
    @type str
    @param lineFlags list of line flags to check against
    @type list of str
    @return flag indicating to ignore the error code
    @rtype bool
    """
    if lineFlags:
        if (
            "__IGNORE_WARNING__" in lineFlags
            or "noqa" in lineFlags
            or "nosec" in lineFlags
        ):
            # ignore all warning codes
            return True

        for flag in lineFlags:
            # check individual warning code
            if flag.startswith("__IGNORE_WARNING_"):
                ignoredCode = flag[2:-2].rsplit("_", 1)[-1]
                if errorCode.startswith(ignoredCode):
                    return True
            elif flag.startswith("noqa:"):
                ignoredCode = flag[len("noqa:") :].strip()
                if errorCode.startswith(ignoredCode):
                    return True

    return False


def securityOk(_errorCode, lineFlags):
    """
    Function to check, if the given error code is an acknowledged security report.

    @param _errorCode error code to be checked (unused)
    @type str
    @param lineFlags list of line flags to check against
    @type list of str
    @return flag indicating an acknowledged security report
    @rtype bool
    """
    if lineFlags:
        return "secok" in lineFlags

    return False


def codeStyleCheck(filename, source, args):
    """
    Do the source code style check and/or fix found errors.

    @param filename source filename
    @type str
    @param source list of code lines to be checked
    @type list of str
    @param args arguments used by the codeStyleCheck function (list of
        excludeMessages, includeMessages, repeatMessages, fixCodes,
        noFixCodes, fixIssues, maxLineLength, maxDocLineLength, blankLines,
        hangClosing, docType, codeComplexityArgs, miscellaneousArgs,
        annotationArgs, securityArgs, importsArgs, nameOrderArgs, unusedArgs, errors,
        eol, encoding, backup)
    @type list of (str, str, bool, str, str, bool, int, list of (int, int),
        bool, str, dict, dict, dict, dict, dict, dict, list of str, str, str, bool)
    @return tuple of statistics (dict) and list of results (tuple for each
        found violation of style (lineno, position, text, ignored, fixed,
        autofixing, fixedMsg))
    @rtype tuple of (dict, list of tuples of (int, int, str, bool, bool, bool,
        str))
    """
    return __checkCodeStyle(filename, source, args)


def codeStyleBatchCheck(argumentsList, send, fx, cancelled, maxProcesses=0):
    """
    Module function to check source code style for a batch of files.

    @param argumentsList list of arguments tuples as given for codeStyleCheck
    @type list
    @param send reference to send function
    @type func
    @param fx registered service name
    @type str
    @param cancelled reference to function checking for a cancellation
    @type func
    @param maxProcesses number of processes to be used
    @type int
    """
    if maxProcesses == 0:
        # determine based on CPU count
        try:
            NumberOfProcesses = multiprocessing.cpu_count()
            if NumberOfProcesses >= 1:
                NumberOfProcesses -= 1
        except NotImplementedError:
            NumberOfProcesses = 1
    else:
        NumberOfProcesses = maxProcesses

    # Create queues
    taskQueue = multiprocessing.Queue()
    doneQueue = multiprocessing.Queue()

    # Submit tasks (initially two times the number of processes)
    tasks = len(argumentsList)
    initialTasks = min(2 * NumberOfProcesses, tasks)
    for _ in range(initialTasks):
        taskQueue.put(argumentsList.pop(0))

    # Start worker processes
    workers = [
        multiprocessing.Process(target=workerTask, args=(taskQueue, doneQueue))
        for _ in range(NumberOfProcesses)
    ]
    for worker in workers:
        worker.start()

    # Get and send results
    for _ in range(tasks):
        resultSent = False
        wasCancelled = False

        while not resultSent:
            try:
                # get result (waiting max. 3 seconds and send it to frontend
                filename, result = doneQueue.get(timeout=3)
                send(fx, filename, result)
                resultSent = True
            except queue.Empty:
                # ignore empty queue, just carry on
                if cancelled():
                    wasCancelled = True
                    break

        if wasCancelled or cancelled():
            # just exit the loop ignoring the results of queued tasks
            break

        if argumentsList:
            taskQueue.put(argumentsList.pop(0))

    # Tell child processes to stop
    for _ in range(NumberOfProcesses):
        taskQueue.put("STOP")

    for worker in workers:
        worker.join()
        worker.close()

    taskQueue.close()
    doneQueue.close()


def workerTask(inputQueue, outputQueue):
    """
    Module function acting as the parallel worker for the style check.

    @param inputQueue input queue
    @type multiprocessing.Queue
    @param outputQueue output queue
    @type multiprocessing.Queue
    """
    for filename, source, args in iter(inputQueue.get, "STOP"):
        result = __checkCodeStyle(filename, source, args)
        outputQueue.put((filename, result))


def __checkSyntax(filename, source):
    """
    Private module function to perform a syntax check.

    @param filename source filename
    @type str
    @param source list of code lines to be checked
    @type list of str
    @return tuple containing the error dictionary with syntax error details,
        a statistics dictionary and None or a tuple containing two None and
        the generated AST tree
    @rtype tuple of (dict, dict, None) or tuple of (None, None, ast.Module)
    """
    src = "".join(source)

    try:
        tree = ast.parse(src, filename, "exec", type_comments=True)
        # need the 'type_comments' parameter to include type annotations
        return None, None, tree
    except (SyntaxError, TypeError):
        exc_type, exc = sys.exc_info()[:2]
        if len(exc.args) > 1:
            offset = exc.args[1]
            if len(offset) > 2:
                offset = offset[1:3]
        else:
            offset = (1, 0)
        return (
            {
                "file": filename,
                "line": offset[0],
                "offset": offset[1],
                "code": "E901",
                "args": [exc_type.__name__, exc.args[0]],
            },
            {
                "E901": 1,
            },
            None,
        )


def __checkCodeStyle(filename, source, args):
    """
    Private module function to perform the source code style check and/or fix
    found errors.

    @param filename source filename
    @type str
    @param source list of code lines to be checked
    @type list of str
    @param args arguments used by the codeStyleCheck function (list of
        excludeMessages, includeMessages, repeatMessages, fixCodes,
        noFixCodes, fixIssues, maxLineLength, maxDocLineLength, blankLines,
        hangClosing, docType, codeComplexityArgs, miscellaneousArgs,
        annotationArgs, securityArgs, importsArgs, nameOrderArgs, unusedArgs, errors,
        eol, encoding, backup)
    @type list of (str, str, bool, str, str, bool, int, list of (int, int),
        bool, str, dict, dict, dict, dict, dict, dict, list of str, str, str, bool)
    @return tuple of statistics data and list of result dictionaries with
        keys:
        <ul>
        <li>file: file name</li>
        <li>line: line_number</li>
        <li>offset: offset within line</li>
        <li>code: error message code</li>
        <li>args: list of arguments to format the message</li>
        <li>ignored: flag indicating this issue was ignored</li>
        <li>fixed: flag indicating this issue was fixed</li>
        <li>autofixing: flag indicating that a fix can be done</li>
        <li>fixcode: message code for the fix</li>
        <li>fixargs: list of arguments to format the fix message</li>
        </ul>
    @rtype tuple of (dict, list of dict)
    """
    (
        excludeMessages,
        includeMessages,
        repeatMessages,
        fixCodes,
        noFixCodes,
        fixIssues,
        maxLineLength,
        maxDocLineLength,
        blankLines,
        hangClosing,
        docType,
        codeComplexityArgs,
        miscellaneousArgs,
        annotationArgs,
        securityArgs,
        importsArgs,
        nameOrderArgs,
        unusedArgs,
        errors,
        eol,
        encoding,
        backup,
    ) = args

    stats = {}

    fixer = (
        CodeStyleFixer(
            filename,
            source,
            fixCodes,
            noFixCodes,
            maxLineLength,
            blankLines,
            True,
            eol,
            backup,
        )
        if fixIssues
        else None
    )

    if not errors:
        if includeMessages:
            select = [s.strip() for s in includeMessages.split(",") if s.strip()]
        else:
            select = []
        if excludeMessages:
            ignore = [i.strip() for i in excludeMessages.split(",") if i.strip()]
        else:
            ignore = []

        syntaxError, syntaxStats, tree = __checkSyntax(filename, source)

        # perform the checks only, if syntax is ok and AST tree was generated
        if tree:
            # check coding style
            pycodestyle.BLANK_LINES_CONFIG = {
                # Top level class and function.
                "top_level": blankLines[0],
                # Methods and nested class and function.
                "method": blankLines[1],
            }
            styleGuide = pycodestyle.StyleGuide(
                reporter=CodeStyleCheckerReport,
                repeat=repeatMessages,
                select=select,
                ignore=ignore,
                max_line_length=maxLineLength,
                max_doc_length=maxDocLineLength,
                hang_closing=hangClosing,
            )
            report = styleGuide.options.report
            styleGuide.input_file(filename, lines=source)
            stats.update(report.counters)
            errors = report.errors

            # check documentation style
            docStyleChecker = DocStyleChecker(
                source,
                filename,
                select,
                ignore,
                [],
                repeatMessages,
                maxLineLength=maxDocLineLength,
                docType=docType,
            )
            docStyleChecker.run()
            stats.update(docStyleChecker.counters)
            errors += docStyleChecker.errors

            # miscellaneous additional checks
            miscellaneousChecker = MiscellaneousChecker(
                source,
                filename,
                tree,
                select,
                ignore,
                [],
                repeatMessages,
                miscellaneousArgs,
            )
            miscellaneousChecker.run()
            stats.update(miscellaneousChecker.counters)
            errors += miscellaneousChecker.errors

            # check code complexity
            complexityChecker = ComplexityChecker(
                source, filename, tree, select, ignore, codeComplexityArgs
            )
            complexityChecker.run()
            stats.update(complexityChecker.counters)
            errors += complexityChecker.errors

            # check function annotations
            annotationsChecker = AnnotationsChecker(
                source,
                filename,
                tree,
                select,
                ignore,
                [],
                repeatMessages,
                annotationArgs,
            )
            annotationsChecker.run()
            stats.update(annotationsChecker.counters)
            errors += annotationsChecker.errors

            # check for security issues
            securityChecker = SecurityChecker(
                source, filename, tree, select, ignore, [], repeatMessages, securityArgs
            )
            securityChecker.run()
            stats.update(securityChecker.counters)
            errors += securityChecker.errors

            # check for pathlib usage
            pathlibChecker = PathlibChecker(
                source, filename, tree, select, ignore, [], repeatMessages
            )
            pathlibChecker.run()
            stats.update(pathlibChecker.counters)
            errors += pathlibChecker.errors

            # check for code simplifications
            simplifyChecker = SimplifyChecker(
                source, filename, tree, select, ignore, [], repeatMessages
            )
            simplifyChecker.run()
            stats.update(simplifyChecker.counters)
            errors += simplifyChecker.errors

            # check import statements
            importsChecker = ImportsChecker(
                source, filename, tree, select, ignore, [], repeatMessages, importsArgs
            )
            importsChecker.run()
            stats.update(importsChecker.counters)
            errors += importsChecker.errors

            # check name ordering
            nameOrderChecker = NameOrderChecker(
                source,
                filename,
                tree,
                select,
                ignore,
                [],
                repeatMessages,
                nameOrderArgs,
            )
            nameOrderChecker.run()
            stats.update(nameOrderChecker.counters)
            errors += nameOrderChecker.errors

            # check unused arguments and variables
            unusedChecker = UnusedChecker(
                source,
                filename,
                tree,
                select,
                ignore,
                [],
                repeatMessages,
                unusedArgs,
            )
            unusedChecker.run()
            stats.update(unusedChecker.counters)
            errors += unusedChecker.errors

            # check async function definitions
            asyncChecker = AsyncChecker(
                source,
                filename,
                tree,
                select,
                ignore,
                [],
                repeatMessages,
                {},  # no arguments yet
            )
            asyncChecker.run()
            stats.update(asyncChecker.counters)
            errors += asyncChecker.errors

            # checking logging statements
            loggingChecker = LoggingChecker(
                source,
                filename,
                tree,
                select,
                ignore,
                [],
                repeatMessages,
                {},  # no arguments yet
            )
            loggingChecker.run()
            stats.update(loggingChecker.counters)
            errors += loggingChecker.errors

        elif syntaxError:
            errors = [syntaxError]
            stats.update(syntaxStats)

    errorsDict = {}
    for error in errors:
        if error["line"] > len(source):
            error["line"] = len(source)
        # inverse processing of messages and fixes
        errorLine = errorsDict.setdefault(error["line"], [])
        errorLine.append((error["offset"], error))
    deferredFixes = {}
    results = []
    for lineno, errorsList in errorsDict.items():
        errorsList.sort(key=lambda x: x[0], reverse=True)
        for _, error in errorsList:
            error.update(
                {
                    "ignored": False,
                    "fixed": False,
                    "autofixing": False,
                    "fixcode": "",
                    "fixargs": [],
                    "securityOk": False,
                }
            )

            if source:
                errorCode = error["code"]
                lineFlags = extractLineFlags(source[lineno - 1].strip())
                with contextlib.suppress(IndexError):
                    lineFlags += extractLineFlags(
                        source[lineno].strip(), flagsLine=True
                    )

                if securityOk(errorCode, lineFlags):
                    error["securityOk"] = True

                if ignoreCode(errorCode, lineFlags):
                    error["ignored"] = True
                else:
                    if fixer:
                        res, fixcode, fixargs, id_ = fixer.fixIssue(
                            lineno, error["offset"], errorCode
                        )
                        if res == -1:
                            deferredFixes[id_] = error
                        else:
                            error.update(
                                {
                                    "fixed": res == 1,
                                    "autofixing": True,
                                    "fixcode": fixcode,
                                    "fixargs": fixargs,
                                }
                            )

            results.append(error)

    if fixer:
        deferredResults = fixer.finalize()
        for id_ in deferredResults:
            fixed, fixcode, fixargs = deferredResults[id_]
            error = deferredFixes[id_]
            error.update(
                {
                    "ignored": False,
                    "fixed": fixed == 1,
                    "autofixing": True,
                    "fixcode": fixcode,
                    "fixargs": fixargs,
                }
            )

        saveError = fixer.saveFile(encoding)
        if saveError:
            for error in results:
                error.update(
                    {
                        "fixcode": saveError[0],
                        "fixargs": saveError[1],
                    }
                )

    return stats, results
