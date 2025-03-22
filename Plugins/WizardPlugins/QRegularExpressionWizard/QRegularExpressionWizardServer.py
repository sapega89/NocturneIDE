# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the PyQt6 server part of the QRegularExpression wizzard.
"""

import importlib.util
import json
import sys

from PyQt6.QtCore import QRegularExpression


def rxValidate(regexp, options):
    """
    Function to validate the given regular expression.

    @param regexp regular expression to validate
    @type str
    @param options list of options
    @type list of str
    @return tuple of flag indicating validity, error string and error offset
    @rtype tuple of (bool, str, int)
    """
    rxOptions = QRegularExpression.PatternOption.NoPatternOption
    if "CaseInsensitiveOption" in options:
        rxOptions |= QRegularExpression.PatternOption.CaseInsensitiveOption
    if "MultilineOption" in options:
        rxOptions |= QRegularExpression.PatternOption.MultilineOption
    if "DotMatchesEverythingOption" in options:
        rxOptions |= QRegularExpression.PatternOption.DotMatchesEverythingOption
    if "ExtendedPatternSyntaxOption" in options:
        rxOptions |= QRegularExpression.PatternOption.ExtendedPatternSyntaxOption
    if "InvertedGreedinessOption" in options:
        rxOptions |= QRegularExpression.PatternOption.InvertedGreedinessOption
    if "UseUnicodePropertiesOption" in options:
        rxOptions |= QRegularExpression.PatternOption.UseUnicodePropertiesOption
    if "DontCaptureOption" in options:
        rxOptions |= QRegularExpression.PatternOption.DontCaptureOption

    error = ""
    errorOffset = -1
    re = QRegularExpression(regexp, rxOptions)
    valid = re.isValid()
    if not valid:
        error = re.errorString()
        errorOffset = re.patternErrorOffset()

    return valid, error, errorOffset


def rxExecute(regexp, options, text, startpos):
    """
    Function to execute the given regular expression for a given text.

    @param regexp regular expression to validate
    @type str
    @param options list of options
    @type list of str
    @param text text to execute on
    @type str
    @param startpos start position for the execution
    @type int
    @return tuple of a flag indicating a successful match and a list of captures
        containing the complete match as matched string, match start, match end
        and match length for each entry
    @rtype tuple of (bool, list of [str, int, int, int])
    """
    valid, error, errorOffset = rxValidate(regexp, options)
    if not valid:
        return valid, error, errorOffset

    rxOptions = QRegularExpression.PatternOption.NoPatternOption
    if "CaseInsensitiveOption" in options:
        rxOptions |= QRegularExpression.PatternOption.CaseInsensitiveOption
    if "MultilineOption" in options:
        rxOptions |= QRegularExpression.PatternOption.MultilineOption
    if "DotMatchesEverythingOption" in options:
        rxOptions |= QRegularExpression.PatternOption.DotMatchesEverythingOption
    if "ExtendedPatternSyntaxOption" in options:
        rxOptions |= QRegularExpression.PatternOption.ExtendedPatternSyntaxOption
    if "InvertedGreedinessOption" in options:
        rxOptions |= QRegularExpression.PatternOption.InvertedGreedinessOption
    if "UseUnicodePropertiesOption" in options:
        rxOptions |= QRegularExpression.PatternOption.UseUnicodePropertiesOption
    if "DontCaptureOption" in options:
        rxOptions |= QRegularExpression.PatternOption.DontCaptureOption

    matched = False
    captures = []
    re = QRegularExpression(regexp, rxOptions)
    match = re.match(text, startpos)
    if match.hasMatch():
        matched = True
        for index in range(match.lastCapturedIndex() + 1):
            captures.append(
                [
                    match.captured(index),
                    match.capturedStart(index),
                    match.capturedEnd(index),
                    match.capturedLength(index),
                ]
            )

    return matched, captures


def main():
    """
    Function containing the main routine.
    """
    while True:
        commandStr = sys.stdin.readline()
        try:
            commandDict = json.loads(commandStr)
            responseDict = {"error": ""}
            if "command" in commandDict:
                command = commandDict["command"]
                if command == "exit":
                    break
                elif command == "available":
                    responseDict["available"] = bool(importlib.util.find_spec("PyQt6"))
                elif command == "validate":
                    valid, error, errorOffset = rxValidate(
                        commandDict["regexp"], commandDict["options"]
                    )
                    responseDict["valid"] = valid
                    responseDict["errorMessage"] = error
                    responseDict["errorOffset"] = errorOffset
                elif command == "execute":
                    valid, error, errorOffset = rxValidate(
                        commandDict["regexp"], commandDict["options"]
                    )
                    if not valid:
                        responseDict["valid"] = valid
                        responseDict["errorMessage"] = error
                        responseDict["errorOffset"] = errorOffset
                    else:
                        matched, captures = rxExecute(
                            commandDict["regexp"],
                            commandDict["options"],
                            commandDict["text"],
                            commandDict["startpos"],
                        )
                        responseDict["matched"] = matched
                        responseDict["captures"] = captures
        except ValueError as err:
            responseDict = {"error": str(err)}
        except Exception as err:
            responseDict = {"error": str(err)}
        responseStr = json.dumps(responseDict)
        sys.stdout.write(responseStr)
        sys.stdout.flush()

    sys.exit(0)


if __name__ == "__main__":
    main()
