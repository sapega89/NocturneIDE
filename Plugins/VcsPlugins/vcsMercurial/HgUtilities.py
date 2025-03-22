# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some common utility functions for the Mercurial package.
"""

import os
import re

from PyQt6.QtCore import QCoreApplication, QProcess, QProcessEnvironment

from eric7.SystemUtilities import OSUtilities, PythonUtilities

# progress bar            topic, bar (ignored), value, maximum, estimate
progressRe = re.compile(r"(\w+)\s+(?:\[[=> ]*\])\s+(\d+)/(\d+)\s+(\w+)")

# version                   major, minor, patch, additional
versionRe = re.compile(r".*?(\d+)\.(\d+)\.?(\d+)?(\+[0-9a-f-]+)?")


def getHgExecutable():
    """
    Function to get the full path of the Mercurial executable.

    @return path of the Mercurial executable
    @rtype str
    """
    from eric7.Plugins.PluginVcsMercurial import VcsMercurialPlugin

    exe = VcsMercurialPlugin.getPreferences("MercurialExecutablePath")
    if not exe:
        program = "hg"
        if OSUtilities.isWindowsPlatform():
            program += ".exe"

        progPath = os.path.join(PythonUtilities.getPythonScriptsDirectory(), program)
        if os.path.exists(progPath):
            exe = progPath

        if not exe:
            exe = program

    return exe


def getConfigPath():
    """
    Function to get the filename of the config file.

    @return filename of the config file
    @rtype str
    """
    if OSUtilities.isWindowsPlatform():
        userprofile = os.environ["USERPROFILE"]
        return os.path.join(userprofile, "Mercurial.ini")
    else:
        homedir = OSUtilities.getHomeDir()
        return os.path.join(homedir, ".hgrc")


def prepareProcess(proc, encoding="", language=""):
    """
    Function to prepare the given process.

    @param proc reference to the process to be prepared
    @type QProcess
    @param encoding encoding to be used by the process
    @type str
    @param language language to be set
    @type str
    """
    env = QProcessEnvironment.systemEnvironment()
    env.insert("HGPLAINEXCEPT", "progress")  # maybe set to 'i18n,progress'

    # set the encoding for the process
    if encoding:
        env.insert("HGENCODING", encoding)

    # set the language for the process
    if language:
        env.insert("LANGUAGE", language)

    proc.setProcessEnvironment(env)


def hgVersion(plugin):
    """
    Public method to determine the Mercurial version.

    @param plugin reference to the plugin object
    @type VcsMercurialPlugin
    @return tuple containing the Mercurial version as a string and as a tuple
        and an error message.
    @rtype tuple of str, tuple of int and str
    """
    versionStr = ""
    version = ()
    errorMsg = ""

    exe = getHgExecutable()

    args = ["version"]
    args.extend(plugin.getGlobalOptions())
    process = QProcess()
    process.start(exe, args)
    procStarted = process.waitForStarted(5000)
    if procStarted:
        finished = process.waitForFinished(30000)
        if finished and process.exitCode() == 0:
            output = str(
                process.readAllStandardOutput(),
                plugin.getPreferences("Encoding"),
                "replace",
            )
            versionStr = output.splitlines()[0].split()[-1][0:-1]
            v = list(versionRe.match(versionStr).groups())
            if v[-1] is None:
                del v[-1]
            for i in range(3):
                try:
                    v[i] = int(v[i])
                except TypeError:
                    v[i] = 0
                except IndexError:
                    v.append(0)
            version = tuple(v)
        else:
            if finished:
                errorMsg = QCoreApplication.translate(
                    "HgUtilities", "The hg process finished with the exit code {0}"
                ).format(process.exitCode())
            else:
                errorMsg = QCoreApplication.translate(
                    "HgUtilities", "The hg process did not finish within 30s."
                )
    else:
        errorMsg = QCoreApplication.translate(
            "HgUtilities", "Could not start the hg executable."
        )

    return versionStr, version, errorMsg


def isProgressInfo(line):
    """
    Function to check, if the given line contains progress information.

    @param line output line to be checked
    @type str
    @return flag indicating a line containing progress information
    @rtype bool
    """
    return progressRe.match(line.strip()) is not None


def parseProgressInfo(progressLine):
    """
    Function to parse an output line containing progress information.

    @param progressLine progress information line to be parsed
    @type str
    @return tuple containing the progress topic, current value, maximum value and
        the completion estimate
    @rtype tuple of (str, int, int, str)
    """
    match = progressRe.match(progressLine)
    if match is not None:
        return (
            match[1],  # topic
            int(match[2]),  # value
            int(match[3]),  # maximum
            match[4],  # estimate
        )
    else:
        return "", 0, 0, ""
