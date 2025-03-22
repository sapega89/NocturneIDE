# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing the preferences interface.

The preferences interface consists of a class, which defines the default
values for all configuration items and stores the actual values. These
values are read and written to the eric7 preferences file by module
functions. The data is stored in a file in a subdirectory of the users home
directory. The individual configuration data is accessed by accessor functions
defined on the module level. The module is simply imported wherever it is
needed with the statement 'from eric7 import Preferences'. Do not use
'from eric7.Preferences import *' to import it.
"""

import ast
import fnmatch
import json
import os
import pathlib
import shutil

from PyQt6.Qsci import QsciLexerPython, QsciScintilla
from PyQt6.QtCore import (
    QByteArray,
    QCoreApplication,
    QDateTime,
    QDir,
    QLibraryInfo,
    QLocale,
    QPoint,
    QSettings,
    QSize,
    Qt,
    QtMsgType,
    QUrl,
)
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import QApplication

try:
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
except ImportError:
    QWebEngineSettings = None

from eric7 import EricUtilities, Globals
from eric7.EricCore import EricPreferences
from eric7.EricUtilities import toBool, toByteArray, toDict, toList  # noqa
from eric7.EricUtilities.crypto import pwConvert
from eric7.EricUtilities.crypto.py3PBKDF2 import hashPassword
from eric7.EricWidgets import EricFileDialog
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricIconBar import EricIconBar
from eric7.QScintilla.QsciScintillaCompat import QsciScintillaPrintColorMode
from eric7.QScintilla.Shell import ShellHistoryStyle
from eric7.SystemUtilities import OSUtilities, PythonUtilities, QtUtilities


class Prefs:
    """
    A class to hold all configuration items for the application.
    """

    # defaults for the variables window
    varDefaults = {"LocalsFilter": "[]", "GlobalsFilter": "[]"}

    # defaults for the debugger
    debuggerDefaults = {
        "RemoteDbgEnabled": False,
        "RemoteHost": "",
        "RemoteExecution": "",
        "RemoteDebugClient": "",
        "PassiveDbgEnabled": False,
        "PassiveDbgPort": 42424,
        "PassiveDbgType": "Python",
        "PassivAutoContinue": False,
        "AutomaticReset": False,
        "Autosave": True,
        "ThreeStateBreakPoints": False,
        "RecentNumber": 9,
        # max. number of file names to be remembered for the add breakpoint
        # dialog
        "BreakAlways": False,
        "IntelligentBreakpoints": True,
        "ShowExceptionInShell": True,
        "Python3VirtualEnv": "",
        "RubyInterpreter": "",
        "DebugClientType3": "standard",
        # supported "standard", "custom"
        "DebugClient3": "",
        "DebugEnvironmentReplace": False,
        "DebugEnvironment": "",
        "PythonRedirect": True,
        "PythonNoEncoding": False,
        "Python3Redirect": True,
        "Python3NoEncoding": False,
        "RubyRedirect": True,
        "ConsoleDbgEnabled": False,
        "ConsoleDbgCommand": "",
        "PathTranslation": False,
        "PathTranslationRemote": "",
        "PathTranslationLocal": "",
        "NetworkInterface": "127.0.0.1",
        "NetworkPortFixed": False,
        "NetworkPortIncrement": False,
        "NetworkPort": 35000,
        "AutoViewSourceCode": False,
        "ShowOnlyAsDefault": False,
        "MaxVariableSize": 0,  # Bytes, 0 = no limit
        "BgColorNew": QColor("#28FFEEAA"),
        "BgColorChanged": QColor("#2870FF66"),
        "AllowedHosts": ["127.0.0.1", "::1%0"],
        # space separated list of Python3 extensions
        "Python3Extensions": ".py .pyw .py3 .pyw3",
        # Global Multiprocess Debugging Support
        "MultiProcessEnabled": True,
        # Python call trace optimization
        "PythonCallTraceOptimization": False,
    }

    # defaults for the UI settings
    uiDefaults = {
        "KeyboardInputInterval": 0,  # 0 = use system default
        "BackgroundServiceProcesses": 0,  # 0 = max. CPUs minus one
        "Language": "System",
        "Style": "System",
        "StyleSheet": "",
        "StyleIconsPath": "",
        "ActivateItemOnSingleClick": "default",
        # "default", "singleclick" or "doubleclick"
        "ViewManager": "tabview",
        "LayoutType": "Sidebars",  # "Toolboxes" or "Sidebars"
        "CombinedLeftRightSidebar": False,  # place all tools into the
        # left sidebar
        "IconBarColor": QColor("#008800"),
        "IconBarSize": EricIconBar.DefaultBarSize,
        "BrowsersListFoldersFirst": True,
        "BrowsersHideNonPublic": False,
        "BrowsersListContentsByOccurrence": False,
        "BrowsersListHiddenFiles": False,
        "BrowsersFileFilters": "*.py[co];*.so;*.dll",
        "BrowserShowCoding": True,
        "BrowsersFilterRemoteEntries": True,
        "LogViewerAutoRaise": True,
        "LogViewerStdoutFilter": [],
        "LogViewerStderrFilter": [],
        "LogViewerStdxxxFilter": [],
        "SingleApplicationMode": False,
        "CaptionShowsFilename": True,
        "CaptionFilenameLength": 100,
        "RecentNumber": 9,
        "TabViewManagerFilenameLength": 40,
        "TabViewManagerFilenameOnly": True,
        "ShowFilePreview": True,
        "ShowFilePreviewSSI": True,
        "ShowTemplateViewer": True,  # left side
        "ShowFileBrowser": True,  # left side
        "ShowSymbolsViewer": True,  # left side
        "ShowFindFileWidget": True,  # left side
        "ShowFindLocationWidget": True,  # left side
        "ShowCodeDocumentationViewer": True,  # right side
        "ShowPyPIPackageManager": True,  # right side
        "ShowCondaPackageManager": True,  # right side
        "ShowCooperation": True,  # right side
        "ShowIrc": True,  # right side
        "ShowMicroPython": True,  # right side
        "ShowInternalHelpViewer": True,  # right side
        "ShowNumbersViewer": True,  # bottom side
        "ViewProfiles": {
            "edit": [
                # saved state main window with toolbox windows (0)
                QByteArray(),
                # visibility of the toolboxes/sidebars (1)
                # left, bottom, right
                [True, True, True],
                # saved states of the splitters and sidebars of the
                # sidebars layout (2)
                # horizontal splitter, vertical splitter,
                # left sidebar, bottom sidebar, right sidebar
                [QByteArray(), QByteArray(), "", "", ""],
            ],
            "debug": [
                # saved state main window with toolbox windows (0)
                QByteArray(),
                # visibility of the toolboxes/sidebars (1)
                # left, bottom, right
                [False, True, True],
                # saved states of the splitters and sidebars of the
                # sidebars layout (2)
                # horizontal splitter, vertical splitter,
                # left sidebar, bottom sidebar, right sidebar
                [QByteArray(), QByteArray(), "", "", ""],
            ],
        },
        "ToolbarManagerState": QByteArray(),
        "PreviewSplitterState": QByteArray(),
        "ShowSplash": True,
        "SplitOrientationVertical": False,
        "UseNativeMenuBar": True,
        "PerformVersionCheck": 3,
        # 0 = off
        # 1 = at startup
        # 2 = daily
        # 3 = weekly
        # 4 = monthly
        "DynamicOnlineCheck": True,
        "PluginRepositoryUrl7": (
            "https://eric-ide.python-projects.org/plugins7/repository.xml"
        ),
        "OpenOnStartup": 0,  # 0 = nothing
        # 1 = last file
        # 2 = last project
        # 3 = last multiproject
        # 4 = last global session
        "OpenCrashSessionOnStartup": True,
        "CrashSessionEnabled": True,
        "DeleteLoadedCrashSession": True,
        "UpgraderDelay": 5,
        "DownloadPath": "",
        "RequestDownloadFilename": True,
        "CheckErrorLog": True,
        "MinimumMessageTypeSeverity": QtMsgType.QtCriticalMsg.value,
        # 0 = QtMsgType.QtDebugMsg
        # 1 = QtMsgType.QtWarningMsg
        # 2 = QtMsgType.QtCriticalMsg
        # 3 = QtMsgType.QtFatalMsg
        "LogStdErrColour": QColor(Qt.GlobalColor.red),
        "NotificationTimeout": 5,  # time in seconds the notification
        # is shown
        "NotificationPosition": QPoint(10, 10),
        "NotificationWarningForeground": "#606000",
        "NotificationWarningBackground": "#ffffd0",
        "NotificationCriticalForeground": "#600000",
        "NotificationCriticalBackground": "#ffd0d0",
        "LoadUnknownMimeTypeFiles": False,
        "TextMimeTypes": [
            "application/atom+xml",
            "application/bookmarks.xbel",
            "application/javascript",
            "application/json",
            "application/opensearchdescription+xml",
            "application/postscript",
            "application/rss+xml",
            "application/sql",
            "application/x-actionscript",
            "application/x-actionscript3",
            "application/x-awk",
            "application/x-befunge",
            "application/x-brainfuck",
            "application/x-cheetah",
            "application/x-clojure",
            "application/x-coldfusion",
            "application/x-csh",
            "application/x-cython",
            "application/x-desktop",
            "application/x-django-templating",
            "application/x-dos-batch",
            "application/x-ecl",
            "application/x-evoque",
            "application/x-fantom",
            "application/x-genshi",
            "application/x-genshi-text",
            "application/x-gettext",
            "application/x-gooddata-maql",
            "application/x-groovy",
            "application/x-httpd-lasso",
            "application/x-httpd-lasso[89]",
            "application/x-httpd-lasso8",
            "application/x-httpd-lasso9",
            "application/x-httpd-php",
            "application/x-httpd-php3",
            "application/x-httpd-php4",
            "application/x-httpd-php5",
            "application/x-hybris",
            "application/x-javascript+cheetah",
            "application/x-javascript+spitfire",
            "application/x-javascript+django",
            "application/x-javascript+jinja",
            "application/x-javascript+ruby",
            "application/x-javascript+genshi",
            "application/x-javascript",
            "application/x-javascript+php",
            "application/x-javascript+smarty",
            "application/x-javascript+lasso",
            "application/x-javascript+mako",
            "application/x-javascript+myghty",
            "application/x-jinja",
            "application/x-jsp",
            "application/x-julia",
            "application/x-kid",
            "application/x-latex",
            "application/x-lua",
            "application/x-mako",
            "application/x-mason",
            "application/x-moonscript",
            "application/x-myghty",
            "application/x-newlisp",
            "application/x-openedge",
            "application/x-perl",
            "application/x-php",
            "application/x-pygments-tokens",
            "application/x-pypylog",
            "application/x-python",
            "application/x-python3",
            "application/x-qml",
            "application/x-racket",
            "application/x-ruby",
            "application/x-ruby-templating",
            "application/x-scheme",
            "application/x-sh",
            "application/x-sh-session",
            "application/x-shell-session",
            "application/x-shellscript",
            "application/x-smarty",
            "application/x-spitfire",
            "application/x-ssp",
            "application/x-standardml",
            "application/x-tcl",
            "application/x-tex",
            "application/x-texinfo",
            "application/x-troff",
            "application/x-troff-man",
            "application/x-troff-me",
            "application/x-troff-ms",
            "application/x-urbiscript",
            "application/x-xbel",
            "application/xhtml+xml",
            "application/xml",
            "application/xml+cheetah",
            "application/xml+django",
            "application/xml+evoque",
            "application/xml+jinja",
            "application/xml+lasso",
            "application/xml+mako",
            "application/xml+myghty",
            "application/xml+php",
            "application/xml+ruby",
            "application/xml+smarty",
            "application/xml+spitfire",
            "application/xml+velocity",
            "application/xml-dtd",
            "application/xquery",
            "application/xsl+xml",
            "application/xslt+xml",
            "image/svg+xml",
            "message/rfc822",
        ],
        "TextFilePatterns": [
            "*.api",
            "*.aux",
            "*.bas",
            "*.bat",
            "*.c",
            "*.cc",
            "*.cfg",
            "*.cmake",
            "*.cmd",
            "*.cnf",
            "*.coffee",
            "*.cpp",
            "*.cs",
            "*.ctest",
            "*.cxx",
            "*.d",
            "*.dat",
            "*.desktop",
            "*.dfm",
            "*.di",
            "*.dic",
            "*.diff",
            "*.docbook",
            "*.dpk",
            "*.dpr",
            "*.dtd",
            "*.e[456]?",
            "*.ecj",
            "*.edj",
            "*.egj",
            "*.ehj",
            "*.ekj",
            "*.emj",
            "*.epj",
            "*.eqj",
            "*.esj",
            "*.ethj",
            "*.etj",
            "*.f2k",
            "*.f90",
            "*.f95",
            "*.gitblame_skiplist",
            "*.gitignore",
            "*.h",
            "*.hgannotate_skiplist",
            "*.hgignore",
            "*.hh",
            "*.hpp",
            "*.idl",
            "*.idx",
            "*.in",
            "*.inc",
            "*.inf",
            "*.ini",
            "*.java",
            "*.js",
            "*.json",
            "*.lua",
            "*.m",
            "*.m.matlab",
            "*.m.octave",
            "*.mak",
            "*.md",
            "*.pas",
            "*.patch",
            "*.ph",
            "*.php",
            "*.php3",
            "*.php4",
            "*.php5",
            "*.phtml",
            "*.pl",
            "*.pm",
            "*.po",
            "*.pov",
            "*.pp",
            "*.properties",
            "*.proto",
            "*.ps",
            "*.ptl",
            "*.pxd",
            "*.pxi",
            "*.py3",
            "*.pyi",
            "*.pyw",
            "*.pyw3",
            "*.pyx",
            "*.qrc",
            "*.qss",
            "*.rb",
            "*.rc",
            "*.reg",
            "*.rst",
            "*.sh",
            "*.sql",
            "*.sty",
            "*.svg",
            "*.tcl",
            "*.tex",
            "*.tk",
            "*.tmpl",
            "*.toc",
            "*.toml",
            "*.ts",
            "*.ui",
            "*.vhd",
            "*.vhdl",
            "*.xbel",
            "*.xml",
            "*.xsd",
            "*.xsl",
            "*.xslt",
            "*.xul",
            "*.yaml",
            "*.yml",
            "*CMakeLists.txt",
            "*Makefile",
            "*PKGLIST",
            "*Pipfile",
            "*makefile",
            "*poetry.lock",
            "*.groovy",
            "*Jenkinsfile",
            "*.jenkinsfile",
            "Jenkinsfile.*",
        ],
        "TextMimeTypesAskUser": False,
    }

    iconsDefaults = {
        "Path": [],
        "DefaultIconsPath": "automatic",
        # automatic, breeze-dark, breeze-light
        "IconSize": "",  # determined by the used style
        "PreferVectorIcons": True,
    }

    # defaults for the cooperation settings
    cooperationDefaults = {
        "ServerPort": 42000,
        "AutoStartServer": False,
        "TryOtherPorts": True,
        "MaxPortsToTry": 100,
        "AutoAcceptConnections": False,
        "BannedUsers": [],
    }

    # defaults for the editor settings
    editorDefaults = {
        "AutosaveIntervalSeconds": 0,
        "AutosaveOnFocusLost": False,
        "TabWidth": 4,
        "IndentWidth": 4,
        "TabIndentOverride": "{}",  # JSON formatted dictionary
        "IndentationGuides": True,
        "LinenoMargin": True,
        "FoldingMargin": True,
        "FoldingStyle": QsciScintilla.FoldStyle.PlainFoldStyle.value,
        "TabForIndentation": False,
        "TabIndents": True,
        "ConvertTabsOnLoad": False,
        "AutomaticEOLConversion": True,
        "ShowWhitespace": False,
        "WhitespaceSize": 1,
        "ShowEOL": False,
        "UseMonospacedFont": False,
        "WrapLongLinesMode": QsciScintilla.WrapMode.WrapNone,
        "WrapVisualFlag": QsciScintilla.WrapVisualFlag.WrapFlagNone,
        "WrapIndentMode": QsciScintilla.WrapIndentMode.WrapIndentFixed,
        "WrapStartIndent": 0,
        "WarnFilesize": 1024,
        "RejectFilesize": 4096,
        "ClearBreaksOnClose": True,
        "StripTrailingWhitespace": False,
        "InsertFinalNewline": True,
        "CommentColumn0": True,
        "OverrideEditAreaColours": False,
        "EdgeMode": QsciScintilla.EdgeMode.EdgeNone,
        "EdgeColumn": 88,
        "AutoIndentation": True,
        "BraceHighlighting": True,
        "CreateBackupFile": False,
        "CaretLineVisible": False,
        "CaretLineAlwaysVisible": False,
        "CaretWidth": 1,
        "CaretLineFrameWidth": 0,
        "ColourizeSelText": False,
        "CustomSelectionColours": False,
        "ExtendSelectionToEol": False,
        "RectangularSelectionModifier": Qt.KeyboardModifier.ControlModifier,
        "LineMarkersBackground": True,
        "AutoPrepareAPIs": False,
        "AutoCompletionEnabled": True,
        "AutoCompletionCaseSensitivity": True,
        "AutoCompletionReplaceWord": False,
        "AutoCompletionShowSingle": False,
        "AutoCompletionSource": QsciScintilla.AutoCompletionSource.AcsDocument,
        "AutoCompletionThreshold": 2,
        # timeout in ms before auto-completion is started
        "AutoCompletionTimeout": 200,
        "AutoCompletionFillups": False,
        # show QScintilla completions, if plug-in fails
        "AutoCompletionScintillaOnFail": False,
        "AutoCompletionReversedList": False,
        "AutoCompletionCacheEnabled": False,
        "AutoCompletionCacheSize": 100,
        "AutoCompletionCacheTime": 300,  # 5 minutes
        "AutoCompletionWatchdogTime": 3000,  # ms
        "AutoCompletionMaxLines": 20,
        "AutoCompletionMaxChars": 80,
        "CallTipsEnabled": True,
        "CallTipsVisible": 20,
        "CallTipsStyle": QsciScintilla.CallTipsStyle.CallTipsNoContext,
        "CallTipsPosition": QsciScintilla.CallTipsPosition.CallTipsBelowText,
        # show QScintilla calltips, if plug-in fails
        "CallTipsScintillaOnFail": False,
        "OnlineSyntaxCheck": True,
        "OnlineSyntaxCheckInterval": 5,
        "OnlineChangeTrace": True,
        "OnlineChangeTraceInterval": 500,  # 500 milliseconds
        "MouseHoverHelp": False,
        "MouseHoverTimeout": 500,  # 500 milliseconds
        "AutoReopen": True,
        "AnnotationsEnabled": True,
        "MiniContextMenu": False,
        "HideFormatButtons": True,
        "QuickSearchEnabled": False,
        "SearchMarkersEnabled": True,
        "QuickSearchMarkersEnabled": True,
        "QuickSearchMarkOccurrencesTimeout": 500,  # 500 milliseconds
        "MarkOccurrencesEnabled": True,
        "MarkOccurrencesTimeout": 500,  # 500 milliseconds
        "SearchRegexpMode": 0,  # 0: POSIX mode, 1: CXX11 mode
        "AdvancedEncodingDetection": True,
        "SpellCheckingEnabled": True,
        "AutoSpellCheckingEnabled": True,
        "AutoSpellCheckChunkSize": 30,
        "SpellCheckStringsOnly": True,
        "SpellCheckingMinWordSize": 3,
        "SpellCheckingDefaultLanguage": "en_US",
        "SpellCheckingPersonalWordList": "",
        "SpellCheckingPersonalExcludeList": "",
        "FullSpellCheckExtensions": ["md", "markdown", "rst", "txt"],
        "FullSpellCheckUnknown": False,
        "DefaultEncoding": "utf-8",
        "DefaultOpenFilter": QCoreApplication.translate(
            "Lexers", "Python Files (*.py *.py3)"
        ),
        "DefaultSaveFilter": QCoreApplication.translate(
            "Lexers", "Python3 Files (*.py)"
        ),
        "AdditionalOpenFilters": [],
        "AdditionalSaveFilters": [],
        "ZoomFactor": 0,
        "PreviewRefreshWaitTimer": 500,  # wait time in milliseconds
        "PreviewHtmlFileNameExtensions": ["html", "htm", "svg", "asp", "kid"],
        "PreviewMarkdownFileNameExtensions": ["md", "markdown"],
        "PreviewRestFileNameExtensions": ["rst"],
        "PreviewQssFileNameExtensions": ["qss"],
        "PreviewRestUseSphinx": False,
        "PreviewMarkdownNLtoBR": False,
        "PreviewMarkdownUsePyMdownExtensions": True,
        "PreviewMarkdownMathJax": True,
        "PreviewMarkdownMermaid": True,
        "PreviewMarkdownHTMLFormat": "HTML5",  # XHTML1, HTML4, HTML5
        "PreviewRestDocutilsHTMLFormat": "HTML5",  # HTML4, HTML5
        "VirtualSpaceOptions": QsciScintilla.SCVS_NONE,
        "MouseClickHandlersEnabled": True,
        "ShowMarkerMapOnRight": True,
        "ShowMarkerChanges": True,
        "ShowMarkerCoverage": True,
        "ShowMarkerSearch": True,
        "ShowSourceNavigator": True,
        "ShowSourceOutline": True,
        "SourceOutlineWidth": 200,
        "SourceOutlineShowCoding": True,
        "SourceOutlineListContentsByOccurrence": False,
        "DocstringType": "ericdoc",
        "DocstringAutoGenerate": True,
        "PrintColorMode": QsciScintillaPrintColorMode.Normal,
        # All (most) lexers
        "AllFoldCompact": True,
        # Bash specifics
        "BashFoldComment": True,
        # CMake specifics
        "CMakeFoldAtElse": False,
        # C++ specifics
        "CppCaseInsensitiveKeywords": False,
        "CppFoldComment": True,
        "CppFoldPreprocessor": False,
        "CppFoldAtElse": False,
        "CppIndentOpeningBrace": False,
        "CppIndentClosingBrace": False,
        "CppDollarsAllowed": True,
        "CppStylePreprocessor": False,
        "CppHighlightTripleQuotedStrings": False,
        "CppHighlightHashQuotedStrings": False,
        "CppHighlightBackQuotedStrings": False,
        "CppHighlightEscapeSequences": False,
        "CppVerbatimStringEscapeSequencesAllowed": False,
        # CoffeeScript specifics
        "CoffeScriptFoldComment": False,
        "CoffeeScriptDollarsAllowed": True,
        "CoffeeScriptStylePreprocessor": False,
        # CSS specifics
        "CssFoldComment": True,
        "CssHssSupport": False,
        "CssLessSupport": False,
        "CssSassySupport": False,
        # D specifics
        "DFoldComment": True,
        "DFoldAtElse": False,
        "DIndentOpeningBrace": False,
        "DIndentClosingBrace": False,
        # Gettext specifics
        "PoFoldComment": False,
        # HTML specifics
        "HtmlFoldPreprocessor": False,
        "HtmlFoldScriptComments": False,
        "HtmlFoldScriptHeredocs": False,
        "HtmlCaseSensitiveTags": False,
        "HtmlDjangoTemplates": False,
        "HtmlMakoTemplates": False,
        # JSON specifics
        "JSONHightlightComments": True,
        "JSONHighlightEscapeSequences": True,
        # Pascal specifics
        "PascalFoldComment": True,
        "PascalFoldPreprocessor": False,
        "PascalSmartHighlighting": True,
        # Perl specifics
        "PerlFoldComment": True,
        "PerlFoldPackages": True,
        "PerlFoldPODBlocks": True,
        "PerlFoldAtElse": False,
        # PostScript specifics
        "PostScriptTokenize": False,
        "PostScriptLevel": 3,
        "PostScriptFoldAtElse": False,
        # Povray specifics
        "PovFoldComment": True,
        "PovFoldDirectives": False,
        # Properties specifics
        "PropertiesInitialSpaces": True,
        # Python specifics
        "PythonBadIndentation": (QsciLexerPython.IndentationWarning.Inconsistent),
        "PythonFoldComment": True,
        "PythonFoldString": True,
        "PythonAutoIndent": True,
        "PythonAllowV2Unicode": True,
        "PythonAllowV3Binary": True,
        "PythonAllowV3Bytes": True,
        "PythonFoldQuotes": False,
        "PythonStringsOverNewLineAllowed": False,
        "PythonHighlightSubidentifier": True,
        # Ruby specifics
        "RubyFoldComment": False,
        # SQL specifics
        "SqlFoldComment": True,
        "SqlBackslashEscapes": False,
        "SqlDottedWords": False,
        "SqlFoldAtElse": False,
        "SqlFoldOnlyBegin": False,
        "SqlHashComments": False,
        "SqlQuotedIdentifiers": False,
        # TCL specifics
        "TclFoldComment": False,
        # TeX specifics
        "TexFoldComment": False,
        "TexProcessComments": False,
        "TexProcessIf": True,
        # VHDL specifics
        "VHDLFoldComment": True,
        "VHDLFoldAtElse": True,
        "VHDLFoldAtBegin": True,
        "VHDLFoldAtParenthesis": True,
        # XML specifics
        "XMLStyleScripts": True,
        # YAML specifics
        "YAMLFoldComment": False,
    }

    if OSUtilities.isWindowsPlatform():
        editorDefaults["EOLMode"] = QsciScintilla.EolMode.EolWindows
    else:
        editorDefaults["EOLMode"] = QsciScintilla.EolMode.EolUnix

    editorColourDefaults = {
        "CurrentMarker": QColor(Qt.GlobalColor.yellow),
        "ErrorMarker": QColor(Qt.GlobalColor.red),
        "MatchingBrace": QColor(Qt.GlobalColor.green),
        "MatchingBraceBack": QColor(Qt.GlobalColor.white),
        "NonmatchingBrace": QColor(Qt.GlobalColor.red),
        "NonmatchingBraceBack": QColor(Qt.GlobalColor.white),
        "CallTipsBackground": QColor(Qt.GlobalColor.white),
        "CallTipsForeground": QColor("#7f7f7f"),
        "CallTipsHighlight": QColor("#00007f"),
        "CaretForeground": QColor(Qt.GlobalColor.black),
        "CaretLineBackground": QColor(Qt.GlobalColor.white),
        "Edge": QColor(Qt.GlobalColor.lightGray),
        "SelectionBackground": QColor(Qt.GlobalColor.black),
        "SelectionForeground": QColor(Qt.GlobalColor.white),
        "SearchMarkers": QColor(Qt.GlobalColor.blue),
        "MarginsBackground": QColor(Qt.GlobalColor.lightGray),
        "MarginsForeground": QColor(Qt.GlobalColor.black),
        "FoldmarginBackground": QColor("#e6e6e6"),
        "FoldMarkersForeground": QColor(Qt.GlobalColor.white),
        "FoldMarkersBackground": QColor(Qt.GlobalColor.black),
        "SpellingMarkers": QColor(Qt.GlobalColor.red),
        "AnnotationsWarningForeground": QColor("#606000"),
        "AnnotationsWarningBackground": QColor("#ffffd0"),
        "AnnotationsErrorForeground": QColor("#600000"),
        "AnnotationsErrorBackground": QColor("#ffd0d0"),
        "AnnotationsStyleForeground": QColor("#000060"),
        "AnnotationsStyleBackground": QColor("#d0d0ff"),
        "AnnotationsInfoForeground": QColor("#006000"),
        "AnnotationsInfoBackground": QColor("#d0ffd0"),
        "WhitespaceForeground": QColor(Qt.GlobalColor.darkGray),
        "WhitespaceBackground": QColor(Qt.GlobalColor.white),
        "OnlineChangeTraceMarkerUnsaved": QColor("#ff8888"),
        "OnlineChangeTraceMarkerSaved": QColor("#88ff88"),
        "IndentationGuidesBackground": QColor(Qt.GlobalColor.white),
        "IndentationGuidesForeground": QColor(Qt.GlobalColor.black),
        "HighlightMarker": QColor("#300000FF"),  # ARGB format
        "SearchSelectionMarker": QColor("#30bbff00"),  # ARGB format
        # colors for the marker map
        "BookmarksMap": QColor("#f8c700"),
        "ErrorsMap": QColor("#dd0000"),
        "WarningsMap": QColor("#606000"),
        "BreakpointsMap": QColor("#f55c07"),
        "TasksMap": QColor("#2278f8"),
        "CoverageMap": QColor("#ad3636"),
        "ChangesMap": QColor("#00b000"),
        "CurrentMap": QColor("#000000"),
        "SearchMarkersMap": QColor(Qt.GlobalColor.blue),
        "VcsConflictMarkersMap": QColor("#dd00dd"),
        "MarkerMapBackground": QColor("#e7e7e7"),
    }

    editorOtherFontsDefaults = {
        "MarginsFont": "Sans Serif,10,-1,5,50,0,0,0,0,0",
        "DefaultFont": "Sans Serif,10,-1,5,50,0,0,0,0,0",
        "MonospacedFont": "Courier,10,-1,5,50,0,0,0,0,0",
    }

    editorTypingDefaults = {
        # Python
        "Python/EnabledTypingAids": True,
        "Python/InsertClosingBrace": True,
        "Python/IndentBrace": False,
        "Python/SkipBrace": True,
        "Python/InsertQuote": True,
        "Python/DedentElse": True,
        "Python/DedentExcept": True,
        "Python/InsertImport": True,
        "Python/ImportBraceType": False,
        "Python/InsertSelf": True,
        "Python/InsertBlank": True,
        "Python/ColonDetection": True,
        "Python/DedentDef": False,
        # Ruby
        "Ruby/EnabledTypingAids": True,
        "Ruby/InsertClosingBrace": True,
        "Ruby/IndentBrace": True,
        "Ruby/SkipBrace": True,
        "Ruby/InsertQuote": True,
        "Ruby/InsertBlank": True,
        "Ruby/InsertHereDoc": True,
        "Ruby/InsertInlineDoc": True,
        # TOML
        "Toml/EnabledTypingAids": True,
        "Toml/InsertClosingBrace": True,
        "Toml/SkipBrace": True,
        "Toml/InsertQuote": True,
        "Toml/AutoIndentation": True,
        "Toml/ColonDetection": True,
        "Toml/InsertBlankEqual": True,
        "Toml/InsertBlankColon": True,
        "Toml/InsertBlankComma": True,
        # YAML
        "Yaml/EnabledTypingAids": True,
        "Yaml/InsertClosingBrace": True,
        "Yaml/SkipBrace": True,
        "Yaml/InsertQuote": True,
        "Yaml/AutoIndentation": True,
        "Yaml/ColonDetection": True,
        "Yaml/InsertBlankDash": True,
        "Yaml/InsertBlankColon": True,
        "Yaml/InsertBlankQuestion": True,
        "Yaml/InsertBlankComma": True,
    }

    editorExporterDefaults = {
        "HTML/WYSIWYG": True,
        "HTML/Folding": False,
        "HTML/OnlyStylesUsed": False,
        "HTML/FullPathAsTitle": False,
        "HTML/UseTabs": False,
        "RTF/WYSIWYG": True,
        "RTF/UseTabs": False,
        "RTF/Font": "Courier New,10,-1,5,50,0,0,0,0,0",
        "PDF/Magnification": 0,
        "PDF/Font": "Helvetica",  # must be Courier, Helvetica or Times
        "PDF/PageSize": "A4",  # must be A4 or Letter
        "PDF/MarginLeft": 36,
        "PDF/MarginRight": 36,
        "PDF/MarginTop": 36,
        "PDF/MarginBottom": 36,
        "TeX/OnlyStylesUsed": False,
        "TeX/FullPathAsTitle": False,
        "ODT/WYSIWYG": True,
        "ODT/OnlyStylesUsed": False,
        "ODT/UseTabs": False,
    }

    # defaults for the printer settings
    printerDefaults = {
        "PrinterName": "",
        "ColorMode": True,
        "FirstPageFirst": True,
        "Magnification": -3,
        "Orientation": 0,
        "PageSize": 0,
        "HeaderFont": "Serif,10,-1,5,50,0,0,0,0,0",
        "LeftMargin": 1.0,
        "RightMargin": 1.0,
        "TopMargin": 1.0,
        "BottomMargin": 1.0,
        "Resolution": 150,  # printer resolution in DPI
    }

    # defaults for the project settings
    projectDefaults = {
        "SearchNewFiles": True,
        "SearchNewFilesRecursively": True,
        "AutoIncludeNewFiles": False,
        "AutoLoadSession": False,
        "AutoSaveSession": False,
        "SessionAllBreakpoints": False,
        "TimestampFile": True,
        "AutoCompileForms": True,
        "AutoCompileResources": False,
        "AutoExecuteMake": False,
        "AutoLoadDbgProperties": True,
        "AutoSaveDbgProperties": True,
        "FollowEditor": True,
        "FollowCursorLine": True,
        "AutoPopulateItems": True,
        "RecentNumber": 9,
        "DeterminePyFromProject": True,
        "TasksProjectAutoSave": True,
        "TasksProjectRescanOnOpen": True,
        "DebugClientsHistory": [],
        "DebuggerInterpreterHistory": [],
        "RestartShellForProject": True,
        "BrowsersListHiddenFiles": False,
        "AutoSaveProject": False,
    }

    # defaults for the multi project settings
    multiProjectDefaults = {
        "OpenMainAutomatically": True,
        "TimestampFile": True,
        "RecentNumber": 9,
        "Workspace": "",
    }

    # defaults for the project browser lists settings
    projectBrowsersDefaults = {
        "allBrowsers": (
            "sources",
            "forms",
            "resources",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
        "PyQt5": (
            "sources",
            "forms",
            "resources",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
        "PyQt5C": (
            "sources",
            "resources",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
        "PyQt6": (
            "sources",
            "forms",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
        "PyQt6C": (
            "sources",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
        "E7Plugin": (
            "sources",
            "forms",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
        "Console": (
            "sources",
            "others",
            "interfaces",
            "protocols",
        ),
        "Other": (
            "sources",
            "others",
            "interfaces",
            "protocols",
        ),
        "PySide2": (
            "sources",
            "forms",
            "resources",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
        "PySide2C": (
            "sources",
            "resources",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
        "PySide6": (
            "sources",
            "forms",
            "resources",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
        "PySide6C": (
            "sources",
            "resources",
            "translations",
            "others",
            "interfaces",
            "protocols",
        ),
    }

    # defaults for the project browser colour settings
    projectBrowserColourDefaults = {
        "Highlighted": QColor(Qt.GlobalColor.red),
        "VcsAdded": QColor(Qt.GlobalColor.blue),
        "VcsConflict": QColor(Qt.GlobalColor.red),
        "VcsModified": QColor(Qt.GlobalColor.yellow),
        "VcsReplaced": QColor(Qt.GlobalColor.cyan),
        "VcsUpdate": QColor(Qt.GlobalColor.green),
        "VcsRemoved": QColor(Qt.GlobalColor.magenta),
    }

    # defaults for the help settings
    helpDefaults = {
        "CustomViewer": "",
        "PythonDocDir": "",
        "Qt5DocDir": "",
        "Qt6DocDir": "",
        "PyQt5DocDir": "https://www.riverbankcomputing.com/static/Docs/PyQt5/",
        "PyQt6DocDir": "https://www.riverbankcomputing.com/static/Docs/PyQt6/",
        "PySide2DocDir": "",
        "PySide6DocDir": "",
        "EricDocDir": "",
        "HelpViewerType": 0,  # internal help viewer
        # 0     internal help viewer
        # 1     eric web browser
        # 2     Qt Assistant
        # 3     system web browser
        # 4     custom
        "ForceQTextBrowser": False,
        "Bookmarks": "[]",  # empty JSON list
        "QtHelpSearchNewOnStart": True,
    }

    # defaults for the web browser settings
    webBrowserDefaults = {
        "SingleWebBrowserWindow": True,
        "ShowToolbars": False,
        "BookmarksToolBarVisible": True,
        "MenuBarVisible": False,
        "StatusBarVisible": True,
        "SaveGeometry": True,
        "WebBrowserState": QByteArray(),
        "StartupBehavior": 2,  # show speed dial
        # 0     open empty page
        # 1     open home page
        # 2     open speed dial
        # 3     restore last session
        # 4     ask user for session
        "NewTabBehavior": 2,  # show speed dial
        # 0     open empty page
        # 1     open home page
        # 2     open speed dial
        "HomePage": "eric:home",
        "LoadTabOnActivation": True,
        "WarnOnMultipleClose": True,
        "DefaultScheme": "https://",
        "UserStyleSheet": "",
        "ZoomValuesDB": "{}",  # empty JSON dictionary
        "HistoryLimit": 30,
        "WebSearchSuggestions": True,
        "WebSearchEngine": "DuckDuckGo",
        "WebSearchKeywords": [],  # array of two tuples (keyword,
        # search engine name)
        "SearchLanguage": QLocale().language(),
        "ImageSearchEngine": "Google",
        "RssFeeds": [],
        "ShowPreview": True,
        "DiskCacheEnabled": True,
        "DiskCacheSize": 50,  # 50 MB
        "SslExceptionsDB": "{}",  # empty JSON dictionary
        "AlwaysRejectFaultyCertificates": False,
        "DoNotTrack": False,
        "RefererSendReferer": 0,  # never send a referrer
        "RefererDefaultPolicy": 3,  # don't send a referrer when downgrading
        "RefererTrimmingPolicy": 0,  # send full URL (no trimming)
        "SendRefererWhitelist": ["qt-apps.org", "kde-apps.org"],
        "AcceptCookies": 2,  # CookieAcceptPolicy.OnlyFromSitesNavigatedTo
        "KeepCookiesUntil": 0,  # CookieKeepPolicy.UntilExpire
        "FilterTrackingCookies": True,
        "SecureUrlColor": QColor(184, 248, 169),
        "InsecureUrlColor": QColor(248, 227, 169),
        "MaliciousUrlColor": QColor(255, 132, 140),
        "PrivateModeUrlColor": QColor(220, 220, 220),
        "UserAgent": "",
        "AcceptQuotaRequest": 2,  # yes/no/ask (0, 1, 2)
        "AcceptProtocolHandlerRequest": 2,  # yes/no/ask (0, 1, 2)
        "AcceptFileSystemAccessRequest": 2,  # yes/no/ask (0, 1, 2)
        # Auto Scroller
        "AutoScrollEnabled": True,
        "AutoScrollDivider": 8.0,
        # Tab Manager
        "TabManagerGroupByType": 0,  # TabGroupByType.GroupByWindow
        # Grease Monkey
        "GreaseMonkeyDisabledScripts": [],
        # Downloads
        "DownloadManagerRemovePolicy": 0,  # never delete downloads
        "DownloadManagerSize": QSize(450, 600),
        "DownloadManagerPosition": QPoint(),
        "DownloadManagerDownloads": [],
        "DownloadManagerAutoOpen": False,
        "DownloadManagerAutoClose": False,
        # Spell Checking
        "SpellCheckEnabled": False,
        "SpellCheckLanguages": [],
        "SpellCheckDictionariesUrl": (
            "https://eric-ide.python-projects.org/qwebengine_dictionaries/"
            "dictionaries.xml"
        ),
        "ForceHttpDictionaryDownload": False,
        # Sync
        "SyncEnabled": False,
        "SyncBookmarks": True,
        "SyncHistory": True,
        "SyncPasswords": False,
        "SyncUserAgents": True,
        "SyncSpeedDial": True,
        "SyncEncryptData": False,
        "SyncEncryptionKey": "",
        "SyncEncryptionKeyLength": 32,  # 16, 24 or 32
        "SyncEncryptPasswordsOnly": False,
        "SyncType": 0,
        "SyncFtpServer": "",
        "SyncFtpUser": "",
        "SyncFtpPassword": "",
        "SyncFtpPath": "",
        "SyncFtpPort": 21,
        "SyncFtpIdleTimeout": 30,
        "SyncDirectoryPath": "",
        # AdBlock
        "AdBlockEnabled": False,
        "AdBlockSubscriptions": [],
        "AdBlockUpdatePeriod": 1,
        "AdBlockExceptions": [],
        "AdBlockUseLimitedEasyList": True,
        # PIM:
        "PimFullName": "",
        "PimFirstName": "",
        "PimLastName": "",
        "PimEmail": "",
        "PimPhone": "",
        "PimMobile": "",
        "PimAddress": "",
        "PimCity": "",
        "PimZip": "",
        "PimState": "",
        "PimCountry": "",
        "PimHomePage": "",
        "PimSpecial1": "",
        "PimSpecial2": "",
        "PimSpecial3": "",
        "PimSpecial4": "",
        # VirusTotal:
        "VirusTotalEnabled": False,
        "VirusTotalServiceKey": "",
        "VirusTotalSecure": True,
        # Sessions
        "SessionAutoSave": True,
        "SessionAutoSaveInterval": 15,  # interval in seconds
        "SessionLastActivePath": "",
        # Google Safe Browsing
        "SafeBrowsingEnabled": True,
        "SafeBrowsingApiKey": "",  # API key
        "SafeBrowsingFilterPlatform": True,
        "SafeBrowsingAutoUpdate": False,
        "SafeBrowsingUpdateDateTime": QDateTime(),
        "SafeBrowsingUseLookupApi": False,
        # Push Messaging
        "PushServiceEnabled": False,
        # Persistent Permissions
        "NoPersistentPermissions": False,
    }

    @classmethod
    def initWebEngineSettingsDefaults(cls):
        """
        Class method to initialize the web engine settings related defaults.
        """
        if QWebEngineSettings is None:
            return

        webEngineSettings = QWebEngineProfile.defaultProfile().settings()
        cls.webBrowserDefaults.update(
            {
                # fonts
                "StandardFontFamily": webEngineSettings.fontFamily(
                    QWebEngineSettings.FontFamily.StandardFont
                ),
                "FixedFontFamily": webEngineSettings.fontFamily(
                    QWebEngineSettings.FontFamily.FixedFont
                ),
                "SerifFontFamily": webEngineSettings.fontFamily(
                    QWebEngineSettings.FontFamily.StandardFont
                ),
                "SansSerifFontFamily": webEngineSettings.fontFamily(
                    QWebEngineSettings.FontFamily.SansSerifFont
                ),
                "CursiveFontFamily": webEngineSettings.fontFamily(
                    QWebEngineSettings.FontFamily.CursiveFont
                ),
                "FantasyFontFamily": webEngineSettings.fontFamily(
                    QWebEngineSettings.FontFamily.FantasyFont
                ),
                # font sizes
                "DefaultFontSize": webEngineSettings.fontSize(
                    QWebEngineSettings.FontSize.DefaultFontSize
                ),
                "DefaultFixedFontSize": webEngineSettings.fontSize(
                    QWebEngineSettings.FontSize.DefaultFixedFontSize
                ),
                "MinimumFontSize": webEngineSettings.fontSize(
                    QWebEngineSettings.FontSize.MinimumFontSize
                ),
                "MinimumLogicalFontSize": webEngineSettings.fontSize(
                    QWebEngineSettings.FontSize.MinimumLogicalFontSize
                ),
                # text encoding
                "DefaultTextEncoding": webEngineSettings.defaultTextEncoding(),
                # web attributes
                "AutoLoadImages": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.AutoLoadImages
                ),
                "JavaScriptEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.JavascriptEnabled
                ),
                "JavaScriptCanOpenWindows": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows
                ),
                "JavaScriptCanAccessClipboard": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard
                ),
                "LinksIncludedInFocusChain": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.LinksIncludedInFocusChain
                ),
                "LocalStorageEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.LocalStorageEnabled
                ),
                "LocalContentCanAccessRemoteUrls": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls
                ),
                "XSSAuditingEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.XSSAuditingEnabled
                ),
                "SpatialNavigationEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.SpatialNavigationEnabled
                ),
                "LocalContentCanAccessFileUrls": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls
                ),
                "ScrollAnimatorEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled
                ),
                "ErrorPageEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.ErrorPageEnabled
                ),
                "PluginsEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.PluginsEnabled
                ),
                "FullScreenSupportEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.FullScreenSupportEnabled
                ),
                "ScreenCaptureEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.ScreenCaptureEnabled
                ),
                "WebGLEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.WebGLEnabled
                ),
                "Accelerated2dCanvasEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled
                ),
                "AutoLoadIconsForPage": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.AutoLoadIconsForPage
                ),
                "FocusOnNavigationEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled
                ),
                "PrintElementBackgrounds": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.PrintElementBackgrounds
                ),
                "AllowRunningInsecureContent": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.AllowRunningInsecureContent
                ),
                "AllowGeolocationOnInsecureOrigins": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.AllowGeolocationOnInsecureOrigins
                ),
                "AllowWindowActivationFromJavaScript": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript
                ),
                "ShowScrollBars": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.ShowScrollBars
                ),
                "PlaybackRequiresUserGesture": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture
                ),
                "JavaScriptCanPaste": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.JavascriptCanPaste
                ),
                "WebRTCPublicInterfacesOnly": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly
                ),
                "DnsPrefetchEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.DnsPrefetchEnabled
                ),
                "PdfViewerEnabled": webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.PdfViewerEnabled
                ),
            }
        )

        if QtUtilities.qVersionTuple() >= (6, 4, 0):
            # Qt 6.4+
            cls.webBrowserDefaults["NavigateOnDropEnabled"] = (
                webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.NavigateOnDropEnabled
                )
            )

        if QtUtilities.qVersionTuple() >= (6, 6, 0):
            # Qt 6.6+
            cls.webBrowserDefaults["ReadingFromCanvasEnabled"] = (
                webEngineSettings.testAttribute(
                    QWebEngineSettings.WebAttribute.ReadingFromCanvasEnabled
                )
            )

        if QtUtilities.qVersionTuple() >= (6, 7, 0):
            # Qt 6.7+
            cls.webBrowserDefaults["ForceDarkMode"] = webEngineSettings.testAttribute(
                QWebEngineSettings.WebAttribute.ForceDarkMode
            )

        cls.webEngineSettingsIntitialized = True

    webEngineSettingsIntitialized = False

    # defaults for system settings
    sysDefaults = {
        "StringEncoding": "utf-8",
        "IOEncoding": "utf-8",
    }

    # defaults for the shell settings
    shellDefaults = {
        "LinenoMargin": True,
        "AutoCompletionEnabled": True,
        "CallTipsEnabled": True,
        "WrapEnabled": True,
        "MaxHistoryEntries": 100,
        "HistoryStyle": ShellHistoryStyle.LINUXSTYLE,
        "HistoryWrap": False,
        "HistoryNavigateByCursor": False,
        "SyntaxHighlightingEnabled": True,
        "ShowStdOutErr": True,
        "UseMonospacedFont": False,
        "MonospacedFont": "Courier,10,-1,5,50,0,0,0,0,0",
        "MarginsFont": "Sans Serif,10,-1,5,50,0,0,0,0,0",
        "LastVirtualEnvironment": "",
        "StartWithMostRecentlyUsedEnvironment": True,
        "CommandExecutionTimeout": 15,
    }

    # defaults for Qt related stuff
    qtDefaults = {
        "Qt6TranslationsDir": "",
        "QtToolsDir": "",
        "QtToolsPrefix": "",
        "QtToolsPostfix": "",
        "Lrelease": "",
        "QHelpGenerator": "",
        "PyuicIndent": 4,
        "PyuicFromImports": False,
        "PyuicExecute": True,
        "PyQtVenvName": "",
        "PyQtToolsDir": "",
        "Pyuic6Indent": 4,
        "Pyuic6Execute": True,
        "PyQt6VenvName": "",
        "PyQt6ToolsDir": "",
        "PySide2FromImports": False,
        "PySide2VenvName": "",
        "PySide2ToolsDir": "",
        "PySide6FromImports": False,
        "PySide6VenvName": "",
        "PySide6ToolsDir": "",
    }

    # defaults for user related stuff
    userDefaults = {
        "Email": "",
        "MailServer": "",
        "Signature": "",
        "MailServerAuthentication": False,
        "MailServerUser": "",
        "MailServerPassword": "",
        "MailServerEncryption": "No",  # valid values: No, SSL, TLS
        "MailServerPort": 25,
        "UseSystemEmailClient": False,
        "UseGoogleMailOAuth2": False,
        "MainPassword": "",  # stores the password hash
        "UseMainPassword": False,
        "SavePasswords": False,
    }

    # defaults for vcs related stuff
    vcsDefaults = {
        "AutoClose": False,
        "AutoSaveFiles": True,
        "AutoSaveProject": True,
        "AutoUpdate": False,
        "StatusMonitorInterval": 30,
        "MonitorLocalStatus": False,
        "ShowVcsToolbar": True,
        "PerProjectCommitHistory": True,
        "CommitMessages": 20,
    }

    # defaults for tasks related stuff
    tasksDefaults = {
        "TasksFixmeMarkers": "FIXME:",  # __NO-TASK__
        "TasksWarningMarkers": "WARNING:",  # __NO-TASK__
        "TasksTodoMarkers": "TODO:",  # __NO-TASK__
        "TasksNoteMarkers": "NOTE:",  # __NO-TASK__
        "TasksTestMarkers": "TEST:",  # __NO-TASK__
        "TasksDocuMarkers": "DOCU:",  # __NO-TASK__
        # needed to keep it from being recognized as a task
        "TasksFixmeColor": QColor("#FFA0A0"),
        "TasksWarningColor": QColor("#FFFFA0"),
        "TasksTodoColor": QColor("#A0FFA0"),
        "TasksNoteColor": QColor("#A0A0FF"),
        "TasksTestColor": QColor("#FFD000"),
        "TasksDocuColor": QColor("#FFA0FF"),
        "ClearOnFileClose": True,
    }

    # defaults for templates related stuff
    templatesDefaults = {
        "AutoOpenGroups": True,
        "SingleDialog": False,
        "ShowTooltip": False,
        "SeparatorChar": "$",
        "EditorFont": "Monospace,9,-1,5,50,0,0,0,0,0",
    }

    # defaults for plugin manager related stuff
    pluginManagerDefaults = {
        "ActivateExternal": True,
        "DownloadPath": "",
        "UpdatesCheckInterval": 3,
        # 0 = off
        # 1 = daily
        # 2 = weekly
        # 3 = monthly
        # 4 = always
        "CheckInstalledOnly": True,
        # list of plug-ins not to be shown in the repo dialog
        "HiddenPlugins": [],
        # parameters for housekeeping
        "KeepGenerations": 2,
        "KeepHidden": False,
        "StartupCleanup": True,
        "AutoInstallDependencies": True,
        "ForceHttpPluginDownload": False,
    }

    # defaults for the printer settings
    graphicsDefaults = {
        "Font": "SansSerif,10,-1,5,50,0,0,0,0,0",
        "DrawingMode": "automatic",
        # automatic - determine mode depending upon desktop scheme
        # black_white - black items on white background
        # white_black - white items on black background
    }

    # defaults for the icon editor
    iconEditorDefaults = {
        "IconEditorState": QByteArray(),
    }

    # defaults for pyflakes
    pyflakesDefaults = {
        "IncludeInSyntaxCheck": True,
        "IgnoreStarImportWarnings": True,
        "AdditionalBuiltins": [],
    }

    # defaults for tray starter
    trayStarterDefaults = {
        "TrayStarterIcon": "erict",
        # valid values are: erict, erict-hc,
        #                   erict-bw, erict-bwi
    }

    # defaults for geometry
    geometryDefaults = {
        "MainGeometry": QByteArray(),
        "MainMaximized": False,
        "HexEditorGeometry": QByteArray(),
        "IconEditorGeometry": QByteArray(),
        "MPyWindowGeometry": QByteArray(),
        "PdfViewerGeometry": QByteArray(),
        "WebBrowserGeometry": QByteArray(),
        "WebInspectorGeometry": QByteArray(),
    }

    # if true, revert layouts to factory defaults
    resetLayout = False

    # defaults for IRC
    ircDefaults = {
        "ShowTimestamps": True,
        "TimestampIncludeDate": False,
        "TimeFormat": "hh:mm",
        "DateFormat": "yyyy-MM-dd",
        "NetworkMessageColour": "#000055",
        "ServerMessageColour": "#91640A",
        "ErrorMessageColour": "#FF0000",
        "TimestampColour": "#709070",
        "HyperlinkColour": "#0000FF",
        "ChannelMessageColour": "#000000",
        "OwnNickColour": "#000000",
        "NickColour": "#18B33C",
        "JoinChannelColour": "#72D672",
        "LeaveChannelColour": "#B00000",
        "ChannelInfoColour": "#9E54B3",
        "EnableIrcColours": True,
        "IrcColor0": "#FFFF00",
        "IrcColor1": "#000000",
        "IrcColor2": "#000080",
        "IrcColor3": "#008000",
        "IrcColor4": "#FF0000",
        "IrcColor5": "#A52A2A",
        "IrcColor6": "#800080",
        "IrcColor7": "#FF8000",
        "IrcColor8": "#808000",
        "IrcColor9": "#00FF00",
        "IrcColor10": "#008080",
        "IrcColor11": "#00FFFF",
        "IrcColor12": "#0000FF",
        "IrcColor13": "#FFC0CB",
        "IrcColor14": "#A0A0A0",
        "IrcColor15": "#C0C0C0",
        "ShowNotifications": True,
        "NotifyJoinPart": True,
        "NotifyMessage": False,
        "NotifyNick": False,
        "AutoUserInfoLookup": True,
        "AutoUserInfoMax": 200,
        "AutoUserInfoInterval": 90,
        "MarkPositionWhenHidden": True,
        "MarkerLineForegroundColour": "#000000",  # Black on
        "MarkerLineBackgroundColour": "#ffff00",  # Yellow
        "AskOnShutdown": True,
    }

    # defaults for Hex Editor
    hexEditorDefaults = {
        "HexEditorState": QByteArray(),
        "AddressAreaWidth": 4,
        "ShowAddressArea": True,
        "ShowAsciiArea": True,
        "OpenInOverwriteMode": True,
        "OpenReadOnly": False,
        "HighlightChanges": True,
        "RecentNumber": 9,
    }
    if OSUtilities.isWindowsPlatform():
        hexEditorDefaults["Font"] = "Courier,10,-1,5,50,0,0,0,0,0"
    else:
        hexEditorDefaults["Font"] = "Monospace,10,-1,5,50,0,0,0,0,0"

    # defaults for Diff colors
    diffColourDefaults = {
        "TextColor": QColor(0, 0, 0),
        "AddedColor": QColor(190, 237, 190),
        "RemovedColor": QColor(237, 190, 190),
        "ReplacedColor": QColor(190, 190, 237),
        "ContextColor": QColor(255, 220, 168),
        "HeaderColor": QColor(237, 237, 190),
        "BadWhitespaceColor": QColor(255, 0, 0, 192),
    }

    # defaults for Code Documentation Viewer
    docuViewerDefaults = {
        "Provider": "disabled",
        "ShowInfoOnOpenParenthesis": True,
    }

    # defaults for conda
    condaDefaults = {
        "CondaExecutable": "",
    }

    # defaults for pip
    pipDefaults = {
        "PipSearchIndex": "",  # used by the search command
        "ExcludeGlobalEnvironments": True,
        # don't show global environments in selector
        "ExcludeCondaEnvironments": True,
        # don't show conda environments in selector
        # defaults for the package vulnerability check
        "VulnerabilityDbMirror": (
            "https://raw.githubusercontent.com/pyupio/safety-db/master/data/"
        ),
        "VulnerabilityDbCacheValidity": 60 * 60 * 6,  # 6 hours
        "VulnerabilityCheckEnabled": True,
    }

    # defaults for MicroPython
    microPythonDefaults = {
        "MpyWorkspace": "",
        "SerialTimeout": 2000,  # timeout in milliseconds for serial connections
        "WebreplTimeout": 5000,  # timeout in milliseconds for webrepl connections
        "WebreplUrls": "{}",  # empty dict of WebREPL URLs as JSON
        "ReplLineWrap": True,  # wrap the REPL lines
        "SyncTimeAfterConnect": True,
        "ShowHiddenLocal": True,
        "ShowHiddenDevice": True,
        "EnableManualDeviceSelection": False,
        "MPyWindowSplitterSizes": "[]",  # empty list encoded as JSON
        "ChartColorTheme": -1,  # -1 = automatic,
        # QChart.ChartTheme otherwise
        "MpyCrossCompiler": "",  # path of the mpy-cross compiler
        "DfuUtilPath": "",  # path of the dfu-util flashing tool
        "StFlashPath": "",  # path of the st-flash flashing tool
        "StInfoPath": "",  # path of the st-info tool to get STLink info
        "IgnoredUnknownDevices": "[]",  # empty list encoded as JSON
        "ManualDevices": "[]",  # empty list encoded as JSON
        "WifiName": "",
        "WifiPassword": "",
        "WifiHostname": "",
        "WifiApName": "",
        "WifiApPassword": "",
        "WifiApAuthMode": 4,  # WPA/WPA2
        "WifiApHostname": "",
        "WifiApAddress": "",
        "WifiApNetmask": "",
        "WifiApGateway": "",
        "WifiApDNS": "",
        "WifiCountry": "",
        "NtpServer": "0.pool.ntp.org",
        "NtpOffset": 0,
        "NtpDaylight": False,
        "NtpTimeout": 10,
        # MicroPython URLs
        "MicroPythonDocuUrl": "https://docs.micropython.org/en/latest/",
        "MicroPythonFirmwareUrl": "http://micropython.org/download/",
        # CircuitPython URLS
        "CircuitPythonDocuUrl": "https://circuitpython.readthedocs.io/en/latest/",
        "CircuitPythonFirmwareUrl": "https://circuitpython.org/downloads/",
        "CircuitPythonLibrariesUrl": "https://circuitpython.org/libraries",
        # BBC micro:bit URLs
        "MicrobitDocuUrl": "https://microbit-micropython.readthedocs.io/en/latest/",
        "MicrobitFirmwareUrl": "https://microbit.org/guide/firmware/",
        "MicrobitMicroPythonUrl": (
            "https://github.com/bbcmicrobit/micropython/releases/"
        ),
        "MicrobitV2MicroPythonUrl": (
            "https://github.com/microbit-foundation/micropython-microbit-v2/releases/"
        ),
        # calliope mini URLS
        "CalliopeDocuUrl": (
            "https://github.com/calliope-mini/calliope-mini-micropython/"
        ),
        "CalliopeDAPLinkUrl": (
            "https://github.com/calliope-mini/production-test/releases/"
        ),
        "CalliopeMicroPythonUrl": (
            "https://github.com/calliope-mini/calliope-mini-micropython/"
        ),
    }
    if OSUtilities.isWindowsPlatform():
        microPythonDefaults["ColorScheme"] = "Windows 10"
    elif OSUtilities.isMacPlatform():
        microPythonDefaults["ColorScheme"] = "xterm"
    else:
        microPythonDefaults["ColorScheme"] = "Ubuntu"

    # defaults for Python specific settings
    pythonDefaults = {
        "ASTViewerErrorColor": QColor(Qt.GlobalColor.darkRed),
        "DisViewerErrorColor": QColor(Qt.GlobalColor.darkRed),
        "DisViewerCurrentColor": QColor(Qt.GlobalColor.darkMagenta),
        "DisViewerLabeledColor": QColor(Qt.GlobalColor.darkGreen),
        "DisViewerExpandCodeInfoDetails": False,
    }

    # defaults for the jedi interface
    jediDefaults = {
        "JediCompletionsEnabled": True,
        "JediFuzzyCompletionsEnabled": False,
        "JediCalltipsEnabled": True,
        "MouseClickEnabled": True,
        "MouseClickGotoButton": Qt.MouseButton.LeftButton,
    }
    if OSUtilities.isWindowsPlatform():
        jediDefaults["MouseClickGotoModifiers"] = (
            Qt.KeyboardModifier.MetaModifier | Qt.KeyboardModifier.ControlModifier
        )
    else:
        jediDefaults["MouseClickGotoModifiers"] = Qt.KeyboardModifier.ControlModifier

    # defaults for PDF viewer
    pdfViewerDefaults = {
        "PdfViewerState": QByteArray(),
        "PdfViewerSplitterState": QByteArray(),
        "RecentNumber": 9,
        "PdfViewerDisplayMode": "single",  # single or continuous
        "PdfViewerSidebarVisible": True,
        "PdfViewerZoomMode": QPdfView.ZoomMode.Custom.value,
        "PdfViewerZoomFactor": 1.0,
        "PdfViewerOpenRecentInNewWindow": False,
        "PdfSearchContextLength": 30,
        "PdfSearchHighlightAll": True,
    }

    # defaults for the eric-ide server interface
    ericServerDefaults = {
        "ConnectionProfiles": "{}",  # JSON encoded dictionary
        "ConnectionTimeout": 10,  # timeout in seconds
        "AutostartShell": True,
    }


def readToolGroups():
    """
    Module function to read the tool groups configuration.

    @return list of tuples defing the tool groups
    @rtype list of tuple
    """
    toolGroups = []
    groups = int(Prefs.settings.value("Toolgroups/Groups", 0))
    for groupIndex in range(groups):
        groupName = Prefs.settings.value("Toolgroups/{0:02d}/Name".format(groupIndex))
        group = [groupName, []]
        items = int(
            Prefs.settings.value("Toolgroups/{0:02d}/Items".format(groupIndex), 0)
        )
        for ind in range(items):
            menutext = Prefs.settings.value(
                "Toolgroups/{0:02d}/{1:02d}/Menutext".format(groupIndex, ind)
            )
            icon = Prefs.settings.value(
                "Toolgroups/{0:02d}/{1:02d}/Icon".format(groupIndex, ind)
            )
            executable = Prefs.settings.value(
                "Toolgroups/{0:02d}/{1:02d}/Executable".format(groupIndex, ind)
            )
            arguments = Prefs.settings.value(
                "Toolgroups/{0:02d}/{1:02d}/Arguments".format(groupIndex, ind)
            )
            redirect = Prefs.settings.value(
                "Toolgroups/{0:02d}/{1:02d}/Redirect".format(groupIndex, ind)
            )

            if menutext:
                if menutext == "--":
                    tool = {
                        "menutext": "--",
                        "icon": "",
                        "executable": "",
                        "arguments": "",
                        "redirect": "no",
                    }
                    group[1].append(tool)
                elif executable:
                    tool = {
                        "menutext": menutext,
                        "icon": icon,
                        "executable": executable,
                        "arguments": arguments,
                        "redirect": redirect,
                    }
                    group[1].append(tool)
        toolGroups.append(group)
    currentGroup = int(Prefs.settings.value("Toolgroups/Current Group", -1))
    return toolGroups, currentGroup


def saveToolGroups(toolGroups, currentGroup):
    """
    Module function to write the tool groups configuration.

    @param toolGroups reference to the list of tool groups
    @type list
    @param currentGroup index of the currently selected tool group
    @type int
    """
    # first step, remove all tool group entries
    Prefs.settings.remove("Toolgroups")

    # second step, write the tool group entries
    Prefs.settings.setValue("Toolgroups/Groups", len(toolGroups))
    for groupIndex, group in enumerate(toolGroups):
        Prefs.settings.setValue("Toolgroups/{0:02d}/Name".format(groupIndex), group[0])
        Prefs.settings.setValue(
            "Toolgroups/{0:02d}/Items".format(groupIndex), len(group[1])
        )
        for ind, tool in enumerate(group[1]):
            Prefs.settings.setValue(
                "Toolgroups/{0:02d}/{1:02d}/Menutext".format(groupIndex, ind),
                tool["menutext"],
            )
            Prefs.settings.setValue(
                "Toolgroups/{0:02d}/{1:02d}/Icon".format(groupIndex, ind), tool["icon"]
            )
            Prefs.settings.setValue(
                "Toolgroups/{0:02d}/{1:02d}/Executable".format(groupIndex, ind),
                tool["executable"],
            )
            Prefs.settings.setValue(
                "Toolgroups/{0:02d}/{1:02d}/Arguments".format(groupIndex, ind),
                tool["arguments"],
            )
            Prefs.settings.setValue(
                "Toolgroups/{0:02d}/{1:02d}/Redirect".format(groupIndex, ind),
                tool["redirect"],
            )
    Prefs.settings.setValue("Toolgroups/Current Group", currentGroup)


_Migrations = {
    # dictionary with old key as key and new key as value
    "MultiProject/OpenMasterAutomatically": "MultiProject/OpenMainAutomatically",
    "User/MasterPassword": "User/MainPassword",
    "User/UseMasterPassword": "User/UseMainPassword",
}


def initPreferences(withMigration=False):
    """
    Function to initialize the central configuration store.

    @param withMigration flag indicating to migrate old keys to new ones
        (defaults to False)
    @type bool (optional)
    """
    from eric7.EricWidgets.EricApplication import ericApp

    Prefs.settings = QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        Globals.settingsNameOrganization,
        Globals.settingsNameGlobal,
        ericApp(),
    )
    if not OSUtilities.isWindowsPlatform():
        hp = QDir.homePath()
        dn = QDir(hp)
        dn.mkdir(".eric7")
    QCoreApplication.setOrganizationName(Globals.settingsNameOrganization)
    QCoreApplication.setApplicationName(Globals.settingsNameGlobal)

    Prefs.settings.value("UI/SingleApplicationMode")

    if withMigration:
        for oldKey in _Migrations:
            if Prefs.settings.contains(oldKey):
                Prefs.settings.setValue(
                    _Migrations[oldKey], Prefs.settings.value(oldKey)
                )
                Prefs.settings.remove(oldKey)


def getSettings():
    """
    Function to get a reference to the settings object.

    @return reference to the settings object
    @rtype QSettings
    """
    return Prefs.settings


def syncPreferences():
    """
    Module function to sync the preferences to disk.

    In addition to syncing, the central configuration store is reinitialized
    as well.
    """
    Prefs.settings.sync()
    EricPreferences.syncPreferences()


def exportPreferences():
    """
    Module function to export the current preferences.
    """
    filename, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
        None,
        QCoreApplication.translate("Preferences", "Export Preferences"),
        "",
        QCoreApplication.translate(
            "Preferences", "Properties File (*.ini);;All Files (*)"
        ),
        None,
        EricFileDialog.DontConfirmOverwrite,
    )
    if filename:
        fpath = pathlib.Path(filename)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)
        settingsFile = Prefs.settings.fileName()
        Prefs.settings = None
        shutil.copy(settingsFile, fpath)
        initPreferences()


def importPreferences():
    """
    Module function to from eric7 import Preferences from a file previously saved by
    the export function.
    """
    filename = EricFileDialog.getOpenFileName(
        None,
        QCoreApplication.translate("Preferences", "Import Preferences"),
        "",
        QCoreApplication.translate(
            "Preferences", "Properties File (*.ini);;All Files (*)"
        ),
    )
    if filename:
        settingsFile = Prefs.settings.fileName()
        shutil.copy(filename, settingsFile)
        initPreferences(withMigration=True)


def isConfigured():
    """
    Module function to check, if the the application has been configured.

    @return flag indicating the configured status
    @rtype bool
    """
    return EricUtilities.toBool(Prefs.settings.value("General/Configured", False))


def setConfigured():
    """
    Function to set the configured flag.
    """
    Prefs.settings.setValue("General/Configured", True)


def initRecentSettings():
    """
    Module function to initialize the central configuration store for recently
    opened files and projects.

    This function is called once upon import of the module.
    """
    Prefs.rsettings = QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        Globals.settingsNameOrganization,
        Globals.settingsNameRecent,
    )


def getVarFilters():
    """
    Module function to retrieve the variables filter settings.

    @return a tuple defining the variables filter
    @rtype tuple of (list, list)
    """
    localsFilter = ast.literal_eval(
        Prefs.settings.value(
            "Variables/LocalsFilter", Prefs.varDefaults["LocalsFilter"]
        )
    )
    globalsFilter = ast.literal_eval(
        Prefs.settings.value(
            "Variables/GlobalsFilter", Prefs.varDefaults["GlobalsFilter"]
        )
    )
    return (localsFilter, globalsFilter)


def setVarFilters(filters):
    """
    Module function to store the variables filter settings.

    @param filters variable filters to set
    @type list
    """
    Prefs.settings.setValue("Variables/LocalsFilter", str(filters[0]))
    Prefs.settings.setValue("Variables/GlobalsFilter", str(filters[1]))


def getDebugger(key):
    """
    Module function to retrieve the debugger settings.

    @param key the key of the value to get
    @type str
    @return the requested debugger setting
    @rtype Any
    """
    if key in (
        "RemoteDbgEnabled",
        "PassiveDbgEnabled",
        "PassivAutoContinue",
        "AutomaticReset",
        "DebugEnvironmentReplace",
        "PythonRedirect",
        "PythonNoEncoding",
        "Python3Redirect",
        "Python3NoEncoding",
        "RubyRedirect",
        "ConsoleDbgEnabled",
        "PathTranslation",
        "Autosave",
        "ThreeStateBreakPoints",
        "BreakAlways",
        "IntelligentBreakpoints",
        "AutoViewSourceCode",
        "ShowOnlyAsDefault",
        "ShowExceptionInShell",
        "MultiProcessEnabled",
        "NetworkPortFixed",
        "NetworkPortIncrement",
        "PythonCallTraceOptimization",
    ):
        return EricUtilities.toBool(
            Prefs.settings.value("Debugger/" + key, Prefs.debuggerDefaults[key])
        )
    elif key in ("PassiveDbgPort", "MaxVariableSize", "RecentNumber", "NetworkPort"):
        return int(Prefs.settings.value("Debugger/" + key, Prefs.debuggerDefaults[key]))
    elif key in ["AllowedHosts"]:
        return EricUtilities.toList(
            Prefs.settings.value("Debugger/" + key, Prefs.debuggerDefaults[key])
        )
    elif key in ["PythonInterpreter", "Python3Interpreter"]:
        # This code is here to ensure backward compatibility.
        # Keep "PythonInterpreter" for backward compatibility.
        newKey = "Python3VirtualEnv"
        venvName = Prefs.settings.value(
            "Debugger/" + newKey, Prefs.debuggerDefaults[newKey]
        )
        if venvName:
            try:
                virtualenvManager = ericApp().getObject("VirtualEnvManager")
            except KeyError:
                from eric7.VirtualEnv.VirtualenvManager import (  # noqa: I101
                    VirtualenvManager,
                )

                virtualenvManager = VirtualenvManager()
            interpreter = virtualenvManager.getVirtualenvInterpreter(venvName)
        else:
            interpreter = ""
        if not interpreter:
            return PythonUtilities.getPythonExecutable()
        return interpreter
    elif key == "DebugClientType3":
        debugClientType = Prefs.settings.value(
            "Debugger/" + key, Prefs.debuggerDefaults[key]
        )
        # Correct obsolete entry "threaded"
        if debugClientType == "threaded":
            return "standard"
        else:
            return debugClientType
    elif key in ["BgColorNew", "BgColorChanged"]:
        col = Prefs.settings.value("Debugger/" + key)
        if col is not None:
            return QColor(col)
        else:
            return Prefs.debuggerDefaults[key]
    else:
        return Prefs.settings.value("Debugger/" + key, Prefs.debuggerDefaults[key])


def setDebugger(key, value):
    """
    Module function to store the debugger settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in ["BgColorNew", "BgColorChanged"]:
        Prefs.settings.setValue(
            "Debugger/" + key, value.name(QColor.NameFormat.HexArgb)
        )
    else:
        Prefs.settings.setValue("Debugger/" + key, value)


