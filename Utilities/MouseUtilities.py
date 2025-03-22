# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing utility functions related to Mouse stuff.
"""

from PyQt6.QtCore import QCoreApplication, Qt

from eric7.SystemUtilities import OSUtilities

if OSUtilities.isMacPlatform():
    __modifier2String = {
        Qt.KeyboardModifier.ShiftModifier: QCoreApplication.translate(
            "MouseUtilities", "Shift"
        ),
        Qt.KeyboardModifier.AltModifier: QCoreApplication.translate(
            "MouseUtilities", "Alt"
        ),
        Qt.KeyboardModifier.ControlModifier: QCoreApplication.translate(
            "MouseUtilities", "Cmd"
        ),
        Qt.KeyboardModifier.MetaModifier: QCoreApplication.translate(
            "MouseUtilities", "Ctrl"
        ),
    }
    __modifierOrder = [
        Qt.KeyboardModifier.MetaModifier,
        Qt.KeyboardModifier.AltModifier,
        Qt.KeyboardModifier.ShiftModifier,
        Qt.KeyboardModifier.ControlModifier,
    ]
else:
    __modifier2String = {
        Qt.KeyboardModifier.ShiftModifier: QCoreApplication.translate(
            "MouseUtilities", "Shift"
        ),
        Qt.KeyboardModifier.AltModifier: QCoreApplication.translate(
            "MouseUtilities", "Alt"
        ),
        Qt.KeyboardModifier.ControlModifier: QCoreApplication.translate(
            "MouseUtilities", "Ctrl"
        ),
        Qt.KeyboardModifier.MetaModifier: QCoreApplication.translate(
            "MouseUtilities", "Meta"
        ),
    }
    __modifierOrder = [
        Qt.KeyboardModifier.MetaModifier,
        Qt.KeyboardModifier.ControlModifier,
        Qt.KeyboardModifier.AltModifier,
        Qt.KeyboardModifier.ShiftModifier,
    ]


__button2String = {
    Qt.MouseButton.LeftButton: QCoreApplication.translate(
        "MouseUtilities", "Left Button"
    ),
    Qt.MouseButton.RightButton: QCoreApplication.translate(
        "MouseUtilities", "Right Button"
    ),
    Qt.MouseButton.MiddleButton: QCoreApplication.translate(
        "MouseUtilities", "Middle Button"
    ),
    Qt.MouseButton.XButton1: QCoreApplication.translate(
        "MouseUtilities", "Extra Button 1"
    ),
    Qt.MouseButton.XButton2: QCoreApplication.translate(
        "MouseUtilities", "Extra Button 2"
    ),
}


def MouseButtonModifier2String(modifiers, button):
    """
    Function to convert a modifier and mouse button combination to a
    displayable string.

    @param modifiers keyboard modifiers of the handler
    @type Qt.KeyboardModifiers
    @param button mouse button of the handler
    @type Qt.MouseButton
    @return display string of the modifier and mouse button combination
    @rtype str
    """
    if button not in __button2String:
        return ""

    parts = []
    for mod in __modifierOrder:
        if modifiers & mod:
            parts.append(__modifier2String[mod])
    parts.append(__button2String[button])
    return "+".join(parts)
