# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the test runner script for the 'pytest' framework.
"""

import contextlib
import importlib.util
import json
import os
import sys
import time

sys.path.insert(
    2,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
)
# three times up is our installation directory

with contextlib.suppress(ImportError):
    import pytest


class GetPluginVersionsPlugin:
    """
    Class implementing a pytest plugin to extract the version info of all
    installed plugins.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__versions = []

    def pytest_cmdline_main(self, config):
        """
        Public method called for performing the main command line action.

        @param config pytest config object
        @type Config
        """
        pluginInfo = config.pluginmanager.list_plugin_distinfo()
        if pluginInfo:
            for _plugin, dist in pluginInfo:
                self.__versions.append(
                    {"name": dist.project_name, "version": dist.version}
                )

    def getVersions(self):
        """
        Public method to get the assembled list of plugin versions.

        @return list of collected plugin versions
        @rtype list of dict
        """
        return self.__versions


class GetMarkersPlugin:
    """
    Class implementing a pytest plugin to extract the list of all defined markers.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__markers = {}

    @pytest.hookimpl(tryfirst=True)
    def pytest_cmdline_main(self, config):
        """
        Public method called for performing the main command line action.

        @param config pytest config object
        @type Config
        """
        config._do_configure()
        for line in config.getini("markers"):
            parts = line.split(":", 1)
            name = parts[0]
            rest = parts[1] if len(parts) == 2 else ""
            self.__markers[name] = rest
        config._ensure_unconfigure()

        print(json.dumps(self.__markers))
        sys.exit(0)

    def getMarkers(self):
        """
        Public method to get the assembled list of markers.

        @return list of collected markers (marker name as key and description as value)
        @rtype dict
        """
        return self.__markers


class EricPlugin:
    """
    Class implementing a pytest plugin which reports the data in a format
    suitable for the PytestExecutor.
    """

    def __init__(self, writer):
        """
        Constructor

        @param writer reference to the object to write the results to
        @type EricJsonWriter
        """
        self.__writer = writer

        self.__testsRun = 0

    def __initializeReportData(self):
        """
        Private method to initialize attributes for data collection.
        """
        self.__status = "---"
        self.__duration = 0
        self.__report = []
        self.__reportPhase = ""
        self.__sections = []
        self.__hadError = False
        self.__wasSkipped = False
        self.__wasXfail = False

    def pytest_report_header(self, config):
        """
        Public method called by pytest before any reporting.

        @param config reference to the configuration object
        @type Config
        """
        self.__writer.write({"event": "config", "root": str(config.rootdir)})

    def pytest_collectreport(self, report):
        """
        Public method called by pytest after the tests have been collected.

        @param report reference to the report object
        @type CollectReport
        """
        if report.outcome == "failed":
            self.__writer.write(
                {
                    "event": "collecterror",
                    "nodeid": report.nodeid,
                    "report": str(report.longrepr),
                }
            )

    def pytest_itemcollected(self, item):
        """
        Public malled by pytest after a test item has been collected.

        @param item reference to the collected test item
        @type Item
        """
        self.__writer.write(
            {
                "event": "collected",
                "nodeid": item.nodeid,
                "name": item.name,
                "filename": item.location[0],
                "linenumber": item.location[1],
            }
        )

    def pytest_runtest_logstart(self, nodeid, location):  # noqa: U100
        """
        Public method called by pytest before running a test.

        @param nodeid node id of the test item
        @type str
        @param location tuple containing the file name, the line number and
            the test name (unused)
        @type tuple of (str, int, str)
        """
        self.__testsRun += 1

        self.__writer.write(
            {
                "event": "starttest",
                "nodeid": nodeid,
            }
        )

        self.__initializeReportData()

    def pytest_runtest_logreport(self, report):
        """
        Public method called by pytest when a test phase (setup, call and
            teardown) has been completed.

        @param report reference to the test report object
        @type TestReport
        """
        if report.when == "call":
            self.__status = report.outcome
            self.__duration = report.duration
        else:
            if report.outcome == "failed":
                self.__hadError = True
            elif report.outcome == "skipped":
                self.__wasSkipped = True

        if hasattr(report, "wasxfail"):
            self.__wasXfail = True
            self.__report.append(report.wasxfail)
            self.__reportPhase = report.when

        self.__sections = report.sections

        if report.longrepr:
            self.__reportPhase = report.when
            if (
                hasattr(report.longrepr, "reprcrash")
                and report.longrepr.reprcrash is not None
            ):
                self.__report.append(report.longrepr.reprcrash.message)
            if isinstance(report.longrepr, tuple):
                self.__report.append(report.longrepr[2])
            elif isinstance(report.longrepr, str):
                self.__report.append(report.longrepr)
            else:
                self.__report.append(str(report.longrepr))

    def pytest_runtest_logfinish(self, nodeid, location):
        """
        Public method called by pytest after a test has been completed.

        @param nodeid node id of the test item
        @type str
        @param location tuple containing the file name, the line number and
            the test name
        @type tuple of (str, int, str)
        """
        if self.__wasXfail:
            self.__status = "xpassed" if self.__status == "passed" else "xfailed"
        elif self.__wasSkipped:
            self.__status = "skipped"

        data = {
            "event": "result",
            "status": self.__status,
            "with_error": self.__hadError,
            "sections": self.__sections,
            "duration_s": self.__duration,
            "nodeid": nodeid,
            "filename": location[0],
            "linenumber": location[1],
            "report_phase": self.__reportPhase,
        }
        if self.__report:
            messageLines = self.__report[0].rstrip().splitlines()
            data["message"] = messageLines[0]
        data["report"] = "\n".join(self.__report)

        self.__writer.write(data)

    def pytest_sessionstart(self, session):  # noqa: U100
        """
        Public method called by pytest before performing collection and
        entering the run test loop.

        @param session reference to the session object (unused)
        @type Session
        """
        self.__totalStartTime = time.monotonic_ns()
        self.__testsRun = 0

    def pytest_sessionfinish(self, session, exitstatus):  # noqa: U100
        """
        Public method called by pytest after the whole test run finished.

        @param session reference to the session object (unused)
        @type Session
        @param exitstatus exit status (unused)
        @type int or ExitCode
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