def getPython(key):
    """
    Module function to retrieve the Python settings.

    @param key the key of the value to get
    @type str
    @return the requested debugger setting
    @rtype Any
    """
    if key == "Python3Extensions":
        exts = []
        for ext in getDebugger(key).split():
            if ext.startswith("."):
                exts.append(ext)
            else:
                exts.append(".{0}".format(ext))
        return exts
    elif key in (
        "ASTViewerErrorColor",
        "DisViewerErrorColor",
        "DisViewerCurrentColor",
        "DisViewerLabeledColor",
    ):
        return QColor(Prefs.settings.value("Python/" + key, Prefs.pythonDefaults[key]))
    elif key in ("DisViewerExpandCodeInfoDetails"):
        return EricUtilities.toBool(
            Prefs.settings.value("Python/" + key, Prefs.pythonDefaults[key])
        )
    else:
        return Prefs.settings.value("Python/" + key, Prefs.pythonDefaults[key])


def setPython(key, value):
    """
    Module function to store the Python settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key == "Python3Extensions":
        setDebugger(key, value)
    elif key in (
        "ASTViewerErrorColor",
        "DisViewerErrorColor",
        "DisViewerCurrentColor",
        "DisViewerLabeledColor",
    ):
        val = "#{0:8x}".format(value.rgba()) if value.alpha() < 255 else value.name()
        Prefs.settings.setValue("Python/" + key, val)
    else:
        Prefs.settings.setValue("Python/" + key, value)


def getUILanguage():
    """
    Module function to retrieve the language for the user interface.

    @return the language for the UI
    @rtype str
    """
    lang = Prefs.settings.value("UI/Language", Prefs.uiDefaults["Language"])
    if lang in ("None", "", None):
        return None
    else:
        return lang


def setUILanguage(lang):
    """
    Module function to store the language for the user interface.

    @param lang the language
    @type str
    """
    if lang is None:
        Prefs.settings.setValue("UI/Language", "None")
    else:
        Prefs.settings.setValue("UI/Language", lang)


def getViewManager():
    """
    Module function to retrieve the selected viewmanager type.

    @return the viewmanager type
    @rtype str
    """
    return Prefs.settings.value("UI/ViewManager", Prefs.uiDefaults["ViewManager"])


def setViewManager(vm):
    """
    Module function to store the selected viewmanager type.

    @param vm the viewmanager type
    @type str
    """
    Prefs.settings.setValue("UI/ViewManager", vm)


def getUI(key):
    """
    Module function to retrieve the various UI settings.

    @param key the key of the value to get
    @type str
    @return the requested UI setting
    @rtype Any
    """
    if key in [
        "BrowsersListFoldersFirst",
        "BrowsersHideNonPublic",
        "BrowsersListContentsByOccurrence",
        "BrowsersListHiddenFiles",
        "BrowserShowCoding",
        "BrowsersFilterRemoteEntries",
        "LogViewerAutoRaise",
        "SingleApplicationMode",
        "TabViewManagerFilenameOnly",
        "ShowFilePreview",
        "ShowFilePreviewSSI",
        "CaptionShowsFilename",
        "ShowSplash",
        "SplitOrientationVertical",
        "DynamicOnlineCheck",
        "RequestDownloadFilename",
        "CheckErrorLog",
        "OpenCrashSessionOnStartup",
        "DeleteLoadedCrashSession",
        "CrashSessionEnabled",
        "ShowCodeDocumentationViewer",
        "ShowPyPIPackageManager",
        "ShowCondaPackageManager",
        "ShowCooperation",
        "ShowIrc",
        "ShowTemplateViewer",
        "ShowFileBrowser",
        "ShowSymbolsViewer",
        "ShowNumbersViewer",
        "ShowMicroPython",
        "ShowFindFileWidget",
        "ShowFindLocationWidget",
        "ShowInternalHelpViewer",
        "UseNativeMenuBar",
        "CombinedLeftRightSidebar",
        "LoadUnknownMimeTypeFiles",
        "TextMimeTypesAskUser",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value("UI/" + key, Prefs.uiDefaults[key])
        )
    elif key in [
        "TabViewManagerFilenameLength",
        "CaptionFilenameLength",
        "OpenOnStartup",
        "PerformVersionCheck",
        "RecentNumber",
        "NotificationTimeout",
        "UpgraderDelay",
        "KeyboardInputInterval",
        "BackgroundServiceProcesses",
        "MinimumMessageTypeSeverity",
    ]:
        return int(Prefs.settings.value("UI/" + key, Prefs.uiDefaults[key]))
    elif key in ("LogStdErrColour", "IconBarColor"):
        col = Prefs.settings.value("UI/" + key)
        if col is not None:
            return QColor(col)
        else:
            return Prefs.uiDefaults[key]
    elif key in "ViewProfiles":
        profilesStr = Prefs.settings.value("UI/ViewProfiles")
        if profilesStr is None:
            # use the defaults
            viewProfiles = Prefs.uiDefaults["ViewProfiles"]
        else:
            viewProfiles = {}
            profiles = json.loads(profilesStr)
            for name in ["edit", "debug"]:
                viewProfiles[name] = [
                    QByteArray.fromBase64(profiles[name][0].encode("utf-8")),
                    profiles[name][1][:],
                    [],
                ]
                if len(profiles[name][2]) == 6:
                    del profiles[name][2][2]
                for bs in profiles[name][2][:2]:
                    # splitters
                    viewProfiles[name][2].append(
                        QByteArray.fromBase64(bs.encode("utf-8"))
                    )
                viewProfiles[name][2] += profiles[name][2][2:]  # side bars
        return viewProfiles
    elif key in ["ToolbarManagerState", "PreviewSplitterState"]:
        state = Prefs.settings.value("UI/" + key)
        if state is not None:
            return state
        else:
            return Prefs.uiDefaults[key]
    elif key in [
        "LogViewerStdoutFilter",
        "LogViewerStderrFilter",
        "LogViewerStdxxxFilter",
        "TextMimeTypes",
        "TextFilePatterns",
    ]:
        return EricUtilities.toList(
            Prefs.settings.value("UI/" + key, Prefs.uiDefaults[key])
        )
    else:
        return Prefs.settings.value("UI/" + key, Prefs.uiDefaults[key])


def setUI(key, value):
    """
    Module function to store the various UI settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key == "ViewProfiles":
        profiles = {}
        for name in ["edit", "debug"]:
            profiles[name] = [
                bytes(value[name][0].toBase64()).decode(),
                value[name][1][:],
                [],
            ]
            for ba in value[name][2][:2]:
                # Splitters
                profiles[name][2].append(bytes(ba.toBase64()).decode())
            profiles[name][2] += value[name][2][2:]  # side bars
        Prefs.settings.setValue("UI/" + key, json.dumps(profiles))
    elif key in ("LogStdErrColour", "IconBarColor"):
        Prefs.settings.setValue("UI/" + key, value.name())
    else:
        Prefs.settings.setValue("UI/" + key, value)


