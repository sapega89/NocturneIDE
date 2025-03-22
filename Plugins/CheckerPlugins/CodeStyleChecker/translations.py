# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing message translations for the code style plugin messages.
"""

import contextlib
import re

from PyQt6.QtCore import QCoreApplication

from .Annotations.translations import (
    _annotationsMessages,
    _annotationsMessagesSampleArgs,
)
from .Async.translations import _asyncMessages, _asyncMessageSampleArgs
from .Complexity.translations import _complexityMessages, _complexityMessagesSampleArgs
from .DocStyle.translations import _docStyleMessages, _docStyleMessagesSampleArgs
from .Imports.translations import _importsMessages, _importsMessagesSampleArgs
from .Logging.translations import _loggingMessages, _loggingMessagesSampleArgs
from .Miscellaneous.translations import (
    _miscellaneousMessages,
    _miscellaneousMessagesSampleArgs,
)
from .NameOrder.translations import _nameOrderMessages, _nameOrderMessagesSampleArgs
from .Naming.translations import _namingStyleMessages
from .PathLib.translations import _pathlibMessages
from .Security.translations import _securityMessages, _securityMessagesSampleArgs
from .Simplify.translations import _simplifyMessages, _simplifyMessagesSampleArgs
from .Unused.translations import _unusedMessages, _unusedMessagesSampleArgs

##################################################################
## pycodestyle error messages
##################################################################

_pycodestyleErrorMessages = {
    "E101": QCoreApplication.translate(
        "pycodestyle", "indentation contains mixed spaces and tabs"
    ),
    "E111": QCoreApplication.translate(
        "pycodestyle", "indentation is not a multiple of four"
    ),
    "E112": QCoreApplication.translate("pycodestyle", "expected an indented block"),
    "E113": QCoreApplication.translate("pycodestyle", "unexpected indentation"),
    "E114": QCoreApplication.translate(
        "pycodestyle", "indentation is not a multiple of four (comment)"
    ),
    "E115": QCoreApplication.translate(
        "pycodestyle", "expected an indented block (comment)"
    ),
    "E116": QCoreApplication.translate(
        "pycodestyle", "unexpected indentation (comment)"
    ),
    "E117": QCoreApplication.translate("pycodestyle", "over-indented"),
    "E121": QCoreApplication.translate(
        "pycodestyle", "continuation line indentation is not a multiple of four"
    ),
    "E122": QCoreApplication.translate(
        "pycodestyle", "continuation line missing indentation or outdented"
    ),
    "E123": QCoreApplication.translate(
        "pycodestyle",
        "closing bracket does not match indentation of opening bracket's line",
    ),
    "E124": QCoreApplication.translate(
        "pycodestyle", "closing bracket does not match visual indentation"
    ),
    "E125": QCoreApplication.translate(
        "pycodestyle", "continuation line with same indent as next logical line"
    ),
    "E126": QCoreApplication.translate(
        "pycodestyle", "continuation line over-indented for hanging indent"
    ),
    "E127": QCoreApplication.translate(
        "pycodestyle", "continuation line over-indented for visual indent"
    ),
    "E128": QCoreApplication.translate(
        "pycodestyle", "continuation line under-indented for visual indent"
    ),
    "E129": QCoreApplication.translate(
        "pycodestyle", "visually indented line with same indent as next logical line"
    ),
    "E131": QCoreApplication.translate(
        "pycodestyle", "continuation line unaligned for hanging indent"
    ),
    "E133": QCoreApplication.translate(
        "pycodestyle", "closing bracket is missing indentation"
    ),
    "E201": QCoreApplication.translate("pycodestyle", "whitespace after '{0}'"),
    "E202": QCoreApplication.translate("pycodestyle", "whitespace before '{0}'"),
    "E203": QCoreApplication.translate("pycodestyle", "whitespace before '{0}'"),
    "E204": QCoreApplication.translate("pycodestyle", "whitespace after decorator '@'"),
    "E211": QCoreApplication.translate("pycodestyle", "whitespace before '{0}'"),
    "E221": QCoreApplication.translate(
        "pycodestyle", "multiple spaces before operator"
    ),
    "E222": QCoreApplication.translate("pycodestyle", "multiple spaces after operator"),
    "E223": QCoreApplication.translate("pycodestyle", "tab before operator"),
    "E224": QCoreApplication.translate("pycodestyle", "tab after operator"),
    "E225": QCoreApplication.translate(
        "pycodestyle", "missing whitespace around operator"
    ),
    "E226": QCoreApplication.translate(
        "pycodestyle", "missing whitespace around arithmetic operator"
    ),
    "E227": QCoreApplication.translate(
        "pycodestyle", "missing whitespace around bitwise or shift operator"
    ),
    "E228": QCoreApplication.translate(
        "pycodestyle", "missing whitespace around modulo operator"
    ),
    "E231": QCoreApplication.translate("pycodestyle", "missing whitespace after '{0}'"),
    "E241": QCoreApplication.translate("pycodestyle", "multiple spaces after '{0}'"),
    "E242": QCoreApplication.translate("pycodestyle", "tab after '{0}'"),
    "E251": QCoreApplication.translate(
        "pycodestyle", "unexpected spaces around keyword / parameter equals"
    ),
    "E252": QCoreApplication.translate(
        "pycodestyle", "missing whitespace around parameter equals"
    ),
    "E261": QCoreApplication.translate(
        "pycodestyle", "at least two spaces before inline comment"
    ),
    "E262": QCoreApplication.translate(
        "pycodestyle", "inline comment should start with '# '"
    ),
    "E265": QCoreApplication.translate(
        "pycodestyle", "block comment should start with '# '"
    ),
    "E266": QCoreApplication.translate(
        "pycodestyle", "too many leading '#' for block comment"
    ),
    "E271": QCoreApplication.translate("pycodestyle", "multiple spaces after keyword"),
    "E272": QCoreApplication.translate("pycodestyle", "multiple spaces before keyword"),
    "E273": QCoreApplication.translate("pycodestyle", "tab after keyword"),
    "E274": QCoreApplication.translate("pycodestyle", "tab before keyword"),
    "E275": QCoreApplication.translate(
        "pycodestyle", "missing whitespace after keyword"
    ),
    "E301": QCoreApplication.translate(
        "pycodestyle", "expected {0} blank lines, found {1}"
    ),
    "E302": QCoreApplication.translate(
        "pycodestyle", "expected {0} blank lines, found {1}"
    ),
    "E303": QCoreApplication.translate(
        "pycodestyle", "too many blank lines ({0}), expected {1}"
    ),
    "E304": QCoreApplication.translate(
        "pycodestyle", "blank lines found after function decorator"
    ),
    "E305": QCoreApplication.translate(
        "pycodestyle",
        "expected {0} blank lines after class or function definition, found {1}",
    ),
    "E306": QCoreApplication.translate(
        "pycodestyle", "expected {0} blank lines before a nested definition, found {1}"
    ),
    "E307": QCoreApplication.translate(
        "pycodestyle",
        "too many blank lines ({0}) before a nested definition, expected {1}",
    ),
    "E308": QCoreApplication.translate("pycodestyle", "too many blank lines ({0})"),
    "E401": QCoreApplication.translate("pycodestyle", "multiple imports on one line"),
    "E402": QCoreApplication.translate(
        "pycodestyle", "module level import not at top of file"
    ),
    "E501": QCoreApplication.translate(
        "pycodestyle", "line too long ({0} > {1} characters)"
    ),
    "E502": QCoreApplication.translate(
        "pycodestyle", "the backslash is redundant between brackets"
    ),
    "E701": QCoreApplication.translate(
        "pycodestyle", "multiple statements on one line (colon)"
    ),
    "E702": QCoreApplication.translate(
        "pycodestyle", "multiple statements on one line (semicolon)"
    ),
    "E703": QCoreApplication.translate(
        "pycodestyle", "statement ends with a semicolon"
    ),
    "E704": QCoreApplication.translate(
        "pycodestyle", "multiple statements on one line (def)"
    ),
    "E711": QCoreApplication.translate(
        "pycodestyle", "comparison to {0} should be {1}"
    ),
    "E712": QCoreApplication.translate(
        "pycodestyle", "comparison to {0} should be {1}"
    ),
    "E713": QCoreApplication.translate(
        "pycodestyle", "test for membership should be 'not in'"
    ),
    "E714": QCoreApplication.translate(
        "pycodestyle", "test for object identity should be 'is not'"
    ),
    "E721": QCoreApplication.translate(
        "pycodestyle",
        "do not compare types, for exact checks use 'is' / 'is not', "
        "for instance checks use 'isinstance()'",
    ),
    "E722": QCoreApplication.translate("pycodestyle", "do not use bare except"),
    "E731": QCoreApplication.translate(
        "pycodestyle", "do not assign a lambda expression, use a def"
    ),
    "E741": QCoreApplication.translate("pycodestyle", "ambiguous variable name '{0}'"),
    "E742": QCoreApplication.translate(
        "pycodestyle", "ambiguous class definition '{0}'"
    ),
    "E743": QCoreApplication.translate(
        "pycodestyle", "ambiguous function definition '{0}'"
    ),
    "E901": QCoreApplication.translate("pycodestyle", "{0}: {1}"),
    "E902": QCoreApplication.translate("pycodestyle", "{0}"),
}

##################################################################
## pycodestyle warning messages
##################################################################

_pycodestyleWarningMessages = {
    "W191": QCoreApplication.translate("pycodestyle", "indentation contains tabs"),
    "W291": QCoreApplication.translate("pycodestyle", "trailing whitespace"),
    "W292": QCoreApplication.translate("pycodestyle", "no newline at end of file"),
    "W293": QCoreApplication.translate("pycodestyle", "blank line contains whitespace"),
    "W391": QCoreApplication.translate("pycodestyle", "blank line at end of file"),
    "W503": QCoreApplication.translate(
        "pycodestyle", "line break before binary operator"
    ),
    "W504": QCoreApplication.translate(
        "pycodestyle", "line break after binary operator"
    ),
    "W505": QCoreApplication.translate(
        "pycodestyle", "doc line too long ({0} > {1} characters)"
    ),
    "W605": QCoreApplication.translate(
        "pycodestyle", "invalid escape sequence '\\{0}'"
    ),
    "W606": QCoreApplication.translate(
        "pycodestyle",
        "'async' and 'await' are reserved keywords starting with Python 3.7",
    ),
}

##################################################################
## CodeStyleFixer messages
##################################################################

_fixMessages = {
    "FIXD111": QCoreApplication.translate(
        "CodeStyleFixer", "Triple single quotes converted to triple double quotes."
    ),
    "FIXD112": QCoreApplication.translate(
        "CodeStyleFixer", 'Introductory quotes corrected to be {0}"""'
    ),
    "FIXD121": QCoreApplication.translate(
        "CodeStyleFixer", "Single line docstring put on one line."
    ),
    "FIXD131": QCoreApplication.translate(
        "CodeStyleFixer", "Period added to summary line."
    ),
    "FIXD141": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line before function/method docstring removed."
    ),
    "FIXD142": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line inserted before class docstring."
    ),
    "FIXD143": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line inserted after class docstring."
    ),
    "FIXD144": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line inserted after docstring summary."
    ),
    "FIXD145": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line inserted after last paragraph of docstring."
    ),
    "FIXD221": QCoreApplication.translate(
        "CodeStyleFixer", "Leading quotes put on separate line."
    ),
    "FIXD222": QCoreApplication.translate(
        "CodeStyleFixer", "Trailing quotes put on separate line."
    ),
    "FIXD242": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line before class docstring removed."
    ),
    "FIXD244": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line before function/method docstring removed."
    ),
    "FIXD243": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line after class docstring removed."
    ),
    "FIXD245": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line after function/method docstring removed."
    ),
    "FIXD247": QCoreApplication.translate(
        "CodeStyleFixer", "Blank line after last paragraph removed."
    ),
    "FIXE101": QCoreApplication.translate(
        "CodeStyleFixer", "Tab converted to 4 spaces."
    ),
    "FIXE111": QCoreApplication.translate(
        "CodeStyleFixer", "Indentation adjusted to be a multiple of four."
    ),
    "FIXE121": QCoreApplication.translate(
        "CodeStyleFixer", "Indentation of continuation line corrected."
    ),
    "FIXE124": QCoreApplication.translate(
        "CodeStyleFixer", "Indentation of closing bracket corrected."
    ),
    "FIXE122": QCoreApplication.translate(
        "CodeStyleFixer", "Missing indentation of continuation line corrected."
    ),
    "FIXE123": QCoreApplication.translate(
        "CodeStyleFixer", "Closing bracket aligned to opening bracket."
    ),
    "FIXE125": QCoreApplication.translate(
        "CodeStyleFixer", "Indentation level changed."
    ),
    "FIXE126": QCoreApplication.translate(
        "CodeStyleFixer", "Indentation level of hanging indentation changed."
    ),
    "FIXE127": QCoreApplication.translate(
        "CodeStyleFixer", "Visual indentation corrected."
    ),
    "FIXE201": QCoreApplication.translate(
        "CodeStyleFixer", "Extraneous whitespace removed."
    ),
    "FIXE225": QCoreApplication.translate(
        "CodeStyleFixer", "Missing whitespace added."
    ),
    "FIXE221": QCoreApplication.translate(
        "CodeStyleFixer", "Extraneous whitespace removed."
    ),
    "FIXE231": QCoreApplication.translate(
        "CodeStyleFixer", "Missing whitespace added."
    ),
    "FIXE251": QCoreApplication.translate(
        "CodeStyleFixer", "Extraneous whitespace removed."
    ),
    "FIXE261": QCoreApplication.translate(
        "CodeStyleFixer", "Whitespace around comment sign corrected."
    ),
    "FIXE302+": lambda n=1: QCoreApplication.translate(
        "CodeStyleFixer", "%n blank line(s) inserted.", "", n
    ),
    "FIXE302-": lambda n=1: QCoreApplication.translate(
        "CodeStyleFixer", "%n superfluous lines removed", "", n
    ),
    "FIXE303": QCoreApplication.translate(
        "CodeStyleFixer", "Superfluous blank lines removed."
    ),
    "FIXE304": QCoreApplication.translate(
        "CodeStyleFixer", "Superfluous blank lines after function decorator removed."
    ),
    "FIXE401": QCoreApplication.translate(
        "CodeStyleFixer", "Imports were put on separate lines."
    ),
    "FIXE501": QCoreApplication.translate(
        "CodeStyleFixer", "Long lines have been shortened."
    ),
    "FIXE502": QCoreApplication.translate(
        "CodeStyleFixer", "Redundant backslash in brackets removed."
    ),
    "FIXE701": QCoreApplication.translate(
        "CodeStyleFixer", "Compound statement corrected."
    ),
    "FIXE702": QCoreApplication.translate(
        "CodeStyleFixer", "Compound statement corrected."
    ),
    "FIXE711": QCoreApplication.translate(
        "CodeStyleFixer", "Comparison to None/True/False corrected."
    ),
    "FIXN804": QCoreApplication.translate("CodeStyleFixer", "'{0}' argument added."),
    "FIXN806": QCoreApplication.translate("CodeStyleFixer", "'{0}' argument removed."),
    "FIXW291": QCoreApplication.translate(
        "CodeStyleFixer", "Whitespace stripped from end of line."
    ),
    "FIXW292": QCoreApplication.translate(
        "CodeStyleFixer", "newline added to end of file."
    ),
    "FIXW391": QCoreApplication.translate(
        "CodeStyleFixer", "Superfluous trailing blank lines removed from end of file."
    ),
    "FIXW603": QCoreApplication.translate("CodeStyleFixer", "'<>' replaced by '!='."),
    "FIXWRITE_ERROR": QCoreApplication.translate(
        "CodeStyleFixer", "Could not save the file! Skipping it. Reason: {0}"
    ),
}

