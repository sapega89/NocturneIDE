# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module defining the different Python types and their display strings.
"""

from PyQt6.QtCore import QT_TRANSLATE_NOOP

# Variable type definitions
ConfigVarTypeDispStrings = {
    "__": QT_TRANSLATE_NOOP("Variable Types", "Hidden Attributes"),
    "NoneType": QT_TRANSLATE_NOOP("Variable Types", "None"),
    "bool": QT_TRANSLATE_NOOP("Variable Types", "Boolean"),
    "int": QT_TRANSLATE_NOOP("Variable Types", "Integer"),
    "float": QT_TRANSLATE_NOOP("Variable Types", "Float"),
    "complex": QT_TRANSLATE_NOOP("Variable Types", "Complex"),
    "str": QT_TRANSLATE_NOOP("Variable Types", "String"),
    "tuple": QT_TRANSLATE_NOOP("Variable Types", "Tuple"),
    "list": QT_TRANSLATE_NOOP("Variable Types", "List/Array"),
    "dict": QT_TRANSLATE_NOOP("Variable Types", "Dictionary/Hash/Map"),
    "dict-proxy": QT_TRANSLATE_NOOP("Variable Types", "Dictionary Proxy"),
    "set": QT_TRANSLATE_NOOP("Variable Types", "Set"),
    "frozenset": QT_TRANSLATE_NOOP("Variable Types", "Frozen Set"),
    "file": QT_TRANSLATE_NOOP("Variable Types", "File"),
    "range": QT_TRANSLATE_NOOP("Variable Types", "Range"),
    "slice": QT_TRANSLATE_NOOP("Variable Types", "Slice"),
    "buffer": QT_TRANSLATE_NOOP("Variable Types", "Buffer"),
    "class": QT_TRANSLATE_NOOP("Variable Types", "Class"),
    "instance": QT_TRANSLATE_NOOP("Variable Types", "Class Instance"),
    "method": QT_TRANSLATE_NOOP("Variable Types", "Class Method"),
    "property": QT_TRANSLATE_NOOP("Variable Types", "Class Property"),
    "generator": QT_TRANSLATE_NOOP("Variable Types", "Generator"),
    "function": QT_TRANSLATE_NOOP("Variable Types", "Function"),
    "builtin_function_or_method": QT_TRANSLATE_NOOP(
        "Variable Types", "Builtin Function"
    ),
    "code": QT_TRANSLATE_NOOP("Variable Types", "Code"),
    "module": QT_TRANSLATE_NOOP("Variable Types", "Module"),
    "ellipsis": QT_TRANSLATE_NOOP("Variable Types", "Ellipsis"),
    "traceback": QT_TRANSLATE_NOOP("Variable Types", "Traceback"),
    "frame": QT_TRANSLATE_NOOP("Variable Types", "Frame"),
    "bytes": QT_TRANSLATE_NOOP("Variable Types", "Bytes"),
    "special_attributes": QT_TRANSLATE_NOOP("Variable Types", "Special Attributes"),
    "dict_items": QT_TRANSLATE_NOOP("Variable Types", "Dict. Items View"),
    "dict_keys": QT_TRANSLATE_NOOP("Variable Types", "Dict. Keys View"),
    "dict_values": QT_TRANSLATE_NOOP("Variable Types", "Dict. Values View"),
    "async_generator": QT_TRANSLATE_NOOP("Variable Types", "Asynchronous Generator"),
    "coroutine": QT_TRANSLATE_NOOP("Variable Types", "Coroutine"),
    "mappingproxy": QT_TRANSLATE_NOOP("Variable Types", "Mapping Proxy"),
}