def getIcons(key):
    """
    Module function to retrieve the various Icons settings.

    @param key the key of the value to get
    @type str
    @return the requested Icons setting
    @rtype Any
    """
    if key in ("Path",):
        return EricUtilities.toList(
            Prefs.settings.value("UI/Icons/" + key, Prefs.iconsDefaults[key])
        )
    elif key in ("PreferVectorIcons",):
        return EricUtilities.toBool(
            Prefs.settings.value("UI/Icons/" + key, Prefs.iconsDefaults[key])
        )
    else:
        return Prefs.settings.value("UI/Icons/" + key, Prefs.iconsDefaults[key])


def setIcons(key, value):
    """
    Module function to store the various Icons settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("UI/Icons/" + key, value)


def getCooperation(key):
    """
    Module function to retrieve the various Cooperation settings.

    @param key the key of the value to get
    @type str
    @return the requested UI setting
    @rtype Any
    """
    if key in ["AutoStartServer", "TryOtherPorts", "AutoAcceptConnections"]:
        return EricUtilities.toBool(
            Prefs.settings.value("Cooperation/" + key, Prefs.cooperationDefaults[key])
        )
    elif key in ["ServerPort", "MaxPortsToTry"]:
        return int(
            Prefs.settings.value("Cooperation/" + key, Prefs.cooperationDefaults[key])
        )
    elif key in ["BannedUsers"]:
        return EricUtilities.toList(
            Prefs.settings.value("Cooperation/" + key, Prefs.cooperationDefaults[key])
        )
    else:
        return Prefs.settings.value(
            "Cooperation/" + key, Prefs.cooperationDefaults[key]
        )


def setCooperation(key, value):
    """
    Module function to store the various Cooperation settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("Cooperation/" + key, value)


