# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a file icon provider determining the icon based on file name.
"""

import fnmatch

from PyQt6.QtGui import QImageReader

from . import EricPixmapCache


class EricFileIconProvider:
    """
    Class implementing a file icon provider determining the icon based on file name.
    """

    def __init__(self):
        """
        Constructor
        """
        # pixmap icon names first because some are overwritten later
        self.__iconMappings = {
            "*.{0}".format(bytes(f).decode()): "filePixmap"
            for f in QImageReader.supportedImageFormats()
        }

        # specific one next
        self.__iconMappings.update(
            {
                "*.sh": "lexerBash",
                "*.bash": "lexerBash",
                "*.bat": "lexerBatch",
                "*.cmd": "lexerBatch",
                "*.cpp": "lexerCPP",
                "*.cxx": "lexerCPP",
                "*.cc": "lexerCPP",
                "*.c": "lexerCPP",
                "*.hpp": "lexerCPP",
                "*.hh": "lexerCPP",
                "*.h": "lexerCPP",
                "*.cs": "lexerCsharp",
                "CMakeLists.txt": "lexerCMake",
                "*.cmake": "lexerCMake",
                "*.cmake.in": "lexerCMake",
                "*.ctest": "lexerCMake",
                "*.ctest.in": "lexerCMake",
                "*.css": "lexerCSS",
                "*.qss": "lexerCSS",
                "*.d": "lexerD",
                "*.di": "lexerD",
                "*.diff": "lexerDiff",
                "*.patch": "lexerDiff",
                "*.html": "lexerHTML",
                "*.htm": "lexerHTML",
                "*.asp": "lexerHTML",
                "*.shtml": "lexerHTML",
                "*.php": "lexerHTML",
                "*.php3": "lexerHTML",
                "*.php4": "lexerHTML",
                "*.php5": "lexerHTML",
                "*.phtml": "lexerHTML",
                "*.docbook": "lexerHTML",
                "*.ui": "fileDesigner",
                "*.ts": "fileLinguist",
                "*.qm": "fileLinguist2",
                "*.qrc": "fileResource",
                "*.kid": "lexerHTML",
                "*.java": "lexerJava",
                "*.js": "lexerJavaScript",
                "*.lua": "lexerLua",
                "*makefile": "lexerMakefile",
                "Makefile*": "lexerMakefile",
                "*.mak": "lexerMakefile",
                "*.pl": "lexerPerl",
                "*.pm": "lexerPerl",
                "*.ph": "lexerPerl",
                "*.pov": "lexerPovray",
                "*.properties": "lexerProperties",
                "*.ini": "lexerProperties",
                "*.inf": "lexerProperties",
                "*.reg": "lexerProperties",
                "*.cfg": "lexerProperties",
                "*.cnf": "lexerProperties",
                "*.rc": "lexerProperties",
                "*.py": "lexerPython3",
                "*.pyw": "lexerPython3",
                "*.py3": "lexerPython3",
                "*.pyw3": "lexerPython3",
                "*.pyx": "lexerCython",
                "*.pxd": "lexerCython",
                "*.pxi": "lexerCython",
                "*.ptl": "lexerPython3",
                "*.rb": "lexerRuby",
                "*.rbw": "lexerRuby",
                "*.sql": "lexerSQL",
                "*.tex": "lexerTeX",
                "*.sty": "lexerTeX",
                "*.aux": "lexerTeX",
                "*.toc": "lexerTeX",
                "*.idx": "lexerTeX",
                "*.vhd": "lexerVHDL",
                "*.vhdl": "lexerVHDL",
                "*.tcl": "lexerTCL",
                "*.tk": "lexerTCL",
                "*.f": "lexerFortran",
                "*.for": "lexerFortran",
                "*.f90": "lexerFortran",
                "*.f95": "lexerFortran",
                "*.f2k": "lexerFortran",
                "*.dpr": "lexerPascal",
                "*.dpk": "lexerPascal",
                "*.pas": "lexerPascal",
                "*.dfm": "lexerPascal",
                "*.inc": "lexerPascal",
                "*.pp": "lexerPascal",
                "*.ps": "lexerPostScript",
                "*.xml": "lexerXML",
                "*.xsl": "lexerXML",
                "*.svg": "fileSvg",
                "*.xsd": "lexerXML",
                "*.xslt": "lexerXML",
                "*.dtd": "lexerXML",
                "*.rdf": "lexerXML",
                "*.xul": "lexerXML",
                "*.yaml": "lexerYAML",
                "*.yml": "lexerYAML",
                "*.m": "lexerMatlab",
                "*.m.matlab": "lexerMatlab",
                "*.m.octave": "lexerOctave",
                "*.e4c": "lexerXML",
                "*.e4d": "lexerXML",
                "*.e4k": "fileShortcuts",
                "*.e4m": "fileMultiProject",
                "*.e4p": "fileProject",
                "*.e4q": "lexerXML",
                "*.e4s": "lexerXML",
                "*.e4t": "lexerXML",
                "*.e5d": "lexerXML",
                "*.e5g": "fileUML",
                "*.e5k": "fileShortcuts",
                "*.e5m": "fileMultiProject",
                "*.e5p": "fileProject",
                "*.e5q": "lexerXML",
                "*.e5s": "lexerXML",
                "*.e5t": "lexerXML",
                "*.e6d": "lexerXML",
                "*.e6k": "fileShortcuts",
                "*.e6m": "fileMultiProject",
                "*.e6p": "fileProject",
                "*.e6q": "lexerXML",
                "*.e6s": "lexerXML",
                "*.e6t": "lexerXML",
                "*.ecj": "lexerJSON",
                "*.edj": "lexerJSON",
                "*.egj": "fileUML",
                "*.ehj": "lexerJSON",
                "*.ekj": "fileShortcuts",
                "*.emj": "fileMultiProject",
                "*.epj": "fileProject",
                "*.eqj": "lexerJSON",
                "*.esj": "lexerJSON",
                "*.etj": "lexerJSON",
                "*.ethj": "lexerJSON",
                "*.po": "lexerGettext",
                "*.coffee": "lexerCoffeeScript",
                "*.json": "lexerJSON",
                "*.md": "lexerMarkdown",
                "*.toml": "lexerProperties",
                "Pipfile": "lexerProperties",
                "poetry.lock": "lexerProperties",
                "*.pdf": "pdfviewer",
            }
        )

    def fileIcon(self, name):
        """
        Public method to get an icon for the given file name.

        @param name file name
        @type str
        @return icon
        @rtype QIcon
        """
        for pat in self.__iconMappings:
            if fnmatch.fnmatch(name, pat):
                return EricPixmapCache.getIcon(self.__iconMappings[pat])
        else:
            return EricPixmapCache.getIcon("fileMisc")

    def fileIconName(self, name):
        """
        Public method to get an icon name for the given file name.

        @param name file name
        @type str
        @return icon name
        @rtype str
        """
        for pat in self.__iconMappings:
            if fnmatch.fnmatch(name, pat):
                return self.__iconMappings[pat]
        else:
            return "fileMisc"
