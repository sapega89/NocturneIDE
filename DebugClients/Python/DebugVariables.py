# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing classes and functions to dump variable contents.
"""

import contextlib
import sys

from collections.abc import ItemsView, KeysView, ValuesView

from DebugConfig import (
    BatchSize,
    ConfigKnownQtTypes,
    ConfigQtNames,
    UnknownAttributeValueMarker,
)

#
# This code was inspired by pydevd.
#

############################################################
## Classes implementing resolvers for various compound types
############################################################


class BaseResolver:
    """
    Base class of the resolver class tree.
    """

    def resolve(self, var, attribute):
        """
        Public method to get an attribute from a variable.

        @param var variable to extract an attribute or value from
        @type Any
        @param attribute name of the attribute to extract
        @type str
        @return value of the attribute
        @rtype Any
        """
        return getattr(var, attribute, None)

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @return list containing the variable attributes
        @rtype list
        """
        d = []
        for name in dir(var):
            try:
                attribute = getattr(var, name)
                d.append((name, attribute))
            except AttributeError:
                # ignore non-existent attributes
                pass
            except Exception as exc:
                # The attribute value cannot be determined/is not available yet.
                d.append((name, "{0}{1}".format(UnknownAttributeValueMarker, str(exc))))

        return d


############################################################
## Default Resolver
############################################################


class DefaultResolver(BaseResolver):
    """
    Class used to resolve the default way.
    """

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @yield tuple containing the batch start index and a list
            containing the variable attributes
        @ytype tuple of (int, list)
        """
        d = super().getVariableList(var)

        yield -1, d
        while True:
            yield -2, []


############################################################
## Resolver for Dictionaries
############################################################


class DictResolver(BaseResolver):
    """
    Class used to resolve from a dictionary.
    """

    def resolve(self, var, attribute):
        """
        Public method to get an attribute from a variable.

        @param var variable to extract an attribute or value from
        @type dict
        @param attribute name of the attribute to extract
        @type str
        @return value of the attribute
        @rtype Any
        """
        if " (ID:" not in attribute:
            try:
                return var[attribute]
            except Exception:
                return getattr(var, attribute, None)

        expectedID = int(attribute.split(" (ID:")[-1][:-1])
        for key, value in var.items():
            if id(key) == expectedID:
                return value

        return None

    def keyToStr(self, key):
        """
        Public method to get a string representation for a key.

        @param key key to be converted
        @type Any
        @return string representation of the given key
        @rtype str
        """
        if isinstance(key, str):
            key = repr(key)
            # Special handling for bytes object
            # Raw and f-Strings are always converted to str
            if key[0] == "b":
                key = key[1:]

        return key  # __IGNORE_WARNING_M834__

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @yield tuple containing the batch start index and a list
            containing the variable attributes
        @ytype tuple of (int, list)
        """
        d = []
        start = count = 0
        allItems = list(var.items())
        try:
            # Fast path: all items from same type
            allItems.sort(key=lambda x: x[0])
        except TypeError:
            # Slow path: only sort items with same type (Py3 only)
            allItems.sort(key=lambda x: (str(x[0]), x[0]))

        for key, value in allItems:
            key = "{0} (ID:{1})".format(self.keyToStr(key), id(key))
            d.append((key, value))
            count += 1
            if count >= BatchSize:
                yield start, d
                start += count
                count = 0
                d = []

        if d:
            yield start, d

        # in case it has additional fields
        d = super().getVariableList(var)
        yield -1, d

        while True:
            yield -2, []


############################################################
## Resolver for Lists and Tuples
############################################################