def getEditor(key):
    """
    Module function to retrieve the various editor settings.

    @param key the key of the value to get
    @type str
    @return the requested editor setting
    @rtype Any
    """
    if key in [
        "DefaultEncoding",
        "DefaultOpenFilter",
        "DefaultSaveFilter",
        "SpellCheckingDefaultLanguage",
        "SpellCheckingPersonalWordList",
        "SpellCheckingPersonalExcludeList",
        "DocstringType",
        "PreviewMarkdownHTMLFormat",
        "PreviewRestDocutilsHTMLFormat",
        "WrapLongLinesMode",
        "WrapVisualFlag",
        "WrapIndentMode",
        "CallTipsStyle",
        "CallTipsPosition",
        "AutoCompletionSource",
        "EdgeMode",
        "EOLMode",
        "PythonBadIndentation",
        "RectangularSelectionModifier",
    ]:
        # no special treatment for str and PyQt6 Enum
        return Prefs.settings.value("Editor/" + key, Prefs.editorDefaults[key])
    elif key in [
        "AutosaveIntervalSeconds",
        "TabWidth",
        "IndentWidth",
        "WarnFilesize",
        "RejectFilesize",
        "EdgeColumn",
        "CaretWidth",
        "CaretLineFrameWidth",
        "AutoCompletionThreshold",
        "AutoCompletionTimeout",
        "AutoCompletionCacheSize",
        "AutoCompletionCacheTime",
        "AutoCompletionWatchdogTime",
        "AutoCompletionMaxLines",
        "AutoCompletionMaxChars",
        "CallTipsVisible",
        "MarkOccurrencesTimeout",
        "QuickSearchMarkOccurrencesTimeout",
        "SearchRegexpMode",
        "AutoSpellCheckChunkSize",
        "SpellCheckingMinWordSize",
        "PostScriptLevel",
        "ZoomFactor",
        "WhitespaceSize",
        "OnlineSyntaxCheckInterval",
        "OnlineChangeTraceInterval",
        "WrapStartIndent",
        "VirtualSpaceOptions",
        "PreviewRefreshWaitTimer",
        "SourceOutlineWidth",
        "FoldingStyle",
        "MouseHoverTimeout",
    ]:
        return int(Prefs.settings.value("Editor/" + key, Prefs.editorDefaults[key]))
    elif key in [
        "AdditionalOpenFilters",
        "AdditionalSaveFilters",
        "PreviewMarkdownFileNameExtensions",
        "PreviewRestFileNameExtensions",
        "PreviewHtmlFileNameExtensions",
        "PreviewQssFileNameExtensions",
        "FullSpellCheckExtensions",
    ]:
        return EricUtilities.toList(
            Prefs.settings.value("Editor/" + key, Prefs.editorDefaults[key])
        )
    elif key == "TabIndentOverride":
        overrideStr = Prefs.settings.value("Editor/" + key, Prefs.editorDefaults[key])
        if overrideStr:
            return json.loads(overrideStr)
        else:
            return {}
    elif key == "PrintColorMode":
        return QsciScintillaPrintColorMode(
            int(Prefs.settings.value("Editor/" + key, Prefs.editorDefaults[key]))
        )
    else:
        return EricUtilities.toBool(
            Prefs.settings.value("Editor/" + key, Prefs.editorDefaults[key])
        )


