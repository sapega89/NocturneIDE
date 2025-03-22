# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing various functions/classes needed everywhere within eric.
"""

import codecs
import contextlib
import glob
import importlib.util
import json
import os
import re
import shlex
import sys
import warnings

import chardet

from PyQt6 import sip
from PyQt6.Qsci import QSCINTILLA_VERSION_STR, QsciScintilla
from PyQt6.QtCore import (
    PYQT_VERSION_STR,
    QByteArray,
    QCoreApplication,
    QCryptographicHash,
    QProcess,
    qVersion,
)

from eric7 import Preferences
from eric7.__version__ import Version
from eric7.EricUtilities import (  # noqa
    decodeBytes,
    decodeString,
    html_encode,
    html_udecode,
    html_uencode,
    readStringFromStream,
)
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import DesktopUtilities, FileSystemUtilities, OSUtilities
from eric7.UI.Info import Program


def __showwarning(
    message, category, filename, lineno, file=None, line=None  # noqa: U100
):
    """
    Module function to raise a SyntaxError for a SyntaxWarning.

    @param message warning object
    @type Class
    @param category type object of the warning
    @type SyntaxWarning
    @param filename name of the file causing the warning
    @type str
    @param lineno line number causing the warning
    @type int
    @param file file to write the warning message to (unused)
    @type file
    @param line line causing the warning (unused)
    @type int
    @exception err exception of type SyntaxError
    """
    if category is SyntaxWarning:
        err = SyntaxError(str(message))
        err.filename = filename
        err.lineno = lineno
        raise err


warnings.showwarning = __showwarning

codingBytes_regexps = [
    (5, re.compile(rb"""coding[:=]\s*([-\w_.]+)""")),
    (1, re.compile(rb"""<\?xml.*\bencoding\s*=\s*['"]([-\w_.]+)['"]\?>""")),
]
coding_regexps = [
    (5, re.compile(r"""coding[:=]\s*([-\w_.]+)""")),
    (1, re.compile(r"""<\?xml.*\bencoding\s*=\s*['"]([-\w_.]+)['"]\?>""")),
]

supportedCodecs = [  # noqa: U200
    "utf-8",
    "iso-8859-1",
    "iso-8859-2",
    "iso-8859-3",
    "iso-8859-4",
    "iso-8859-5",
    "iso-8859-6",
    "iso-8859-7",
    "iso-8859-8",
    "iso-8859-9",
    "iso-8859-10",
    "iso-8859-11",
    "iso-8859-13",
    "iso-8859-14",
    "iso-8859-15",
    "iso-8859-16",
    "latin-1",
    "koi8-r",
    "koi8-t",
    "koi8-u",
    "utf-7",
    "utf-16",
    "utf-16-be",
    "utf-16-le",
    "utf-32",
    "utf-32-be",
    "utf-32-le",
    "cp037",
    "cp273",
    "cp424",
    "cp437",
    "cp500",
    "cp720",
    "cp737",
    "cp775",
    "cp850",
    "cp852",
    "cp855",
    "cp856",
    "cp857",
    "cp858",
    "cp860",
    "cp861",
    "cp862",
    "cp863",
    "cp864",
    "cp865",
    "cp866",
    "cp869",
    "cp874",
    "cp875",
    "cp932",
    "cp949",
    "cp950",
    "cp1006",
    "cp1026",
    "cp1125",
    "cp1140",
    "windows-1250",
    "windows-1251",
    "windows-1252",
    "windows-1253",
    "windows-1254",
    "windows-1255",
    "windows-1256",
    "windows-1257",
    "windows-1258",
    "gb2312",
    "hz",
    "gb18030",
    "gbk",
    "iso-2022-jp",
    "iso-2022-jp-1",
    "iso-2022-jp-2",
    "iso-2022-jp-2004",
    "iso-2022-jp-3",
    "iso-2022-jp-ext",
    "iso-2022-kr",
    "mac-cyrillic",
    "mac-greek",
    "mac-iceland",
    "mac-latin2",
    "mac-roman",
    "mac-turkish",
    "ascii",
    "big5-tw",
    "big5-hkscs",
]


