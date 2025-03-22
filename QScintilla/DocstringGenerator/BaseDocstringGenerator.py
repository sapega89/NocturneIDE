# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a docstring generator base class.
"""

import contextlib
import importlib
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu

from eric7 import Preferences
from eric7.EricWidgets.EricApplication import ericApp


def getIndentStr(text):
    """
    Function to get the indentation of a text.

    @param text text to extract indentation from
    @type str
    @return indentation string
    @rtype str
    """
    indent = ""

    ret = re.match(r"(\s*)", text)
    if ret:
        indent = ret.group(1)

    return indent


class BaseDocstringGenerator:
    """
    Class implementing a docstring generator base class.
    """

    def __init__(self, editor):
        """
        Constructor

        @param editor reference to the editor widget
        @type Editor
        """
        self.editor = editor

    def isFunctionStart(self, text):  # noqa: U100
        """
        Public method to test, if a text is the start of a function or method
        definition.

        @param text line of text to be tested (unused)
        @type str
        @return flag indicating that the given text starts a function or
            method definition (always False)
        @rtype bool
        """
        return False

    def hasFunctionDefinition(self, cursorPosition):  # noqa: U100
        """
        Public method to test, if the cursor is right below a function
        definition.

        @param cursorPosition current cursor position (line and column) (unused)
        @type tuple of (int, int)
        @return flag indicating cursor is right below a function definition
        @rtype bool
        """
        return False

    def isDocstringIntro(self, cursorPosition):  # noqa: U100
        """
        Public function to test, if the line up to the cursor position might be
        introducing a docstring.

        @param cursorPosition current cursor position (line and column) (unused)
        @type tuple of (int, int)
        @return flag indicating a potential start of a docstring
        @rtype bool
        """
        return False

    def insertDocstring(self, cursorPosition, fromStart=True):  # noqa: U100
        """
        Public method to insert a docstring for the function at the cursor
        position.

        @param cursorPosition position of the cursor (line and index) (unused)
        @type tuple of (int, int)
        @param fromStart flag indicating that the editor text cursor is placed
            on the line starting the function definition (unused)
        @type bool
        """
        # just do nothing in the base class
        return

    def insertDocstringFromShortcut(self, cursorPosition):  # noqa: U100
        """
        Public method to insert a docstring for the function at the cursor
        position initiated via a keyboard shortcut.

        @param cursorPosition position of the cursor (line and index) (unused)
        @type tuple of (int, int)
        """
        # just do nothing in the base class
        return

    def getDocstringType(self):
        """
        Public method to determine the docstring type to be generated.

        @return docstring type (one of 'ericdoc', 'numpydoc', 'googledoc',
            'sphinxdoc')
        @rtype str
        """
        docstringStyle = ""

        project = ericApp().getObject("Project")
        filename = self.editor.getFileName()
        if filename and project.isOpen() and project.isProjectFile(filename):
            docstringStyle = project.getDocstringType().lower()

        if docstringStyle == "":
            docstringStyle = Preferences.getEditor("DocstringType")

        return docstringStyle

    def _generateDocstringList(self, functionInfo, docstringType):
        """
        Protected method to generate type specific docstrings based on the
        extracted function information.

        @param functionInfo reference to the function info object
        @type FunctionInfo
        @param docstringType kind of docstring to be generated
        @type str
        @return list of docstring lines
        @rtype str
        """
        generatorModuleMapping = {
            "ericdoc": ".EricdocGenerator",
            "numpydoc": ".NumpydocGenerator",
            "googledoc": ".GoogledocGenerator",
            "sphinxdoc": ".SphinxdocGenerator",
        }
        with contextlib.suppress(KeyError):
            mod = importlib.import_module(
                generatorModuleMapping[docstringType], __package__
            )
            return mod.generateDoc(functionInfo, self.editor)

        return []


class FunctionInfo:
    """
    Class implementing an object to store function information.

    Methods to extract the relevant information need to be implemented in
    language specific subclasses.
    """

    def __init__(self):
        """
        Constructor
        """
        self.hasInfo = False
        self.funcionText = ""
        self.argumentsText = ""

        self.functionName = ""
        # name of the function
        self.functionIndent = ""
        # indentation fo function definition
        self.argumentsList = []
        # list of tuples with name, type and value
        self.returnTypeAnnotated = None
        # return type extracted from type annotation
        self.returnValueInBody = []
        # return values extracted from function body
        self.raiseList = None
        # exceptions raised by function
        self.hasYield = False
        # function is a generator
        self.functionType = ""
        # function type with these values
        # classmethod, staticmethod, qtslot, constructor or empty (i.e.
        # standard)
        self.isAsync = False
        # function is an asynchronous function, i.e. async def f():
        self.visibility = ""
        # function visibility with allowed values:
        # public, protected, private or special (i.e. starting and
        # ending with '__'
        self.eventHandler = False
        # function is an event handler method

    def parseDefinition(self, text, quote, quoteReplace):
        """
        Public method to parse the function definition text.

        Note: This method should be overwritten in subclasses.

        @param text text containing the function definition
        @type str
        @param quote quote string to be replaced
        @type str
        @param quoteReplace quote string to replace the original
        @type str
        """
        pass

    def parseBody(self, text):
        """
        Public method to parse the function body text.

        Note: This method should be overwritten in subclasses.

        @param text function body text
        @type str
        """
        pass


class DocstringMenuForEnterOnly(QMenu):
    """
    Class implementing a special menu reacting to the enter/return keys only.

    If a keyboard input is not the "enter key", the menu is closed and the
    input is inserted to the code editor.
    """

    def __init__(self, editor):
        """
        Constructor

        @param editor reference to the editor
        @type Editor
        """
        super().__init__(editor)
        self.__editor = editor

    def keyPressEvent(self, evt):
        """
        Protected method to handle key press events.

        @param evt reference to the key press event object
        @type QKeyEvent
        """
        key = evt.key()
        if key not in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            self.__editor.keyPressEvent(evt)
            self.close()
        else:
            super().keyPressEvent(evt)
