# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the executor for the 'pytest' framework.
"""

import contextlib
import json
import os

from PyQt6.QtCore import QProcess, pyqtSlot

from eric7 import Preferences
from eric7.EricNetwork.EricJsonStreamReader import EricJsonReader

from .TestExecutorBase import TestExecutorBase, TestResult, TestResultCategory


class PytestExecutor(TestExecutorBase):
    """
    Class implementing the executor for the 'pytest' framework.
    """

    module = "pytest"
    name = "pytest"

    runner = os.path.join(os.path.dirname(__file__), "PytestRunner.py")

    def __init__(self, testWidget):
        """
        Constructor

        @param testWidget reference to the unit test widget
        @type TestingWidget
        """
        super().__init__(testWidget)

        self.__statusDisplayMapping = {
            "failed": self.tr("Failure"),
            "skipped": self.tr("Skipped"),
            "xfailed": self.tr("Expected Failure"),
            "xpassed": self.tr("Unexpected Success"),
            "passed": self.tr("Success"),
        }

        self.__config = None

    def getVersions(self, interpreter):
        """
        Public method to get the test framework version and version information
        of its installed plugins.

        @param interpreter interpreter to be used for the test
        @type str
        @return dictionary containing the framework name and version and the
            list of available plugins with name and version each
        @rtype dict
        """
        proc = QProcess()
        proc.start(interpreter, [PytestExecutor.runner, "versions"])
        if proc.waitForFinished(3000):
            exitCode = proc.exitCode()
            if exitCode == 0:
                outputLines = self.readAllOutput(proc).splitlines()
                for line in outputLines:
                    if line.startswith("{") and line.endswith("}"):
                        with contextlib.suppress(json.JSONDecodeError):
                            return json.loads(line)

        return {}

    def hasCoverage(self, interpreter):
        """
        Public method to check, if the collection of coverage data is available.

        @param interpreter interpreter to be used for the test
        @type str
        @return flag indicating the availability of coverage functionality
        @rtype bool
        """
        versions = self.getVersions(interpreter)
        if "plugins" in versions:
            return any(plugin["name"] == "pytest-cov" for plugin in versions["plugins"])

        return False

    def supportsPatterns(self, _interpreter):
        """
        Public method to indicate the support for test filtering using test name
        patterns or a test name pattern expression.

        @param _interpreter interpreter to be used for the test (unused)
        @type str
        @return flag indicating support of markers
        @rtype bool
        """
        return True

    def supportsMarkers(self, _interpreter):
        """
        Public method to indicate the support for test filtering using markers and/or
        marker expressions.

        @param _interpreter interpreter to be used for the test (unused)
        @type str
        @return flag indicating support of markers
        @rtype bool
        """
        return True

    def getMarkers(self, interpreter, workdir):
        """
        Public method to get the list of defined markers.

        @param interpreter interpreter to be used for the test
        @type str
        @param workdir name of the working directory
        @type str
        @return dictionary containing the marker as key and the associated description
            as value
        @rtype dict
        """
        proc = QProcess()
        proc.setWorkingDirectory(workdir)
        proc.start(interpreter, [PytestExecutor.runner, "markers"])
        if proc.waitForFinished(3000):
            exitCode = proc.exitCode()
            if exitCode == 0:
                outputLines = self.readAllOutput(proc).splitlines()
                for line in outputLines:
                    if line.startswith("{") and line.endswith("}"):
                        with contextlib.suppress(json.JSONDecodeError):
                            return json.loads(line)

        return {}

    def createArguments(self, config):
        """
        Public method to create the arguments needed to start the test process.

        @param config configuration for the test execution
        @type TestConfig
        @return list of process arguments
        @rtype list of str
        """
        #
        # collectCoverage: --cov= + --cov-report= to suppress report generation
        # eraseCoverage: --cov-append if eraseCoverage is False
        # coverageFile
        #
        args = [
            PytestExecutor.runner,
            "runtest",
            self.reader.address(),
            str(self.reader.port()),
            "--quiet",
        ]

        if config.failFast:
            args.append("--exitfirst")

        if config.failedOnly:
            args.append("--last-failed")
        else:
            args.append("--cache-clear")

        if not config.discoverOnly and config.collectCoverage:
            args.extend(["--cov=.", "--cov-report="])
            if not config.eraseCoverage:
                args.append("--cov-append")

        if config.testMarkerExpression:
            args.append("-m")
            args.append(config.testMarkerExpression)

        if config.testNamePattern:
            args.append("-k")
            args.append(config.testNamePattern)

        if config.discoverOnly:
            args.append("--collect-only")

        if config.testCases:
            args.extend(config.testCases)
        elif config.testFilename:
            if config.testName:
                args.append(
                    "{0}::{1}".format(
                        config.testFilename, config.testName.replace(".", "::")
                    )
                )
            else:
                args.append(config.testFilename)

        return args

    def discover(self, config, pythonpath):
        """
        Public method to start the test discovery process.

        @param config configuration for the test discovery
        @type TestConfig
        @param pythonpath list of directories to be added to the Python path
        @type list of str
        """
        self.reader = EricJsonReader(
            name="Pytest Reader",
            interface=Preferences.getDebugger("NetworkInterface"),
            parent=self,
        )
        self.reader.dataReceived.connect(self.__processData)

        self.__config = config

        pythonpath.insert(0, os.path.abspath(config.discoveryStart))
        self.__rootdir = config.discoveryStart

        super().discover(config, pythonpath)

    def start(self, config, pythonpath):
        """
        Public method to start the testing process.

        @param config configuration for the test execution
        @type TestConfig
        @param pythonpath list of directories to be added to the Python path
        @type list of str
        """
        self.reader = EricJsonReader(
            name="Pytest Reader",
            interface=Preferences.getDebugger("NetworkInterface"),
            parent=self,
        )
        self.reader.dataReceived.connect(self.__processData)

        self.__config = config

        if config.discoveryStart:
            pythonpath.insert(0, os.path.abspath(config.discoveryStart))
        elif config.testFilename:
            pythonpath.insert(0, os.path.abspath(os.path.dirname(config.testFilename)))

        if config.discover:
            self.__rootdir = config.discoveryStart
        elif config.testFilename:
            self.__rootdir = os.path.dirname(config.testFilename)
        else:
            self.__rootdir = ""

        super().start(config, pythonpath)

    def startDebug(self, config, pythonpath, debugger):
        """
        Public method to start the test run with debugger support.

        @param config configuration for the test execution
        @type TestConfig
        @param pythonpath list of directories to be added to the Python path
        @type list of str
        @param debugger refference to the debugger interface
        @type DebugUI
        """
        self.reader = EricJsonReader(
            name="Pytest Reader",
            interface=Preferences.getDebugger("NetworkInterface"),
            parent=self,
        )
        self.reader.dataReceived.connect(self.__processData)

        self.__config = config

        if config.discoveryStart:
            pythonpath.insert(0, os.path.abspath(config.discoveryStart))
        elif config.testFilename:
            pythonpath.insert(0, os.path.abspath(os.path.dirname(config.testFilename)))

        if config.discover:
            self.__rootdir = config.discoveryStart
        elif config.testFilename:
            self.__rootdir = os.path.dirname(config.testFilename)
        else:
            self.__rootdir = ""

        super().startDebug(config, pythonpath, debugger)

    def finished(self):
        """
        Public method handling the unit test process been finished.

        This method should read the results (if necessary) and emit the signal
        testFinished.
        """
        if self.__config.collectCoverage:
            self.coverageDataSaved.emit(os.path.join(self.__rootdir, ".coverage"))

        self.__config = None

        self.reader.close()

        output = self.readAllOutput()
        self.testFinished.emit([], output)

        super().finished()

    @pyqtSlot(object)
    def __processData(self, data):
        """
        Private slot to process the received data.

        @param data data object received
        @type dict
        """
        # test configuration
        if data["event"] == "config":
            self.__rootdir = data["root"]

        # error collecting tests
        elif data["event"] == "collecterror":
            name = self.__normalizeModuleName(data["nodeid"])
            self.collectError.emit([(name, data["report"])])

        # tests collected
        elif data["event"] == "collected":
            self.collected.emit(
                [
                    (
                        data["nodeid"],
                        self.__nodeid2testname(data["nodeid"]),
                        "",
                        os.path.join(self.__rootdir, data["filename"]),
                        data["linenumber"],
                        self.__nodeid2testpath(data["nodeid"]),
                    )
                ]
            )

        # test started
        elif data["event"] == "starttest":
            self.startTest.emit(
                (data["nodeid"], self.__nodeid2testname(data["nodeid"]), "")
            )

        # test result
        elif data["event"] == "result":
            if data["status"] in ("failed", "xpassed") or data["with_error"]:
                category = TestResultCategory.FAIL
            elif data["status"] in ("passed", "xfailed"):
                category = TestResultCategory.OK
            else:
                category = TestResultCategory.SKIP

            status = (
                self.tr("Error")
                if data["with_error"]
                else self.__statusDisplayMapping[data["status"]]
            )

            message = data.get("message", "")
            extraText = data.get("report", "")
            reportPhase = data.get("report_phase")
            if reportPhase in ("setup", "teardown"):
                message = self.tr("ERROR at {0}: {1}", "phase, message").format(
                    reportPhase, message
                )
                extraText = self.tr("ERROR at {0}: {1}", "phase, extra text").format(
                    reportPhase, extraText
                )
            sections = data.get("sections", [])
            if sections:
                extraText += "\n"
                for heading, text in sections:
                    extraText += "----- {0} -----\n{1}".format(heading, text)

            duration = data.get("duration_s")
            if duration:
                # convert to ms
                duration *= 1000

            filename = data["filename"]
            if self.__rootdir:
                filename = os.path.join(self.__rootdir, filename)

            self.testResult.emit(
                TestResult(
                    category=category,
                    status=status,
                    name=self.__nodeid2testname(data["nodeid"]),
                    id=data["nodeid"],
                    description="",
                    message=message,
                    extra=extraText.rstrip().splitlines(),
                    duration=duration,
                    filename=filename,
                    lineno=data.get("linenumber", 0) + 1,
                    # pytest reports 0-based line numbers
                )
            )

        # test run finished
        elif data["event"] == "finished":
            self.testRunFinished.emit(data["tests"], data["duration_s"])

    def __normalizeModuleName(self, name):
        r"""
        Private method to convert a module name reported by pytest to Python
        conventions.

        This method strips the extensions '.pyw' and '.py' first and replaces
        '/' and '\' thereafter.

        @param name module name reported by pytest
        @type str
        @return module name iaw. Python conventions
        @rtype str
        """
        return (
            name.replace(".pyw", "")
            .replace(".py", "")
            .replace("/", ".")
            .replace("\\", ".")
        )

    def __nodeid2testname(self, nodeid):
        """
        Private method to convert a nodeid to a test name.

        @param nodeid nodeid to be converted
        @type str
        @return test name
        @rtype str
        """
        module, name = nodeid.split("::", 1)
        module = self.__normalizeModuleName(module)
        name = name.replace("::", ".")
        testname, name = "{0}.{1}".format(module, name).rsplit(".", 1)
        return "{0} ({1})".format(name, testname)

    def __nodeid2testpath(self, nodeid):
        """
        Private method to convert a nodeid to a test path list.

        @param nodeid nodeid to be converted
        @type str
        @return test path list
        @rtype list of str
        """
        module, name = nodeid.split("::", 1)
        module = self.__normalizeModuleName(module)
        name = "{0}.{1}".format(module, name.replace("::", "."))
        return name.split(".")