class CodingError(Exception):
    """
    Class implementing an exception, which is raised, if a given coding is
    incorrect.
    """

    def __init__(self, coding):
        """
        Constructor

        @param coding coding to include in the message
        @type str
        """
        self.errorMessage = QCoreApplication.translate(
            "CodingError", "The coding '{0}' is wrong for the given text."
        ).format(coding)

    def __repr__(self):
        """
        Special method returning a representation of the exception.

        @return string representing the error message
        @rtype str
        """
        return str(self.errorMessage)

    def __str__(self):
        """
        Special method returning a string representation of the exception.

        @return string representing the error message
        @rtype str
        """
        return str(self.errorMessage)


def get_codingBytes(text):
    """
    Function to get the coding of a bytes text.

    @param text bytes text to inspect
    @type bytes
    @return coding string
    @rtype str
    """
    lines = text.splitlines()
    for coding in codingBytes_regexps:
        coding_re = coding[1]
        head = lines[: coding[0]]
        for line in head:
            m = coding_re.search(line)
            if m:
                return str(m.group(1), "ascii").lower()
    return None


def get_coding(text):
    """
    Function to get the coding of a text.

    @param text text to inspect
    @type str
    @return coding string
    @rtype str
    """
    lines = text.splitlines()
    for coding in coding_regexps:
        coding_re = coding[1]
        head = lines[: coding[0]]
        for line in head:
            m = coding_re.search(line)
            if m:
                return m.group(1).lower()
    return None


def readEncodedFile(filename):
    """
    Function to read a file and decode its contents into proper text.

    @param filename name of the file to read
    @type str
    @return tuple of decoded text and encoding
    @rtype tuple of (str, str)
    """
    with open(filename, "rb") as f:
        text = f.read()
    return decode(text)


def readEncodedFileWithHash(filename):
    """
    Function to read a file, calculate a hash value and decode its contents
    into proper text.

    @param filename name of the file to read
    @type str
    @return tuple of decoded text, encoding and hash value
    @rtype tuple of (str, str, str)
    """
    with open(filename, "rb") as f:
        text = f.read()
    hashStr = str(
        QCryptographicHash.hash(
            QByteArray(text), QCryptographicHash.Algorithm.Md5
        ).toHex(),
        encoding="ASCII",
    )
    return decode(text) + (hashStr,)


def decode(text):
    """
    Function to decode some byte text into a string.

    @param text byte text to decode
    @type bytes
    @return tuple of decoded text and encoding
    @rtype tuple of (str, str)
    """
    with contextlib.suppress(UnicodeError, LookupError):
        if text.startswith(codecs.BOM_UTF8):
            # UTF-8 with BOM
            return str(text[len(codecs.BOM_UTF8) :], "utf-8"), "utf-8-bom"
        elif text.startswith(codecs.BOM_UTF16):
            # UTF-16 with BOM
            return str(text[len(codecs.BOM_UTF16) :], "utf-16"), "utf-16"
        elif text.startswith(codecs.BOM_UTF32):
            # UTF-32 with BOM
            return str(text[len(codecs.BOM_UTF32) :], "utf-32"), "utf-32"
        coding = get_codingBytes(text)
        if coding:
            return str(text, coding), coding

    # Assume UTF-8
    with contextlib.suppress(UnicodeError, LookupError):
        return str(text, "utf-8"), "utf-8-guessed"

    guess = None
    if Preferences.getEditor("AdvancedEncodingDetection"):
        # Try the universal character encoding detector
        try:
            guess = chardet.detect(text)
            if guess and guess["confidence"] > 0.95 and guess["encoding"] is not None:
                codec = guess["encoding"].lower()
                return str(text, codec), "{0}-guessed".format(codec)
        except (LookupError, UnicodeError):
            pass
        except ImportError:
            pass

    # Try default encoding
    with contextlib.suppress(UnicodeError, LookupError):
        codec = Preferences.getEditor("DefaultEncoding")
        return str(text, codec), "{0}-default".format(codec)

    if (
        Preferences.getEditor("AdvancedEncodingDetection")
        and guess
        and guess["encoding"] is not None
    ):
        # Use the guessed one even if confidence level is low
        with contextlib.suppress(UnicodeError, LookupError):
            codec = guess["encoding"].lower()
            return str(text, codec), "{0}-guessed".format(codec)

    # Assume UTF-8 loosing information
    return str(text, "utf-8", "ignore"), "utf-8-ignore"


