# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing message translations for the code style plugin messages
(async part).
"""

from PyQt6.QtCore import QCoreApplication

_asyncMessages = {
    "ASY100": QCoreApplication.translate(
        "AsyncChecker", "sync HTTP call in async function, use httpx.AsyncClient"
    ),
    "ASY101": QCoreApplication.translate(
        "AsyncChecker", "blocking sync call in async function, use framework equivalent"
    ),
    "ASY102": QCoreApplication.translate(
        "AsyncChecker", "sync process call in async function, use framework equivalent"
    ),
    "ASY103": QCoreApplication.translate(
        "AsyncChecker",
        "blocking sync context manager in async function,"
        " use 'async with' statement",
    ),
    "ASY104": QCoreApplication.translate(
        "AsyncChecker",
        "avoid using os.path, prefer using 'trio.Path' or 'anyio.Path' objects",
    ),
    "ASY105": QCoreApplication.translate(
        "AsyncChecker",
        "use of potentially dangerous class in async function, use"
        " httpx.AsyncClient",
    ),
}

_asyncMessageSampleArgs = {}
