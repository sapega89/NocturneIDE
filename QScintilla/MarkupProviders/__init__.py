# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package providing various markup providers.
"""

import importlib
import os

from eric7 import Preferences


def getMarkupProvider(editor):
    """
    Public method to get a markup provider for the given editor.

    @param editor reference to the editor to get the markup provider for
    @type Editor
    @return markup provider
    @rtype MarkupBase
    """
    markupModule = ".MarkupBase"
    if editor is not None:
        fn = editor.getFileName()

        if fn:
            extension = os.path.normcase(os.path.splitext(fn)[1][1:])
        else:
            extension = ""
        if (
            extension in Preferences.getEditor("PreviewHtmlFileNameExtensions")
            or editor.getLanguage() == "HTML"
        ):
            markupModule = ".HtmlProvider"
        elif (
            extension in Preferences.getEditor("PreviewMarkdownFileNameExtensions")
            or editor.getLanguage().lower() == "markdown"
        ):
            markupModule = ".MarkdownProvider"
        elif (
            extension in Preferences.getEditor("PreviewRestFileNameExtensions")
            or editor.getLanguage().lower() == "restructuredtext"
        ):
            markupModule = ".RestructuredTextProvider"

    mod = importlib.import_module(markupModule, __package__)
    return mod.createProvider()