def decodeWithEncoding(text, encoding):
    """
    Function to decode some byte text into a string.

    @param text byte text to decode
    @type bytes
    @param encoding encoding to be used to read the file
    @type str
    @return tuple of decoded text and encoding
    @rtype tuple of (str, str)
    """
    if encoding:
        with contextlib.suppress(UnicodeError, LookupError):
            return str(text, encoding), "{0}-selected".format(encoding)

        # Try default encoding
        with contextlib.suppress(UnicodeError, LookupError):
            codec = Preferences.getEditor("DefaultEncoding")
            return str(text, codec), "{0}-default".format(codec)

        # Assume UTF-8 loosing information
        return str(text, "utf-8", "ignore"), "utf-8-ignore"
    else:
        return decode(text)


def readEncodedFileWithEncoding(filename, encoding):
    """
    Function to read a file and decode its contents into proper text.

    @param filename name of the file to read
    @type str
    @param encoding encoding to be used to read the file
    @type str
    @return tuple of decoded text and encoding
    @rtype tuple of (str, str)
    """
    with open(filename, "rb") as f:
        text = f.read()
    return decodeWithEncoding(text, encoding)


def writeEncodedFile(filename, text, origEncoding, forcedEncoding=""):
    """
    Function to write a file with properly encoded text.

    @param filename name of the file to read
    @type str
    @param text text to be written
    @type str
    @param origEncoding type of the original encoding
    @type str
    @param forcedEncoding encoding to be used for writing, if no coding
        line is present
    @type str
    @return encoding used for writing the file
    @rtype str
    """
    etext, encoding = encode(text, origEncoding, forcedEncoding=forcedEncoding)

    with open(filename, "wb") as f:
        f.write(etext)

    return encoding


def encode(text, origEncoding, forcedEncoding=""):
    """
    Function to encode text into a byte text.

    @param text text to be encoded
    @type str
    @param origEncoding type of the original encoding
    @type str
    @param forcedEncoding encoding to be used for writing, if no coding line
        is present
    @type str
    @return tuple of encoded text and encoding used
    @rtype tuple of (bytes, str)
    @exception CodingError raised to indicate an invalid encoding
    """
    encoding = None
    if origEncoding == "utf-8-bom":
        etext, encoding = codecs.BOM_UTF8 + text.encode("utf-8"), "utf-8-bom"
    else:
        # Try declared coding spec
        coding = get_coding(text)
        if coding:
            try:
                etext, encoding = text.encode(coding), coding
            except (LookupError, UnicodeError):
                # Error: Declared encoding is incorrect
                raise CodingError(coding)
        else:
            if forcedEncoding:
                with contextlib.suppress(UnicodeError, LookupError):
                    etext, encoding = (text.encode(forcedEncoding), forcedEncoding)
                    # if forced encoding is incorrect, ignore it

            if encoding is None:
                # Try the original encoding
                if origEncoding and origEncoding.endswith(
                    ("-selected", "-default", "-guessed", "-ignore")
                ):
                    coding = (
                        origEncoding.replace("-selected", "")
                        .replace("-default", "")
                        .replace("-guessed", "")
                        .replace("-ignore", "")
                    )
                    with contextlib.suppress(UnicodeError, LookupError):
                        etext, encoding = text.encode(coding), coding

                if encoding is None:
                    # Try configured default
                    with contextlib.suppress(UnicodeError, LookupError):
                        codec = Preferences.getEditor("DefaultEncoding")
                        etext, encoding = text.encode(codec), codec

                    if encoding is None:
                        # Try saving as ASCII
                        with contextlib.suppress(UnicodeError):
                            etext, encoding = text.encode("ascii"), "ascii"

                        if encoding is None:
                            # Save as UTF-8 without BOM
                            etext, encoding = text.encode("utf-8"), "utf-8"

    return etext, encoding


