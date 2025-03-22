# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing testing functionality and interface to various test
frameworks.
"""

from .Interfaces import FrameworkNames


def supportedLanguages():
    """
    Function to get a list of supported programming languages.

    @return list of supported programming languages
    @rtype list of str
    """
    return list(FrameworkNames)


def isLanguageSupported(language):
    """
    Function to check, if the given programming language is supported by any
    testing framework.

    @param language programming language
    @type str
    @return flag indicating support
    @rtype bool
    """
    return language in FrameworkNames