def setEditor(key, value):
    """
    Module function to store the various editor settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key == "TabIndentOverride":
        Prefs.settings.setValue("Editor/" + key, json.dumps(value))
    elif key == "PrintColorMode":
        Prefs.settings.setValue("Editor/" + key, value.value)
    else:
        Prefs.settings.setValue("Editor/" + key, value)


def getEditorColour(key):
    """
    Module function to retrieve the various editor marker colours.

    @param key the key of the value to get
    @type str
    @return the requested editor colour
    @rtype QColor
    """
    col = Prefs.settings.value("Editor/Colour/" + key)
    if col is not None:
        if len(col) == 9:
            # color string with alpha
            return QColor.fromRgba(int(col[1:], 16))
        else:
            return QColor(col)
    else:
        # palette based defaults here because of Qt6
        if key == "EditAreaForeground":
            return QApplication.palette().color(
                QPalette.ColorGroup.Active, QPalette.ColorRole.Base
            )
        elif key == "EditAreaBackground":
            return QApplication.palette().color(
                QPalette.ColorGroup.Active, QPalette.ColorRole.Text
            )
        else:
            return Prefs.editorColourDefaults[key]


def setEditorColour(key, value):
    """
    Module function to store the various editor marker colours.

    @param key the key of the colour to be set
    @type str
    @param value the colour to be set
    @type QColor
    """
    val = value.name(QColor.NameFormat.HexArgb) if value.alpha() < 255 else value.name()
    Prefs.settings.setValue("Editor/Colour/" + key, val)


def getEditorOtherFonts(key):
    """
    Module function to retrieve the various editor fonts except the lexer
    fonts.

    @param key the key of the value to get
    @type str
    @return the requested editor font
    @rtype QFont
    """
    f = QFont()
    f.fromString(
        Prefs.settings.value(
            "Editor/Other Fonts/" + key, Prefs.editorOtherFontsDefaults[key]
        )
    )
    return f


def setEditorOtherFonts(key, font):
    """
    Module function to store the various editor fonts except the lexer fonts.

    @param key the key of the font to be set
    @type str
    @param font the font to be set
    @type QFont
    """
    Prefs.settings.setValue("Editor/Other Fonts/" + key, font.toString())


def getEditorAPI(language, projectType=""):
    """
    Module function to retrieve the various lists of API files.

    @param language language of the API list
    @type str
    @param projectType project type of the API list
    @type str
    @return requested list of API files
    @rtype list of str
    """
    key = "{0}_{1}".format(language, projectType) if projectType else language
    apis = Prefs.settings.value("Editor/APIs/" + key)
    if apis is not None:
        if len(apis) and apis[0] == "":
            return []
        else:
            return apis
    else:
        if projectType:
            # try again without project type
            return getEditorAPI(language)

        return []


def setEditorAPI(language, projectType, apilist):
    """
    Module function to store the various lists of API files.

    @param language language of the API list
    @type str
    @param projectType project type of the API list
    @type str
    @param apilist list of API files
    @type list of str
    """
    key = "{0}_{1}".format(language, projectType) if projectType else language
    Prefs.settings.setValue("Editor/APIs/" + key, apilist)


def getEditorKeywords(key):
    """
    Module function to retrieve the various lists of language keywords.

    @param key the key of the value to get
    @type str
    @return the requested list of language keywords
    @rtype list of str
    """
    keywords = Prefs.settings.value("Editor/Keywords/" + key)
    if keywords is not None:
        return keywords
    else:
        return []


def setEditorKeywords(key, keywordsLists):
    """
    Module function to store the various lists of language keywords.

    @param key the key of the api to be set
    @type str
    @param keywordsLists the list of language keywords
    @type list of str
    """
    Prefs.settings.setValue("Editor/Keywords/" + key, keywordsLists)


def getEditorLexerAssocs():
    """
    Module function to retrieve all lexer associations.

    @return a reference to the list of lexer associations
    @rtype dict of str
    """
    from eric7.QScintilla import Lexers

    editorLexerAssoc = {}
    Prefs.settings.beginGroup("Editor/LexerAssociations")
    keyList = Prefs.settings.childKeys()
    Prefs.settings.endGroup()

    editorLexerAssocDefaults = Lexers.getDefaultLexerAssociations()

    if len(keyList) == 0:
        # build from scratch
        for key in editorLexerAssocDefaults:
            editorLexerAssoc[key] = editorLexerAssocDefaults[key]
    else:
        for key in keyList:
            defaultValue = editorLexerAssocDefaults.get(key, "")
            editorLexerAssoc[key] = Prefs.settings.value(
                "Editor/LexerAssociations/" + key, defaultValue
            )

        # check for new default lexer associations
        for key in editorLexerAssocDefaults:
            if key not in editorLexerAssoc:
                editorLexerAssoc[key] = editorLexerAssocDefaults[key]
    return editorLexerAssoc


def setEditorLexerAssocs(assocs):
    """
    Module function to retrieve all lexer associations.

    @param assocs dictionary of lexer associations to be set
    @type dict
    """
    # first remove lexer associations that no longer exist, than save the rest
    Prefs.settings.beginGroup("Editor/LexerAssociations")
    keyList = Prefs.settings.childKeys()
    Prefs.settings.endGroup()
    for key in keyList:
        if key not in assocs:
            Prefs.settings.remove("Editor/LexerAssociations/" + key)
    for key in assocs:
        Prefs.settings.setValue("Editor/LexerAssociations/" + key, assocs[key])


def getEditorLexerAssoc(filename):
    """
    Module function to retrieve a lexer association.

    @param filename filename used to determine the associated lexer language
    @type str
    @return the requested lexer language
    @rtype str
    """
    for pattern, language in getEditorLexerAssocs().items():
        if fnmatch.fnmatch(filename, pattern):
            return language

    return ""


def getEditorTyping(key):
    """
    Module function to retrieve the various editor typing settings.

    @param key the key of the value to get
    @type str
    @return the requested editor setting
    @rtype Any
    """
    return EricUtilities.toBool(
        Prefs.settings.value("Editor/Typing/" + key, Prefs.editorTypingDefaults[key])
    )


def setEditorTyping(key, value):
    """
    Module function to store the various editor typing settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("Editor/Typing/" + key, value)