def normalizeCode(codestring):
    """
    Function to normalize the given code.

    @param codestring code to be normalized
    @type str
    @return normalized code
    @rtype str
    """
    codestring = codestring.replace("\r\n", "\n").replace("\r", "\n")

    if codestring and codestring[-1] != "\n":
        codestring += "\n"

    return codestring


def convertLineEnds(text, eol):
    """
    Function to convert the end of line characters.

    @param text text to be converted
    @type str
    @param eol new eol setting
    @type str
    @return text with converted eols
    @rtype str
    """
    if eol == "\r\n":
        regexp = re.compile(r"""(\r(?!\n)|(?<!\r)\n)""")
        return regexp.sub("\r\n", text)
    elif eol == "\n":
        regexp = re.compile(r"""(\r\n|\r)""")
        return regexp.sub("\n", text)
    elif eol == "\r":
        regexp = re.compile(r"""(\r\n|\n)""")
        return regexp.sub("\r", text)
    else:
        return text


def linesep():
    """
    Function to return the line separator used by the editor.

    @return line separator used by the editor
    @rtype str
    """
    eolMode = Preferences.getEditor("EOLMode")
    if eolMode == QsciScintilla.EolMode.EolUnix:
        return "\n"
    elif eolMode == QsciScintilla.EolMode.EolMac:
        return "\r"
    else:
        return "\r\n"


def extractFlags(text):
    """
    Function to extract eric specific flags out of the given text.

    Flags are contained in comments and are introduced by 'eflag:'.
    The rest of the line is interpreted as 'key = value'. value is
    analyzed for being an integer or float value. If that fails, it
    is assumed to be a string. If a key does not contain a '='
    character, it is assumed to be a boolean flag. Flags are expected
    at the very end of a file. The search is ended, if a line without
    the 'eflag:' marker is found.

    @param text text to be scanned
    @type str
    @return dictionary of string, boolean, complex, float and int
    @rtype dict
    """
    flags = {}
    lines = text.rstrip().splitlines() if isinstance(text, str) else text
    for line in reversed(lines):
        try:
            index = line.index("eflag:")
        except ValueError:
            # no flag found, don't look any further
            break

        flag = line[index + 6 :].strip()
        if "=" in flag:
            key, value = flag.split("=", 1)
            key = key.strip()
            value = value.strip()

            if value.lower() in ["true", "false", "yes", "no", "ok"]:
                # it is a flag
                flags[key] = value.lower() in ["true", "yes", "ok"]
                continue

            try:
                # interpret as int first
                value = int(value)
            except ValueError:
                with contextlib.suppress(ValueError):
                    # interpret as float next
                    value = float(value)

            flags[key] = value
        else:
            # treat it as a boolean
            if flag[0] == "-":
                # false flags start with '-'
                flags[flag[1:]] = False
            else:
                flags[flag] = True

    return flags


def extractFlagsFromFile(filename):
    """
    Function to extract eric specific flags out of the given file.

    @param filename name of the file to be scanned
    @type str
    @return dictionary of string, boolean, complex, float and int
    @rtype dict
    """
    try:
        source, encoding = readEncodedFile(filename)
    except (OSError, UnicodeError):
        return {}

    return extractFlags(source)


