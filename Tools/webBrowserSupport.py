#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Script to determine the supported web browser variant.

It looks for QtWebEngine. It reports the variant found or the string 'None' if
it is absent.
"""

import importlib.util
import sys

variant = (
    "QtWebEngine"
    if (
        bool(importlib.util.find_spec("PyQt6"))
        and bool(importlib.util.find_spec("PyQt6.QtWebEngineWidgets"))
    )
    else "None"
)
print(variant)  # noqa: M801

sys.exit(0)
