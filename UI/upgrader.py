#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Script to upgrade the packages eric depends on.

This process must be performed while eric is closed. The script will upgrade
the requested packages and will restart eric.
"""

import contextlib
import subprocess  # secok
import sys
import time

_pyqtPackages = [
    "pyqt6",
    "pyqt6-sip",
    "pyqt6-webengine",
    "pyqt6-charts",
    "pyqt6-qscintilla",
    "pyqt6-qt6",
    "pyqt6-webengine-qt6",
    "pyqt6-charts-qt6",
]
_ericPackages = ["eric-ide"]


def doUpgrade(packages):
    """
    Function to upgrade the given packages via pip.

    @param packages list of packages to be upgraded
    @type list of str
    @return flag indicating a successful installation
    @rtype bool
    """
    exitCode = subprocess.run(  # secok
        [sys.executable, "-m", "pip", "install", "--prefer-binary", "--upgrade"]
        + packages
    ).returncode
    ok = exitCode == 0

    return ok


def startEric(args):
    """
    Function to start eric with the given arguments.

    @param args list containing the start arguments
    @type list of str
    """
    args = [sys.executable] + args
    subprocess.Popen(args)  # secok


def main():
    """
    Main entry point into the upgrader.
    """
    try:
        ddindex = sys.argv.index("--")
    except ValueError:
        # '--' was not found. Start eric with all parameters given.
        ddindex = 0

    ericStartArgs = sys.argv[ddindex + 1 :] if bool(ddindex) else []
    if not ericStartArgs:
        # create default start arguments
        ericStartArgs = ["-m", "eric7", "--start-session"]

    upgraderArgs = sys.argv[1:ddindex] if bool(ddindex) else sys.argv[:]

    upgradeType = ""
    upgradeDelay = 2

    for arg in upgraderArgs:
        if arg.startswith("--delay="):
            with contextlib.suppress(ValueError):
                upgradeDelay = int(arg.split("=")[1].strip())
        elif arg.startswith("--type="):
            upgradeType = arg.split("=")[1].strip()

    # wait a few seconds to give eric the chance to fully shut down
    time.sleep(upgradeDelay)

    # now perform the upgrade and start eric, if it was successful
    if upgradeType == "pyqt":
        ok = doUpgrade(_pyqtPackages)
    elif upgradeType == "eric":
        ok = doUpgrade(_ericPackages)
    elif upgradeType == "ericpyqt":
        ok = doUpgrade(_ericPackages + _pyqtPackages)
    else:
        ok = False

    if ok:
        startEric(ericStartArgs)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
