# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package containing utility modules and functions.
"""

import codecs
import contextlib
import os
import re

import chardet
import semver

from PyQt6.QtCore import QByteArray, QCoreApplication

###############################################################################
## Functions dealing with the configuration directory.
###############################################################################

_configDir = None


def getConfigDir():
    """
    Module function to get the name of the directory storing the config data.

    @return directory name of the config dir
    @rtype str
    """
    if _configDir is not None and os.path.exists(_configDir):
        return _configDir
    else:
        confDir = os.path.join(os.path.expanduser("~"), ".eric7")
        if not os.path.exists(confDir):
            os.mkdir(confDir)
        return confDir


def setConfigDir(d):
    """
    Module function to set the name of the directory storing the config data.

    @param d name of an existing directory
    @type str
    """
    global _configDir

    _configDir = os.path.expanduser(d)


###############################################################################
## Functions for converting QSetting return types to valid types.
###############################################################################


def toBool(value):
    """
    Function to convert a value to bool.

    @param value value to be converted
    @type str
    @return converted data
    @rtype bool
    """
    if (isinstance(value, str) and value.lower() in ["true", "1", "yes"]) or (
        isinstance(value, bytes) and value.lower() in [b"true", b"1", b"yes"]
    ):
        return True
    elif (isinstance(value, str) and value.lower() in ["false", "0", "no"]) or (
        isinstance(value, bytes) and value.lower() in [b"false", b"0", b"no"]
    ):
        return False
    else:
        return bool(value)


def toList(value):
    """
    Function to convert a value to a list.

    @param value value to be converted
    @type None, list or Any
    @return converted data
    @rtype list
    """
    if value is None:
        return []
    elif not isinstance(value, list):
        return [value]
    else:
        return value


def toByteArray(value):
    """
    Function to convert a value to a byte array.

    @param value value to be converted
    @type QByteArray or None
    @return converted data
    @rtype QByteArray
    """
    if value is None:
        return QByteArray()
    else:
        return value


def toDict(value):
    """
    Function to convert a value to a dictionary.

    @param value value to be converted
    @type dict or None
    @return converted data
    @rtype dict
    """
    if value is None:
        return {}
    else:
        return value


###############################################################################
## Functions for version handling.
###############################################################################


def versionIsValid(version):
    """
    Function to check, if the given version string is valid.

    @param version version string
    @type str
    @return flag indicating validity
    @rtype bool
    """
    try:
        return semver.VersionInfo.is_valid(version)
    except AttributeError:
        return semver.VersionInfo.isvalid(version)


def versionToTuple(version):
    """
    Function to convert a version string into a tuple.

    Note: A version string consists of non-negative decimals separated by "."
    optionally followed by a suffix. Suffix is everything after the last
    decimal.

    @param version version string
    @type str
    @return version named tuple containing the version parts
    @rtype semver.VersionInfo
    """
    while version and not version[0].isdecimal():
        # sanitize version string (get rid of leading non-decimal characters)
        version = version[1:]

    while version.count(".") < 2:
        # ensure the version string contains at least three parts
        version += ".0"

    if versionIsValid(version):
        return semver.VersionInfo.parse(version)
    elif version.count(".") > 2:
        v = ".".join(version.split(".")[:3])
        if versionIsValid(v):
            return semver.VersionInfo.parse(v)

    return semver.VersionInfo(0, 0, 0)


###############################################################################
## Functions for extended string handling.
###############################################################################


def strGroup(txt, sep, groupLen=4):
    """
    Function to group a string into sub-strings separated by a
    separator.

    @param txt text to be grouped
    @type str
    @param sep separator string
    @type str
    @param groupLen length of each group
    @type int
    @return result string
    @rtype str
    """
    groups = []

    while len(txt) // groupLen != 0:
        groups.insert(0, txt[-groupLen:])
        txt = txt[:-groupLen]
    if len(txt) > 0:
        groups.insert(0, txt)
    return sep.join(groups)


def strToQByteArray(txt):
    """
    Function to convert a Python string into a QByteArray.

    @param txt Python string to be converted
    @type str, bytes, bytearray
    @return converted QByteArray
    @rtype QByteArray
    """
    if isinstance(txt, str):
        txt = txt.encode("utf-8")

    return QByteArray(txt)


def dataString(size, loc=None):
    """
    Function to generate a formatted size string.

    @param size size to be formatted
    @type int
    @param loc locale to be used for localized size strings (defaults to None)
    @type QLocale (optional)
    @return formatted data string
    @rtype str
    """
    if loc is None:
        if size < 1024:
            return QCoreApplication.translate("EricUtilities", "{0:4d} Bytes").format(
                size
            )
        elif size < 1024 * 1024:
            size /= 1024
            return QCoreApplication.translate("EricUtilities", "{0:4.2f} KiB").format(
                size
            )
        elif size < 1024 * 1024 * 1024:
            size /= 1024 * 1024
            return QCoreApplication.translate("EricUtilities", "{0:4.2f} MiB").format(
                size
            )
        elif size < 1024 * 1024 * 1024 * 1024:
            size /= 1024 * 1024 * 1024
            return QCoreApplication.translate("EricUtilities", "{0:4.2f} GiB").format(
                size
            )
        else:
            size /= 1024 * 1024 * 1024 * 1024
            return QCoreApplication.translate("EricUtilities", "{0:4.2f} TiB").format(
                size
            )
    else:
        if not isinstance(size, float):
            size = float(size)

        if size < 1024:
            return QCoreApplication.translate("EricUtilities", "{0} Bytes").format(
                loc.toString(size)
            )
        elif size < 1024 * 1024:
            size /= 1024
            return QCoreApplication.translate("EricUtilities", "{0} KiB").format(
                loc.toString(size, "f", 2)
            )
        elif size < 1024 * 1024 * 1024:
            size /= 1024 * 1024
            return QCoreApplication.translate("EricUtilities", "{0} MiB").format(
                loc.toString(size, "f", 2)
            )
        elif size < 1024 * 1024 * 1024 * 1024:
            size /= 1024 * 1024 * 1024
            return QCoreApplication.translate("EricUtilities", "{0} GiB").format(
                loc.toString(size, "f", 2)
            )
        else:
            size /= 1024 * 1024 * 1024 * 1024
            return QCoreApplication.translate("EricUtilities", "{0} TiB").format(
                loc.toString(size, "f", 2)
            )


def decodeString(text):
    """
    Function to decode a string containing Unicode encoded characters.

    @param text text containing encoded chars
    @type str
    @return decoded text
    @rtype str
    """
    buf = b""
    index = 0
    while index < len(text):
        if text[index] == "\\":
            qb = QByteArray.fromHex(text[index : index + 4].encode())
            buf += bytes(qb)
            index += 4
        else:
            buf += codecs.encode(text[index], "utf-8")
            index += 1
    buf = buf.replace(b"\x00", b"")
    return decodeBytes(buf)


def decodeBytes(buffer):
    """
    Function to decode some byte text into a string.

    @param buffer byte buffer to decode
    @type bytes
    @return decoded text
    @rtype str
    """
    # try UTF with BOM
    with contextlib.suppress(UnicodeError, LookupError):
        if buffer.startswith(codecs.BOM_UTF8):
            # UTF-8 with BOM
            return str(buffer[len(codecs.BOM_UTF8) :], encoding="utf-8")
        elif buffer.startswith(codecs.BOM_UTF16):
            # UTF-16 with BOM
            return str(buffer[len(codecs.BOM_UTF16) :], encoding="utf-16")
        elif buffer.startswith(codecs.BOM_UTF32):
            # UTF-32 with BOM
            return str(buffer[len(codecs.BOM_UTF32) :], encoding="utf-32")

    # try UTF-8
    with contextlib.suppress(UnicodeError):
        return str(buffer, encoding="utf-8")

    # try codec detection
    try:
        guess = chardet.detect(buffer)
        if guess and guess["encoding"] is not None:
            codec = guess["encoding"].lower()
            return str(buffer, encoding=codec)
    except (LookupError, UnicodeError):
        pass
    except ImportError:
        pass

    return str(buffer, encoding="utf-8", errors="ignore")


def readStringFromStream(stream):
    """
    Module function to read a string from the given stream.

    @param stream data stream opened for reading
    @type QDataStream
    @return string read from the stream
    @rtype str
    """
    data = stream.readString()
    if data is None:
        data = b""
    return data.decode("utf-8")


###############################################################################
## Functions for HTML string handling.
###############################################################################


_escape = re.compile("[&<>\"'\u0080-\uffff]")

_escape_map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
}


def escape_entities(m, escmap=_escape_map):
    """
    Function to encode html entities.

    @param m the match object
    @type re.Match
    @param escmap the map of entities to encode
    @type dict
    @return the converted text
    @rtype str
    """
    char = m.group()
    text = escmap.get(char)
    if text is None:
        text = "&#{0:d};".format(ord(char))
    return text


def html_encode(text, pattern=_escape):
    """
    Function to correctly encode a text for html.

    @param text text to be encoded
    @type str
    @param pattern search pattern for text to be encoded
    @type str
    @return the encoded text
    @rtype str
    """
    if not text:
        return ""
    text = pattern.sub(escape_entities, text)
    return text


_uescape = re.compile("[\u0080-\uffff]")


def escape_uentities(m):
    """
    Function to encode html entities.

    @param m the match object
    @type re.Match
    @return the converted text
    @rtype str
    """
    char = m.group()
    text = "&#{0:d};".format(ord(char))
    return text


def html_uencode(text, pattern=_uescape):
    """
    Function to correctly encode a unicode text for html.

    @param text text to be encoded
    @type str
    @param pattern search pattern for text to be encoded
    @type str
    @return the encoded text
    @rtype str
    """
    if not text:
        return ""
    text = pattern.sub(escape_uentities, text)
    return text


_uunescape = re.compile(r"&#\d+;")


def unescape_uentities(m):
    """
    Function to decode html entities.

    @param m the match object
    @type re.Match
    @return the converted text
    @rtype str
    """
    char = m.group()
    ordinal = int(char[2:-1])
    return chr(ordinal)


def html_udecode(text, pattern=_uunescape):
    """
    Function to correctly decode a html text to a unicode text.

    @param text text to be decoded
    @type str
    @param pattern search pattern for text to be decoded
    @type str
    @return the decoded text
    @rtype str
    """
    if not text:
        return ""
    text = pattern.sub(unescape_uentities, text)
    return text
