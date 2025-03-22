# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing exporters for various file formats.
"""

import contextlib
import importlib

from PyQt6.QtCore import QCoreApplication


def getSupportedFormats():
    """
    Module function to get a dictionary of supported exporters.

    @return dictionary of supported exporters. The keys are the
        internal format names. The items are the display strings
        for the exporters.
    @rtype dict
    """
    supportedFormats = {
        "HTML": QCoreApplication.translate("Exporters", "HTML"),
        "RTF": QCoreApplication.translate("Exporters", "RTF"),
        "PDF": QCoreApplication.translate("Exporters", "PDF"),
        "TeX": QCoreApplication.translate("Exporters", "TeX"),
        "ODT": QCoreApplication.translate("Exporters", "ODT"),
    }

    return supportedFormats


def getExporter(exporterFormat, editor):
    """
    Module function to instantiate an exporter object for a given format.

    @param exporterFormat format of the exporter
    @type str
    @param editor reference to the editor object
    @type QScintilla.Editor.Editor
    @return reference to the instanciated exporter object
    @rtype QScintilla.Exporter.Exporter
    """
    exporterMapping = {
        "HTML": ".ExporterHTML",
        "ODT": ".ExporterODT",
        "PDF": ".ExporterPDF",
        "RTF": ".ExporterRTF",
        "TeX": ".ExporterTEX",
    }
    with contextlib.suppress(ImportError):
        if exporterFormat in exporterMapping:
            mod = importlib.import_module(exporterMapping[exporterFormat], __package__)
            return mod.createExporter(editor)

    return None