def extractLineFlags(line, startComment="#", endComment="", flagsLine=False):
    """
    Function to extract flags starting and ending with '__' from a line
    comment.

    @param line line to extract flags from
    @type str
    @param startComment string identifying the start of the comment
    @type str
    @param endComment string identifying the end of a comment
    @type str
    @param flagsLine flag indicating to check for a flags only line
    @type bool
    @return list containing the extracted flags
    @rtype list of str
    """
    flags = []

    if not flagsLine or (flagsLine and line.strip().startswith(startComment)):
        pos = line.rfind(startComment)
        if pos >= 0:
            comment = line[pos + len(startComment) :].strip()
            if endComment:
                endPos = line.rfind(endComment)
                if endPos >= 0:
                    comment = comment[:endPos]
            flags = [
                f.strip()
                for f in comment.split()
                if (f.startswith("__") and f.endswith("__"))
            ]
    return flags


def filterAnsiSequences(txt):
    """
    Function to filter out ANSI escape sequences (color only).

    @param txt text to be filtered
    @type str
    @return text without ANSI escape sequences
    @rtype str
    """
    ntxt = txt[:]
    while True:
        start = ntxt.find("\33[")  # find escape character
        if start == -1:
            break
        end = ntxt.find("m", start)
        if end == -1:
            break
        ntxt = ntxt[:start] + ntxt[end + 1 :]

    return ntxt


def getTestFileNames(fn):
    """
    Function to build the potential file names of a test file.

    The file names for the test file is built by prepending the string
    "test" and "test_" to the file name passed into this function and
    by appending the string "_test".

    @param fn file name basis to be used for the test file names
    @type str
    @return file names of the corresponding test file
    @rtype list of str
    """
    dn, fn = os.path.split(fn)
    fn, ext = os.path.splitext(fn)
    prefixes = ["test", "test_"]
    postfixes = ["_test"]
    return [
        os.path.join(dn, "{0}{1}{2}".format(prefix, fn, ext)) for prefix in prefixes
    ] + [
        os.path.join(dn, "{0}{1}{2}".format(fn, postfix, ext)) for postfix in postfixes
    ]


def getCoverageFileNames(fn):
    """
    Function to build a list of coverage data file names.

    @param fn file name basis to be used for the coverage data file
    @type str
    @return list of existing coverage data files
    @rtype list of str
    """
    files = []
    for filename in [fn, os.path.dirname(fn) + os.sep] + getTestFileNames(fn):
        f = getCoverageFileName(filename)
        if f:
            files.append(f)
    return files


def getCoverageFileName(fn, mustExist=True):
    """
    Function to build a file name for a coverage data file.

    @param fn file name basis to be used for the coverage data file name
    @type str
    @param mustExist flag indicating to check that the file exists (defaults
        to True)
    @type bool (optional)
    @return coverage data file name
    @rtype str
    """
    basename = os.path.splitext(fn)[0]
    filename = "{0}.coverage".format(basename)
    if mustExist:
        if FileSystemUtilities.isRemoteFileName(fn):
            ericServer = ericApp().getObject("EricServer")
            if ericServer.isServerConnected() and ericServer.getServiceInterface(
                "FileSystem"
            ).exists(filename):
                return filename
            else:
                return ""

        # It is a local file.
        if os.path.isfile(filename):
            return filename
        else:
            return ""
    else:
        return filename


def getProfileFileNames(fn):
    """
    Function to build a list of profile data file names.

    @param fn file name basis to be used for the profile data file
    @type str
    @return list of existing profile data files
    @rtype list of str
    """
    files = []
    for filename in [fn, os.path.dirname(fn) + os.sep] + getTestFileNames(fn):
        f = getProfileFileName(filename)
        if f:
            files.append(f)
    return files


