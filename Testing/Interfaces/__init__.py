# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package containg the various test framework interfaces.
"""

from .PytestExecutor import PytestExecutor
from .UnittestExecutor import UnittestExecutor

Frameworks = (
    UnittestExecutor,
    PytestExecutor,
)

FrameworkNames = {
    "MicroPython": (
        UnittestExecutor.name,
        PytestExecutor.name,
    ),
    "Python3": (
        UnittestExecutor.name,
        PytestExecutor.name,
    ),
}
