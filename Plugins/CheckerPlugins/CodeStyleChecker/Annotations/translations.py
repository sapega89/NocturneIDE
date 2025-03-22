# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing message translations for the code style plugin messages
(code annotations part).
"""

from PyQt6.QtCore import QCoreApplication

_annotationsMessages = {
    "A001": QCoreApplication.translate(
        "AnnotationsChecker", "missing type annotation for function argument '{0}'"
    ),
    "A002": QCoreApplication.translate(
        "AnnotationsChecker", "missing type annotation for '*{0}'"
    ),
    "A003": QCoreApplication.translate(
        "AnnotationsChecker", "missing type annotation for '**{0}'"
    ),
    "A101": QCoreApplication.translate(
        "AnnotationsChecker", "missing type annotation for 'self' in method"
    ),
    "A102": QCoreApplication.translate(
        "AnnotationsChecker", "missing type annotation for 'cls' in classmethod"
    ),
    "A201": QCoreApplication.translate(
        "AnnotationsChecker", "missing return type annotation for public function"
    ),
    "A202": QCoreApplication.translate(
        "AnnotationsChecker", "missing return type annotation for protected function"
    ),
    "A203": QCoreApplication.translate(
        "AnnotationsChecker", "missing return type annotation for private function"
    ),
    "A204": QCoreApplication.translate(
        "AnnotationsChecker", "missing return type annotation for special method"
    ),
    "A205": QCoreApplication.translate(
        "AnnotationsChecker", "missing return type annotation for staticmethod"
    ),
    "A206": QCoreApplication.translate(
        "AnnotationsChecker", "missing return type annotation for classmethod"
    ),
    "A401": QCoreApplication.translate(
        "AnnotationsChecker",
        "Dynamically typed expressions (typing.Any) are disallowed",
    ),
    "A402": QCoreApplication.translate(
        "AnnotationsChecker", "Type comments are disallowed"
    ),
    "A871": QCoreApplication.translate(
        "AnnotationsChecker",
        "missing 'from __future__ import annotations' but imports: {0}",
    ),
    "A872": QCoreApplication.translate(
        "AnnotationsChecker", "missing 'from __future__ import annotations'"
    ),
    "A873": QCoreApplication.translate(
        "AnnotationsChecker",
        "missing 'from __future__ import annotations' but uses simplified type"
        " annotations: {0}",
    ),
    "A881": QCoreApplication.translate(
        "AnnotationsChecker", "type annotation coverage of {0}% is too low"
    ),
    "A891": QCoreApplication.translate(
        "AnnotationsChecker", "type annotation is too complex ({0} > {1})"
    ),
    "A892": QCoreApplication.translate(
        "AnnotationsChecker", "type annotation is too long ({0} > {1})"
    ),
    "A901": QCoreApplication.translate(
        "AnnotationsChecker",
        "'typing.Union' is deprecated, use '|' instead (see PEP 604)",
    ),
    "A911": QCoreApplication.translate(
        "AnnotationsChecker",
        "'typing.{0}' is deprecated, use '{1}' instead (see PEP 585)",
    ),
}

_annotationsMessagesSampleArgs = {
    "A001": ["arg1"],
    "A002": ["args"],
    "A003": ["kwargs"],
    "A871": ["Dict, List"],
    "A873": ["dict, list"],
    "A881": [60],
    "A891": [5, 3],
    "A892": [10, 7],
    "A911": ["List", "list"],
}
