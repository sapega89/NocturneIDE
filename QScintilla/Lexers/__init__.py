# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing lexers for the various supported programming languages.
"""

import contextlib
import importlib

from PyQt6.QtCore import QCoreApplication

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache

# The lexer registry
# Dictionary with the language name as key. Each entry is a list with
#       0. display string (string)
#       1. dummy filename to derive lexer name (string)
#       2. reference to a function instantiating the specific lexer
#          This function must take a reference to the parent as argument.
#       3. list of open file filters (list of strings)
#       4. list of save file filters (list of strings)
#       5. default lexer associations (list of strings of filename wildcard
#          patterns to be associated with the lexer)
#       6. name of an icon file (string)
LexerRegistry = {}


def registerLexer(
    name,
    displayString,
    filenameSample,
    getLexerFunc,
    openFilters=None,
    saveFilters=None,
    defaultAssocs=None,
    iconFileName="",
):
    """
    Module function to register a custom QScintilla lexer.

    @param name lexer language name
    @type str
    @param displayString display string
    @type str
    @param filenameSample dummy filename to derive lexer name
    @type str
    @param getLexerFunc reference to a function instantiating the specific
        lexer. This function must take a reference to the parent as its only
        argument.
    @type function
    @param openFilters list of open file filters
    @type list of str
    @param saveFilters list of save file filters
    @type list of str
    @param defaultAssocs default lexer associations (list of filename wildcard
        patterns to be associated with the lexer)
    @type list of str
    @param iconFileName name of an icon file
    @type str
    @exception KeyError raised when the given name is already in use
    """
    global LexerRegistry

    if name in LexerRegistry:
        raise KeyError('Lexer "{0}" already registered.'.format(name))
    else:
        LexerRegistry[name] = [
            displayString,
            filenameSample,
            getLexerFunc,
            [] if openFilters is None else openFilters[:],
            [] if saveFilters is None else saveFilters[:],
            [] if defaultAssocs is None else defaultAssocs[:],
            iconFileName,
        ]

        textFilePatterns = Preferences.getUI("TextFilePatterns")
        textFilePatterns.extend([p for p in defaultAssocs if p not in textFilePatterns])
        Preferences.setUI("TextFilePatterns", textFilePatterns)


def unregisterLexer(name):
    """
    Module function to unregister a custom QScintilla lexer.

    @param name lexer language name
    @type str
    """
    global LexerRegistry

    if name in LexerRegistry:
        textFilePatterns = Preferences.getUI("TextFilePatterns")
        for pat in LexerRegistry[name][5]:
            with contextlib.suppress(ValueError):
                textFilePatterns.remove(pat)
        Preferences.setUI("TextFilePatterns", textFilePatterns)

        del LexerRegistry[name]


def getSupportedLanguages():
    """
    Module function to get a dictionary of supported lexer languages.

    @return dictionary of supported lexer languages. The keys are the
        internal language names. The items are lists of three entries.
        The first is the display string for the language, the second
        is a dummy file name, which can be used to derive the lexer, and
        the third is the name of an icon file.
    @rtype dict of {str: [str, str, str]}
    """
    supportedLanguages = {
        "Bash": [QCoreApplication.translate("Lexers", "Bash"), "dummy.sh", "lexerBash"],
        "Batch": [
            QCoreApplication.translate("Lexers", "Batch"),
            "dummy.bat",
            "lexerBatch",
        ],
        "C++": [QCoreApplication.translate("Lexers", "C/C++"), "dummy.cpp", "lexerCPP"],
        "C#": [QCoreApplication.translate("Lexers", "C#"), "dummy.cs", "lexerCsharp"],
        "CMake": [
            QCoreApplication.translate("Lexers", "CMake"),
            "dummy.cmake",
            "lexerCMake",
        ],
        "CSS": [QCoreApplication.translate("Lexers", "CSS"), "dummy.css", "lexerCSS"],
        "Cython": [
            QCoreApplication.translate("Lexers", "Cython"),
            "dummy.pyx",
            "lexerCython",
        ],
        "D": [QCoreApplication.translate("Lexers", "D"), "dummy.d", "lexerD"],
        "Diff": [
            QCoreApplication.translate("Lexers", "Diff"),
            "dummy.diff",
            "lexerDiff",
        ],
        "Fortran": [
            QCoreApplication.translate("Lexers", "Fortran"),
            "dummy.f95",
            "lexerFortran",
        ],
        "Fortran77": [
            QCoreApplication.translate("Lexers", "Fortran77"),
            "dummy.f",
            "lexerFortran",
        ],
        "HTML": [
            QCoreApplication.translate("Lexers", "HTML/PHP/XML"),
            "dummy.html",
            "lexerHTML",
        ],
        "Java": [
            QCoreApplication.translate("Lexers", "Java"),
            "dummy.java",
            "lexerJava",
        ],
        "JavaScript": [
            QCoreApplication.translate("Lexers", "JavaScript"),
            "dummy.js",
            "lexerJavaScript",
        ],
        "Lua": [QCoreApplication.translate("Lexers", "Lua"), "dummy.lua", "lexerLua"],
        "Makefile": [
            QCoreApplication.translate("Lexers", "Makefile"),
            "dummy.mak",
            "lexerMakefile",
        ],
        "Matlab": [
            QCoreApplication.translate("Lexers", "Matlab"),
            "dummy.m.matlab",
            "lexerMatlab",
        ],
        "Octave": [
            QCoreApplication.translate("Lexers", "Octave"),
            "dummy.m.octave",
            "lexerOctave",
        ],
        "Pascal": [
            QCoreApplication.translate("Lexers", "Pascal"),
            "dummy.pas",
            "lexerPascal",
        ],
        "Perl": [QCoreApplication.translate("Lexers", "Perl"), "dummy.pl", "lexerPerl"],
        "PostScript": [
            QCoreApplication.translate("Lexers", "PostScript"),
            "dummy.ps",
            "lexerPostscript",
        ],
        "Povray": [
            QCoreApplication.translate("Lexers", "Povray"),
            "dummy.pov",
            "lexerPOV",
        ],
        "Properties": [
            QCoreApplication.translate("Lexers", "Properties"),
            "dummy.ini",
            "lexerProperties",
        ],
        "Python3": [
            QCoreApplication.translate("Lexers", "Python3"),
            "dummy.py",
            "lexerPython3",
        ],
        "MicroPython": [
            QCoreApplication.translate("Lexers", "MicroPython"),
            "dummy.py",
            "micropython",
        ],
        "QSS": [QCoreApplication.translate("Lexers", "QSS"), "dummy.qss", "lexerCSS"],
        "Ruby": [QCoreApplication.translate("Lexers", "Ruby"), "dummy.rb", "lexerRuby"],
        "SQL": [QCoreApplication.translate("Lexers", "SQL"), "dummy.sql", "lexerSQL"],
        "TCL": [QCoreApplication.translate("Lexers", "TCL"), "dummy.tcl", "lexerTCL"],
        "TeX": [QCoreApplication.translate("Lexers", "TeX"), "dummy.tex", "lexerTeX"],
        "VHDL": [
            QCoreApplication.translate("Lexers", "VHDL"),
            "dummy.vhd",
            "lexerVHDL",
        ],
        "XML": [QCoreApplication.translate("Lexers", "XML"), "dummy.xml", "lexerXML"],
        "YAML": [
            QCoreApplication.translate("Lexers", "YAML"),
            "dummy.yml",
            "lexerYAML",
        ],
        "Gettext": [
            QCoreApplication.translate("Lexers", "Gettext"),
            "dummy.po",
            "lexerGettext",
        ],
        "CoffeeScript": [
            QCoreApplication.translate("Lexers", "CoffeeScript"),
            "dummy.coffee",
            "lexerCoffeeScript",
        ],
        "JSON": [
            QCoreApplication.translate("Lexers", "JSON"),
            "dummy.json",
            "lexerJSON",
        ],
        "Markdown": [
            QCoreApplication.translate("Lexers", "Markdown"),
            "dummy.md",
            "lexerMarkdown",
        ],
    }

    for name in LexerRegistry:
        if not name.startswith("Pygments|"):
            supportedLanguages[name] = LexerRegistry[name][:2] + [
                LexerRegistry[name][6]
            ]

    supportedLanguages["Guessed"] = [
        QCoreApplication.translate("Lexers", "Pygments"),
        "dummy.pygments",
        "",
    ]

    return supportedLanguages


def getSupportedApiLanguages():
    """
    Module function to get a list of supported API languages.

    @return list of supported API languages
    @rtype list of str
    """
    return [
        lang
        for lang in getSupportedLanguages()
        if lang != "Guessed" and not lang.startswith("Pygments|")
    ]


def getLanguageIcon(language, pixmap):
    """
    Module function to get an icon for a language.

    @param language language of the lexer
    @type str
    @param pixmap flag indicating to return a pixmap
    @type bool
    @return icon for the language
    @rtype QPixmap or QIcon
    """
    supportedLanguages = getSupportedLanguages()
    iconFileName = (
        supportedLanguages[language][2] if language in supportedLanguages else ""
    )
    if pixmap:
        return EricPixmapCache.getPixmap(iconFileName)
    else:
        return EricPixmapCache.getIcon(iconFileName)


def getLexer(language, parent=None, pyname=""):
    """
    Module function to instantiate a lexer object for a given language.

    @param language language of the lexer
    @type str
    @param parent reference to the parent object
    @type QObject
    @param pyname name of the pygments lexer to use
    @type str
    @return reference to the instantiated lexer object
    @rtype QsciLexer
    """
    if not pyname:
        languageLexerMapping = {
            "Bash": ".LexerBash",
            "Batch": ".LexerBatch",
            "C#": ".LexerCSharp",
            "C++": ".LexerCPP",
            "CMake": ".LexerCMake",
            "CoffeeScript": ".LexerCoffeeScript",
            "CSS": ".LexerCSS",
            "Cython": ".LexerPython",
            "D": ".LexerD",
            "Diff": ".LexerDiff",
            "Fortran": ".LexerFortran",
            "Fortran77": ".LexerFortran77",
            "Gettext": ".LexerPO",
            "HTML": ".LexerHTML",
            "Java": ".LexerJava",
            "JavaScript": ".LexerJavaScript",
            "JSON": ".LexerJSON",
            "Lua": ".LexerLua",
            "Makefile": ".LexerMakefile",
            "Markdown": ".LexerMarkdown",
            "Matlab": ".LexerMatlab",
            "MicroPython": ".LexerPython",
            "Octave": ".LexerOctave",
            "Pascal": ".LexerPascal",
            "Perl": ".LexerPerl",
            "PostScript": ".LexerPostScript",
            "Properties": ".LexerProperties",
            "Povray": ".LexerPOV",
            "Python": ".LexerPython",
            "Python3": ".LexerPython",
            "QSS": ".LexerQSS",
            "Ruby": ".LexerRuby",
            "SQL": ".LexerSQL",
            "TCL": ".LexerTCL",
            "TeX": ".LexerTeX",
            "VHDL": ".LexerVHDL",
            "XML": ".LexerXML",
            "YAML": ".LexerYAML",
        }
        try:
            if language in languageLexerMapping:
                mod = importlib.import_module(
                    languageLexerMapping[language], __package__
                )
                if mod:
                    return mod.createLexer(language, parent)
                else:
                    return __getPygmentsLexer(parent)

            elif language in LexerRegistry:
                return LexerRegistry[language][2](parent)

            else:
                return __getPygmentsLexer(parent)
        except ImportError:
            return __getPygmentsLexer(parent)
    else:
        return __getPygmentsLexer(parent, name=pyname)


def __getPygmentsLexer(parent, name=""):
    """
    Private module function to instantiate a pygments lexer.

    @param parent reference to the parent widget
    @type QWidget
    @param name name of the pygments lexer to use
    @type str
    @return reference to the lexer or None
    @rtype LexerPygments
    """
    from .LexerPygments import LexerPygments

    lexer = LexerPygments(parent, name=name)
    if lexer.canStyle():
        return lexer
    else:
        return None


def getOpenFileFiltersList(includeAll=False, asString=False, withAdditional=True):
    """
    Module function to get the file filter list for an open file operation.

    @param includeAll flag indicating the inclusion of the "All Files" filter
    @type bool
    @param asString flag indicating the list should be returned as a string
    @type bool
    @param withAdditional flag indicating to include additional filters defined
        by the user
    @type bool
    @return file filter list
    @rtype list of str or str
    """
    openFileFiltersList = [
        QCoreApplication.translate("Lexers", "Python Files (*.py *.py3)"),
        QCoreApplication.translate("Lexers", "Python GUI Files (*.pyw *.pyw3)"),
        QCoreApplication.translate("Lexers", "Cython Files (*.pyx *.pxd *.pxi)"),
        QCoreApplication.translate("Lexers", "Quixote Template Files (*.ptl)"),
        QCoreApplication.translate("Lexers", "Ruby Files (*.rb)"),
        QCoreApplication.translate("Lexers", "C Files (*.h *.c)"),
        QCoreApplication.translate(
            "Lexers", "C++ Files (*.h *.hpp *.hh *.cxx *.cpp *.cc)"
        ),
        QCoreApplication.translate("Lexers", "C# Files (*.cs)"),
        QCoreApplication.translate("Lexers", "HTML Files (*.html *.htm *.asp *.shtml)"),
        QCoreApplication.translate("Lexers", "CSS Files (*.css)"),
        QCoreApplication.translate("Lexers", "QSS Files (*.qss)"),
        QCoreApplication.translate(
            "Lexers", "PHP Files (*.php *.php3 *.php4 *.php5 *.phtml)"
        ),
        QCoreApplication.translate(
            "Lexers", "XML Files (*.xml *.xsl *.xslt *.dtd *.svg *.xul *.xsd)"
        ),
        QCoreApplication.translate("Lexers", "Qt Resource Files (*.qrc)"),
        QCoreApplication.translate("Lexers", "D Files (*.d *.di)"),
        QCoreApplication.translate("Lexers", "Java Files (*.java)"),
        QCoreApplication.translate("Lexers", "JavaScript Files (*.js)"),
        QCoreApplication.translate("Lexers", "SQL Files (*.sql)"),
        QCoreApplication.translate("Lexers", "Docbook Files (*.docbook)"),
        QCoreApplication.translate("Lexers", "Perl Files (*.pl *.pm *.ph)"),
        QCoreApplication.translate("Lexers", "Lua Files (*.lua)"),
        QCoreApplication.translate(
            "Lexers", "Tex Files (*.tex *.sty *.aux *.toc *.idx)"
        ),
        QCoreApplication.translate("Lexers", "Shell Files (*.sh)"),
        QCoreApplication.translate("Lexers", "Batch Files (*.bat *.cmd)"),
        QCoreApplication.translate("Lexers", "Diff Files (*.diff *.patch)"),
        QCoreApplication.translate("Lexers", "Makefiles (*makefile Makefile *.mak)"),
        QCoreApplication.translate(
            "Lexers",
            "Properties Files (*.properties *.ini *.inf *.reg *.cfg *.cnf *.rc)",
        ),
        QCoreApplication.translate("Lexers", "Povray Files (*.pov)"),
        QCoreApplication.translate(
            "Lexers", "CMake Files (CMakeLists.txt *.cmake *.ctest)"
        ),
        QCoreApplication.translate("Lexers", "VHDL Files (*.vhd *.vhdl)"),
        QCoreApplication.translate("Lexers", "TCL/Tk Files (*.tcl *.tk)"),
        QCoreApplication.translate("Lexers", "Fortran Files (*.f90 *.f95 *.f2k)"),
        QCoreApplication.translate("Lexers", "Fortran77 Files (*.f *.for)"),
        QCoreApplication.translate(
            "Lexers", "Pascal Files (*.dpr *.dpk *.pas *.dfm *.inc *.pp)"
        ),
        QCoreApplication.translate("Lexers", "PostScript Files (*.ps)"),
        QCoreApplication.translate("Lexers", "YAML Files (*.yaml *.yml)"),
        QCoreApplication.translate("Lexers", "TOML Files (*.toml)"),
        QCoreApplication.translate("Lexers", "Matlab Files (*.m *.m.matlab)"),
        QCoreApplication.translate("Lexers", "Octave Files (*.m *.m.octave)"),
        QCoreApplication.translate("Lexers", "Gettext Files (*.po)"),
        QCoreApplication.translate("Lexers", "CoffeeScript Files (*.coffee)"),
        QCoreApplication.translate("Lexers", "JSON Files (*.json)"),
        QCoreApplication.translate("Lexers", "Markdown Files (*.md)"),
    ]

    for name in LexerRegistry:
        openFileFiltersList.extend(LexerRegistry[name][3])

    if withAdditional:
        openFileFiltersList.extend(Preferences.getEditor("AdditionalOpenFilters"))

    openFileFiltersList.sort()
    if includeAll:
        openFileFiltersList.append(
            QCoreApplication.translate("Lexers", "All Files (*)")
        )

    if asString:
        return ";;".join(openFileFiltersList)
    else:
        return openFileFiltersList


def getSaveFileFiltersList(includeAll=False, asString=False, withAdditional=True):
    """
    Module function to get the file filter list for a save file operation.

    @param includeAll flag indicating the inclusion of the "All Files" filter
    @type bool
    @param asString flag indicating the list should be returned as a string
    @type bool
    @param withAdditional flag indicating to include additional filters defined
        by the user
    @type bool
    @return file filter list
    @rtype list of str or str
    """
    saveFileFiltersList = [
        QCoreApplication.translate("Lexers", "Python3 Files (*.py)"),
        QCoreApplication.translate("Lexers", "Python3 GUI Files (*.pyw)"),
        QCoreApplication.translate("Lexers", "Cython Files (*.pyx)"),
        QCoreApplication.translate("Lexers", "Cython Declaration Files (*.pxd)"),
        QCoreApplication.translate("Lexers", "Cython Include Files (*.pxi)"),
        QCoreApplication.translate("Lexers", "Quixote Template Files (*.ptl)"),
        QCoreApplication.translate("Lexers", "Ruby Files (*.rb)"),
        QCoreApplication.translate("Lexers", "C Files (*.c)"),
        QCoreApplication.translate("Lexers", "C++ Files (*.cpp)"),
        QCoreApplication.translate("Lexers", "C++/C Header Files (*.h)"),
        QCoreApplication.translate("Lexers", "C# Files (*.cs)"),
        QCoreApplication.translate("Lexers", "HTML Files (*.html)"),
        QCoreApplication.translate("Lexers", "PHP Files (*.php)"),
        QCoreApplication.translate("Lexers", "ASP Files (*.asp)"),
        QCoreApplication.translate("Lexers", "CSS Files (*.css)"),
        QCoreApplication.translate("Lexers", "QSS Files (*.qss)"),
        QCoreApplication.translate("Lexers", "XML Files (*.xml)"),
        QCoreApplication.translate("Lexers", "XSL Files (*.xsl)"),
        QCoreApplication.translate("Lexers", "DTD Files (*.dtd)"),
        QCoreApplication.translate("Lexers", "Qt Resource Files (*.qrc)"),
        QCoreApplication.translate("Lexers", "D Files (*.d)"),
        QCoreApplication.translate("Lexers", "D Interface Files (*.di)"),
        QCoreApplication.translate("Lexers", "Java Files (*.java)"),
        QCoreApplication.translate("Lexers", "JavaScript Files (*.js)"),
        QCoreApplication.translate("Lexers", "SQL Files (*.sql)"),
        QCoreApplication.translate("Lexers", "Docbook Files (*.docbook)"),
        QCoreApplication.translate("Lexers", "Perl Files (*.pl)"),
        QCoreApplication.translate("Lexers", "Perl Module Files (*.pm)"),
        QCoreApplication.translate("Lexers", "Lua Files (*.lua)"),
        QCoreApplication.translate("Lexers", "Shell Files (*.sh)"),
        QCoreApplication.translate("Lexers", "Batch Files (*.bat)"),
        QCoreApplication.translate("Lexers", "TeX Files (*.tex)"),
        QCoreApplication.translate("Lexers", "TeX Template Files (*.sty)"),
        QCoreApplication.translate("Lexers", "Diff Files (*.diff)"),
        QCoreApplication.translate("Lexers", "Make Files (*.mak)"),
        QCoreApplication.translate("Lexers", "Properties Files (*.ini)"),
        QCoreApplication.translate("Lexers", "Configuration Files (*.cfg)"),
        QCoreApplication.translate("Lexers", "Povray Files (*.pov)"),
        QCoreApplication.translate("Lexers", "CMake Files (CMakeLists.txt)"),
        QCoreApplication.translate("Lexers", "CMake Macro Files (*.cmake)"),
        QCoreApplication.translate("Lexers", "VHDL Files (*.vhd)"),
        QCoreApplication.translate("Lexers", "TCL Files (*.tcl)"),
        QCoreApplication.translate("Lexers", "Tk Files (*.tk)"),
        QCoreApplication.translate("Lexers", "Fortran Files (*.f95)"),
        QCoreApplication.translate("Lexers", "Fortran77 Files (*.f)"),
        QCoreApplication.translate("Lexers", "Pascal Files (*.pas)"),
        QCoreApplication.translate("Lexers", "PostScript Files (*.ps)"),
        QCoreApplication.translate("Lexers", "YAML Files (*.yml)"),
        QCoreApplication.translate("Lexers", "TOML Files (*.toml)"),
        QCoreApplication.translate("Lexers", "Matlab Files (*.m)"),
        QCoreApplication.translate("Lexers", "Octave Files (*.m.octave)"),
        QCoreApplication.translate("Lexers", "Gettext Files (*.po)"),
        QCoreApplication.translate("Lexers", "CoffeeScript Files (*.coffee)"),
        QCoreApplication.translate("Lexers", "JSON Files (*.json)"),
        QCoreApplication.translate("Lexers", "Markdown Files (*.md)"),
    ]

    for name in LexerRegistry:
        saveFileFiltersList.extend(LexerRegistry[name][4])

    if withAdditional:
        saveFileFiltersList.extend(Preferences.getEditor("AdditionalSaveFilters"))

    saveFileFiltersList.sort()

    if includeAll:
        saveFileFiltersList.append(
            QCoreApplication.translate("Lexers", "All Files (*)")
        )

    if asString:
        return ";;".join(saveFileFiltersList)
    else:
        return saveFileFiltersList


def getDefaultLexerAssociations():
    """
    Module function to get a dictionary with the default associations.

    @return dictionary with the default lexer associations
    @rtype dict
    """
    assocs = {
        "*.sh": "Bash",
        "*.bash": "Bash",
        "*.bat": "Batch",
        "*.cmd": "Batch",
        "*.cpp": "C++",
        "*.cxx": "C++",
        "*.cc": "C++",
        "*.c": "C++",
        "*.hpp": "C++",
        "*.hh": "C++",
        "*.h": "C++",
        "*.cs": "C#",
        "CMakeLists.txt": "CMake",
        "*.cmake": "CMake",
        "*.cmake.in": "CMake",
        "*.ctest": "CMake",
        "*.ctest.in": "CMake",
        "*.css": "CSS",
        "*.qss": "QSS",
        "*.d": "D",
        "*.di": "D",
        "*.diff": "Diff",
        "*.patch": "Diff",
        "*.html": "HTML",
        "*.htm": "HTML",
        "*.asp": "HTML",
        "*.shtml": "HTML",
        "*.php": "HTML",
        "*.php3": "HTML",
        "*.php4": "HTML",
        "*.php5": "HTML",
        "*.phtml": "HTML",
        "*.docbook": "HTML",
        "*.ui": "HTML",
        "*.ts": "HTML",
        "*.qrc": "HTML",
        "*.kid": "HTML",
        "*.java": "Java",
        "*.js": "JavaScript",
        "*.lua": "Lua",
        "*makefile": "Makefile",
        "Makefile*": "Makefile",
        "*.mak": "Makefile",
        "*.pl": "Perl",
        "*.pm": "Perl",
        "*.ph": "Perl",
        "*.pov": "Povray",
        "*.properties": "Properties",
        "*.ini": "Properties",
        "*.inf": "Properties",
        "*.reg": "Properties",
        "*.cfg": "Properties",
        "*.cnf": "Properties",
        "*.rc": "Properties",
        "*.py": "Python",
        "*.pyw": "Python",
        "*.py3": "Python",
        "*.pyw3": "Python",
        "*.pyx": "Cython",
        "*.pxd": "Cython",
        "*.pxi": "Cython",
        "*.ptl": "Python",
        "*.rb": "Ruby",
        "*.rbw": "Ruby",
        "*.sql": "SQL",
        "*.tex": "TeX",
        "*.sty": "TeX",
        "*.aux": "TeX",
        "*.toc": "TeX",
        "*.idx": "TeX",
        "*.vhd": "VHDL",
        "*.vhdl": "VHDL",
        "*.tcl": "TCL",
        "*.tk": "TCL",
        "*.f": "Fortran77",
        "*.for": "Fortran77",
        "*.f90": "Fortran",
        "*.f95": "Fortran",
        "*.f2k": "Fortran",
        "*.dpr": "Pascal",
        "*.dpk": "Pascal",
        "*.pas": "Pascal",
        "*.dfm": "Pascal",
        "*.inc": "Pascal",
        "*.pp": "Pascal",
        "*.ps": "PostScript",
        "*.xml": "XML",
        "*.xsl": "XML",
        "*.svg": "XML",
        "*.xsd": "XML",
        "*.xslt": "XML",
        "*.dtd": "XML",
        "*.rdf": "XML",
        "*.xul": "XML",
        "*.yaml": "YAML",
        "*.yml": "YAML",
        "*.m": "Matlab",
        "*.m.matlab": "Matlab",
        "*.m.octave": "Octave",
        "*.ecj": "JSON",
        "*.edj": "JSON",
        "*.egj": "JSON",
        "*.ehj": "JSON",
        "*.ekj": "JSON",
        "*.emj": "JSON",
        "*.epj": "JSON",
        "*.eqj": "JSON",
        "*.esj": "JSON",
        "*.etj": "JSON",
        "*.ethj": "JSON",
        "*.po": "Gettext",
        "*.coffee": "CoffeeScript",
        "*.json": "JSON",
        "*.md": "Markdown",
        "*.toml": "Pygments|TOML",
        "Pipfile": "Pygments|TOML",
        "poetry.lock": "Pygments|TOML",
        "*.groovy": "Pygments|Groovy",
        "Jenkinsfile": "Pygments|Groovy",
        "*.jenkinsfile": "Pygments|Groovy",
        "Jenkinsfile.*": "Pygments|Groovy",
    }

    for name in LexerRegistry:
        for pattern in LexerRegistry[name][5]:
            assocs[pattern] = name

    return assocs
