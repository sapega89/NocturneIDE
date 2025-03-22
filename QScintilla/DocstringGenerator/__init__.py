# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package containing the documentation string generator tool.
"""

from PyQt6.QtCore import QCoreApplication


def getDocstringGenerator(editor):
    """
    Function to get a docstring generator for the given editor.

    @param editor reference to the editor to create a docstring generator for
    @type Editor
    @return reference to the created docstring generator
    @rtype BaseDocstringGenerator
    """
    if editor.isPyFile() or editor.getFileType() in (
        "Cython",
        "Python",
        "Python3",
        "MicroPython",
    ):
        from .PyDocstringGenerator import (  # __IGNORE_WARNING_I101__
            PyDocstringGenerator,
        )

        return PyDocstringGenerator(editor)
    else:
        from .BaseDocstringGenerator import (  # __IGNORE_WARNING_I101__
            BaseDocstringGenerator,
        )

        return BaseDocstringGenerator(editor)


def getSupportedDocstringTypes():
    """
    Function to get the supported docstring types/styles.

    @return list of tuples with supported docstring type/style and the
        corresponding display string
    @rtype tuple of (str, str)
    """
    return [
        ("ericdoc", QCoreApplication.translate("DocstringGenerator", "Eric")),
        ("numpydoc", QCoreApplication.translate("DocstringGenerator", "NumPy")),
        ("googledoc", QCoreApplication.translate("DocstringGenerator", "Google")),
        ("sphinxdoc", QCoreApplication.translate("DocstringGenerator", "Sphinx")),
    ]
