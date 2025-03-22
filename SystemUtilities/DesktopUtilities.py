# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing Linux desktop related utility functions.
"""

import os

from eric7.SystemUtilities import OSUtilities


def desktopName():
    """
    Function to determine the name of the desktop environment used
    (Linux only).

    @return name of the desktop environment
    @rtype str
    """
    if OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
        currDesktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
        if currDesktop:
            return currDesktop

        currDesktop = os.environ.get("XDG_SESSION_DESKTOP", "")
        if currDesktop:
            return currDesktop

        currDesktop = os.environ.get("GDMSESSION", "")
        if currDesktop:
            return currDesktop

        currDesktop = os.environ.get("GNOME_DESKTOP_SESSION_ID", "")
        if currDesktop:
            return currDesktop

        currDesktop = os.environ.get("KDE_FULL_SESSION", "")
        if currDesktop:
            if currDesktop == "true":
                return "KDE"

            return currDesktop

        currDesktop = os.environ.get("DESKTOP_SESSION", "")
        if currDesktop:
            return currDesktop

    return ""


def isKdeDesktop():
    """
    Function to check, if the current session is a KDE desktop (Linux only).

    @return flag indicating a KDE desktop
    @rtype bool
    """
    if OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
        desktop = (
            os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            or os.environ.get("XDG_SESSION_DESKTOP", "").lower()
            or os.environ.get("DESKTOP_SESSION", "").lower()
        )
        return (
            "kde" in desktop or "plasma" in desktop
            if desktop
            else bool(os.environ.get("KDE_FULL_SESSION", ""))
        )

    return False


def isGnomeDesktop():
    """
    Function to check, if the current session is a Gnome desktop (Linux only).

    @return flag indicating a Gnome desktop
    @rtype bool
    """
    if OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
        desktop = (
            os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            or os.environ.get("XDG_SESSION_DESKTOP", "").lower()
            or os.environ.get("GDMSESSION", "").lower()
        )
        return (
            "gnome" in desktop
            if desktop
            else bool(os.environ.get("GNOME_DESKTOP_SESSION_ID", ""))
        )

    return False


def sessionType():
    """
    Function to determine the name of the running session (Linux only).

    @return name of the desktop environment
    @rtype str
    """
    if OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
        sessionType = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if "x11" in sessionType:
            return "X11"
        elif "wayland" in sessionType:
            return "Wayland"

        sessionType = os.environ.get("WAYLAND_DISPLAY", "").lower()
        if "wayland" in sessionType:
            return "Wayland"

    return ""


def isWaylandSession():
    """
    Function to check, if the current session is a wayland session.

    @return flag indicating a wayland session
    @rtype bool
    """
    return sessionType() == "Wayland"
