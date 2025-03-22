# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing typing completers for the various supported programming languages.
"""

import collections
import contextlib
import importlib

# Typing Completer Registry Item
# Each item contains two function references.
# createCompleter:  A function that must accept two arguments, a reference to the editor
#                   and a reference to the parent object. It must return an instantiated
#                   typing completer object.
# createConfigPage: A function that must return a fully populated configuration widget
#                   to be added to the Editor / Typing configuration page. This widget
#                   must have a method "save" to save the entered values.
CompleterRegistryItem = collections.namedtuple(
    "CompleterRegistryItem", ["createCompleter", "createConfigPage"]
)

# The Typing Completer Registry
# Dictionary with the language name as key. Each entry contains a reference to a
# 'CompleterRegistryItem' object.
CompleterRegistry = {}


def registerCompleter(language, createCompleterFunction, createConfigPageFunction):
    """
    Function to register a typing completer for a lexer language.

    @param language lexer language of the typing completer
    @type str
    @param createCompleterFunction reference to a function to instantiate a
        typing completer object
    @type function
    @param createConfigPageFunction reference to a function returning a ready
        populated configuration widget
    @type function
    @exception KeyError raised when the given name is already in use
    """
    global CompleterRegistry

    if language in CompleterRegistry:
        raise KeyError('Typing completer "{0}" already registered.'.format(language))
    else:
        CompleterRegistry[language] = CompleterRegistryItem(
            createCompleter=createCompleterFunction,
            createConfigPage=createConfigPageFunction,
        )


def unregisterTypingCompleter(language):
    """
    Function to unregister a previously registered typing completer.

    @param language lexer language of the typing completer
    @type str
    """
    global CompleterRegistry

    with contextlib.suppress(KeyError):
        del CompleterRegistry[language]


def getCompleter(language, editor, parent=None):
    """
    Module function to instantiate a lexer object for a given language.

    @param language language of the lexer
    @type str
    @param editor reference to the editor object
    @type QScintilla.Editor
    @param parent reference to the parent object (defaults to None)
    @type QObject (optional)
    @return reference to the instantiated typing completer object
    @rtype CompleterBase
    """
    languageCompleterMapping = {
        "Python": ".CompleterPython",
        "Python3": ".CompleterPython",
        "MicroPython": ".CompleterPython",
        "Cython": ".CompleterPython",
        "Ruby": ".CompleterRuby",
        "YAML": ".CompleterYaml",
        "Pygments|TOML": ".CompleterToml",
    }

    if language in languageCompleterMapping:
        mod = importlib.import_module(languageCompleterMapping[language], __package__)
        if mod:
            return mod.createCompleter(editor, parent)

    elif language in CompleterRegistry:
        return CompleterRegistry[language].createCompleter(editor, parent)

    return None