class ListResolver(BaseResolver):
    """
    Class used to resolve from a tuple or list.
    """

    def resolve(self, var, attribute):
        """
        Public method to get an attribute from a variable.

        @param var variable to extract an attribute or value from
        @type tuple or list
        @param attribute name of the attribute to extract
        @type str
        @return value of the attribute
        @rtype Any
        """
        try:
            return var[int(attribute)]
        except Exception:
            return getattr(var, str(attribute), None)

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @yield tuple containing the batch start index and a list
            containing the variable attributes
        @ytype tuple of (int, list)
        """
        d = []
        start = count = 0
        for idx, value in enumerate(var):
            d.append((idx, value))
            count += 1
            if count >= BatchSize:
                yield start, d
                start = idx + 1
                count = 0
                d = []

        if d:
            yield start, d

        # in case it has additional fields
        d = super().getVariableList(var)
        yield -1, d

        while True:
            yield -2, []


############################################################
## Resolver for dict_items, dict_keys and dict_values
############################################################


class DictViewResolver(ListResolver):
    """
    Class used to resolve from dict views.
    """

    def resolve(self, var, attribute):
        """
        Public method to get an attribute from a variable.

        @param var variable to extract an attribute or value from
        @type dict_items, dict_keys or dict_values
        @param attribute id of the value to extract
        @type str
        @return value of the attribute
        @rtype Any
        """
        return super().resolve(list(var), attribute)

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @yield tuple containing the batch start index and a list
            containing the variable attributes
        @ytype tuple of (int, list)
        """
        yield from super().getVariableList(list(var))


############################################################
## Resolver for Sets and Frozensets
############################################################


class SetResolver(BaseResolver):
    """
    Class used to resolve from a set or frozenset.
    """

    def resolve(self, var, attribute):
        """
        Public method to get an attribute from a variable.

        @param var variable to extract an attribute or value from
        @type tuple or list
        @param attribute id of the value to extract
        @type str
        @return value of the attribute
        @rtype Any
        """
        if attribute.startswith("'ID: "):
            attribute = attribute.split(None, 1)[1][:-1]
        try:
            attribute = int(attribute)
        except Exception:
            return getattr(var, attribute, None)

        for v in var:
            if id(v) == attribute:
                return v

        return None

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @yield tuple containing the batch start index and a list
            containing the variable attributes
        @ytype tuple of (int, list)
        """
        d = []
        start = count = 0
        for value in var:
            count += 1
            d.append(("'ID: {0}'".format(id(value)), value))
            if count >= BatchSize:
                yield start, d
                start += count
                count = 0
                d = []

        if d:
            yield start, d

        # in case it has additional fields
        d = super().getVariableList(var)
        yield -1, d

        while True:
            yield -2, []


############################################################
## Resolver for Numpy Arrays
############################################################


class NdArrayResolver(BaseResolver):
    """
    Class used to resolve from numpy ndarray including some meta data.
    """

    def __isNumeric(self, arr):
        """
        Private method to check, if an array is of a numeric type.

        @param arr array to check
        @type ndarray
        @return flag indicating a numeric array
        @rtype bool
        """
        try:
            return arr.dtype.kind in "biufc"
        except AttributeError:
            return False

    def resolve(self, var, attribute):
        """
        Public method to get an attribute from a variable.

        @param var variable to extract an attribute or value from
        @type ndarray
        @param attribute id of the value to extract
        @type str
        @return value of the attribute
        @rtype Any
        """
        if attribute == "min":
            if self.__isNumeric(var):
                return var.min()
            else:
                return None

        if attribute == "max":
            if self.__isNumeric(var):
                return var.max()
            else:
                return None

        if attribute == "mean":
            if self.__isNumeric(var):
                return var.mean()
            else:
                return None

        try:
            return var[int(attribute)]
        except Exception:
            return getattr(var, attribute, None)

        return None

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @yield tuple containing the batch start index and a list
            containing the variable attributes
        @ytype tuple of (int, list)
        """
        d = []
        start = count = 0
        try:
            len(var)  # Check if it's an unsized object, e.g. np.ndarray(())
            allItems = var.tolist()
        except TypeError:  # TypeError: len() of unsized object
            allItems = []

        for idx, value in enumerate(allItems):
            d.append((str(idx), value))
            count += 1
            if count >= BatchSize:
                yield start, d
                start += count
                count = 0
                d = []

        if d:
            yield start, d

        # in case it has additional fields
        d = super().getVariableList(var)

        if var.size > 1024 * 1024:
            d.append(
                ("min", "ndarray too big, calculating min would slow down debugging")
            )
            d.append(
                ("max", "ndarray too big, calculating max would slow down debugging")
            )
            d.append(
                ("mean", "ndarray too big, calculating mean would slow down debugging")
            )
        elif self.__isNumeric(var):
            if var.size == 0:
                d.append(("min", "empty array"))
                d.append(("max", "empty array"))
                d.append(("mean", "empty array"))
            else:
                d.append(("min", var.min()))
                d.append(("max", var.max()))
                d.append(("mean", var.mean()))
        else:
            d.append(("min", "not a numeric object"))
            d.append(("max", "not a numeric object"))
            d.append(("mean", "not a numeric object"))

        yield -1, d

        while True:
            yield -2, []


