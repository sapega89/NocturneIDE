# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing complex defaults for the miscellaneous checker.
"""

MiscellaneousCheckerDefaultArgs = {
    "BuiltinsChecker": {
        "chr": [
            "unichr",
        ],
        "str": [
            "unicode",
        ],
    },
    "CodingChecker": "latin-1, utf-8",
    "CopyrightChecker": {
        "Author": "",
        "MinFilesize": 0,
    },
    "CommentedCodeChecker": {
        "Aggressive": False,
        "WhiteList": [
            r"pylint",
            r"pyright",
            r"noqa",
            r"type:\s*ignore",
            r"fmt:\s*(on|off)",
            r"TODO",
            r"FIXME",
            r"WARNING",
            r"NOTE",
            r"TEST",
            r"DOCU",
            r"XXX",
        ],
    },
}
