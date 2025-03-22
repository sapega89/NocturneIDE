# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some utility functions for the Black based code formatting.
"""

import re

import black

from PyQt6.QtCore import QCoreApplication, pyqtSlot

from eric7.EricWidgets import EricMessageBox


def getDefaultConfiguration():
    """
    Function to generate a default set of configuration parameters.

    @return dictionary containing the default parameters
    @rtype dict
    """
    return {
        "target-version": set(),
        "line-length": black.DEFAULT_LINE_LENGTH,
        "skip-string-normalization": False,
        "skip-magic-trailing-comma": False,
        "extend-exclude": "",
        "exclude": black.DEFAULT_EXCLUDES,  # not shown in config dialog
        "force-exclude": "",  # not shown in config dialog
    }


def compileRegExp(regexp):
    """
    Function to compile a given regular expression.

    @param regexp regular expression to be compiled
    @type str
    @return compiled regular expression object
    @rtype re.Pattern
    """
    if "\n" in regexp:
        # multi line regexp
        regexp = f"(?x){regexp}"
    compiled = re.compile(regexp)
    return compiled


def validateRegExp(regexp):
    """
    Function to validate a given regular expression.

    @param regexp regular expression to be validated
    @type str
    @return tuple containing a flag indicating validity and an error message
    @rtype tuple of (bool, str)
    """
    if regexp:
        try:
            compileRegExp(regexp)
            return True, ""
        except re.error as e:
            return (
                False,
                QCoreApplication.translate(
                    "BlackUtilities", "Invalid regular expression: {0}"
                ).format(str(e)),
            )
        except IndexError:
            return (
                False,
                QCoreApplication.translate(
                    "BlackUtilities", "Invalid regular expression: missing group name"
                ),
            )
    else:
        return (
            False,
            QCoreApplication.translate(
                "BlackUtilities", "A regular expression must be given."
            ),
        )


@pyqtSlot()
def aboutBlack():
    """
    Slot to show an 'About Black' dialog.
    """
    EricMessageBox.information(
        None,
        QCoreApplication.translate("BlackUtilities", "About Black"),
        QCoreApplication.translate(
            "BlackUtilities",
            """<p><b>Black Version {0}</b></p>"""
            """<p><i>Black</i> is the uncompromising Python code"""
            """ formatter.</p>""",
        ).format(black.__version__),
    )