_pycodestyleErrorMessagesSampleArgs = {
    "E201": ["([{"],
    "E202": ["}])"],
    "E203": [",;:"],
    "E211": ["(["],
    "E231": [",;:"],
    "E241": [",;:"],
    "E242": [",;:"],
    "E301": [1, 0],
    "E302": [2, 1],
    "E303": [3, 2],
    "E305": [2, 1],
    "E306": [1, 0],
    "E307": [3, 1],
    "E308": [3],
    "E501": [95, 88],
    "E711": ["None", "'if cond is None:'"],
    "E712": ["True", "'if cond is True:' or 'if cond:'"],
    "E741": ["l"],
    "E742": ["l"],
    "E743": ["l"],
    "E901": ["SyntaxError", "Invalid Syntax"],
    "E902": ["OSError"],
}

_pycodestyleWarningMessagesSampleArgs = {
    "W505": [80, 72],
    "W605": ["A"],
}

_fixMessagesSampleArgs = {
    "FIXWRITE_ERROR": ["OSError"],
}

messageCatalogs = {
    "A": _annotationsMessages,
    "ASY": _asyncMessages,
    "C": _complexityMessages,
    "D": _docStyleMessages,
    "E": _pycodestyleErrorMessages,
    "I": _importsMessages,
    "L": _loggingMessages,
    "M": _miscellaneousMessages,
    "N": _namingStyleMessages,
    "NO": _nameOrderMessages,
    "P": _pathlibMessages,
    "S": _securityMessages,
    "U": _unusedMessages,
    "W": _pycodestyleWarningMessages,
    "Y": _simplifyMessages,
    "FIX": _fixMessages,
}