def getVersions():
    """
    Function to determine the framework version and versions of all available
    plugins.
    """
    try:
        import pytest  # __IGNORE_WARNING_I10__

        versions = {
            "name": "pytest",
            "version": pytest.__version__,
            "plugins": [],
        }

        # --capture=sys needed on Windows to avoid
        # ValueError: saved filedescriptor not valid anymore
        plugin = GetPluginVersionsPlugin()
        pytest.main(["--version", "--capture=sys"], plugins=[plugin])
        versions["plugins"] = plugin.getVersions()
    except ImportError:
        versions = {}

    print(json.dumps(versions))
    sys.exit(0)


def getMarkers():
    """
    Function to determine the defined markers and their descriptions.
    """
    try:
        import pytest  # __IGNORE_WARNING_I10__

        # --capture=sys needed on Windows to avoid
        # ValueError: saved filedescriptor not valid anymore
        plugin = GetMarkersPlugin()
        pytest.main(["--markers", "--capture=sys"], plugins=[plugin])
        # dumping the markers is done in the plugin
    except ImportError:
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "installed":
        if bool(importlib.util.find_spec("pytest")):
            sys.exit(0)
        else:
            sys.exit(1)

    elif command == "versions":
        getVersions()

    elif command == "markers":
        getMarkers()

    elif command == "runtest":
        import pytest

        from eric7.EricNetwork.EricJsonStreamWriter import EricJsonWriter

        writer = EricJsonWriter(sys.argv[2], int(sys.argv[3]))
        pytest.main(sys.argv[4:], plugins=[EricPlugin(writer)])
        writer.close()
        sys.exit(0)

    sys.exit(42)

#
# eflag: noqa = M801