def getEditorExporter(key):
    """
    Module function to retrieve the various editor exporters settings.

    @param key the key of the value to get
    @type str
    @return the requested editor setting
    @rtype Any
    """
    if key in ["RTF/Font"]:
        f = QFont()
        f.fromString(
            Prefs.settings.value(
                "Editor/Exporters/" + key, Prefs.editorExporterDefaults[key]
            )
        )
        return f
    elif key in [
        "HTML/WYSIWYG",
        "HTML/Folding",
        "HTML/OnlyStylesUsed",
        "HTML/FullPathAsTitle",
        "HTML/UseTabs",
        "RTF/WYSIWYG",
        "RTF/UseTabs",
        "TeX/OnlyStylesUsed",
        "TeX/FullPathAsTitle",
        "ODT/WYSIWYG",
        "ODT/OnlyStylesUsed",
        "ODT/UseTabs",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value(
                "Editor/Exporters/" + key, Prefs.editorExporterDefaults[key]
            )
        )
    elif key in [
        "PDF/Magnification",
        "PDF/MarginLeft",
        "PDF/MarginRight",
        "PDF/MarginTop",
        "PDF/MarginBottom",
    ]:
        return int(
            Prefs.settings.value(
                "Editor/Exporters/" + key, Prefs.editorExporterDefaults[key]
            )
        )
    else:
        return Prefs.settings.value(
            "Editor/Exporters/" + key, Prefs.editorExporterDefaults[key]
        )


def setEditorExporter(key, value):
    """
    Module function to store the various editor exporters settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in ["RTF/Font"]:
        Prefs.settings.setValue("Editor/Exporters/" + key, value.toString())
    else:
        Prefs.settings.setValue("Editor/Exporters/" + key, value)


def getPrinter(key):
    """
    Module function to retrieve the various printer settings.

    @param key the key of the value to get
    @type str
    @return the requested printer setting
    @rtype Any
    """
    if key in ["ColorMode", "FirstPageFirst"]:
        return EricUtilities.toBool(
            Prefs.settings.value("Printer/" + key, Prefs.printerDefaults[key])
        )
    elif key in ["Magnification", "Orientation", "PageSize", "Resolution"]:
        return int(Prefs.settings.value("Printer/" + key, Prefs.printerDefaults[key]))
    elif key in ["LeftMargin", "RightMargin", "TopMargin", "BottomMargin"]:
        return float(Prefs.settings.value("Printer/" + key, Prefs.printerDefaults[key]))
    elif key in ["HeaderFont"]:
        f = QFont()
        f.fromString(Prefs.settings.value("Printer/" + key, Prefs.printerDefaults[key]))
        return f
    else:
        return Prefs.settings.value("Printer/" + key, Prefs.printerDefaults[key])


def setPrinter(key, value):
    """
    Module function to store the various printer settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in ["HeaderFont"]:
        Prefs.settings.setValue("Printer/" + key, value.toString())
    else:
        Prefs.settings.setValue("Printer/" + key, value)


def getShell(key):
    """
    Module function to retrieve the various shell settings.

    @param key the key of the value to get
    @type str
    @return the requested shell setting
    @rtype Any
    """
    if key in ["MonospacedFont", "MarginsFont"]:
        f = QFont()
        f.fromString(Prefs.settings.value("Shell/" + key, Prefs.shellDefaults[key]))
        return f
    elif key in ["MaxHistoryEntries", "CommandExecutionTimeout"]:
        return int(Prefs.settings.value("Shell/" + key, Prefs.shellDefaults[key]))
    elif key in ["HistoryStyle"]:
        return ShellHistoryStyle(
            int(Prefs.settings.value("Shell/" + key, Prefs.shellDefaults[key].value))
        )
    elif key in ["LastVirtualEnvironment"]:
        return Prefs.settings.value("Shell/" + key, Prefs.shellDefaults[key])
    else:
        return EricUtilities.toBool(
            Prefs.settings.value("Shell/" + key, Prefs.shellDefaults[key])
        )


def setShell(key, value):
    """
    Module function to store the various shell settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in ["MonospacedFont", "MarginsFont"]:
        Prefs.settings.setValue("Shell/" + key, value.toString())
    elif key in ["HistoryStyle"]:
        Prefs.settings.setValue("Shell/" + key, value.value)
    else:
        Prefs.settings.setValue("Shell/" + key, value)


def getProject(key):
    """
    Module function to retrieve the various project handling settings.

    @param key the key of the value to get
    @type str
    @return the requested project setting
    @rtype Any
    """
    if key in ["RecentNumber"]:
        return int(Prefs.settings.value("Project/" + key, Prefs.projectDefaults[key]))
    elif key in ["DebugClientsHistory", "DebuggerInterpreterHistory"]:
        return EricUtilities.toList(
            Prefs.settings.value("Project/" + key, Prefs.projectDefaults[key])
        )
    else:
        return EricUtilities.toBool(
            Prefs.settings.value("Project/" + key, Prefs.projectDefaults[key])
        )


def setProject(key, value):
    """
    Module function to store the various project handling settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in ["DebugClientsHistory", "DebuggerInterpreterHistory"]:
        # max. list sizes is hard coded to 20 entries
        newList = [v for v in value if v]
        if len(newList) > 20:
            newList = newList[:20]
        Prefs.settings.setValue("Project/" + key, newList)
    else:
        Prefs.settings.setValue("Project/" + key, value)


def getProjectBrowsers(key):
    """
    Function to retrieve the enabled project browsers per project type.

    @param key project type
    @type str
    @return list of enabled project browsers
    @rtype list of str
    """
    try:
        default = list(Prefs.projectBrowsersDefaults[key][:])
    except KeyError:
        default = list(Prefs.projectBrowsersDefaults["allBrowsers"][:])

    return EricUtilities.toList(
        Prefs.settings.value("Project/BrowsersEnabled/" + key, default)
    )


def setProjectBrowsers(key, value):
    """
    Function to store the enabled project browsers per project type.

    @param key project type
    @type str
    @param value list of enabled project browsers
    @type list of str
    """
    Prefs.settings.setValue("Project/BrowsersEnabled/" + key, value)


def removeProjectBrowsers(key):
    """
    Function to remove the browsers list of the given project type.

    @param key project type
    @type str
    """
    Prefs.settings.remove("Project/BrowsersEnabled/" + key)


def setProjectBrowsersDefault(projectType, browsersList):
    """
    Function to store the given project browser list to the list of defaults.

    @param projectType project type
    @type str
    @param browsersList default list of browsers for the project type
    @type list of str or tuple of str
    """
    Prefs.projectBrowsersDefaults[projectType] = browsersList


def getProjectBrowserColour(key):
    """
    Module function to retrieve the various project browser colours.

    @param key the key of the value to get
    @type str
    @return the requested project browser colour
    @rtype Any
    """
    col = Prefs.settings.value("Project/Colour/" + key)
    if col is not None:
        return QColor(col)
    else:
        return Prefs.projectBrowserColourDefaults[key]


def setProjectBrowserColour(key, value):
    """
    Module function to store the various project browser colours.

    @param key the key of the colour to be set
    @type str
    @param value the colour to be set
    @type Any
    """
    Prefs.settings.setValue("Project/Colour/" + key, value.name())


def getMultiProject(key):
    """
    Module function to retrieve the various project handling settings.

    @param key the key of the value to get
    @type str
    @return the requested project setting
    @rtype Any
    """
    if key in ["RecentNumber"]:
        return int(
            Prefs.settings.value("MultiProject/" + key, Prefs.multiProjectDefaults[key])
        )
    elif key in ["OpenMainAutomatically", "TimestampFile"]:
        return EricUtilities.toBool(
            Prefs.settings.value("MultiProject/" + key, Prefs.multiProjectDefaults[key])
        )
    else:
        return Prefs.settings.value(
            "MultiProject/" + key, Prefs.multiProjectDefaults[key]
        )