def getProfileFileName(fn, mustExist=True):
    """
    Function to build a file name for a profile data file.

    @param fn file name basis to be used for the profile data file name
    @type str
    @param mustExist flag indicating to check that the file exists (defaults
        to True)
    @type bool (optional)
    @return profile data file name
    @rtype str
    """
    basename = os.path.splitext(fn)[0]
    filename = "{0}.profile".format(basename)
    if mustExist:
        if FileSystemUtilities.isRemoteFileName(fn):
            ericServer = ericApp().getObject("EricServer")
            if ericServer.isServerConnected() and ericServer.getServiceInterface(
                "FileSystem"
            ).exists(filename):
                return filename
            else:
                return ""

        # It is a local file.
        if os.path.isfile(filename):
            return filename
        else:
            return ""

    return filename


def parseOptionString(s):
    """
    Function used to convert an option string into a list of options.

    @param s option string
    @type str
    @return list of options
    @rtype list of str
    """
    s = re.sub(r"%[A-Z%]", _percentReplacementFunc, s)
    return shlex.split(s)


def _percentReplacementFunc(matchobj):
    """
    Protected function called for replacing % codes.

    @param matchobj match object for the code
    @type re.Match
    @return replacement string
    @rtype str
    """
    return getPercentReplacement(matchobj.group(0))


def getPercentReplacement(code):
    """
    Function to get the replacement for code.

    @param code code indicator
    @type str
    @return replacement string
    @rtype str
    """
    if code in ["C", "%C"]:
        # column of the cursor of the current editor
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw is None:
            column = -1
        else:
            column = aw.getCursorPosition()[1]
        return "{0:d}".format(column)
    elif code in ["D", "%D"]:
        # directory of active editor
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw is None:
            dn = "not_available"
        else:
            fn = aw.getFileName()
            if fn is None:
                dn = "not_available"
            else:
                dn = os.path.dirname(fn)
        return dn
    elif code in ["F", "%F"]:
        # filename (complete) of active editor
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw is None:
            fn = "not_available"
        else:
            fn = aw.getFileName()
            if fn is None:
                fn = "not_available"
        return fn
    elif code in ["H", "%H"]:
        # home directory
        return OSUtilities.getHomeDir()
    elif code in ["L", "%L"]:
        # line of the cursor of the current editor
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw is None:
            line = 0
        else:
            line = aw.getCursorPosition()[0] + 1
        return "{0:d}".format(line)
    elif code in ["P", "%P"]:
        # project path
        projectPath = ericApp().getObject("Project").getProjectPath()
        if not projectPath:
            projectPath = "not_available"
        return projectPath
    elif code in ["S", "%S"]:
        # selected text of the current editor
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw is None:
            text = "not_available"
        else:
            text = aw.selectedText()
        return text
    elif code in ["U", "%U"]:
        # username
        un = OSUtilities.getUserName()
        if un is None:
            return code
        else:
            return un
    elif code in ["%", "%%"]:
        # the percent sign
        return "%"
    else:
        # unknown code, just return it
        return code


def getPercentReplacementHelp():
    """
    Function to get the help text for the supported %-codes.

    @return help text
    @rtype str
    """
    return QCoreApplication.translate(
        "Utilities",
        """<p>You may use %-codes as placeholders in the string."""
        """ Supported codes are:"""
        """<table>"""
        """<tr><td>%C</td><td>column of the cursor of the current editor"""
        """</td></tr>"""
        """<tr><td>%D</td><td>directory of the current editor</td></tr>"""
        """<tr><td>%F</td><td>filename of the current editor</td></tr>"""
        """<tr><td>%H</td><td>home directory of the current user</td></tr>"""
        """<tr><td>%L</td><td>line of the cursor of the current editor"""
        """</td></tr>"""
        """<tr><td>%P</td><td>path of the current project</td></tr>"""
        """<tr><td>%S</td><td>selected text of the current editor</td></tr>"""
        """<tr><td>%U</td><td>username of the current user</td></tr>"""
        """<tr><td>%%</td><td>the percent sign</td></tr>"""
        """</table>"""
        """</p>""",
    )