############################################################
## Resolver for Django Multi Value Dictionaries
############################################################


class MultiValueDictResolver(DictResolver):
    """
    Class used to resolve from Django multi value dictionaries.
    """

    def resolve(self, var, attribute):
        """
        Public method to get an attribute from a variable.

        @param var variable to extract an attribute or value from
        @type MultiValueDict
        @param attribute name of the attribute to extract
        @type str
        @return value of the attribute
        @rtype Any
        """
        if " (ID:" not in attribute:
            try:
                return var[attribute]
            except Exception:
                return getattr(var, attribute, None)

        expectedID = int(attribute.split(" (ID:")[-1][:-1])
        for key in var:
            if id(key) == expectedID:
                return var.getlist(key)

        return None

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @yield tuple containing the batch start index and a list
            containing the variable attributes
        @ytype tuple of (int, list)
        """
        d = []
        start = count = 0
        allKeys = list(var)
        try:
            # Fast path: all items from same type
            allKeys.sort()
        except TypeError:
            # Slow path: only sort items with same type (Py3 only)
            allKeys.sort(key=lambda x: (str(x), x))

        for key in allKeys:
            dkey = "{0} (ID:{1})".format(self.keyToStr(key), id(key))
            d.append((dkey, var.getlist(key)))
            count += 1
            if count >= BatchSize:
                yield start, d
                start += count
                count = 0
                d = []

        if d:
            yield start, d

        # in case it has additional fields
        d = super(DictResolver, self).getVariableList(var)
        yield -1, d

        while True:
            yield -2, []


############################################################
## Resolver for array.array
############################################################


class ArrayResolver(BaseResolver):
    """
    Class used to resolve from array.array including some meta data.
    """

    TypeCodeMap = {
        "b": "int (signed char)",
        "B": "int (unsigned char)",
        "u": "Unicode character (Py_UNICODE)",
        "h": "int (signed short)",
        "H": "int (unsigned short)",
        "i": "int (signed int)",
        "I": "int (unsigned int)",
        "l": "int (signed long)",
        "L": "int (unsigned long)",
        "q": "int (signed long long)",
        "Q": "int (unsigned long long)",
        "f": "float (float)",
        "d": "float (double)",
    }

    def resolve(self, var, attribute):
        """
        Public method to get an attribute from a variable.

        @param var variable to extract an attribute or value from
        @type array.array
        @param attribute id of the value to extract
        @type str
        @return value of the attribute
        @rtype Any
        """
        try:
            return var[int(attribute)]
        except Exception:
            return getattr(var, attribute, None)

        return None

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @yield tuple containing the batch start index and a list
            containing the variable attributes
        @ytype tuple of (int, list)
        """
        d = []
        start = count = 0
        allItems = var.tolist()

        for idx, value in enumerate(allItems):
            d.append((str(idx), value))
            count += 1
            if count >= BatchSize:
                yield start, d
                start += count
                count = 0
                d = []

        if d:
            yield start, d

        # in case it has additional fields
        d = super().getVariableList(var)

        # Special data for array type: convert typecode to readable text
        d.append(("type", self.TypeCodeMap.get(var.typecode, "illegal type")))

        yield -1, d

        while True:
            yield -2, []


