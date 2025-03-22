# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some utility functions for the Download package.
"""

from PyQt6.QtCore import QCoreApplication


def timeString(timeRemaining):
    """
    Module function to format the given time.

    @param timeRemaining time to be formatted
    @type float
    @return time string
    @rtype str
    """
    if timeRemaining < 10:
        return QCoreApplication.translate("DownloadUtilities", "few seconds remaining")
    elif timeRemaining < 60:  # < 1 minute
        seconds = int(timeRemaining)
        return QCoreApplication.translate(
            "DownloadUtilities", "%n seconds remaining", "", seconds
        )
    elif timeRemaining < 3600:  # < 1 hour
        minutes = int(timeRemaining / 60)
        return QCoreApplication.translate(
            "DownloadUtilities", "%n minutes remaining", "", minutes
        )
    else:
        hours = int(timeRemaining / 3600)
        return QCoreApplication.translate(
            "DownloadUtilities", "%n hours remaining", "", hours
        )


def dataString(size):
    """
    Module function to generate a formatted size string.

    @param size size to be formatted
    @type int
    @return formatted data string
    @rtype str
    """
    if size < 1024:
        return QCoreApplication.translate("DownloadUtilities", "{0:.1f} Bytes").format(
            size
        )
    elif size < 1024 * 1024:
        size /= 1024
        return QCoreApplication.translate("DownloadUtilities", "{0:.1f} KiB").format(
            size
        )
    elif size < 1024 * 1024 * 1024:
        size /= 1024 * 1024
        return QCoreApplication.translate("DownloadUtilities", "{0:.2f} MiB").format(
            size
        )
    else:
        size /= 1024 * 1024 * 1024
        return QCoreApplication.translate("DownloadUtilities", "{0:.2f} GiB").format(
            size
        )


def speedString(speed):
    """
    Module function to generate a formatted speed string.

    @param speed speed to be formatted
    @type float
    @return formatted speed string
    @rtype str
    """
    if speed < 0:
        return QCoreApplication.translate("DownloadUtilities", "Unknown speed")

    speed /= 1024  # kB
    if speed < 1024:
        return QCoreApplication.translate("DownloadUtilities", "{0:.1f} KiB/s").format(
            speed
        )

    speed /= 1024  # MB
    if speed < 1024:
        return QCoreApplication.translate("DownloadUtilities", "{0:.2f} MiB/s").format(
            speed
        )

    speed /= 1024  # GB
    if speed < 1024:
        return QCoreApplication.translate("DownloadUtilities", "{0:.2f} GiB/s").format(
            speed
        )

    return ""
