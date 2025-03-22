# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing mimetype dependent functions.
"""

import fnmatch
import mimetypes

from PyQt6.QtCore import QCoreApplication

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox


def isTextFile(filename):
    """
    Function to test, if the given file is a text (i.e. editable) file.

    @param filename name of the file to be checked
    @type str
    @return flag indicating an editable file
    @rtype bool
    """
    mimetype = mimetypes.guess_type(filename)[0]
    if mimetype is None:
        return (
            Preferences.getUI("LoadUnknownMimeTypeFiles")
            or any(
                fnmatch.fnmatch(filename, pat)
                for pat in Preferences.getUI("TextFilePatterns")
            )
            or (
                Preferences.getUI("TextMimeTypesAskUser")
                and EricMessageBox.yesNo(
                    None,
                    QCoreApplication.translate("MimeTypes", "Open File"),
                    QCoreApplication.translate(
                        "MimeTypes",
                        "<p>Is the file <b>{0}</b> a text file to be opened in eric?"
                        "</p><p><b>Note:</b> You may suppress this question by adding"
                        " a pattern to the list of known text files on the"
                        " <b>MimeTypes</b> configuration page.</p>",
                    ).format(filename),
                )
            )
        )
    else:
        return (
            mimetype.split("/")[0] == "text"
            or mimetype in Preferences.getUI("TextMimeTypes")
            or (
                Preferences.getUI("TextMimeTypesAskUser")
                and EricMessageBox.yesNo(
                    None,
                    QCoreApplication.translate("MimeTypes", "Open File"),
                    QCoreApplication.translate(
                        "MimeTypes",
                        "<p>The file <b>{0}</b> has the mime type <b>{1}</b>. This type"
                        " is not recognized as being text to be opened in eric. Is this"
                        " an editable text file?</p>"
                        "<p><b>Note:</b> You may suppress this question by adding an"
                        " entry to the list of known text file types on the"
                        " <b>MimeTypes</b> configuration page.</p>",
                    ).format(filename, mimetype),
                )
            )
        )


def mimeType(filename):
    """
    Function to get the mime type of a file.

    @param filename name of the file to be checked
    @type str
    @return mime type of the file
    @rtype str
    """
    return mimetypes.guess_type(filename)[0]
