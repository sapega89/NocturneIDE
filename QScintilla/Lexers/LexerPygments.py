# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a custom lexer using pygments.
"""

import contextlib

from pygments.lexers import find_lexer_class, guess_lexer, guess_lexer_for_filename
from pygments.token import Token
from pygments.util import ClassNotFound
from PyQt6.QtGui import QColor, QFont

from eric7.QScintilla.Lexers.LexerContainer import LexerContainer
from eric7.SystemUtilities import OSUtilities

PYGMENTS_DEFAULT = 0
PYGMENTS_COMMENT = 1
PYGMENTS_PREPROCESSOR = 2
PYGMENTS_KEYWORD = 3
PYGMENTS_PSEUDOKEYWORD = 4
PYGMENTS_TYPEKEYWORD = 5
PYGMENTS_OPERATOR = 6
PYGMENTS_WORD = 7
PYGMENTS_BUILTIN = 8
PYGMENTS_FUNCTION = 9
PYGMENTS_CLASS = 10
PYGMENTS_NAMESPACE = 11
PYGMENTS_EXCEPTION = 12
PYGMENTS_VARIABLE = 13
PYGMENTS_CONSTANT = 14
PYGMENTS_LABEL = 15
PYGMENTS_ENTITY = 16
PYGMENTS_ATTRIBUTE = 17
PYGMENTS_TAG = 18
PYGMENTS_DECORATOR = 19
PYGMENTS_STRING = 20
PYGMENTS_DOCSTRING = 21
PYGMENTS_SCALAR = 22
PYGMENTS_ESCAPE = 23
PYGMENTS_REGEX = 24
PYGMENTS_SYMBOL = 25
PYGMENTS_OTHER = 26
PYGMENTS_NUMBER = 27
PYGMENTS_HEADING = 28
PYGMENTS_SUBHEADING = 29
PYGMENTS_DELETED = 30
PYGMENTS_INSERTED = 31
# 32 to 39 are reserved for QScintilla internal styles
PYGMENTS_GENERIC_ERROR = 40
PYGMENTS_EMPHASIZE = 41
PYGMENTS_STRONG = 42
PYGMENTS_PROMPT = 43
PYGMENTS_OUTPUT = 44
PYGMENTS_TRACEBACK = 45
PYGMENTS_ERROR = 46
PYGMENTS_MULTILINECOMMENT = 47
PYGMENTS_PROPERTY = 48
PYGMENTS_CHAR = 49
PYGMENTS_HEREDOC = 50
PYGMENTS_PUNCTUATION = 51
# added with Pygments 2.1
PYGMENTS_HASHBANG = 52
PYGMENTS_RESERVEDKEYWORD = 53
PYGMENTS_LITERAL = 54
PYGMENTS_DOUBLESTRING = 55
PYGMENTS_SINGLESTRING = 56
PYGMENTS_BACKTICKSTRING = 57
PYGMENTS_WHITESPACE = 58

# -----------------------------------------------------------------------------#

TOKEN_MAP = {
    Token.Comment: PYGMENTS_COMMENT,
    Token.Comment.Hashbang: PYGMENTS_HASHBANG,
    Token.Comment.Multiline: PYGMENTS_MULTILINECOMMENT,
    Token.Comment.Preproc: PYGMENTS_PREPROCESSOR,
    Token.Comment.PreprocFile: PYGMENTS_PREPROCESSOR,
    Token.Comment.Single: PYGMENTS_COMMENT,
    Token.Comment.Special: PYGMENTS_COMMENT,
    Token.Escape: PYGMENTS_ESCAPE,
    Token.Error: PYGMENTS_ERROR,
    Token.Generic: PYGMENTS_DEFAULT,
    Token.Generic.Deleted: PYGMENTS_DELETED,
    Token.Generic.Emph: PYGMENTS_EMPHASIZE,
    Token.Generic.Error: PYGMENTS_GENERIC_ERROR,
    Token.Generic.Heading: PYGMENTS_HEADING,
    Token.Generic.Inserted: PYGMENTS_INSERTED,
    Token.Generic.Output: PYGMENTS_OUTPUT,
    Token.Generic.Prompt: PYGMENTS_PROMPT,
    Token.Generic.Strong: PYGMENTS_STRONG,
    Token.Generic.Subheading: PYGMENTS_SUBHEADING,
    Token.Generic.Traceback: PYGMENTS_TRACEBACK,
    Token.Keyword: PYGMENTS_KEYWORD,
    Token.Keyword.Constant: PYGMENTS_KEYWORD,
    Token.Keyword.Declaration: PYGMENTS_KEYWORD,
    Token.Keyword.Namespace: PYGMENTS_KEYWORD,
    Token.Keyword.Pseudo: PYGMENTS_PSEUDOKEYWORD,
    Token.Keyword.Reserved: PYGMENTS_RESERVEDKEYWORD,
    Token.Keyword.Type: PYGMENTS_TYPEKEYWORD,
    Token.Literal: PYGMENTS_LITERAL,
    Token.Literal.Date: PYGMENTS_LITERAL,
    Token.Name: PYGMENTS_DEFAULT,
    Token.Name.Attribute: PYGMENTS_ATTRIBUTE,
    Token.Name.Builtin: PYGMENTS_BUILTIN,
    Token.Name.Builtin.Pseudo: PYGMENTS_BUILTIN,
    Token.Name.Class: PYGMENTS_CLASS,
    Token.Name.Constant: PYGMENTS_CONSTANT,
    Token.Name.Decorator: PYGMENTS_DECORATOR,
    Token.Name.Entity: PYGMENTS_ENTITY,
    Token.Name.Exception: PYGMENTS_EXCEPTION,
    Token.Name.Function: PYGMENTS_FUNCTION,
    Token.Name.Function.Magic: PYGMENTS_FUNCTION,
    Token.Name.Label: PYGMENTS_LABEL,
    Token.Name.Namespace: PYGMENTS_NAMESPACE,
    Token.Name.Other: PYGMENTS_VARIABLE,
    Token.Name.Property: PYGMENTS_PROPERTY,
    Token.Name.Tag: PYGMENTS_TAG,
    Token.Name.Variable: PYGMENTS_VARIABLE,
    Token.Name.Variable.Class: PYGMENTS_VARIABLE,
    Token.Name.Variable.Global: PYGMENTS_VARIABLE,
    Token.Name.Variable.Instance: PYGMENTS_VARIABLE,
    Token.Name.Variable.Magic: PYGMENTS_VARIABLE,
    Token.Number: PYGMENTS_NUMBER,
    Token.Number.Bin: PYGMENTS_NUMBER,
    Token.Number.Float: PYGMENTS_NUMBER,
    Token.Number.Hex: PYGMENTS_NUMBER,
    Token.Number.Integer: PYGMENTS_NUMBER,
    Token.Number.Integer.Long: PYGMENTS_NUMBER,
    Token.Number.Oct: PYGMENTS_NUMBER,
    Token.Operator: PYGMENTS_OPERATOR,
    Token.Operator.Word: PYGMENTS_WORD,
    Token.Other: PYGMENTS_DEFAULT,
    Token.Punctuation: PYGMENTS_PUNCTUATION,
    Token.String: PYGMENTS_STRING,
    Token.String.Affix: PYGMENTS_STRING,
    Token.String.Backtick: PYGMENTS_BACKTICKSTRING,
    Token.String.Char: PYGMENTS_CHAR,
    Token.String.Delimiter: PYGMENTS_STRING,
    Token.String.Doc: PYGMENTS_DOCSTRING,
    Token.String.Double: PYGMENTS_DOUBLESTRING,
    Token.String.Escape: PYGMENTS_ESCAPE,
    Token.String.Heredoc: PYGMENTS_HEREDOC,
    Token.String.Interpol: PYGMENTS_SCALAR,
    Token.String.Other: PYGMENTS_OTHER,
    Token.String.Regex: PYGMENTS_REGEX,
    Token.String.Single: PYGMENTS_SINGLESTRING,
    Token.String.Symbol: PYGMENTS_SYMBOL,
    Token.Whitespace: PYGMENTS_WHITESPACE,
    Token.Text: PYGMENTS_DEFAULT,
}

# -----------------------------------------------------------------------------#


class LexerPygments(LexerContainer):
    """
    Class implementing a custom lexer using pygments.
    """

    def __init__(self, parent=None, name=""):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        @param name name of the pygments lexer to use
        @type str
        """
        super().__init__(parent)

        self.__inReadSettings = False

        if name.startswith("Pygments|"):
            self.__forcedPygmentsName = True
            self.__pygmentsName = name.replace("Pygments|", "")
        elif name:
            self.__pygmentsName = name
            self.__forcedPygmentsName = True
        else:
            self.__pygmentsName = ""
            self.__forcedPygmentsName = False

        self.descriptions = {
            PYGMENTS_DEFAULT: self.tr("Default"),
            PYGMENTS_COMMENT: self.tr("Comment"),
            PYGMENTS_PREPROCESSOR: self.tr("Preprocessor"),
            PYGMENTS_KEYWORD: self.tr("Keyword"),
            PYGMENTS_PSEUDOKEYWORD: self.tr("Pseudo Keyword"),
            PYGMENTS_TYPEKEYWORD: self.tr("Type Keyword"),
            PYGMENTS_OPERATOR: self.tr("Operator"),
            PYGMENTS_WORD: self.tr("Word"),
            PYGMENTS_BUILTIN: self.tr("Builtin"),
            PYGMENTS_FUNCTION: self.tr("Function or method name"),
            PYGMENTS_CLASS: self.tr("Class name"),
            PYGMENTS_NAMESPACE: self.tr("Namespace"),
            PYGMENTS_EXCEPTION: self.tr("Exception"),
            PYGMENTS_VARIABLE: self.tr("Identifier"),
            PYGMENTS_CONSTANT: self.tr("Constant"),
            PYGMENTS_LABEL: self.tr("Label"),
            PYGMENTS_ENTITY: self.tr("Entity"),
            PYGMENTS_ATTRIBUTE: self.tr("Attribute"),
            PYGMENTS_TAG: self.tr("Tag"),
            PYGMENTS_DECORATOR: self.tr("Decorator"),
            PYGMENTS_STRING: self.tr("String"),
            PYGMENTS_DOCSTRING: self.tr("Documentation string"),
            PYGMENTS_SCALAR: self.tr("Scalar"),
            PYGMENTS_ESCAPE: self.tr("Escape"),
            PYGMENTS_REGEX: self.tr("Regular expression"),
            PYGMENTS_SYMBOL: self.tr("Symbol"),
            PYGMENTS_OTHER: self.tr("Other string"),
            PYGMENTS_NUMBER: self.tr("Number"),
            PYGMENTS_HEADING: self.tr("Heading"),
            PYGMENTS_SUBHEADING: self.tr("Subheading"),
            PYGMENTS_DELETED: self.tr("Deleted"),
            PYGMENTS_INSERTED: self.tr("Inserted"),
            PYGMENTS_GENERIC_ERROR: self.tr("Generic error"),
            PYGMENTS_EMPHASIZE: self.tr("Emphasized text"),
            PYGMENTS_STRONG: self.tr("Strong text"),
            PYGMENTS_PROMPT: self.tr("Prompt"),
            PYGMENTS_OUTPUT: self.tr("Output"),
            PYGMENTS_TRACEBACK: self.tr("Traceback"),
            PYGMENTS_ERROR: self.tr("Error"),
            PYGMENTS_MULTILINECOMMENT: self.tr("Comment block"),
            PYGMENTS_PROPERTY: self.tr("Property"),
            PYGMENTS_CHAR: self.tr("Character"),
            PYGMENTS_HEREDOC: self.tr("Here document"),
            PYGMENTS_PUNCTUATION: self.tr("Punctuation"),
            PYGMENTS_HASHBANG: self.tr("Hashbang"),
            PYGMENTS_RESERVEDKEYWORD: self.tr("Reserved Keyword"),
            PYGMENTS_LITERAL: self.tr("Literal"),
            PYGMENTS_DOUBLESTRING: self.tr("Double quoted string"),
            PYGMENTS_SINGLESTRING: self.tr("Single quoted string"),
            PYGMENTS_BACKTICKSTRING: self.tr("Backtick string"),
            PYGMENTS_WHITESPACE: self.tr("Whitespace"),
        }

        self.defaultColors = {
            PYGMENTS_DEFAULT: QColor("#000000"),
            PYGMENTS_COMMENT: QColor("#408080"),
            PYGMENTS_PREPROCESSOR: QColor("#BC7A00"),
            PYGMENTS_KEYWORD: QColor("#008000"),
            PYGMENTS_PSEUDOKEYWORD: QColor("#008000"),
            PYGMENTS_TYPEKEYWORD: QColor("#B00040"),
            PYGMENTS_OPERATOR: QColor("#666666"),
            PYGMENTS_WORD: QColor("#AA22FF"),
            PYGMENTS_BUILTIN: QColor("#008000"),
            PYGMENTS_FUNCTION: QColor("#0000FF"),
            PYGMENTS_CLASS: QColor("#0000FF"),
            PYGMENTS_NAMESPACE: QColor("#0000FF"),
            PYGMENTS_EXCEPTION: QColor("#D2413A"),
            PYGMENTS_VARIABLE: QColor("#19177C"),
            PYGMENTS_CONSTANT: QColor("#880000"),
            PYGMENTS_LABEL: QColor("#A0A000"),
            PYGMENTS_ENTITY: QColor("#999999"),
            PYGMENTS_ATTRIBUTE: QColor("#7D9029"),
            PYGMENTS_TAG: QColor("#008000"),
            PYGMENTS_DECORATOR: QColor("#AA22FF"),
            PYGMENTS_STRING: QColor("#BA2121"),
            PYGMENTS_DOCSTRING: QColor("#BA2121"),
            PYGMENTS_SCALAR: QColor("#BB6688"),
            PYGMENTS_ESCAPE: QColor("#BB6622"),
            PYGMENTS_REGEX: QColor("#BB6688"),
            PYGMENTS_SYMBOL: QColor("#19177C"),
            PYGMENTS_OTHER: QColor("#008000"),
            PYGMENTS_NUMBER: QColor("#666666"),
            PYGMENTS_HEADING: QColor("#000080"),
            PYGMENTS_SUBHEADING: QColor("#800080"),
            PYGMENTS_DELETED: QColor("#A00000"),
            PYGMENTS_INSERTED: QColor("#00A000"),
            PYGMENTS_GENERIC_ERROR: QColor("#FF0000"),
            PYGMENTS_PROMPT: QColor("#000080"),
            PYGMENTS_OUTPUT: QColor("#808080"),
            PYGMENTS_TRACEBACK: QColor("#0040D0"),
            PYGMENTS_MULTILINECOMMENT: QColor("#007F00"),
            PYGMENTS_PROPERTY: QColor("#00A0E0"),
            PYGMENTS_CHAR: QColor("#7F007F"),
            PYGMENTS_HEREDOC: QColor("#7F007F"),
            PYGMENTS_PUNCTUATION: QColor("#000000"),
            PYGMENTS_HASHBANG: QColor("#00C000"),
            PYGMENTS_RESERVEDKEYWORD: QColor("#A90D91"),
            PYGMENTS_LITERAL: QColor("#1C01CE"),
            PYGMENTS_DOUBLESTRING: QColor("#7F007F"),
            PYGMENTS_SINGLESTRING: QColor("#7F007F"),
            PYGMENTS_BACKTICKSTRING: QColor("#FFFF00"),
            PYGMENTS_WHITESPACE: QColor("#BBBBBB"),
        }

        self.defaultPapers = {
            PYGMENTS_ERROR: QColor("#FF0000"),
            PYGMENTS_MULTILINECOMMENT: QColor("#A8FFA8"),
            PYGMENTS_HEREDOC: QColor("#DDD0DD"),
            PYGMENTS_BACKTICKSTRING: QColor("#a08080"),
        }

        self.defaultEolFills = {
            PYGMENTS_ERROR: True,
            PYGMENTS_MULTILINECOMMENT: True,
            PYGMENTS_HEREDOC: True,
            PYGMENTS_BACKTICKSTRING: True,
        }

        self.__commentString = {
            "Bash": "#",
            "Batchfile": "REM ",
            "C": "//",
            "C++": "//",
            "C#": "//",
            "CMake": "#",
            "CoffeScript": "#",
            "CSS": "#",
            "D": "//",
            "Fortran": "c ",
            "Gettext Catalog": "#",
            "Groovy": "//",
            "IDL": "//",
            "INI": "#",
            "Java": "//",
            "JavaScript": "//",
            "JSON": "//",
            "Lua": "--",
            "Makefile": "#",
            "Matlab": "%~",
            "Octave": "#",
            "Perl": "#",
            "PostScript": "%",
            "POVRay": "//",
            "Properties": "#",
            "Python": "#",
            "RPMSpec": "#",
            "Ruby": "#",
            "SQL": "--",
            "Tcl": "#",
            "TeX": "%",
            "TOML": "#",
            "YAML": "#",
        }

        self.__streamCommentString = {
            "CoffeScript": {"start": "###\n", "end": "\n###"},
            "C": {"start": "/* ", "end": " */"},
            "C++": {"start": "/* ", "end": " */"},
            "C#": {"start": "/* ", "end": " */"},
            "CSS": {"start": "/* ", "end": " */"},
            "D": {"start": "/+ ", "end": " +/"},
            "Groovy": {"start": "/* ", "end": " */"},
            "HTML": {"start": "<!-- ", "end": " -->"},
            "IDL": {"start": "/* ", "end": " */"},
            "Java": {"start": "/* ", "end": " */"},
            "JavaScript": {"start": "/* ", "end": " */"},
            "JSON": {"start": "/* ", "end": " */"},
            "Lua": {"start": "--[[ ", "end": " ]]--"},
            "POVRay": {"start": "/* ", "end": " */"},
            "XML": {"start": "<!-- ", "end": " -->"},
        }

        self.__boxCommentString = {
            "C": {"start": "/* ", "middle": " * ", "end": " */"},
            "C++": {"start": "/* ", "middle": " * ", "end": " */"},
            "C#": {"start": "/* ", "middle": " * ", "end": " */"},
            "D": {"start": "/* ", "middle": " * ", "end": " */"},
            "Groovy": {"start": "/* ", "middle": " * ", "end": " */"},
            "IDL": {"start": "/* ", "middle": " * ", "end": " */"},
            "Java": {"start": "/* ", "middle": " * ", "end": " */"},
            "JavaScript": {"start": "/* ", "middle": " * ", "end": " */"},
            "POVRay": {"start": "/* ", "middle": " * ", "end": " */"},
        }

    def readSettings(self, qs, prefix="/Scintilla"):
        """
        Public method to read the lexer settings.

        Note: Overridden to treat the Pygments lexer specially.

        @param qs reference to the settings object
        @type QSettings
        @param prefix prefix for the settings key (defaults to "/Scintilla")
        @type str (optional)
        """
        self.__inReadSettings = True
        super().readSettings(qs, prefix=prefix)
        self.__inReadSettings = False

    def language(self):
        """
        Public method returning the language of the lexer.

        @return language of the lexer
        @rtype str
        """
        if self.__pygmentsName and not self.__inReadSettings:
            return self.__pygmentsName
        else:
            return "Guessed"

    def description(self, style):
        """
        Public method returning the descriptions of the styles supported
        by the lexer.

        @param style style number
        @type int
        @return description for the style
        @rtype str
        """
        try:
            return self.descriptions[style]
        except KeyError:
            return ""

    def defaultColor(self, style):
        """
        Public method to get the default foreground color for a style.

        @param style style number
        @type int
        @return foreground color
        @rtype QColor
        """
        try:
            return self.defaultColors[style]
        except KeyError:
            return LexerContainer.defaultColor(self, style)

    def defaultPaper(self, style):
        """
        Public method to get the default background color for a style.

        @param style style number
        @type int
        @return background color
        @rtype QColor
        """
        try:
            return self.defaultPapers[style]
        except KeyError:
            return LexerContainer.defaultPaper(self, style)

    def defaultFont(self, style):
        """
        Public method to get the default font for a style.

        @param style style number
        @type int
        @return font
        @rtype QFont
        """
        if style in [
            PYGMENTS_COMMENT,
            PYGMENTS_PREPROCESSOR,
            PYGMENTS_MULTILINECOMMENT,
        ]:
            if OSUtilities.isWindowsPlatform():
                f = QFont(["Comic Sans MS"], 9)
            elif OSUtilities.isMacPlatform():
                f = QFont(["Courier"], 11)
            else:
                f = QFont(["Bitstream Vera Serif"], 9)
            if style == PYGMENTS_PREPROCESSOR:
                f.setItalic(True)
            return f

        if style in [PYGMENTS_STRING, PYGMENTS_CHAR]:
            if OSUtilities.isWindowsPlatform():
                return QFont(["Comic Sans MS"], 10)
            elif OSUtilities.isMacPlatform():
                f = QFont(["Courier"], 11)
            else:
                return QFont(["Bitstream Vera Serif"], 10)

        if style in [
            PYGMENTS_KEYWORD,
            PYGMENTS_OPERATOR,
            PYGMENTS_WORD,
            PYGMENTS_BUILTIN,
            PYGMENTS_ATTRIBUTE,
            PYGMENTS_FUNCTION,
            PYGMENTS_CLASS,
            PYGMENTS_NAMESPACE,
            PYGMENTS_EXCEPTION,
            PYGMENTS_ENTITY,
            PYGMENTS_TAG,
            PYGMENTS_SCALAR,
            PYGMENTS_ESCAPE,
            PYGMENTS_HEADING,
            PYGMENTS_SUBHEADING,
            PYGMENTS_STRONG,
            PYGMENTS_PROMPT,
        ]:
            f = LexerContainer.defaultFont(self, style)
            f.setBold(True)
            return f

        if style in [PYGMENTS_DOCSTRING, PYGMENTS_EMPHASIZE]:
            f = LexerContainer.defaultFont(self, style)
            f.setItalic(True)
            return f

        return LexerContainer.defaultFont(self, style)

    def defaultEolFill(self, style):
        """
        Public method to get the default fill to eol flag.

        @param style style number
        @type int
        @return fill to eol flag
        @rtype bool
        """
        try:
            return self.defaultEolFills[style]
        except KeyError:
            return LexerContainer.defaultEolFill(self, style)

    def __guessLexer(self, text):
        """
        Private method to guess a pygments lexer.

        @param text text to base guessing on
        @type str
        @return reference to the guessed lexer
        @rtype pygments.lexer
        """
        lexer = None

        if self.__pygmentsName:
            lexerClass = find_lexer_class(self.__pygmentsName)
            if lexerClass is not None:
                lexer = lexerClass()

        elif text:
            # step 1: guess based on filename and text
            if self.editor is not None:
                fn = self.editor.getFileName()
                if fn:
                    with contextlib.suppress(ClassNotFound, AttributeError):
                        lexer = guess_lexer_for_filename(fn, text)

            # step 2: guess on text only
            if lexer is None:
                with contextlib.suppress(ClassNotFound, AttributeError):
                    lexer = guess_lexer(text)

        return lexer

    def canStyle(self):
        """
        Public method to check, if the lexer is able to style the text.

        @return flag indicating the lexer capability
        @rtype bool
        """
        if self.editor is None:
            return True

        text = self.editor.text()
        self.__lexer = self.__guessLexer(text)

        return self.__lexer is not None

    def name(self):
        """
        Public method to get the name of the pygments lexer.

        @return name of the pygments lexer
        @rtype str
        """
        if self.__lexer is None:
            return ""
        else:
            return self.__lexer.name

    def styleText(self, _start, end):
        """
        Public method to perform the styling.

        @param _start position of first character to be styled (unused)
        @type int
        @param end position of last character to be styled
        @type int
        """
        text = self.editor.text()[: end + 1]
        textLen = len(text.encode("utf-8"))
        self.__lexer = self.__guessLexer(text)

        cpos = 0
        # adjust start position because pygments ignores empty line at
        # start of text
        for c in text:
            if c == "\n":
                cpos += 1
            else:
                break

        self.editor.startStyling(cpos, 0x3F)
        if self.__lexer is None:
            self.editor.setStyling(len(text), PYGMENTS_DEFAULT)
        else:
            eolLen = len(self.editor.getLineSeparator())
            for token, txt in self.__lexer.get_tokens(text):
                style = TOKEN_MAP.get(token, PYGMENTS_DEFAULT)

                tlen = len(txt.encode("utf-8"))
                if eolLen > 1:
                    tlen += txt.count("\n")
                cpos += tlen
                if tlen and cpos < textLen:
                    self.editor.setStyling(tlen, style)
                if cpos >= textLen:
                    break
            self.editor.startStyling(cpos, 0x3F)

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [PYGMENTS_COMMENT]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [
            PYGMENTS_STRING,
            PYGMENTS_DOCSTRING,
            PYGMENTS_OTHER,
            PYGMENTS_HEADING,
            PYGMENTS_SUBHEADING,
            PYGMENTS_EMPHASIZE,
            PYGMENTS_STRONG,
        ]

    def defaultKeywords(self, _kwSet):
        """
        Public method to get the default keywords.

        @param _kwSet number of the keyword set (unused)
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return None  # __IGNORE_WARNING_M831__

    def commentStr(self):
        """
        Public method to return the comment string.

        @return comment string
        @rtype str
        """
        try:
            return self.__commentString[self.name()]
        except KeyError:
            return ""

    def canBlockComment(self):
        """
        Public method to determine, whether the lexer language supports a
        block comment.

        @return flag indicating block comment is available
        @rtype bool
        """
        return self.name() in self.__commentString

    def streamCommentStr(self):
        """
        Public method to return the stream comment strings.

        @return dictionary containing the start and end stream comment strings
        @rtype dict of {"start": str, "end": str}
        """
        try:
            return self.__streamCommentString[self.name()]
        except KeyError:
            return {"start": "", "end": ""}

    def canStreamComment(self):
        """
        Public method to determine, whether the lexer language supports a
        stream comment.

        @return flag indicating stream comment is available
        @rtype bool
        """
        return self.name() in self.__streamCommentString

    def boxCommentStr(self):
        """
        Public method to return the box comment strings.

        @return dictionary containing the start, middle and end box comment strings
        @rtype dict of {"start": str, "middle": str, "end": str}
        """
        try:
            return self.__boxCommentString[self.name()]
        except KeyError:
            return {"start": "", "middle": "", "end": ""}

    def canBoxComment(self):
        """
        Public method to determine, whether the lexer language supports a
        box comment.

        @return flag box comment is available
        @rtype bool
        """
        return self.name() in self.__boxCommentString