def setMultiProject(key, value):
    """
    Module function to store the various project handling settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("MultiProject/" + key, value)


def getQtDocDir(version):
    """
    Module function to retrieve the Qt5DocDir/Qt6DocDir setting.

    @param version Qt version to get documentation directory for
    @type int
    @return the requested Qt5DocDir/Qt6DocDir setting
    @rtype str
    """
    key = "Qt{0}DocDir".format(version)
    s = Prefs.settings.value("Help/{0}".format(key), Prefs.helpDefaults[key])
    if s == "":
        s = os.getenv(key.upper(), "")
    if s == "" and version == 6:  # that only works for Qt6
        s = os.path.join(
            QLibraryInfo.path(QLibraryInfo.LibraryPath.DocumentationPath), "qtdoc"
        )
    return s


def getHelp(key):
    """
    Module function to retrieve the various help settings.

    @param key the key of the value to get
    @type str
    @return the requested help setting
    @rtype Any
    """
    if key in ("HelpViewerType",):
        return int(Prefs.settings.value("Help/" + key, Prefs.helpDefaults[key]))
    elif key in ("QtHelpSearchNewOnStart", "ForceQTextBrowser"):
        return EricUtilities.toBool(
            Prefs.settings.value("Help/" + key, Prefs.helpDefaults[key])
        )
    else:
        return Prefs.settings.value("Help/" + key, Prefs.helpDefaults[key])


def setHelp(key, value):
    """
    Module function to store the various help settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("Help/" + key, value)


def getWebBrowser(key):
    """
    Module function to retrieve the various web browser settings.

    @param key the key of the value to get
    @type str
    @return the requested help setting
    @rtype Any
    """
    if not Prefs.webEngineSettingsIntitialized:
        Prefs.initWebEngineSettingsDefaults()

    if key in ["StandardFont", "FixedFont"]:
        f = QFont()
        f.fromString(
            Prefs.settings.value("WebBrowser/" + key, Prefs.webBrowserDefaults[key])
        )
        return f
    elif key in [
        "SecureUrlColor",
        "InsecureUrlColor",
        "MaliciousUrlColor",
        "PrivateModeUrlColor",
    ]:
        col = Prefs.settings.value("WebBrowser/" + key)
        if col is not None:
            return QColor(col)
        else:
            return Prefs.webBrowserDefaults[key]
    elif key in ["WebSearchKeywords"]:
        # return a list of tuples of (keyword, engine name)
        keywords = []
        size = Prefs.settings.beginReadArray("WebBrowser/" + key)
        for index in range(size):
            Prefs.settings.setArrayIndex(index)
            keyword = Prefs.settings.value("Keyword")
            engineName = Prefs.settings.value("Engine")
            keywords.append((keyword, engineName))
        Prefs.settings.endArray()
        return keywords
    elif key == "DownloadManagerDownloads":
        # return a list of dicts containing the URL, save location, done flag,
        # page URL, date/time downloaded
        downloads = []
        length = Prefs.settings.beginReadArray("WebBrowser/" + key)
        for index in range(length):
            download = {}
            Prefs.settings.setArrayIndex(index)
            download["URL"] = Prefs.settings.value("URL")
            if download["URL"] is None:
                download["URL"] = QUrl()
            download["Location"] = Prefs.settings.value("Location")
            download["Done"] = EricUtilities.toBool(Prefs.settings.value("Done"))
            download["PageURL"] = Prefs.settings.value("PageURL")
            if download["PageURL"] is None:
                download["PageURL"] = QUrl()
            download["Downloaded"] = Prefs.settings.value("Downloaded")
            if download["Downloaded"] is None:
                download["Downloaded"] = QDateTime()
            elif isinstance(download["Downloaded"], str):
                download["Downloaded"] = QDateTime.fromString(
                    download["Downloaded"], "yyyy-MM-dd hh:mm:ss"
                )
            downloads.append(download)
        Prefs.settings.endArray()
        return downloads
    elif key == "RssFeeds":
        # return a list of tuples of (URL, title, icon)
        feeds = []
        length = Prefs.settings.beginReadArray("WebBrowser/" + key)
        for index in range(length):
            Prefs.settings.setArrayIndex(index)
            url = Prefs.settings.value("URL")
            title = Prefs.settings.value("Title")
            icon = Prefs.settings.value("Icon")
            feeds.append((url, title, icon))
        Prefs.settings.endArray()
        return feeds
    elif key in ["SyncFtpPassword", "SyncEncryptionKey"]:
        return pwConvert(
            Prefs.settings.value("WebBrowser/" + key, Prefs.webBrowserDefaults[key]),
            encode=False,
        )
    elif key in (
        "StartupBehavior",
        "HistoryLimit",
        "DownloadManagerRemovePolicy",
        "SyncType",
        "SyncFtpPort",
        "SyncFtpIdleTimeout",
        "SyncEncryptionKeyLength",
        "DefaultFontSize",
        "DefaultFixedFontSize",
        "MinimumFontSize",
        "MinimumLogicalFontSize",
        "DiskCacheSize",
        "AcceptCookies",
        "KeepCookiesUntil",
        "AdBlockUpdatePeriod",
        "TabManagerGroupByType",
        "SessionAutoSaveInterval",
        "NewTabBehavior",
        "RefererSendReferer",
        "RefererDefaultPolicy",
        "RefererTrimmingPolicy",
        "AcceptQuotaRequest",
        "AcceptProtocolHandlerRequest",
        "AcceptFileSystemAccessRequest",
    ):
        return int(
            Prefs.settings.value("WebBrowser/" + key, Prefs.webBrowserDefaults[key])
        )
    elif key in [
        "SingleWebBrowserWindow",
        "SaveGeometry",
        "JavaScriptEnabled",
        "JavaScriptCanOpenWindows",
        "JavaScriptCanAccessClipboard",
        "AutoLoadImages",
        "LocalStorageEnabled",
        "SpatialNavigationEnabled",
        "LinksIncludedInFocusChain",
        "LocalContentCanAccessRemoteUrls",
        "LocalContentCanAccessFileUrls",
        "XSSAuditingEnabled",
        "ScrollAnimatorEnabled",
        "ErrorPageEnabled",
        "WarnOnMultipleClose",
        "WebSearchSuggestions",
        "SyncEnabled",
        "SyncBookmarks",
        "SyncHistory",
        "SyncPasswords",
        "SyncUserAgents",
        "SyncSpeedDial",
        "SyncEncryptData",
        "SyncEncryptPasswordsOnly",
        "ShowPreview",
        "DiskCacheEnabled",
        "DoNotTrack",
        "FilterTrackingCookies",
        "AdBlockEnabled",
        "AdBlockUseLimitedEasyList",
        "PluginsEnabled",
        "FullScreenSupportEnabled",
        "AutoScrollEnabled",
        "ScreenCaptureEnabled",
        "WebGLEnabled",
        "FocusOnNavigationEnabled",
        "PrintElementBackgrounds",
        "AllowRunningInsecureContent",
        "SpellCheckEnabled",
        "ForceHttpDictionaryDownload",
        "ShowToolbars",
        "MenuBarVisible",
        "BookmarksToolBarVisible",
        "StatusBarVisible",
        "SessionAutoSave",
        "LoadTabOnActivation",
        "SafeBrowsingEnabled",
        "SafeBrowsingFilterPlatform",
        "SafeBrowsingAutoUpdate",
        "SafeBrowsingUseLookupApi",
        "AllowGeolocationOnInsecureOrigins",
        "AllowWindowActivationFromJavaScript",
        "ShowScrollBars",
        "DownloadManagerAutoOpen",
        "DownloadManagerAutoClose",
        "PlaybackRequiresUserGesture",
        "JavaScriptCanPaste",
        "WebRTCPublicInterfacesOnly",
        "DnsPrefetchEnabled",
        "VirusTotalEnabled",
        "VirusTotalSecure",
        "PdfViewerEnabled",
        "AlwaysRejectFaultyCertificates",
        "Accelerated2dCanvasEnabled",
        "AutoLoadIconsForPage",
        "PushServiceEnabled",
        "NavigateOnDropEnabled",
        "ReadingFromCanvasEnabled",
        "ForceDarkMode",
        "NoPersistentPermissions",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value("WebBrowser/" + key, Prefs.webBrowserDefaults[key])
        )
    elif key in [
        "GreaseMonkeyDisabledScripts",
        "SendRefererWhitelist",
        "AdBlockSubscriptions",
        "AdBlockExceptions",
        "SpellCheckLanguages",
    ]:
        return EricUtilities.toList(
            Prefs.settings.value("WebBrowser/" + key, Prefs.webBrowserDefaults[key])
        )
    elif key in ["AutoScrollDivider"]:
        return float(
            Prefs.settings.value("WebBrowser/" + key, Prefs.webBrowserDefaults[key])
        )
    elif key in ["SafeBrowsingUpdateDateTime"]:
        dateTimeStr = Prefs.settings.value("WebBrowser/" + key)
        if dateTimeStr is not None:
            return QDateTime.fromString(dateTimeStr, Qt.DateFormat.ISODate)
        else:
            return Prefs.webBrowserDefaults[key]
    else:
        return Prefs.settings.value("WebBrowser/" + key, Prefs.webBrowserDefaults[key])


def setWebBrowser(key, value):
    """
    Module function to store the various web browser settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in ["StandardFont", "FixedFont"]:
        Prefs.settings.setValue("WebBrowser/" + key, value.toString())
    elif key in [
        "SecureUrlColor",
        "InsecureUrlColor",
        "MaliciousUrlColor",
        "PrivateModeUrlColor",
    ]:
        Prefs.settings.setValue("WebBrowser/" + key, value.name())
    elif key == "WebSearchKeywords":
        # value is list of tuples of (keyword, engine name)
        Prefs.settings.remove("WebBrowser/" + key)
        Prefs.settings.beginWriteArray("WebBrowser/" + key, len(value))
        for index, v in enumerate(value):
            Prefs.settings.setArrayIndex(index)
            Prefs.settings.setValue("Keyword", v[0])
            Prefs.settings.setValue("Engine", v[1])
        Prefs.settings.endArray()
    elif key == "DownloadManagerDownloads":
        # value is list of dicts containing the URL, save location, done flag,
        # page URL, date/time downloaded
        Prefs.settings.remove("Help/" + key)
        Prefs.settings.beginWriteArray("WebBrowser/" + key, len(value))
        for index, v in enumerate(value):
            Prefs.settings.setArrayIndex(index)
            Prefs.settings.setValue("URL", v["URL"])
            Prefs.settings.setValue("Location", v["Location"])
            Prefs.settings.setValue("Done", v["Done"])
            Prefs.settings.setValue("PageURL", v["PageURL"])
            Prefs.settings.setValue(
                "Downloaded", v["Downloaded"].toString("yyyy-MM-dd hh:mm:ss")
            )
        Prefs.settings.endArray()
    elif key == "RssFeeds":
        # value is list of tuples of (URL, title, icon)
        Prefs.settings.remove("WebBrowser/" + key)
        Prefs.settings.beginWriteArray("WebBrowser/" + key, len(value))
        for index, v in enumerate(value):
            Prefs.settings.setArrayIndex(index)
            Prefs.settings.setValue("URL", v[0])
            Prefs.settings.setValue("Title", v[1])
            Prefs.settings.setValue("Icon", v[2])
        Prefs.settings.endArray()
    elif key in ["SyncFtpPassword", "SyncEncryptionKey"]:
        Prefs.settings.setValue("WebBrowser/" + key, pwConvert(value, encode=True))
    elif key in ["SafeBrowsingUpdateDateTime"]:
        # value is a QDateTime
        Prefs.settings.setValue(
            "WebBrowser/" + key, value.toString(Qt.DateFormat.ISODate)
        )
    else:
        Prefs.settings.setValue("WebBrowser/" + key, value)


def getSystem(key):
    """
    Module function to retrieve the various system settings.

    @param key the key of the value to get
    @type str
    @return the requested system setting
    @rtype Any
    """
    from eric7.Utilities import supportedCodecs

    if key in ["StringEncoding", "IOEncoding"]:
        encoding = Prefs.settings.value("System/" + key, Prefs.sysDefaults[key])
        if encoding not in supportedCodecs:
            encoding = Prefs.sysDefaults[key]
        return encoding

    return None


def setSystem(key, value):
    """
    Module function to store the various system settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("System/" + key, value)


def getQtTranslationsDir():
    """
    Module function to retrieve the Qt6TranslationsDir
    setting depending on the current Qt version.

    @return the requested setting
    @rtype str
    """
    s = Prefs.settings.value(
        "Qt/Qt6TranslationsDir", Prefs.qtDefaults["Qt6TranslationsDir"]
    )
    if s == "":
        s = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if s == "" and OSUtilities.isWindowsPlatform():
        transPath = os.path.join(QtUtilities.getPyQt6ModulesDirectory(), "translations")
        if os.path.exists(transPath):
            s = transPath
    return s


def getQt(key):
    """
    Module function to retrieve the various Qt settings.

    @param key the key of the value to get
    @type str
    @return the requested Qt setting
    @rtype Any
    """
    if key in ["Qt6TranslationsDir"]:
        return getQtTranslationsDir()
    elif key in ["PyuicIndent", "Pyuic6Indent"]:
        return int(Prefs.settings.value("Qt/" + key, Prefs.qtDefaults[key]))
    elif key in [
        "PyuicFromImports",
        "PyuicExecute",
        "Pyuic6Execute",
        "PySide2FromImports",
        "PySide6FromImports",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value("Qt/" + key, Prefs.qtDefaults[key])
        )
    else:
        return Prefs.settings.value("Qt/" + key, Prefs.qtDefaults[key])


def setQt(key, value):
    """
    Module function to store the various Qt settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("Qt/" + key, value)


def getUser(key):
    """
    Module function to retrieve the various user settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key == "MailServerPassword":
        return pwConvert(
            Prefs.settings.value("User/" + key, Prefs.userDefaults[key]), encode=False
        )
    elif key in ["MailServerPort"]:
        try:
            return int(Prefs.settings.value("User/" + key, Prefs.userDefaults[key]))
        except ValueError:
            return Prefs.userDefaults[key]
    elif key in [
        "MailServerAuthentication",
        "UseSystemEmailClient",
        "UseMainPassword",
        "SavePasswords",
        "UseGoogleMailOAuth2",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value("User/" + key, Prefs.userDefaults[key])
        )
    elif key == "MailServerEncryption":
        # convert from old key 'MailServerUseTLS'
        val = Prefs.settings.value("User/" + key)
        if val is None:
            if EricUtilities.toBool(Prefs.settings.value("User/MailServerUseTLS")):
                val = "TLS"
            else:
                val = Prefs.userDefaults[key]
        return val
    else:
        return Prefs.settings.value("User/" + key, Prefs.userDefaults[key])


def setUser(key, value):
    """
    Module function to store the various user settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key == "MailServerPassword":
        Prefs.settings.setValue("User/" + key, pwConvert(value, encode=True))
    elif key == "MainPassword":
        Prefs.settings.setValue("User/" + key, hashPassword(value))
    else:
        Prefs.settings.setValue("User/" + key, value)


def getVCS(key):
    """
    Module function to retrieve the VCS related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key in ["StatusMonitorInterval", "CommitMessages"]:
        return int(Prefs.settings.value("VCS/" + key, Prefs.vcsDefaults[key]))
    else:
        return EricUtilities.toBool(
            Prefs.settings.value("VCS/" + key, Prefs.vcsDefaults[key])
        )


def setVCS(key, value):
    """
    Module function to store the VCS related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("VCS/" + key, value)


def getTasks(key):
    """
    Module function to retrieve the Tasks related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key in [
        "TasksFixmeColor",
        "TasksWarningColor",
        "TasksTodoColor",
        "TasksNoteColor",
        "TasksTestColor",
        "TasksDocuColor",
    ]:
        col = Prefs.settings.value("Tasks/" + key)
        if col is not None:
            return QColor(col)
        else:
            return Prefs.tasksDefaults[key]
    elif key in [
        "ClearOnFileClose",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value("Tasks/" + key, Prefs.tasksDefaults[key])
        )
    else:
        return Prefs.settings.value("Tasks/" + key, Prefs.tasksDefaults[key])