def rxIndex(rx, txt):
    """
    Function to get the index (start position) of a regular expression match
    within some text.

    @param rx regular expression object as created by re.compile()
    @type re.Pattern
    @param txt text to be scanned
    @type str
    @return start position of the match or -1 indicating no match was found
    @rtype int
    """
    match = rx.search(txt)
    if match is None:
        return -1
    else:
        return match.start()


def unslash(txt):
    """
    Function to convert a string containing escape codes to an escaped string.

    @param txt string to be converted
    @type str
    @return converted string containing escape codes
    @rtype str
    """
    s = []
    index = 0
    while index < len(txt):
        c = txt[index]
        if c == "\\" and index + 1 < len(txt):
            index += 1
            c = txt[index]
            if c == "a":
                o = "\a"
            elif c == "b":
                o = "\b"
            elif c == "f":
                o = "\f"
            elif c == "n":
                o = "\n"
            elif c == "r":
                o = "\r"
            elif c == "t":
                o = "\t"
            elif c == "v":
                o = "\v"
            elif c in "01234567":
                # octal
                oc = c
                if index + 1 < len(txt) and txt[index + 1] in "01234567":
                    index += 1
                    oc += txt[index]
                    if index + 1 < len(txt) and txt[index + 1] in "01234567":
                        index += 1
                        oc += txt[index]
                o = chr(int(oc, base=8))
            elif c.lower() == "x":
                val = 0
                if index + 1 < len(txt) and txt[index + 1] in "0123456789abcdefABCDEF":
                    index += 1
                    hx = txt[index]
                    if (
                        index + 1 < len(txt)
                        and txt[index + 1] in "0123456789abcdefABCDEF"
                    ):
                        index += 1
                        hx += txt[index]
                    val = int(hx, base=16)
                o = chr(val)
            else:
                o = c
        else:
            o = c

        s.append(o)
        index += 1

    return "".join(s)


_slashmap = {i: hex(i).replace("0x", "\\x") for i in range(7)}
_slashmap.update(
    {
        7: "\\a",
        8: "\\b",
        9: "\\t",
        10: "\\n",
        11: "\\v",
        12: "\\f",
        13: "\\r",
    }
)
_slashmap.update({i: hex(i).replace("0x", "\\x") for i in range(14, 32)})
_slashmap.update({i: hex(i).replace("0x", "\\x") for i in range(127, 160)})


def slash(txt):
    """
    Function to convert an escaped string to a string containing escape codes.

    Note: This is the reverse of 'unslash()'.

    @param txt string to be converted
    @type str
    @return converted string containing escaped escape codes
    @rtype str
    """
    return txt.translate(_slashmap)


###############################################################################
## Other utility functions below
###############################################################################


