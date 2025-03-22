# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the test runner script for the 'unittest' framework.
"""

import importlib
import importlib.util
import json
import os
import sys
import time
import unittest

sys.path.insert(
    2,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
)
# three times up is our installation directory


class EricTestResult(unittest.TestResult):
    """
    Class implementing a TestResult derivative to send the data via a network
    connection.
    """

    def __init__(self, writer, failfast):
        """
        Constructor

        @param writer reference to the object to write the results to
        @type EricJsonWriter
        @param failfast flag indicating to stop at the first error
        @type bool
        """
        super().__init__()
        self.__writer = writer
        self.failfast = failfast
        self.__testsRun = 0

        self.__currentTestStatus = {}

    def addFailure(self, test, err):
        """
        Public method called if a test failed.

        @param test reference to the test object
        @type TestCase
        @param err tuple containing the exception data like sys.exc_info
            (exception type, exception instance, traceback)
        @type tuple
        """
        super().addFailure(test, err)
        tracebackLines = self._exc_info_to_string(err, test)

        self.__currentTestStatus.update(
            {
                "status": "failure",
                "traceback": tracebackLines,
            }
        )

    def addError(self, test, err):
        """
        Public method called if a test errored.

        @param test reference to the test object
        @type TestCase
        @param err tuple containing the exception data like sys.exc_info
            (exception type, exception instance, traceback)
        @type tuple
        """
        super().addError(test, err)
        tracebackLines = self._exc_info_to_string(err, test)

        self.__currentTestStatus.update(
            {
                "status": "error",
                "traceback": tracebackLines,
            }
        )

    def addSkip(self, test, reason):
        """
        Public method called if a test was skipped.

        @param test reference to the test object
        @type TestCase
        @param reason reason for skipping the test
        @type str
        """
        super().addSkip(test, reason)

        self.__currentTestStatus.update(
            {
                "status": "skipped",
                "shortmsg": reason,
            }
        )

    def addExpectedFailure(self, test, err):
        """
        Public method called if a test failed expected.

        @param test reference to the test object
        @type TestCase
        @param err tuple containing the exception data like sys.exc_info
            (exception type, exception instance, traceback)
        @type tuple
        """
        super().addExpectedFailure(test, err)
        tracebackLines = self._exc_info_to_string(err, test)

        self.__currentTestStatus.update(
            {
                "status": "expected failure",
                "traceback": tracebackLines,
            }
        )

    def addUnexpectedSuccess(self, test):
        """
        Public method called if a test succeeded expectedly.

        @param test reference to the test object
        @type TestCase
        """
        super().addUnexpectedSuccess(test)

        self.__currentTestStatus["status"] = "unexpected success"

    def addSubTest(self, test, subtest, err):
        """
        Public method called for each subtest to record its result.

        @param test reference to the test object
        @type TestCase
        @param subtest reference to the subtest object
        @type TestCase
        @param err tuple containing the exception data like sys.exc_info
            (exception type, exception instance, traceback)
        @type tuple
        """
        if err is not None:
            super().addSubTest(test, subtest, err)
            tracebackLines = self._exc_info_to_string(err, test)
            status = "failure" if issubclass(err[0], test.failureException) else "error"

            # record the last subtest fail status as the overall status
            self.__currentTestStatus["status"] = status

            self.__writer.write(
                {
                    "event": "result",
                    "status": status,
                    "name": str(subtest),
                    "id": subtest.id(),
                    "description": subtest.shortDescription(),
                    "traceback": tracebackLines,
                    "subtest": True,
                }
            )

            if self.failfast:
                self.stop()
        else:
            self.__writer.write(
                {
                    "event": "result",
                    "status": "success",
                    "name": str(subtest),
                    "id": subtest.id(),
                    "description": subtest.shortDescription(),
                    "subtest": True,
                }
            )

    def startTest(self, test):
        """
        Public method called at the start of a test.

        @param test reference to the test object
        @type TestCase
        """
        super().startTest(test)

        self.__testsRun += 1
        self.__currentTestStatus = {
            "event": "result",
            "status": "success",
            "name": str(test),
            "id": test.id(),
            "description": test.shortDescription(),
            "subtest": False,
        }

        self.__writer.write(
            {
                "event": "started",
                "name": str(test),
                "id": test.id(),
                "description": test.shortDescription(),
            }
        )

        self.__startTime = time.monotonic_ns()

    def stopTest(self, test):
        """
        Public method called at the end of a test.

        @param test reference to the test object
        @type TestCase
        """
        stopTime = time.monotonic_ns()
        duration = (stopTime - self.__startTime) / 1_000_000  # ms

        super().stopTest(test)

        self.__currentTestStatus["duration_ms"] = duration
        self.__writer.write(self.__currentTestStatus)

    def startTestRun(self):
        """
        Public method called once before any tests are executed.
        """
        self.__totalStartTime = time.monotonic_ns()
        self.__testsRun = 0

    def stopTestRun(self):
        """
        Public method called once after all tests are executed.
        """
        stopTime = time.monotonic_ns()
        duration = (stopTime - self.__totalStartTime) / 1_000_000_000  # s

        self.__writer.write(
            {
                "event": "finished",
                "duration_s": duration,
                "tests": self.__testsRun,
            }
        )


def _assembleTestCasesList(suite, start):
    """
    Protected function to assemble a list of test cases included in a test
    suite.

    @param suite test suite to be inspected
    @type unittest.TestSuite
    @param start name of directory discovery was started at
    @type str
    @return list of tuples containing the test case ID, the string representation,
        a short description and the path of the test file name
    @rtype list of tuples of (str, str, str, str)
    """
    testCases = []
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            testCases.extend(_assembleTestCasesList(test, start))
        else:
            testId = test.id()
            if (
                "ModuleImportFailure" not in testId
                and "LoadTestsFailure" not in testId
                and "_FailedTest" not in testId
            ):
                filename = os.path.join(
                    start, test.__module__.replace(".", os.sep) + ".py"
                )
                testCases.append((testId, str(test), test.shortDescription(), filename))
    return testCases


def runtest(argv, discoverOnly=False):
    """
    Function to run and/or discover the tests.

    @param argv list of command line parameters.
    @type list of str
    @param discoverOnly flag indicating to just discover the available test cases
        (defaults to False)
    @type bool (optional)
    """
    from eric7.EricNetwork.EricJsonStreamWriter import EricJsonWriter

    writer = EricJsonWriter(argv[0], int(argv[1]))
    del argv[:2]

    # process arguments
    if argv[0] == "discover":
        discover = True
        argv.pop(0)
        if argv[0] == "--start-directory":
            discoveryStart = argv[1]
            del argv[:2]
    else:
        discover = False
        discoveryStart = ""

    failfast = "--failfast" in argv
    if failfast:
        argv.remove("--failfast")

    collectCoverage = "--cover" in argv
    if collectCoverage:
        argv.remove("--cover")
    coverageErase = "--cover-erase" in argv
    if coverageErase:
        argv.remove("--cover-erase")
    if "--cover-file" in argv:
        index = argv.index("--cover-file")
        covDataFile = argv[index + 1]
        del argv[index : index + 2]
    else:
        covDataFile = ""

    if "--pattern" in argv:
        index = argv.index("--pattern")
        testNamePatterns = argv[index + 1].split()
        del argv[index : index + 2]
    else:
        testNamePatterns = []

    if argv and argv[0] == "--failed-only":
        if discover:
            testFileName = ""
            failed = argv[1:]
        else:
            testFileName = argv[1]
            failed = argv[2:]
    else:
        failed = []
        if discover:
            testFileName = testName = ""
            testCases = argv[:]
        else:
            testFileName, testName = argv[:2]
            del argv[:2]

    if testFileName:
        sys.path.insert(1, os.path.dirname(os.path.abspath(testFileName)))
    elif discoveryStart:
        sys.path.insert(1, os.path.abspath(discoveryStart))

    # setup test coverage
    if collectCoverage:
        if not covDataFile:
            if discover:
                covname = os.path.join(discoveryStart, "test")
            elif testFileName:
                covname = os.path.splitext(os.path.abspath(testFileName))[0]
            else:
                covname = "test"
            covDataFile = "{0}.coverage".format(covname)
        if not os.path.isabs(covDataFile):
            covDataFile = os.path.abspath(covDataFile)

        sys.path.insert(
            2,
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__), "..", "..", "DebugClients", "Python"
                )
            ),
        )
        try:
            from coverage import Coverage  # __IGNORE_WARNING_I10__

            cover = Coverage(data_file=covDataFile)
            if coverageErase:
                cover.erase()
            cover.start()
        except ImportError:
            cover = None
    else:
        cover = None

    try:
        testLoader = unittest.TestLoader()
        if testNamePatterns:
            testLoader.testNamePatterns = testNamePatterns

        if discover and not failed:
            if testCases:
                test = testLoader.loadTestsFromNames(testCases)
            else:
                test = testLoader.discover(discoveryStart)
        else:
            if testFileName:
                module = importlib.import_module(
                    os.path.splitext(os.path.basename(testFileName))[0]
                )
            else:
                module = None
            if failed:
                if module:
                    failed = [t.split(".", 1)[1] for t in failed]
                test = testLoader.loadTestsFromNames(failed, module)
            else:
                test = (
                    testLoader.loadTestsFromName(testName, module)
                    if testName != "@NONE@"
                    else testLoader.loadTestsFromModule(module)
                )
    except Exception as err:
        print("Exception:", str(err))
        writer.write(
            {
                "event": "collecterror",
                "error": str(err),
            }
        )
        sys.exit(1)

    collectedTests = {
        "event": "collected",
        "tests": [
            {"id": id, "name": name, "description": desc, "filename": filename}
            for id, name, desc, filename in _assembleTestCasesList(test, discoveryStart)
        ],
    }
    writer.write(collectedTests)

    if not discoverOnly:
        testResult = EricTestResult(writer, failfast)
        startTestRun = getattr(testResult, "startTestRun", None)
        if startTestRun is not None:
            startTestRun()
        try:
            test.run(testResult)
        finally:
            if cover:
                cover.stop()
                cover.save()
                writer.write(
                    {
                        "event": "coverage",
                        "file": covDataFile,
                    }
                )
            stopTestRun = getattr(testResult, "stopTestRun", None)
            if stopTestRun is not None:
                stopTestRun()

    writer.close()
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "installed":
            sys.exit(0)

        elif command == "versions":
            import platform

            versions = {
                "name": "unittest",
                "version": platform.python_version(),
                "plugins": [],
            }
            print(json.dumps(versions))
            sys.exit(0)

        elif command == "has_coverage":
            if importlib.util.find_spec("coverage") is None:
                # not available
                sys.exit(1)
            else:
                # available
                sys.exit(0)

        elif command == "runtest":
            runtest(sys.argv[2:])
            sys.exit(0)

        elif command == "discovery":
            runtest(sys.argv[2:], discoverOnly=True)
            sys.exit(0)

    sys.exit(42)

#
# eflag: noqa = M801