############################################################
## PySide / PyQt Resolver
############################################################


class QtResolver(BaseResolver):
    """
    Class used to resolve the Qt implementations.
    """

    def resolve(self, var, attribute):
        """
        Public method to get an attribute from a variable.

        @param var variable to extract an attribute or value from
        @type Qt objects
        @param attribute name of the attribute to extract
        @type str
        @return value of the attribute
        @rtype Any
        """
        if attribute == "internalPointer":
            return var.internalPointer()

        return getattr(var, attribute, None)

    def getVariableList(self, var):
        """
        Public method to get the attributes of a variable as a list.

        @param var variable to be converted
        @type Any
        @yield tuple containing the batch start index and a list
            containing the variable attributes
        @ytype tuple of (int, list)
        """
        d = []
        attributes = ()
        # Gently handle exception which could occur as special
        # cases, e.g. already deleted C++ objects, str conversion...
        with contextlib.suppress(Exception):  # secok
            qttype = type(var).__name__

            if qttype in ("QLabel", "QPushButton"):
                attributes = ("text",)
            elif qttype == "QByteArray":
                d.append(("bytes", bytes(var)))
                d.append(("hex", "QByteArray", "{0}".format(var.toHex())))
                d.append(("base64", "QByteArray", "{0}".format(var.toBase64())))
                d.append(
                    (
                        "percent encoding",
                        "QByteArray",
                        "{0}".format(var.toPercentEncoding()),
                    )
                )
            elif qttype in ("QPoint", "QPointF"):
                attributes = ("x", "y")
            elif qttype in ("QRect", "QRectF"):
                attributes = ("x", "y", "width", "height")
            elif qttype in ("QSize", "QSizeF"):
                attributes = ("width", "height")
            elif qttype == "QColor":
                attributes = ("name",)
                r, g, b, a = var.getRgb()
                d.append(("rgba", "{0:d}, {1:d}, {2:d}, {3:d}".format(r, g, b, a)))
                h, s, v, a = var.getHsv()
                d.append(("hsva", "{0:d}, {1:d}, {2:d}, {3:d}".format(h, s, v, a)))
                c, m, y, k, a = var.getCmyk()
                d.append(
                    ("cmyka", "{0:d}, {1:d}, {2:d}, {3:d}, {4:d}".format(c, m, y, k, a))
                )
            elif qttype in ("QDate", "QTime", "QDateTime"):
                d.append((qttype[1:].lower(), var.toString()))
            elif qttype == "QDir":
                attributes = ("path", "absolutePath", "canonicalPath")
            elif qttype == "QFile":
                attributes = ("fileName",)
            elif qttype == "QFont":
                attributes = ("family", "pointSize", "weight", "bold", "italic")
            elif qttype == "QUrl":
                d.append(("url", var.toString()))
                attributes = ("scheme", "userName", "password", "host", "port", "path")
            elif qttype == "QModelIndex":
                valid = var.isValid()
                d.append(("valid", valid))
                if valid:
                    d.append(("internalPointer", var.internalPointer()))
                    attributes = ("row", "column", "internalId")
            elif qttype in ("QRegExp", "QRegularExpression"):
                attributes = ("pattern",)

            # GUI stuff
            elif qttype == "QAction":
                d.append(("shortcut", var.shortcut().toString()))
                attributes = ("objectName", "text", "iconText", "toolTip", "whatsThis")

            elif qttype == "QKeySequence":
                d.append(("keySequence", var.toString()))

            # XML stuff
            elif qttype == "QDomAttr":
                attributes = ("name", "var")
            elif qttype in ("QDomCharacterData", "QDomComment", "QDomText"):
                attributes = ("data",)
            elif qttype == "QDomDocument":
                d.append(("text", var.toString()))
            elif qttype == "QDomElement":
                attributes = ("tagName", "text")

            # Networking stuff
            elif qttype == "QHostAddress":
                d.append(("address", var.toString()))

            # PySide specific
            elif qttype == "EnumType":  # Not in PyQt possible
                for key, value in var.values.items():
                    d.append((key, int(value)))

        for attribute in attributes:
            d.append((attribute, getattr(var, attribute)()))

        # add additional fields
        if qttype != "EnumType":
            d.extend(super().getVariableList(var))

        yield -1, d
        while True:
            yield -2, []