def generateVersionInfo(linesep="\n"):
    """
    Module function to generate a string with various version infos.

    @param linesep string to be used to separate lines
    @type str
    @return string with version infos
    @rtype str
    """
    try:
        sip_version_str = sip.SIP_VERSION_STR
    except AttributeError:
        sip_version_str = "sip version not available"

    sizeStr = "64-Bit" if sys.maxsize > 2**32 else "32-Bit"

    info = [
        "Version Numbers",
        "===============",
    ]

    info.append(f"  {Program} {Version}")
    info.append("")

    info.append(f"  Python {sys.version.split()[0]}, {sizeStr}")
    info.append(f"  Qt {qVersion()}")
    info.append(f"  PyQt6 {PYQT_VERSION_STR}")
    try:
        from PyQt6 import QtCharts  # noqa: I101, I102

        info.append(f"  PyQt6-Charts {QtCharts.PYQT_CHART_VERSION_STR}")
    except (AttributeError, ImportError):
        info.append("  PyQt6-Charts not installed")
    try:
        from PyQt6 import QtWebEngineCore  # noqa: I101, I102

        info.append(f"  PyQt6-WebEngine {QtWebEngineCore.PYQT_WEBENGINE_VERSION_STR}")
    except (AttributeError, ImportError):
        info.append("  PyQt6-WebEngine not installed")
    info.append(f"  PyQt6-QScintilla {QSCINTILLA_VERSION_STR}")
    info.append(f"  sip {sip_version_str}")
    if bool(importlib.util.find_spec("PyQt6.QtWebEngineWidgets")):
        from eric7.WebBrowser.Tools import WebBrowserTools  # noqa: I101

        (
            chromiumVersion,
            chromiumSecurityVersion,
        ) = WebBrowserTools.getWebEngineVersions()[0:2]
        info.append(f"  WebEngine {chromiumVersion}")
        if chromiumSecurityVersion:
            info.append(f"    (Security) {chromiumSecurityVersion}")
    info.append("")
    info.append("Platform")
    info.append("========")
    info.append(sys.platform)
    if os.environ.get("SOMMELIER_VERSION", ""):
        info[-1] += ", ChromeOS"
    info.append(f"Python {sys.version}")
    desktop = DesktopUtilities.desktopName()
    if desktop:
        info.append("")
        info.append(f"Desktop: {desktop}")
    session = DesktopUtilities.sessionType()
    if session:
        if not desktop:
            info.append("")
        info.append(f"Session Type: {session}")

    return linesep.join(info)


def generatePluginsVersionInfo(linesep="\n"):
    """
    Module function to generate a string with plugins version infos.

    @param linesep string to be used to separate lines
    @type str
    @return string with plugins version infos
    @rtype str
    """
    info = []
    app = ericApp()
    if app is not None:
        with contextlib.suppress(KeyError):
            pm = app.getObject("PluginManager")
            versions = {}
            for pinfo in pm.getPluginInfos():
                versions[pinfo["module_name"]] = pinfo["version"]

            info.append("Plugin Version Numbers")
            info.append("======================")
            for pluginModuleName in sorted(versions):
                info.append(f"  {pluginModuleName} {versions[pluginModuleName]}")

    return linesep.join(info)


def generateDistroInfo(linesep="\n"):
    """
    Module function to generate a string with distribution infos.

    @param linesep string to be used to separate lines
    @type str
    @return string with distribution infos
    @rtype str
    """
    info = []
    if OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
        releaseList = glob.glob("/etc/*-release")
        if releaseList:
            info.append("Distribution Info")
            info.append("=================")
            for rfile in releaseList:
                try:
                    with open(rfile, "r") as f:
                        lines = f.read().splitlines()
                except OSError:
                    continue

                info.append("  {0}".format(rfile))
                info.extend(["    {0}".format(line) for line in lines])
                info.append("")

    return linesep.join(info)


def getSysPath(interpreter):
    """
    Module function to get the Python path (sys.path) of a specific
    interpreter.

    @param interpreter Python interpreter executable to get sys.path for
    @type str
    @return list containing sys.path of the interpreter; an empty list
        is returned, if the interpreter is the one used to run eric itself
    @rtype list of str
    """
    sysPath = []

    getSysPathSkript = os.path.join(os.path.dirname(__file__), "GetSysPath.py")
    args = [getSysPathSkript]
    proc = QProcess()
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    proc.start(interpreter, args)
    finished = proc.waitForFinished(30000)
    if finished and proc.exitCode() == 0:
        text = proc.readAllStandardOutput()
        sysPathResult = str(text, "utf-8", "replace").strip()
        with contextlib.suppress(TypeError, ValueError):
            sysPath = json.loads(sysPathResult)
            if "" in sysPath:
                sysPath.remove("")

    return sysPath
