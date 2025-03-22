# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the exporter base class.
"""

import pathlib

from PyQt6.QtCore import QCoreApplication, QObject

from eric7.EricWidgets import EricFileDialog, EricMessageBox


class ExporterBase(QObject):
    """
    Class implementing the exporter base class.
    """

    def __init__(self, editor, parent=None):
        """
        Constructor

        @param editor reference to the editor object
        @type QScintilla.Editor.Editor
        @param parent parent object of the exporter
        @type QObject
        """
        super().__init__(parent)
        self.editor = editor

    def _getFileName(self, fileFilter):
        """
        Protected method to get the file name of the export file from the user.

        @param fileFilter filter string to be used. The filter for "All Files (*)"
            is appended by this method.
        @type str
        @return file name entered by the user
        @rtype str
        """
        fileFilter += ";;"
        fileFilter += QCoreApplication.translate("Exporter", "All Files (*)")
        fn, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self.editor,
            QCoreApplication.translate("Exporter", "Export source"),
            "",
            fileFilter,
            "",
            EricFileDialog.DontConfirmOverwrite,
        )

        if fn:
            fpath = pathlib.Path(fn)
            if not fpath.suffix:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fpath = fpath.with_suffix(ex)
            if fpath.exists():
                res = EricMessageBox.yesNo(
                    self.editor,
                    QCoreApplication.translate("Exporter", "Export source"),
                    QCoreApplication.translate(
                        "Exporter",
                        "<p>The file <b>{0}</b> already exists. Overwrite it?</p>",
                    ).format(fpath),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    return ""

            fn = str(fpath)

        return fn

    def exportSource(self):
        """
        Public method performing the export.

        This method must be overridden by the real exporters.

        @exception NotImplementedError raised to indicate that this method
            must be implemented by a subclass
        """
        raise NotImplementedError
