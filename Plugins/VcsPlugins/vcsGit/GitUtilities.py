# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some common utility functions for the Git package.
"""

import os

from PyQt6.QtCore import QProcessEnvironment

from eric7.SystemUtilities import OSUtilities


def getConfigPath():
    """
    Public function to get the filename of the config file.

    @return filename of the config file
    @rtype str
    """
    if OSUtilities.isWindowsPlatform():
        userprofile = os.environ["USERPROFILE"]
        return os.path.join(userprofile, ".gitconfig")
    else:
        homedir = OSUtilities.getHomeDir()
        return os.path.join(homedir, ".gitconfig")


def prepareProcess(proc, language=""):
    """
    Public function to prepare the given process.

    @param proc reference to the process to be prepared
    @type QProcess
    @param language language to be set
    @type str
    """
    env = QProcessEnvironment.systemEnvironment()

    # set the language for the process
    if language:
        env.insert("LANGUAGE", language)

    proc.setProcessEnvironment(env)
