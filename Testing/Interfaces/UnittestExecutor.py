# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the executor for the standard 'unittest' framework.
"""

import contextlib
import json
import os
import re

from PyQt6.QtCore import QProcess, pyqtSlot

from eric7 import Preferences
from eric7.EricNetwork.EricJsonStreamReader import EricJsonReader

from .TestExecutorBase import TestExecutorBase, TestResult, TestResultCategory


class UnittestExecutor(TestExecutorBase):
    """
    Class implementing the executor for the standard 'unittest' framework.
    """

    module = "unittest"
    name = "unittest"

    runner = os.path.join(os.path.dirname(__file__), "UnittestRunner.py")

    def __init__(self, testWidget):
        """
        Constructor

        @param testWidget reference to the unit test widget
        @type TestingWidget
        """
        super().__init__(testWidget)

        self.__statusCategoryMapping = {
            "failure": TestResultCategory.FAIL,
            "error": TestResultCategory.FAIL,
            "skipped": TestResultCategory.SKIP,
            "expected failure": TestResultCategory.OK,
            "unexpected success": TestResultCategory.FAIL,
            "success": TestResultCategory.OK,
        }

        self.__statusDisplayMapping = {
            "failure": self.tr("Failure"),
            "error": self.tr("Error"),
            "skipped": self.tr("Skipped"),
            "expected failure": self.tr("Expected Failure"),
            "unexpected success": self.tr("Unexpected Success"),
            "success": self.tr("Success"),
        }

        self.__testWidget = testWidget

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
        proc.start(interpreter, [UnittestExecutor.runner, "versions"])
        if proc.waitForFinished(3000):
            exitCode = proc.exitCode()
            if exitCode == 0:
                versionsStr = self.readAllOutput(proc)
                with contextlib.suppress(json.JSONDecodeError):
                    return json.loads(versionsStr)

        return {}

    def hasCoverage(self, interpreter):
        """
        Public method to check, if the collection of coverage data is available.

        @param interpreter interpreter to be used for the test
        @type str
        @return flag indicating the availability of coverage functionality
        @rtype bool
        """
        proc = QProcess()
        proc.start(interpreter, [UnittestExecutor.runner, "has_coverage"])
        if proc.waitForFinished(3000):
            return proc.exitCode() == 0

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

    def createArguments(self, config):
        """
        Public method to create the arguments needed to start the test process.

        @param config configuration for the test execution
        @type TestConfig
        @return list of process arguments
        @rtype list of str
        """
        args = [
            UnittestExecutor.runner,
            "discovery" if config.discoverOnly else "runtest",
            self.reader.address(),
            str(self.reader.port()),
        ]

        if config.discover:
            args.extend(
                [
                    "discover",
                    "--start-directory",
                    config.discoveryStart,
                ]
            )

        if config.failFast:
            args.append("--failfast")

        if config.collectCoverage:
            args.append("--cover")
            if config.eraseCoverage:
                args.append("--cover-erase")
            if config.coverageFile:
                args.append("--cover-file")
                args.append(config.coverageFile)

        if config.testNamePattern:
            args.append("--pattern")
            args.append(config.testNamePattern)

        if config.failedOnly:
            args.append("--failed-only")
            if config.testFilename:
                args.append(config.testFilename)
            args.extend(self.__testWidget.getFailedTests())
        elif config.testCases:
            args.extend(config.testCases)
        elif config.testFilename:
            args.append(config.testFilename)
            args.append(config.testName if config.testName else "@NONE@")
            # @NONE@ is just a marker for no test name given

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
            name="Unittest Reader",
            interface=Preferences.getDebugger("NetworkInterface"),
            parent=self,
        )
        self.reader.dataReceived.connect(self.__processData)

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
            name="Unittest Reader",
            interface=Preferences.getDebugger("NetworkInterface"),
            parent=self,
        )
        self.reader.dataReceived.connect(self.__processData)

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
            name="Unittest Reader",
            interface=Preferences.getDebugger("NetworkInterface"),
            parent=self,
        )
        self.reader.dataReceived.connect(self.__processData)

        super().startDebug(config, pythonpath, debugger)

    def finished(self):
        """
        Public method handling the unit test process been finished.

        This method should read the results (if necessary) and emit the signal
        testFinished.
        """
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
        # error collecting tests
        if data["event"] == "collecterror":
            self.collectError.emit([("", data["error"])])

        # tests collected
        elif data["event"] == "collected":
            self.collected.emit(
                [
                    (
                        t["id"],
                        t["name"],
                        t["description"],
                        t["filename"],
                        0,
                        t["id"].split("."),
                    )
                    for t in data["tests"]
                ]
            )

        # test started
        elif data["event"] == "started":
            self.startTest.emit((data["id"], data["name"], data["description"]))

        # test result
        elif data["event"] == "result":
            filename, lineno = None, None
            tracebackLines = data.get("traceback", "").splitlines()
            if tracebackLines:
                # find the last entry matching the pattern
                for index in range(len(tracebackLines) - 1, -1, -1):
                    fmatch = re.search(
                        r'File "(.*?)", line (\d*?),.*', tracebackLines[index]
                    )
                    if fmatch:
                        break
                if fmatch:
                    filename = fmatch.group(1)
                    lineno = int(fmatch.group(2))

            message = data.get("shortmsg", "")
            if not message and tracebackLines:
                # search the line containing the assertion error
                for index in range(len(tracebackLines) - 1, -1, -1):
                    line = tracebackLines[index].strip()
                    if line.startswith("AssertionError:"):
                        message = line.replace("AssertionError:", "").strip()
                        break

            self.testResult.emit(
                TestResult(
                    category=self.__statusCategoryMapping[data["status"]],
                    status=self.__statusDisplayMapping[data["status"]],
                    name=data["name"],
                    id=data["id"],
                    description=data["description"],
                    message=message,
                    extra=tracebackLines,
                    duration=data.get("duration_ms"),
                    filename=filename,
                    lineno=lineno,
                    subtestResult=data.get("subtest", False),
                )
            )

        # test run finished
        elif data["event"] == "finished":
            self.testRunFinished.emit(data["tests"], data["duration_s"])

        # coverage data
        elif data["event"] == "coverage":
            self.coverageDataSaved.emit(data["file"])
