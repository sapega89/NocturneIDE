# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing functions to prepare an HTML documentation view.
"""

import os

from PyQt6.QtCore import QCoreApplication

from eric7 import EricUtilities
from eric7.EricWidgets.EricApplication import ericApp

_stylesheetsCache = {
    "dark": "",
    "light": "",
}


def _stylesheet():
    """
    Function to get the stylesheet matching the desktop environment.

    @return stylesheet
    @rtype str
    """
    stylesheetType = "dark" if ericApp().usesDarkPalette() else "light"
    if not _stylesheetsCache[stylesheetType]:
        # load the stylesheet from file
        stylesheetFilePath = os.path.join(
            os.path.dirname(__file__),
            "data",
            "documentViewerStyle-{0}.css".format(stylesheetType),
        )
        with open(stylesheetFilePath, "r") as f:
            _stylesheetsCache[stylesheetType] = f.read()

    return _stylesheetsCache[stylesheetType]


def prepareDocumentationViewerHtmlDocument(documentationInfo):
    """
    Public function to prepare the HTML document.

    @param documentationInfo dictionary containing the various documentation
        parts
    @type dict
    @return prepared HTML document
    @rtype str
    """
    mainTemplate = """
        <!DOCTYPE html>
        <html>
        <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8">
        <style>{0}</style>
        </head>
        <body>
            @HEADER@
            @DOCSTRING@
        </body>
        </html>
    """

    headerTemplate = """
        @TITLE@
        @METADATA@
    """

    titleTemplate = """
        <div class="title"><h1>@NAME@</h1></div>
    """

    metadataTemplate = """
        <div class="metadata">
        @ARGSPEC@
        @TYPE@
        @NOTE@
        </div>
    """

    argspecTemplate = QCoreApplication.translate(
        "CodeDocumentationViewer",
        '<p><b>Definition:</b> <span class="def">@NAME@@ARGSPEC@</span></p>',
        "Just translate 'Definition:' and leave the rest intact.",
    )

    typeTemplate = QCoreApplication.translate(
        "CodeDocumentationViewer",
        "<p><b>Type:</b> @TYPE@</p>",
        "Just translate 'Type:' and leave the rest intact.",
    )

    noteTemplate = QCoreApplication.translate(
        "CodeDocumentationViewer",
        "<p><b>Note:</b> @NOTE@</p>",
        "Just translate 'Note:' and leave the rest intact.",
    )

    docstringTemplate = """
        <div class="docstring">
        @DOCSTRING@
        </div>
    """

    name = documentationInfo["name"]
    if name:
        title = titleTemplate.replace("@NAME@", name)
        if "argspec" in documentationInfo and documentationInfo["argspec"]:
            argspec = EricUtilities.html_encode(documentationInfo["argspec"])
            for char in ["=", ",", "(", ")", "*", "**"]:
                argspec = argspec.replace(
                    char, '<span class="argspec-highlight">{0}</span>'.format(char)
                )
            argspec = argspecTemplate.replace("@NAME@", name).replace(
                "@ARGSPEC@", argspec
            )
        else:
            argspec = argspecTemplate.replace("@NAME@", name).replace("@ARGSPEC@", "")

        if "typ" in documentationInfo and documentationInfo["typ"]:
            typeInfo = typeTemplate.replace("@TYPE@", documentationInfo["typ"])
        else:
            typeInfo = ""

        if "note" in documentationInfo and documentationInfo["note"]:
            note = noteTemplate.replace("@NOTE@", documentationInfo["note"])
        else:
            note = ""

        metaData = (
            metadataTemplate.replace("@ARGSPEC@", argspec)
            .replace("@TYPE@", typeInfo)
            .replace("@NOTE@", note)
        )

        header = headerTemplate.replace("@TITLE@", title).replace(
            "@METADATA@", metaData
        )
    else:
        header = ""

    if "docstring" in documentationInfo and documentationInfo["docstring"]:
        docstring = (
            documentationInfo["docstring"]
            .replace("\r\n", "<br/>")
            .replace("\n", "<br/>")
            .replace("\r", "<br/>")
        )
        docstring = docstringTemplate.replace("@DOCSTRING@", docstring)
    else:
        docstring = """<div class="hr"></div><div id="doc-warning">{0}</div>""".format(
            QCoreApplication.translate(
                "CodeDocumentationViewer", "No further documentation available"
            )
        )

    return (
        mainTemplate.format(_stylesheet())
        .replace("@HEADER@", header)
        .replace("@DOCSTRING@", docstring)
    )


def prepareDocumentationViewerHtmlDocWarningDocument(text):
    """
    Public function to prepare a HTML warning document.

    @param text warning text to be shown
    @type str
    @return prepared HTML document
    @rtype str
    """
    mainTemplate = """
        <!DOCTYPE html>
        <html>
        <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8">
        <style>{0}</style>
        </head>
        <body>
            <div id="doc-warning">@TEXT@</div>
        </body>
        </html>
    """

    return mainTemplate.format(_stylesheet()).replace("@TEXT@", text)


def prepareDocumentationViewerHtmlWarningDocument(text):
    """
    Public function to prepare a HTML warning document.

    @param text warning text to be shown
    @type str
    @return prepared HTML document
    @rtype str
    """
    mainTemplate = """
        <!DOCTYPE html>
        <html>
        <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8">
        <style>{0}</style>
        </head>
        <body>
            <div id="warning">@TEXT@</div>
        </body>
        </html>
    """

    return mainTemplate.format(_stylesheet()).replace("@TEXT@", text)