messageSampleArgsCatalog = {
    "A": _annotationsMessagesSampleArgs,
    "ASY": _asyncMessageSampleArgs,
    "C": _complexityMessagesSampleArgs,
    "D": _docStyleMessagesSampleArgs,
    "E": _pycodestyleErrorMessagesSampleArgs,
    "I": _importsMessagesSampleArgs,
    "L": _loggingMessagesSampleArgs,
    "M": _miscellaneousMessagesSampleArgs,
    "NO": _nameOrderMessagesSampleArgs,
    "S": _securityMessagesSampleArgs,
    "U": _unusedMessagesSampleArgs,
    "W": _pycodestyleWarningMessagesSampleArgs,
    "Y": _simplifyMessagesSampleArgs,
    "FIX": _fixMessagesSampleArgs,
}

messageCategoryRe = re.compile(r"([A-Z]{1,3}).+")
# message category is max. 3 characters


def getTranslatedMessage(messageCode, messageArgs, example=False):
    """
    Module function to get a translated and formatted message for a
    given message ID.

    @param messageCode the message code
    @type str
    @param messageArgs list of arguments or a single integer value to format
        the message
    @type list or int
    @param example flag indicating a translated message filled with example
        data is requested (messageArgs is ignored if given)
    @type bool
    @return translated and formatted message
    @rtype str
    """
    match = messageCategoryRe.match(messageCode)
    if match:
        # the message code is OK
        messageCategory = match.group(1)

        if example:
            try:
                argsCatalog = messageSampleArgsCatalog[messageCategory]
                try:
                    args = argsCatalog[messageCode]
                except KeyError:
                    args = None
            except KeyError:
                args = None
        else:
            args = messageArgs

        with contextlib.suppress(KeyError):
            catalog = messageCatalogs[messageCategory]
            with contextlib.suppress(KeyError):
                message = catalog[messageCode]
                if args is None:
                    return message
                elif isinstance(args, int):
                    # Retranslate with correct plural form
                    return message(args)
                else:
                    return message.format(*args)

    if example:
        return None
    else:
        return QCoreApplication.translate(
            "CodeStyleChecker", "No message defined for code '{0}'."
        ).format(messageCode)


def getMessageCodes():
    """
    Module function to get a list of known message codes.

    @return list of known message codes
    @rtype set of str
    """
    knownCodes = []
    for catalog in messageCatalogs.values():
        knownCodes += list(catalog)
    return {c.split(".", 1)[0] for c in knownCodes}


#
# eflag: noqa = M201