def setTasks(key, value):
    """
    Module function to store the Tasks related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in [
        "TasksFixmeColor",
        "TasksWarningColor",
        "TasksTodoColor",
        "TasksNoteColor",
        "TasksTestColor",
        "TasksDocuColor",
    ]:
        Prefs.settings.setValue("Tasks/" + key, value.name())
    else:
        Prefs.settings.setValue("Tasks/" + key, value)


def getTemplates(key):
    """
    Module function to retrieve the Templates related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key in ["SeparatorChar"]:
        return Prefs.settings.value("Templates/" + key, Prefs.templatesDefaults[key])
    elif key in ["EditorFont"]:
        f = QFont()
        f.fromString(
            Prefs.settings.value("Templates/" + key, Prefs.templatesDefaults[key])
        )
        return f
    else:
        return EricUtilities.toBool(
            Prefs.settings.value("Templates/" + key, Prefs.templatesDefaults[key])
        )


def setTemplates(key, value):
    """
    Module function to store the Templates related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in ["EditorFont"]:
        Prefs.settings.setValue("Templates/" + key, value.toString())
    else:
        Prefs.settings.setValue("Templates/" + key, value)


def getPluginManager(key):
    """
    Module function to retrieve the plugin manager related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key in ["DownloadPath"]:
        return Prefs.settings.value(
            "PluginManager/" + key, Prefs.pluginManagerDefaults[key]
        )
    elif key in ["UpdatesCheckInterval", "KeepGenerations"]:
        return int(
            Prefs.settings.value(
                "PluginManager/" + key, Prefs.pluginManagerDefaults[key]
            )
        )
    elif key in ["HiddenPlugins"]:
        return EricUtilities.toList(
            Prefs.settings.value(
                "PluginManager/" + key, Prefs.pluginManagerDefaults[key]
            )
        )
    else:
        return EricUtilities.toBool(
            Prefs.settings.value(
                "PluginManager/" + key, Prefs.pluginManagerDefaults[key]
            )
        )


def setPluginManager(key, value):
    """
    Module function to store the plugin manager related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("PluginManager/" + key, value)


def getGraphics(key):
    """
    Module function to retrieve the Graphics related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key in ["Font"]:
        font = Prefs.settings.value("Graphics/" + key, Prefs.graphicsDefaults[key])
        if isinstance(font, QFont):
            # workaround for an old bug in eric < 4.4
            return font
        else:
            f = QFont()
            f.fromString(font)
            return f
    else:
        return Prefs.settings.value("Graphics/" + key, Prefs.graphicsDefaults[key])


def setGraphics(key, value):
    """
    Module function to store the Graphics related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in ["Font"]:
        Prefs.settings.setValue("Graphics/" + key, value.toString())
    else:
        Prefs.settings.setValue("Graphics/" + key, value)


def getIconEditor(key):
    """
    Module function to retrieve the Icon Editor related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    return Prefs.settings.value("IconEditor/" + key, Prefs.iconEditorDefaults[key])


def setIconEditor(key, value):
    """
    Module function to store the Icon Editor related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("IconEditor/" + key, value)


def getFlakes(key):
    """
    Module function to retrieve the pyflakes related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key in ("IncludeInSyntaxCheck", "IgnoreStarImportWarnings"):
        return EricUtilities.toBool(
            Prefs.settings.value("Py3Flakes/" + key, Prefs.pyflakesDefaults[key])
        )
    elif key in ("AdditionalBuiltins",):
        return EricUtilities.toList(
            Prefs.settings.value("Py3Flakes/" + key, Prefs.pyflakesDefaults[key])
        )
    else:
        return Prefs.settings.value("Py3Flakes/" + key, Prefs.pyflakesDefaults[key])


def setFlakes(key, value):
    """
    Module function to store the pyflakes related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("Py3Flakes/" + key, value)


def getTrayStarter(key):
    """
    Module function to retrieve the tray starter related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    return Prefs.settings.value("TrayStarter/" + key, Prefs.trayStarterDefaults[key])


def setTrayStarter(key, value):
    """
    Module function to store the tray starter related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("TrayStarter/" + key, value)


def getIrc(key):
    """
    Module function to retrieve the IRC related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key in [
        "TimestampIncludeDate",
        "ShowTimestamps",
        "ShowNotifications",
        "NotifyJoinPart",
        "NotifyMessage",
        "NotifyNick",
        "EnableIrcColours",
        "AutoUserInfoLookup",
        "MarkPositionWhenHidden",
        "AskOnShutdown",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value("IRC/" + key, Prefs.ircDefaults[key])
        )
    elif key in ["AutoUserInfoMax", "AutoUserInfoInterval"]:
        return int(Prefs.settings.value("IRC/" + key, Prefs.ircDefaults[key]))
    else:
        return Prefs.settings.value("IRC/" + key, Prefs.ircDefaults[key])


def setIrc(key, value):
    """
    Module function to store the IRC related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("IRC/" + key, value)


def getHexEditor(key):
    """
    Module function to retrieve the Hex Editor related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key in ["AddressAreaWidth", "RecentNumber"]:
        return int(
            Prefs.settings.value("HexEditor/" + key, Prefs.hexEditorDefaults[key])
        )
    elif key in [
        "ShowAddressArea",
        "ShowAsciiArea",
        "OpenInOverwriteMode",
        "OpenReadOnly",
        "HighlightChanges",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value("HexEditor/" + key, Prefs.hexEditorDefaults[key])
        )
    elif key in ["Font"]:
        f = QFont()
        f.fromString(
            Prefs.settings.value("HexEditor/" + key, Prefs.hexEditorDefaults[key])
        )
        return f
    else:
        return Prefs.settings.value("HexEditor/" + key, Prefs.hexEditorDefaults[key])


def setHexEditor(key, value):
    """
    Module function to store the Hex Editor related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in ["Font"]:
        Prefs.settings.setValue("HexEditor/" + key, value.toString())
    else:
        Prefs.settings.setValue("HexEditor/" + key, value)


def getDiffColour(key):
    """
    Module function to retrieve the colours for the diff highlighter.

    @param key the key of the value to get
    @type str
    @return the requested diff colour
    @rtype QColor
    """
    col = Prefs.settings.value("Diff/" + key)
    if col is not None:
        if len(col) == 9:
            # color string with alpha
            return QColor.fromRgba(int(col[1:], 16))
        else:
            return QColor(col)
    else:
        return Prefs.diffColourDefaults[key]


def setDiffColour(key, value):
    """
    Module function to store the diff highlighter colours.

    @param key the key of the colour to be set
    @type str
    @param value the colour to be set
    @type QColor
    """
    val = "#{0:8x}".format(value.rgba()) if value.alpha() < 255 else value.name()
    Prefs.settings.setValue("Diff/" + key, val)


def getDocuViewer(key):
    """
    Module function to retrieve the Code Documentation Viewer related settings.

    @param key the key of the value to get
    @type str
    @return the requested Code Documentation Viewer value
    @rtype Any
    """
    if key in ["ShowInfoOnOpenParenthesis"]:
        return EricUtilities.toBool(
            Prefs.settings.value(
                "CodeDocumentationViewer/" + key, Prefs.docuViewerDefaults[key]
            )
        )
    else:
        return Prefs.settings.value(
            "CodeDocumentationViewer/" + key, Prefs.docuViewerDefaults[key]
        )


def setDocuViewer(key, value):
    """
    Module function to store the Code Documentation Viewer related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("CodeDocumentationViewer/" + key, value)


def getConda(key):
    """
    Module function to retrieve the conda related settings.

    @param key the key of the value to get
    @type str
    @return the requested conda value
    @rtype Any
    """
    return Prefs.settings.value("Conda/" + key, Prefs.condaDefaults[key])


def setConda(key, value):
    """
    Module function to store the conda related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("Conda/" + key, value)


def getPip(key):
    """
    Module function to retrieve the pip related settings.

    @param key the key of the value to get
    @type str
    @return the requested pip value
    @rtype Any
    """
    if key in (
        "ExcludeGlobalEnvironments",
        "ExcludeCondaEnvironments",
        "VulnerabilityCheckEnabled",
    ):
        return EricUtilities.toBool(
            Prefs.settings.value("Pip/" + key, Prefs.pipDefaults[key])
        )
    elif key in ("VulnerabilityDbCacheValidity",):
        return int(Prefs.settings.value("Pip/" + key, Prefs.pipDefaults[key]))
    else:
        return Prefs.settings.value("Pip/" + key, Prefs.pipDefaults[key])


def setPip(key, value):
    """
    Module function to store the pip related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("Pip/" + key, value)


def getMicroPython(key):
    """
    Module function to retrieve the MicroPython related settings.

    @param key the key of the value to get
    @type str
    @return the requested MicroPython value
    @rtype Any
    """
    if key in (
        "SerialTimeout",
        "WebreplTimeout",
        "ChartColorTheme",
        "WifiApAuthMode",
        "NtpOffset",
        "NtpTimeout",
    ):
        return int(
            Prefs.settings.value("MicroPython/" + key, Prefs.microPythonDefaults[key])
        )
    elif key in [
        "ReplLineWrap",
        "SyncTimeAfterConnect",
        "ShowHiddenLocal",
        "ShowHiddenDevice",
        "EnableManualDeviceSelection",
        "NtpDaylight",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value("MicroPython/" + key, Prefs.microPythonDefaults[key])
        )
    elif key in (
        "IgnoredUnknownDevices",
        "ManualDevices",
        "WebreplUrls",
        "MPyWindowSplitterSizes",
    ):
        jsonStr = Prefs.settings.value(
            "MicroPython/" + key, Prefs.microPythonDefaults[key]
        )
        if jsonStr:
            return json.loads(jsonStr)
        else:
            return None
    elif key in ("WifiPassword", "WifiApPassword"):
        return pwConvert(
            Prefs.settings.value("MicroPython/" + key, Prefs.microPythonDefaults[key]),
            encode=False,
        )
    else:
        return Prefs.settings.value(
            "MicroPython/" + key, Prefs.microPythonDefaults[key]
        )


def setMicroPython(key, value):
    """
    Module function to store the MicroPython settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in (
        "IgnoredUnknownDevices",
        "ManualDevices",
        "WebreplUrls",
        "MPyWindowSplitterSizes",
    ):
        Prefs.settings.setValue("MicroPython/" + key, json.dumps(value))
    elif key in ("WifiPassword", "WifiApPassword"):
        Prefs.settings.setValue("MicroPython/" + key, pwConvert(value, encode=True))
    else:
        Prefs.settings.setValue("MicroPython/" + key, value)


def getJedi(key):
    """
    Function to retrieve the Jedi Assistant related settings.

    @param key the key of the value to get
    @type str
    @return the requested jedi assistant setting
    @rtype Any
    """
    if key in [
        "JediCompletionsEnabled",
        "JediFuzzyCompletionsEnabled",
        "JediCalltipsEnabled",
        "MouseClickEnabled",
    ]:
        return EricUtilities.toBool(
            Prefs.settings.value("AssistantJedi/" + key, Prefs.jediDefaults[key])
        )
    else:
        return Prefs.settings.value("AssistantJedi/" + key, Prefs.jediDefaults[key])


def setJedi(key, value):
    """
    Public method to store the various refactoring settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    Prefs.settings.setValue("AssistantJedi/" + key, value)


def getPdfViewer(key):
    """
    Module function to retrieve the PDF Viewer related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    if key in ("RecentNumber", "PdfSearchContextLength"):
        return int(
            Prefs.settings.value("PdfViewer/" + key, Prefs.pdfViewerDefaults[key])
        )
    elif key in (
        "PdfViewerSidebarVisible",
        "PdfViewerOpenRecentInNewWindow",
        "PdfSearchHighlightAll",
    ):
        return EricUtilities.toBool(
            Prefs.settings.value("PdfViewer/" + key, Prefs.pdfViewerDefaults[key])
        )
    elif key in ("PdfViewerZoomFactor",):
        return float(
            Prefs.settings.value("PdfViewer/" + key, Prefs.pdfViewerDefaults[key])
        )
    elif key == "PdfViewerZoomMode":
        return QPdfView.ZoomMode(
            int(Prefs.settings.value("PdfViewer/" + key, Prefs.pdfViewerDefaults[key]))
        )
    else:
        return Prefs.settings.value("PdfViewer/" + key, Prefs.pdfViewerDefaults[key])


def setPdfViewer(key, value):
    """
    Module function to store the PDF Viewer related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key == "PdfViewerZoomMode":
        value = value.value
    Prefs.settings.setValue("PdfViewer/" + key, value)


def getEricServer(key):
    """
    Module function to retrieve the eric-ide server interface related settings.

    @param key the key of the value to get
    @type str
    @return the requested user setting
    @rtype Any
    """
    prefix = "EricServer/"

    if key in ("ConnectionTimeout",):
        return int(
            Prefs.settings.value(f"{prefix}{key}", Prefs.ericServerDefaults[key])
        )
    elif key in ("AutostartShell",):
        return EricUtilities.toBool(
            Prefs.settings.value(f"{prefix}{key}", Prefs.ericServerDefaults[key])
        )
    elif key in ("ConnectionProfiles",):
        jsonStr = Prefs.settings.value(f"{prefix}{key}", Prefs.ericServerDefaults[key])
        if jsonStr:
            return json.loads(jsonStr)
        else:
            return None
    else:
        return Prefs.settings.value(f"{prefix}{key}", Prefs.ericServerDefaults[key])


def setEricServer(key, value):
    """
    Module function to store the eric-ide server interface related settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    prefix = "EricServer/"

    if key in ("ConnectionProfiles",):
        Prefs.settings.setValue(f"{prefix}{key}", json.dumps(value))
    else:
        Prefs.settings.setValue(f"{prefix}{key}", value)


def getGeometry(key):
    """
    Module function to retrieve the display geometry.

    @param key the key of the value to get
    @type str
    @return the requested geometry setting
    @rtype Any
    """
    if key in ["MainMaximized"]:
        return EricUtilities.toBool(
            Prefs.settings.value("Geometry/" + key, Prefs.geometryDefaults[key])
        )
    else:
        v = Prefs.settings.value("Geometry/" + key)
        if v is not None:
            return v
        else:
            return Prefs.geometryDefaults[key]


def setGeometry(key, value):
    """
    Module function to store the display geometry.

    @param key the key of the setting to be set
    @type str
    @param value the geometry to be set
    @type Any
    """
    if key in ["MainMaximized"]:
        Prefs.settings.setValue("Geometry/" + key, value)
    else:
        if Prefs.resetLayout:
            v = Prefs.geometryDefaults[key]
        else:
            v = value
        Prefs.settings.setValue("Geometry/" + key, v)


def resetLayout():
    """
    Module function to set a flag not storing the current layout.
    """
    Prefs.resetLayout = True


def shouldResetLayout():
    """
    Module function to indicate a reset of the layout.

    @return flag indicating a reset of the layout
    @rtype bool
    """
    return Prefs.resetLayout


def saveResetLayout():
    """
    Module function to save the reset layout.
    """
    if Prefs.resetLayout:
        for key in Prefs.geometryDefaults:
            Prefs.settings.setValue("Geometry/" + key, Prefs.geometryDefaults[key])


def convertPasswords(oldPassword, newPassword):
    """
    Module function to convert all passwords.

    @param oldPassword current password
    @type str
    @param newPassword new password
    @type str
    """
    from eric7.EricUtilities.crypto import pwRecode

    for key in ["MailServerPassword"]:
        Prefs.settings.setValue(
            "User/" + key,
            pwRecode(
                Prefs.settings.value("User/" + key, Prefs.userDefaults[key]),
                oldPassword,
                newPassword,
            ),
        )
    for key in ["SyncFtpPassword", "SyncEncryptionKey"]:
        Prefs.settings.setValue(
            "WebBrowser/" + key,
            pwRecode(
                Prefs.settings.value(
                    "WebBrowser/" + key, Prefs.webBrowserDefaults[key]
                ),
                oldPassword,
                newPassword,
            ),
        )

    EricPreferences.convertPasswords(oldPassword, newPassword)


initPreferences(withMigration=True)
initRecentSettings()
EricPreferences.initPreferences()

#
# eflag: noqa = M201, M613
