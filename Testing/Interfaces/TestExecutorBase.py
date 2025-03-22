# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the executor base class for the various testing frameworks
and supporting classes.
"""

import os

from dataclasses import dataclass, field
from enum import IntEnum

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from eric7 import Preferences


class TestResultCategory(IntEnum):
    """
    Class defining the supported result categories.
    """

    RUNNING = 0
    FAIL = 1
    OK = 2
    SKIP = 3
    PENDING = 4


@dataclass
class TestResult:
    """
    Class containing the test result data.
    """

    category: TestResultCategory  # result category
    status: str  # test status
    name: str  # test name
    id: str  # test id
    description: str = ""  # short description of test
    message: str = ""  # short result message
    extra: list = None  # additional information text
    duration: float = None  # test duration
    filename: str = None  # file name of a (failed) test
    lineno: int = None  # line number of a (failed) test
    subtestResult: bool = False  # flag indicating the result of a subtest


@dataclass
class TestConfig:
    """
    Class containing the test run configuration.
    """

    interpreter: str  # path of the Python interpreter
    discover: bool = False  # auto discovery flag
    discoveryStart: str = ""  # start directory for auto discovery
    testCases: list = field(default_factory=list)  # list of selected test cases
    testFilename: str = ""  # name of the test script
    testName: str = ""  # name of the test function
    testMarkerExpression: str = ""  # marker expression for test selection
    testNamePattern: str = ""  # test name pattern expression or list
    failFast: bool = False  # stop on first fail
    failedOnly: bool = False  # run failed tests only
    collectCoverage: bool = False  # coverage collection flag
    eraseCoverage: bool = False  # erase coverage data first
    coverageFile: str = ""  # name of the coverage data file
    discoverOnly: bool = False  # test discovery only
    venvName: str = ""  # name of the virtual environment


class TestExecutorBase(QObject):
    """
    Base class for test framework specific implementations.

    @signal collected(list of tuple of (str, str, str, str, int, list)) emitted after
        all tests have been collected. Tuple elements are the test id, the test name,
        a short description of the test, the test file name, the line number of
        the test and the elements of the test path as a list.
    @signal collectError(list of tuple of (str, str)) emitted when errors
        are encountered during test collection. Tuple elements are the
        test name and the error message.
    @signal startTest(tuple of (str, str, str) emitted before tests are run.
        Tuple elements are test id, test name and short description.
    @signal testResult(TestResult) emitted when a test result is ready
    @signal testFinished(list, str) emitted when the test has finished.
        The elements are the list of test results and the captured output
        of the test worker (if any).
    @signal testRunAboutToBeStarted() emitted just before the test run will
        be started.
    @signal testRunFinished(int, float) emitted when the test run has finished.
        The elements are the number of tests run and the duration in seconds.
    @signal stop() emitted when the test process is being stopped.
    @signal coverageDataSaved(str) emitted after the coverage data was saved.
        The element is the absolute path of the coverage data file.
    @signal discoveryAboutToBeStarted() emitted just before the test discovery
        will be started
    @signal discoveryFinished(int, float) emitted when the discovery has finished.
        The elements are the number of discovered tests and the duration in seconds.
    """

    collected = pyqtSignal(list)
    collectError = pyqtSignal(list)
    startTest = pyqtSignal(tuple)
    testResult = pyqtSignal(TestResult)
    testFinished = pyqtSignal(list, str)
    testRunAboutToBeStarted = pyqtSignal()
    testRunFinished = pyqtSignal(int, float)
    stop = pyqtSignal()
    coverageDataSaved = pyqtSignal(str)
    discoveryAboutToBeStarted = pyqtSignal()
    discoveryFinished = pyqtSignal(int, float)

    module = ""
    name = ""
    runner = ""

    def __init__(self, testWidget):
        """
        Constructor

        @param testWidget reference to the unit test widget
        @type TestingWidget
        """
        super().__init__(testWidget)

        self.__process = None
        self.__debugger = None

        self._language = "Python3"

    @classmethod
    def isInstalled(cls, interpreter):
        """
        Class method to check whether a test framework is installed.

        The test is performed by checking, if a module loader can found.

        @param interpreter interpreter to be used for the test
        @type str
        @return flag indicating the test framework module is installed
        @rtype bool
        """
        if cls.runner:
            proc = QProcess()
            proc.start(interpreter, [cls.runner, "installed"])
            if proc.waitForFinished(3000):
                exitCode = proc.exitCode()
                return exitCode == 0

        return False

    def getVersions(self, interpreter):  # noqa: U100
        """
        Public method to get the test framework version and version information
        of its installed plugins.

        @param interpreter interpreter to be used for the test (unused)
        @type str
        @return dictionary containing the framework name and version and the
            list of available plugins with name and version each
        @rtype dict
        """
        return {}

    def hasCoverage(self, interpreter):  # noqa: U100
        """
        Public method to check, if the collection of coverage data is available.

        @param interpreter interpreter to be used for the test (unused)
        @type str
        @return flag indicating the availability of coverage functionality
        @rtype bool
        """
        return False

    def supportsPatterns(self, interpreter):  # noqa: U100
        """
        Public method to indicate the support for test filtering using test name
        patterns or a test name pattern expression.

        @param interpreter interpreter to be used for the test (unused)
        @type str
        @return flag indicating support of markers
        @rtype bool
        """
        return False

    def supportsMarkers(self, interpreter):  # noqa: U100
        """
        Public method to indicate the support for test filtering using markers and/or
        marker expressions.

        @param interpreter interpreter to be used for the test (unused)
        @type str
        @return flag indicating support of markers
        @rtype bool
        """
        return False

    def getMarkers(self, interpreter, workdir):  # noqa: U100
        """
        Public method to get the list of defined markers.

        @param interpreter interpreter to be used for the test (unused)
        @type str
        @param workdir name of the working directory
        @type str
        @return dictionary containing the marker as key and the associated description
            as value
        @rtype dict
        """
        return {}

    def createArguments(self, config):
        """
        Public method to create the arguments needed to start the test process.

        @param config configuration for the test execution
        @type TestConfig
        @return list of process arguments
        @rtype list of str
        @exception NotImplementedError this method needs to be implemented by
            derived classes
        """
        raise NotImplementedError

        return []

    def _prepareProcess(self, workDir, pythonpath):
        """
        Protected method to prepare a process object to be started.

        @param workDir working directory
        @type str
        @param pythonpath list of directories to be added to the Python path
        @type list of str
        @return prepared process object
        @rtype QProcess
        """
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.setWorkingDirectory(workDir)
        process.finished.connect(self.finished)
        if pythonpath:
            env = QProcessEnvironment.systemEnvironment()
            currentPythonPath = env.value("PYTHONPATH", None)
            newPythonPath = os.pathsep.join(pythonpath)
            if currentPythonPath:
                newPythonPath += os.pathsep + currentPythonPath
            env.insert("PYTHONPATH", newPythonPath)
            process.setProcessEnvironment(env)

        return process

    def discover(self, config, pythonpath):
        """
        Public method to start the test discovery process.

        @param config configuration for the test discovery
        @type TestConfig
        @param pythonpath list of directories to be added to the Python path
        @type list of str
        @exception RuntimeError raised if the the test discovery process did not start
        @exception ValueError raised if no start directory for the test discovery was
            given
        """
        if not config.discoveryStart:
            raise ValueError("No discovery start directory given.")

        self.__process = self._prepareProcess(config.discoveryStart, pythonpath)
        discoveryArgs = self.createArguments(config)
        self.discoveryAboutToBeStarted.emit()
        self.__process.start(config.interpreter, discoveryArgs)
        running = self.__process.waitForStarted()
        if not running:
            raise RuntimeError("Test discovery process did not start.")

    def start(self, config, pythonpath):
        """
        Public method to start the testing process.

        @param config configuration for the test execution
        @type TestConfig
        @param pythonpath list of directories to be added to the Python path
        @type list of str
        @exception RuntimeError raised if the the testing process did not start
        """
        workDir = (
            config.discoveryStart
            if config.discover
            else os.path.dirname(config.testFilename)
        )
        self.__process = self._prepareProcess(workDir, pythonpath)
        testArgs = self.createArguments(config)
        self.testRunAboutToBeStarted.emit()
        self.__process.start(config.interpreter, testArgs)
        running = self.__process.waitForStarted()
        if not running:
            raise RuntimeError("Test process did not start.")

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
        workDir = (
            config.discoveryStart
            if config.discover
            else os.path.dirname(config.testFilename)
        )
        testArgs = self.createArguments(config)
        if pythonpath:
            currentPythonPath = os.environ.get("PYTHONPATH")
            newPythonPath = os.pathsep.join(pythonpath)
            if currentPythonPath:
                newPythonPath += os.pathsep + currentPythonPath
            environment = {"PYTHONPATH": newPythonPath}
        else:
            environment = {}

        self.__debugger = debugger
        self.__debugger.debuggingFinished.connect(self.finished)
        self.testRunAboutToBeStarted.emit()

        self.__debugger.debugInternalScript(
            venvName=config.venvName,
            scriptName=testArgs[0],
            argv=testArgs[1:],
            workDir=workDir,
            environment=environment,
            clientType=self._language,
            forProject=False,
        )

    def finished(self):
        """
        Public method handling the unit test process been finished.

        This method should read the results (if necessary) and emit the signal
        testFinished.
        """
        if self.__debugger is not None:
            self.__debugger.debuggingFinished.disconnect(self.finished)
            self.__debugger = None

    def readAllOutput(self, process=None):
        """
        Public method to read all output of the test process.

        @param process reference to the process object
        @type QProcess
        @return test process output
        @rtype str
        """
        if process is None:
            process = self.__process
        output = (
            str(
                process.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            if process
            else ""
        )
        return output

    def stopIfRunning(self):
        """
        Public method to stop the testing process, if it is running.
        """
        if self.__process and self.__process.state() == QProcess.ProcessState.Running:
            self.__process.terminate()
            self.__process.waitForFinished(2000)
            self.__process.kill()
            self.__process.waitForFinished(3000)

            self.stop.emit()
