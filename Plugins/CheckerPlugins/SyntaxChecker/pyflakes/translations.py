# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing message translations for pyflakes warning messages.
"""


from PyQt6.QtCore import QCoreApplication

__all__ = ["getTranslatedFlakesMessage"]

_messages = {
    "F01": QCoreApplication.translate(
        "pyFlakes",
        "{0!r} imported but unused. Consider using 'importlib.util.find_spec()'.",
    ),
    "F02": QCoreApplication.translate(
        "pyFlakes", "Redefinition of unused {0!r} from line {1!r}."
    ),
    "F03": QCoreApplication.translate(
        "pyFlakes", "Import {0!r} from line {1!r} shadowed by loop variable."
    ),
    "F04": QCoreApplication.translate(
        "pyFlakes", "'from {0} import *' used; unable to detect undefined names."
    ),
    "F05": QCoreApplication.translate("pyFlakes", "Undefined name {0!r}."),
    "F06": QCoreApplication.translate("pyFlakes", "Undefined name {0!r} in __all__."),
    "F07A": QCoreApplication.translate(
        "pyFlakes",
        "Local variable {0!r} (defined in enclosing scope on line {1!r})"
        " referenced before assignment.",
    ),
    "F07B": QCoreApplication.translate(
        "pyFlakes",
        "Local variable {0!r} (defined as a builtin) referenced before assignment.",
    ),
    "F08": QCoreApplication.translate(
        "pyFlakes", "Duplicate argument {0!r} in function definition."
    ),
    "F09": QCoreApplication.translate(
        "pyFlakes", "Redefinition of {0!r} from line {1!r}."
    ),
    "F10": QCoreApplication.translate(
        "pyFlakes", "from __future__ imports must occur at the beginning of the file"
    ),
    "F11": QCoreApplication.translate(
        "pyFlakes", "Local variable {0!r} is assigned to but never used."
    ),
    "F12": QCoreApplication.translate(
        "pyFlakes", "Local variable {0!r} is annotated but never used."
    ),
    "F13": QCoreApplication.translate("pyFlakes", "Syntax error detected in doctest."),
    "F15": QCoreApplication.translate("pyFlakes", "'return' outside function"),
    "F16": QCoreApplication.translate(
        "pyFlakes", "'from {0} import *' only allowed at module level"
    ),
    "F17": QCoreApplication.translate(
        "pyFlakes", "{0!r} may be undefined, or defined from star imports: {1}"
    ),
    "F18": QCoreApplication.translate(
        "pyFlakes", "Dictionary key {0} repeated with different values"
    ),
    "F19": QCoreApplication.translate(
        "pyFlakes", "Dictionary key variable {0} repeated with different values"
    ),
    "F20": QCoreApplication.translate("pyFlakes", "Future feature {0} is not defined"),
    "F21": QCoreApplication.translate("pyFlakes", "'yield' outside function"),
    "F22": QCoreApplication.translate("pyFlakes", "'continue' not properly in loop"),
    "F23": QCoreApplication.translate("pyFlakes", "'break' outside loop"),
    "F25": QCoreApplication.translate("pyFlakes", "Default 'except:' must be last"),
    "F26": QCoreApplication.translate(
        "pyFlakes", "Two starred expressions in assignment"
    ),
    "F27": QCoreApplication.translate(
        "pyFlakes", "Too many expressions in star-unpacking assignment"
    ),
    "F28": QCoreApplication.translate(
        "pyFlakes", "Assertion is always true, perhaps remove parentheses?"
    ),
    "F29": QCoreApplication.translate(
        "pyFlakes", "syntax error in forward annotation {0!r}"
    ),
    "F30": QCoreApplication.translate(
        "pyFlakes", "'raise NotImplemented' should be 'raise NotImplementedError'"
    ),
    "F32": QCoreApplication.translate(
        "pyFlakes", "use of >> is invalid with print function"
    ),
    "F33": QCoreApplication.translate(
        "pyFlakes", "use ==/!= to compare str, bytes, and int literals"
    ),
    "F34": QCoreApplication.translate("pyFlakes", "f-string is missing placeholders"),
    "F35": QCoreApplication.translate(
        "pyFlakes", "'...'.format(...) has unused arguments at position(s): {0}"
    ),
    "F36": QCoreApplication.translate(
        "pyFlakes", "'...'.format(...) has unused named argument(s): {0}"
    ),
    "F37": QCoreApplication.translate(
        "pyFlakes", "'...'.format(...) is missing argument(s) for placeholder(s): {0}"
    ),
    "F38": QCoreApplication.translate(
        "pyFlakes", "'...'.format(...) mixes automatic and manual numbering"
    ),
    "F39": QCoreApplication.translate(
        "pyFlakes", "'...'.format(...) has invalid format string: {0}"
    ),
    "F40": QCoreApplication.translate(
        "pyFlakes", "'...' % ... has invalid format string: {0}"
    ),
    "F41": QCoreApplication.translate(
        "pyFlakes", "'...' % ... has mixed positional and named placeholders"
    ),
    "F42": QCoreApplication.translate(
        "pyFlakes", "'...' % ... has unsupported format character {0!r}"
    ),
    "F43": QCoreApplication.translate(
        "pyFlakes", "'...' % ... has {0:d} placeholder(s) but {1:d} substitution(s)"
    ),
    "F44": QCoreApplication.translate(
        "pyFlakes", "'...' % ... has unused named argument(s): {0}"
    ),
    "F45": QCoreApplication.translate(
        "pyFlakes", "'...' % ... is missing argument(s) for placeholder(s): {0}"
    ),
    "F46": QCoreApplication.translate(
        "pyFlakes", "'...' % ... expected mapping but got sequence"
    ),
    "F47": QCoreApplication.translate(
        "pyFlakes", "'...' % ... expected sequence but got mapping"
    ),
    "F48": QCoreApplication.translate(
        "pyFlakes", "'...' % ... `*` specifier requires sequence"
    ),
    "F49": QCoreApplication.translate(
        "pyFlakes",
        "'if tuple literal' is always true, perhaps remove accidental comma?",
    ),
}


def getTranslatedFlakesMessage(message_id, message_args):
    """
    Module function to get a translated and formatted message for a
    given pyflakes message ID.

    @param message_id message ID
    @type str
    @param message_args arguments for a formatted message
    @type list
    @return translated and formatted message
    @rtype str
    """
    if message_id in _messages:
        msg = _messages[message_id].replace("{0!r}", "'{0}'")
        msg = msg.replace("{1!r}", "'{1}'")
        return msg.format(*message_args)
    else:
        return QCoreApplication.translate(
            "pyFlakes", "no message defined for code '{0}'"
        ).format(message_id)