defaultResolver = DefaultResolver()
dictResolver = DictResolver()
listResolver = ListResolver()
dictViewResolver = DictViewResolver()
setResolver = SetResolver()
ndarrayResolver = NdArrayResolver()
multiValueDictResolver = MultiValueDictResolver()
arrayResolver = ArrayResolver()
qtResolver = QtResolver()


############################################################
## Methods to determine the type of a variable and the
## resolver class to use
############################################################

_TypeMap = _ArrayTypes = None  # noqa: U200
_TryArray = _TryNumpy = _TryDjango = True
_MapCount = 0


def _initTypeMap():
    """
    Protected function to initialize the type map.
    """
    global _TypeMap

    # Type map for special handling of array types.
    # All other types not listed here use the default resolver.
    _TypeMap = [
        (tuple, listResolver),
        (list, listResolver),
        (dict, dictResolver),
        (set, setResolver),
        (frozenset, setResolver),
        (ItemsView, dictViewResolver),  # Since Python 3.0
        (KeysView, dictViewResolver),
        (ValuesView, dictViewResolver),
    ]


# Initialize the static type map
_initTypeMap()


def updateTypeMap():
    """
    Public function to update the type map based on module imports.
    """
    global _TypeMap, _ArrayTypes, _TryArray, _TryNumpy, _TryDjango, _MapCount

    # array.array may not be imported (yet)
    if _TryArray and "array" in sys.modules:
        import array  # __IGNORE_WARNING_I10__

        _TypeMap.append((array.array, arrayResolver))
        _TryArray = False

    # numpy may not be imported (yet)
    if _TryNumpy and "numpy" in sys.modules:
        import numpy  # __IGNORE_WARNING_I10__

        _TypeMap.append((numpy.ndarray, ndarrayResolver))
        _TryNumpy = False

    # django may not be imported (yet)
    if _TryDjango and "django" in sys.modules:
        from django.utils.datastructures import MultiValueDict  # __IGNORE_WARNING_I10__

        # it should go before dict
        _TypeMap.insert(0, (MultiValueDict, multiValueDictResolver))
        _TryDjango = False

    # If _TypeMap changed, rebuild the _ArrayTypes tuple
    if _MapCount != len(_TypeMap):
        _ArrayTypes = tuple(typ for typ, _resolver in _TypeMap)
        _MapCount = len(_TypeMap)


def getResolver(obj):
    """
    Public method to get the resolver based on the type info of an object.

    @param obj object to get resolver for
    @type Any
    @return resolver
    @rtype BaseResolver
    """
    # Between PyQt and PySide the returned type is different (class vs. type)
    typeStr = str(type(obj)).split(" ", 1)[-1]
    typeStr = typeStr[1:-2]

    if typeStr.startswith(ConfigQtNames) and typeStr.endswith(ConfigKnownQtTypes):
        return qtResolver

    for typeData, resolver in _TypeMap:  # __IGNORE_WARNING_M507__
        if isinstance(obj, typeData):
            return resolver

    return defaultResolver
