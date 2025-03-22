# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing message translations for the code style plugin messages
(import statements part).
"""

from PyQt6.QtCore import QCoreApplication

_importsMessages = {
    "I101": QCoreApplication.translate(
        "ImportsChecker", "local import must be at the beginning of the method body"
    ),
    "I102": QCoreApplication.translate(
        "ImportsChecker",
        "packages from external modules should not be imported locally",
    ),
    "I103": QCoreApplication.translate(
        "ImportsChecker",
        "packages from standard modules should not be imported locally",
    ),
    "I901": QCoreApplication.translate(
        "ImportsChecker", "unnecessary import alias - rewrite as '{0}'"
    ),
    "I902": QCoreApplication.translate("ImportsChecker", "banned import '{0}' used"),
    "I903": QCoreApplication.translate(
        "ImportsChecker", "relative imports from parent modules are banned"
    ),
    "I904": QCoreApplication.translate("ImportsChecker", "relative imports are banned"),
}

_importsMessagesSampleArgs = {
    "I901": ["from foo import bar"],
    "I902": ["foo"],
}
