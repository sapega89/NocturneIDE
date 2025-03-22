# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing message translations for the code style plugin messages
(logging part).
"""

from PyQt6.QtCore import QCoreApplication

_loggingMessages = {
    ## Logging
    "L101": QCoreApplication.translate(
        "LoggingChecker",
        "use logging.getLogger() to instantiate loggers",
    ),
    "L102": QCoreApplication.translate(
        "LoggingChecker",
        "use '__name__' with getLogger()",
    ),
    "L103": QCoreApplication.translate(
        "LoggingChecker",
        "extra key {0} clashes with LogRecord attribute",
    ),
    "L104": QCoreApplication.translate(
        "LoggingChecker",
        "avoid exception() outside of exception handlers",
    ),
    "L105": QCoreApplication.translate(
        "LoggingChecker",
        ".exception(...) should be used instead of .error(..., exc_info=True)",
    ),
    "L106": QCoreApplication.translate(
        "LoggingChecker",
        "redundant exc_info argument for exception() should be removed",
    ),
    "L107": QCoreApplication.translate(
        "LoggingChecker",
        "use error() instead of exception() with exc_info=False",
    ),
    "L108": QCoreApplication.translate(
        "LoggingChecker",
        "warn() is deprecated, use warning() instead",
    ),
    "L109": QCoreApplication.translate(
        "LoggingChecker",
        "WARN is undocumented, use WARNING instead",
    ),
    "L110": QCoreApplication.translate(
        "LoggingChecker",
        "exception() does not take an exception",
    ),
    "L111a": QCoreApplication.translate(
        "LoggingChecker",
        "avoid pre-formatting log messages using f-string",
    ),
    "L111b": QCoreApplication.translate(
        "LoggingChecker",
        "avoid pre-formatting log messages using string.format()",
    ),
    "L111c": QCoreApplication.translate(
        "LoggingChecker",
        "avoid pre-formatting log messages using '%'",  # noqa: M601
    ),
    "L111d": QCoreApplication.translate(
        "LoggingChecker",
        "avoid pre-formatting log messages using '+'",
    ),
    "L112": QCoreApplication.translate(
        "LoggingChecker",
        "formatting error: {0} {1} placeholder(s) but {2} argument(s)",
    ),
    "L113a": QCoreApplication.translate(
        "LoggingChecker",
        "formatting error: missing key(s): {0}",
    ),
    "L113b": QCoreApplication.translate(
        "LoggingChecker",
        "formatting error: unreferenced key(s): {0}",
    ),
    "L114": QCoreApplication.translate(
        "LoggingChecker",
        "avoid exc_info=True outside of exception handlers",
    ),
    "L115": QCoreApplication.translate(
        "LoggingChecker",
        "avoid logging calls on the root logger",
    ),
}

_loggingMessagesSampleArgs = {
    ## Logging
    "L103": ["'pathname'"],
    "L112": [3, "'%'", 2],  # noqa: M601
    "L113a": ["'foo', 'bar'"],
    "L113b": ["'foo', 'bar'"],
}
