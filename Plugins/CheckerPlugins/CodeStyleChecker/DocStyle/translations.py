# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing message translations for the code style plugin messages
(code documentation part).
"""

from PyQt6.QtCore import QCoreApplication

_docStyleMessages = {
    "D101": QCoreApplication.translate(
        "DocStyleChecker", "module is missing a docstring"
    ),
    "D102": QCoreApplication.translate(
        "DocStyleChecker", "public function/method is missing a docstring"
    ),
    "D103": QCoreApplication.translate(
        "DocStyleChecker", "private function/method may be missing a docstring"
    ),
    "D104": QCoreApplication.translate(
        "DocStyleChecker", "public class is missing a docstring"
    ),
    "D105": QCoreApplication.translate(
        "DocStyleChecker", "private class may be missing a docstring"
    ),
    "D111": QCoreApplication.translate(
        "DocStyleChecker", 'docstring not surrounded by """'
    ),
    "D112": QCoreApplication.translate(
        "DocStyleChecker", 'docstring containing \\ not surrounded by r"""'
    ),
    "D121": QCoreApplication.translate(
        "DocStyleChecker", "one-liner docstring on multiple lines"
    ),
    "D122": QCoreApplication.translate(
        "DocStyleChecker", "docstring has wrong indentation"
    ),
    "D130": QCoreApplication.translate(
        "DocStyleChecker", "docstring does not contain a summary"
    ),
    "D131": QCoreApplication.translate(
        "DocStyleChecker", "docstring summary does not end with a period"
    ),
    "D132": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring summary is not in imperative mood (Does instead of Do)",
    ),
    "D133": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring summary looks like a function's/method's signature",
    ),
    "D134": QCoreApplication.translate(
        "DocStyleChecker", "docstring does not mention the return value type"
    ),
    "D141": QCoreApplication.translate(
        "DocStyleChecker", "function/method docstring is separated by a blank line"
    ),
    "D142": QCoreApplication.translate(
        "DocStyleChecker", "class docstring is not preceded by a blank line"
    ),
    "D143": QCoreApplication.translate(
        "DocStyleChecker", "class docstring is not followed by a blank line"
    ),
    "D144": QCoreApplication.translate(
        "DocStyleChecker", "docstring summary is not followed by a blank line"
    ),
    "D145": QCoreApplication.translate(
        "DocStyleChecker", "last paragraph of docstring is not followed by a blank line"
    ),
    "D201": QCoreApplication.translate(
        "DocStyleChecker", "module docstring is still a default string"
    ),
    "D202.1": QCoreApplication.translate(
        "DocStyleChecker", "function docstring is still a default string"
    ),
    "D202.2": QCoreApplication.translate(
        "DocStyleChecker", "function docstring still contains some placeholders"
    ),
    "D203": QCoreApplication.translate(
        "DocStyleChecker", "private function/method is missing a docstring"
    ),
    "D205": QCoreApplication.translate(
        "DocStyleChecker", "private class is missing a docstring"
    ),
    "D206": QCoreApplication.translate(
        "DocStyleChecker", "class docstring is still a default string"
    ),
    "D221": QCoreApplication.translate(
        "DocStyleChecker", "leading quotes of docstring not on separate line"
    ),
    "D222": QCoreApplication.translate(
        "DocStyleChecker", "trailing quotes of docstring not on separate line"
    ),
    "D231": QCoreApplication.translate(
        "DocStyleChecker", "docstring summary does not end with a period"
    ),
    "D232": QCoreApplication.translate(
        "DocStyleChecker", "docstring summary does not start with '{0}'"
    ),
    "D234r": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring does not contain a @return line but function/method"
        " returns something",
    ),
    "D235r": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring contains a @return line but function/method doesn't"
        " return anything",
    ),
    "D234y": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring does not contain a @yield line but function/method"
        " yields something",
    ),
    "D235y": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring contains a @yield line but function/method doesn't"
        " yield anything",
    ),
    "D236": QCoreApplication.translate(
        "DocStyleChecker", "docstring does not contain enough @param/@keyparam lines"
    ),
    "D237": QCoreApplication.translate(
        "DocStyleChecker", "docstring contains too many @param/@keyparam lines"
    ),
    "D238": QCoreApplication.translate(
        "DocStyleChecker",
        "keyword only arguments must be documented with @keyparam lines",
    ),
    "D239": QCoreApplication.translate(
        "DocStyleChecker",
        "order of @param/@keyparam lines does"
        " not match the function/method signature",
    ),
    "D242": QCoreApplication.translate(
        "DocStyleChecker", "class docstring is preceded by a blank line"
    ),
    "D243": QCoreApplication.translate(
        "DocStyleChecker", "class docstring is followed by a blank line"
    ),
    "D244": QCoreApplication.translate(
        "DocStyleChecker", "function/method docstring is preceded by a blank line"
    ),
    "D245": QCoreApplication.translate(
        "DocStyleChecker", "function/method docstring is followed by a blank line"
    ),
    "D246": QCoreApplication.translate(
        "DocStyleChecker", "docstring summary is not followed by a blank line"
    ),
    "D247": QCoreApplication.translate(
        "DocStyleChecker", "last paragraph of docstring is followed by a blank line"
    ),
    "D250": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring does not contain a @exception line but function/method"
        " raises an exception",
    ),
    "D251": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring contains a @exception line but function/method doesn't"
        " raise an exception",
    ),
    "D252": QCoreApplication.translate(
        "DocStyleChecker", "raised exception '{0}' is not documented in docstring"
    ),
    "D253": QCoreApplication.translate(
        "DocStyleChecker", "documented exception '{0}' is not raised"
    ),
    "D260": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring does not contain a @signal line but class defines signals",
    ),
    "D261": QCoreApplication.translate(
        "DocStyleChecker",
        "docstring contains a @signal line but class doesn't define signals",
    ),
    "D262": QCoreApplication.translate(
        "DocStyleChecker", "defined signal '{0}' is not documented in docstring"
    ),
    "D263": QCoreApplication.translate(
        "DocStyleChecker", "documented signal '{0}' is not defined"
    ),
    "D270": QCoreApplication.translate(
        "DocStyleChecker", "'{0}' line should be followed by an '{1}' line"
    ),
    "D271": QCoreApplication.translate(
        "DocStyleChecker", "'{0}' line should not be preceded by an empty line"
    ),
    "D272": QCoreApplication.translate(
        "DocStyleChecker", "don't use '{0}' but '{1}' instead"
    ),
    "D273": QCoreApplication.translate(
        "DocStyleChecker", "'{0}' line has wrong indentation"
    ),
}

_docStyleMessagesSampleArgs = {
    "D232": ["public"],
    "D252": ["RuntimeError"],
    "D253": ["RuntimeError"],
    "D262": ["buttonClicked"],
    "D263": ["buttonClicked"],
    "D270": ["@param", "@type"],
    "D271": ["@type"],
    "D272": ["@ptype", "@type"],
    "D273": ["@type"],
}
