# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a docstring generator for Python.
"""

import collections
import re

from .BaseDocstringGenerator import BaseDocstringGenerator, FunctionInfo, getIndentStr


class PyDocstringGenerator(BaseDocstringGenerator):
    """
    Class implementing a docstring generator for Python.
    """

    def __init__(self, editor):
        """
        Constructor

        @param editor reference to the editor widget
        @type Editor
        """
        super().__init__(editor)

        self.__quote3 = '"""'
        self.__quote3Alternate = "'''"

    def isFunctionStart(self, text):
        """
        Public method to test, if a text is the start of a function or method
        definition.

        @param text line of text to be tested
        @type str
        @return flag indicating that the given text starts a function or
            method definition
        @rtype bool
        """
        if isinstance(text, str):
            text = text.lstrip()
            if text.startswith(("def ", "async def ")):
                return True

        return False

    def hasFunctionDefinition(self, cursorPosition):
        """
        Public method to test, if the cursor is right below a function
        definition.

        @param cursorPosition current cursor position (line and column)
        @type tuple of (int, int)
        @return flag indicating cursor is right below a function definition
        @rtype bool
        """
        return self.__getFunctionDefinitionFromBelow(cursorPosition) is not None

    def isDocstringIntro(self, cursorPosition):
        """
        Public function to test, if the line up to the cursor position might be
        introducing a docstring.

        @param cursorPosition current cursor position (line and column)
        @type tuple of (int, int)
        @return flag indicating a potential start of a docstring
        @rtype bool
        """
        cline, cindex = cursorPosition
        lineToCursor = self.editor.text(cline)[:cindex]
        return self.__isTripleQuotesStart(lineToCursor)

    def __isTripleQuotesStart(self, text):
        """
        Private method to test, if the given text is the start of a triple
        quoted string.

        @param text text to be inspected
        @type str
        @return flag indicating a triple quote start
        @rtype bool
        """
        docstringTriggers = ('"""', 'r"""', "'''", "r'''")
        if text.lstrip() in docstringTriggers:
            return True

        return False

    def insertDocstring(self, cursorPosition, fromStart=True):
        """
        Public method to insert a docstring for the function at the cursor
        position.

        @param cursorPosition position of the cursor (line and index)
        @type tuple of (int, int)
        @param fromStart flag indicating that the editor text cursor is placed
            on the line starting the function definition
        @type bool
        """
        if fromStart:
            self.__functionStartLine = cursorPosition[0]
            docstring, insertPos, newCursorLine = self.__generateDocstringFromStart()
        else:
            docstring, insertPos, newCursorLine = self.__generateDocstringFromBelow(
                cursorPosition
            )

        if docstring:
            self.editor.beginUndoAction()
            self.editor.insertAt(docstring, *insertPos)

            if not fromStart:
                # correct triple quote indentation if neccessary
                functionIndent = self.editor.indentation(self.__functionStartLine)
                quoteIndent = self.editor.indentation(insertPos[0])

                # step 1: unindent quote line until indentation is zero
                while quoteIndent > 0:
                    self.editor.unindent(insertPos[0])
                    quoteIndent = self.editor.indentation(insertPos[0])

                # step 2: indent quote line until indentation is one greater
                # than function definition line
                while quoteIndent <= functionIndent:
                    self.editor.indent(insertPos[0])
                    quoteIndent = self.editor.indentation(insertPos[0])

            self.editor.endUndoAction()
            self.editor.setCursorPosition(
                newCursorLine, len(self.editor.text(newCursorLine)) - 1
            )

    def insertDocstringFromShortcut(self, cursorPosition):
        """
        Public method to insert a docstring for the function at the cursor
        position initiated via a keyboard shortcut.

        @param cursorPosition position of the cursor (line and index)
        @type tuple of (int, int)
        """
        result = self.__getFunctionDefinitionFromBelow(cursorPosition)
        if result is not None:
            # cursor is on the line after the function definition
            cline = cursorPosition[0] - 1
            while not self.isFunctionStart(self.editor.text(cline)):
                cline -= 1
            self.__functionStartLine = cline
        elif self.isFunctionStart(self.editor.text(cursorPosition[0])):
            # cursor is on the start line of the function definition
            self.__functionStartLine = cursorPosition[0]
        else:
            # neither after the function definition nor at the start
            # just do nothing
            return

        docstring, insertPos, newCursorLine = self.__generateDocstringFromStart()
        if docstring:
            self.editor.beginUndoAction()
            self.editor.insertAt(docstring, *insertPos)
            self.editor.endUndoAction()
            self.editor.setCursorPosition(
                newCursorLine, len(self.editor.text(newCursorLine)) - 1
            )

    def __getIndentationInsertString(self, text):
        """
        Private method to create the indentation string for the docstring.

        @param text text to based the indentation on
        @type str
        @return indentation string for docstring
        @rtype str
        """
        indent = getIndentStr(text)
        indentWidth = self.editor.indentationWidth()
        if indentWidth == 0:
            indentWidth = self.editor.tabWidth()

        return indent + indentWidth * " "

    #######################################################################
    ## Methods to generate the docstring when the text cursor is on the
    ## line starting the function definition.
    #######################################################################

    def __generateDocstringFromStart(self):
        """
        Private method to generate a docstring based on the cursor being
        placed on the first line of the definition.

        @return tuple containing the docstring and a tuple containing the
            insertion line and index
        @rtype tuple of (str, tuple(int, int))
        """
        result = self.__getFunctionDefinitionFromStart()
        if result:
            functionDefinition, functionDefinitionLength = result

            insertLine = self.__functionStartLine + functionDefinitionLength
            indentation = self.__getIndentationInsertString(functionDefinition)
            sep = self.editor.getLineSeparator()
            bodyStart = insertLine

            docstringList = self.__generateDocstring('"', functionDefinition, bodyStart)
            if docstringList:
                if self.getDocstringType() == "ericdoc":
                    docstringList.insert(0, self.__quote3)
                    newCursorLine = insertLine + 1
                else:
                    docstringList[0] = self.__quote3 + docstringList[0]
                    newCursorLine = insertLine
                docstringList.append(self.__quote3)
                for index, line in enumerate(docstringList):
                    docstringList[index] = (
                        indentation + line if bool(line.strip()) else ""
                    )
                return sep.join(docstringList) + sep, (insertLine, 0), newCursorLine

        return "", (0, 0), 0

    def __getFunctionDefinitionFromStart(self):
        """
        Private method to extract the function definition based on the cursor
        being placed on the first line of the definition.

        @return text containing the function definition
        @rtype str
        """
        startLine = self.__functionStartLine
        endLine = startLine + min(
            self.editor.lines() - startLine, 20  # max. 20 lines of definition allowed
        )
        isFirstLine = True
        functionIndent = ""
        functionTextList = []

        for lineNo in range(startLine, endLine):
            text = self.editor.text(lineNo).rstrip()
            if isFirstLine:
                if not self.isFunctionStart(text):
                    return None

                functionIndent = getIndentStr(text)
                isFirstLine = False
            else:
                currentIndent = getIndentStr(text)
                if currentIndent <= functionIndent or self.isFunctionStart(text):
                    # no function body exists
                    return None
                if text.strip() == "":
                    # empty line, illegal/incomplete function definition
                    return None

            if text.endswith("\\"):
                text = text[:-1]

            functionTextList.append(text)

            if text.endswith(":"):
                # end of function definition reached
                functionDefinitionLength = len(functionTextList)

                # check, if function is decorated with a supported one
                if startLine > 0:
                    decoratorLine = self.editor.text(startLine - 1)
                    if (
                        "@classmethod" in decoratorLine
                        or "@staticmethod" in decoratorLine
                        or "pyqtSlot" in decoratorLine
                        or "Slot" in decoratorLine  # PyQt slot  # PySide slot
                    ):
                        functionTextList.insert(0, decoratorLine)

                return "".join(functionTextList), functionDefinitionLength

        return None

    #######################################################################
    ## Methods to generate the docstring when the text cursor is on the
    ## line after the function definition (e.g. after a triple quote).
    #######################################################################

    def __generateDocstringFromBelow(self, cursorPosition):
        """
        Private method to generate a docstring when the given position is on
        the line below the end of the definition.

        @param cursorPosition position of the cursor (line and index)
        @type tuple of (int, int)
        @return tuple containing the docstring and a tuple containing the
            insertion line and index
        @rtype tuple of (str, tuple(int, int))
        """
        functionDefinition = self.__getFunctionDefinitionFromBelow(cursorPosition)
        if functionDefinition:
            lineTextToCursor = self.editor.text(cursorPosition[0])[: cursorPosition[1]]
            insertLine = cursorPosition[0]
            indentation = self.__getIndentationInsertString(functionDefinition)
            sep = self.editor.getLineSeparator()
            bodyStart = insertLine

            docstringList = self.__generateDocstring('"', functionDefinition, bodyStart)
            if docstringList:
                if self.__isTripleQuotesStart(lineTextToCursor):
                    if self.getDocstringType() == "ericdoc":
                        docstringList.insert(0, "")
                        newCursorLine = cursorPosition[0] + 1
                    else:
                        newCursorLine = cursorPosition[0]
                    docstringList.append("")
                else:
                    if self.getDocstringType() == "ericdoc":
                        docstringList.insert(0, self.__quote3)
                        newCursorLine = cursorPosition[0] + 1
                    else:
                        docstringList[0] = self.__quote3 + docstringList[0]
                        newCursorLine = cursorPosition[0]
                    docstringList.append(self.__quote3)
                for index, line in enumerate(docstringList):
                    docstringList[index] = (
                        indentation + line if bool(line.strip()) else ""
                    )
                docstring = sep.join(docstringList) + indentation
                return docstring, cursorPosition, newCursorLine

        return "", (0, 0), 0

    def __getFunctionDefinitionFromBelow(self, cursorPosition):
        """
        Private method to extract the function definition based on the cursor
        being placed on the first line after the definition.

        @param cursorPosition current cursor position (line and column)
        @type tuple of (int, int)
        @return text containing the function definition
        @rtype str
        """
        startLine = cursorPosition[0] - 1
        endLine = startLine - min(startLine, 20) - 1
        # max. 20 lines of definition allowed
        if endLine < -1:
            endLine = -1
        isFirstLine = True
        functionTextList = []

        for lineNo in range(startLine, endLine, -1):
            text = self.editor.text(lineNo).rstrip()
            if isFirstLine:
                if not text.endswith(":"):
                    return None
                isFirstLine = False
            elif text.endswith(":") or text == "":
                return None

            if text.endswith("\\"):
                text = text[:-1]

            functionTextList.insert(0, text)

            if self.isFunctionStart(text):
                # start of function definition reached
                self.__functionStartLine = lineNo

                # check, if function is decorated with a supported one
                if lineNo > 0:
                    decoratorLine = self.editor.text(lineNo - 1)
                    if (
                        "@classmethod" in decoratorLine
                        or "@staticmethod" in decoratorLine
                        or "pyqtSlot" in decoratorLine
                        or "Slot" in decoratorLine  # PyQt slot  # PySide slot
                    ):
                        functionTextList.insert(0, decoratorLine)

                return "".join(functionTextList)

        return None

    #######################################################################
    ## Methods to generate the docstring contents.
    #######################################################################

    def __getFunctionBody(self, functionIndent, startLine):
        """
        Private method to get the function body.

        @param functionIndent indentation string of the function definition
        @type str
        @param startLine starting line for the extraction process
        @type int
        @return text containing the function body
        @rtype str
        """
        bodyList = []

        for line in range(startLine, self.editor.lines()):
            text = self.editor.text(line)
            textIndent = getIndentStr(text)

            if text.strip() == "":
                pass
            elif len(textIndent) <= len(functionIndent):
                break

            bodyList.append(text)

        return "".join(bodyList)

    def __generateDocstring(self, quote, functionDef, bodyStartLine):
        """
        Private method to generate the list of docstring lines.

        @param quote quote string
        @type str
        @param functionDef text containing the function definition
        @type str
        @param bodyStartLine starting line of the function body
        @type int
        @return list of docstring lines
        @rtype list of str
        """
        quote3 = 3 * quote
        if quote == '"':
            quote3replace = 3 * "'"
        elif quote == "'":
            quote3replace = 3 * '"'
        functionInfo = PyFunctionInfo()
        functionInfo.parseDefinition(functionDef, quote3, quote3replace)

        if functionInfo.hasInfo:
            functionBody = self.__getFunctionBody(
                functionInfo.functionIndent, bodyStartLine
            )

            if functionBody:
                functionInfo.parseBody(functionBody)

            docstringType = self.getDocstringType()
            return self._generateDocstringList(functionInfo, docstringType)

        return []


class PyFunctionInfo(FunctionInfo):
    """
    Class implementing an object to extract and store function information.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

    def __isCharInPairs(self, posChar, pairs):
        """
        Private method to test, if the given character position is between
        pairs of brackets or quotes.

        @param posChar character position to be tested
        @type int
        @param pairs list containing pairs of positions
        @type list of tuple of (int, int)
        @return flag indicating the position is in between
        @rtype bool
        """
        return any(posLeft < posChar < posRight for (posLeft, posRight) in pairs)

    def __findQuotePosition(self, text):
        """
        Private method to find the start and end position of pairs of quotes.

        @param text text to be parsed
        @type str
        @return list of tuple with start and end position of pairs of quotes
        @rtype list of tuple of (int, int)
        @exception IndexError raised when a matching close quote is missing
        """
        pos = []
        foundLeftQuote = False

        for index, character in enumerate(text):
            if foundLeftQuote is False:
                if character in ("'", '"'):
                    foundLeftQuote = True
                    quote = character
                    leftPos = index
            else:
                if character == quote and text[index - 1] != "\\":
                    pos.append((leftPos, index))
                    foundLeftQuote = False

        if foundLeftQuote:
            raise IndexError("No matching close quote at: {0}".format(leftPos))

        return pos

    def __findBracketPosition(self, text, bracketLeft, bracketRight, posQuote):
        """
        Private method to find the start and end position of pairs of brackets.

        https://stackoverflow.com/questions/29991917/
        indices-of-matching-parentheses-in-python

        @param text text to be parsed
        @type str
        @param bracketLeft character of the left bracket
        @type str
        @param bracketRight character of the right bracket
        @type str
        @param posQuote list of tuple with start and end position of pairs
            of quotes
        @type list of tuple of (int, int)
        @return list of tuple with start and end position of pairs of brackets
        @rtype list of tuple of (int, int)
        @exception IndexError raised when a closing or opening bracket is
            missing
        """
        pos = []
        pstack = []

        for index, character in enumerate(text):
            if character == bracketLeft and not self.__isCharInPairs(index, posQuote):
                pstack.append(index)
            elif character == bracketRight and not self.__isCharInPairs(
                index, posQuote
            ):
                if len(pstack) == 0:
                    raise IndexError("No matching closing parens at: {0}".format(index))
                pos.append((pstack.pop(), index))

        if len(pstack) > 0:
            raise IndexError("No matching opening parens at: {0}".format(pstack.pop()))

        return pos

    def __splitArgumentToNameTypeValue(self, argumentsList, quote, quoteReplace):
        """
        Private method to split some argument text to name, type and value.

        @param argumentsList list of function argument definitions
        @type list of str
        @param quote quote string to be replaced
        @type str
        @param quoteReplace quote string to replace the original
        @type str
        """
        for arg in argumentsList:
            hasType = False
            hasValue = False

            colonPosition = arg.find(":")
            equalPosition = arg.find("=")

            if equalPosition > -1:
                hasValue = True

            if colonPosition > -1 and (not hasValue or equalPosition > colonPosition):
                # exception for def foo(arg1=":")
                hasType = True

            if hasValue and hasType:
                argName = arg[0:colonPosition].strip()
                argType = arg[colonPosition + 1 : equalPosition].strip()
                argValue = arg[equalPosition + 1 :].strip()
            elif not hasValue and hasType:
                argName = arg[0:colonPosition].strip()
                argType = arg[colonPosition + 1 :].strip()
                argValue = None
            elif hasValue and not hasType:
                argName = arg[0:equalPosition].strip()
                argType = None
                argValue = arg[equalPosition + 1 :].strip()
            else:
                argName = arg.strip()
                argType = None
                argValue = None
            if argValue and quote:
                # sanitize argValue with respect to quotes
                argValue = argValue.replace(quote, quoteReplace)

            self.argumentsList.append((argName, argType, argValue))

    def __splitArgumentsTextToList(self, argumentsText):
        """
        Private method to split the given arguments text into a list of
        arguments.

        This function uses a comma to separate arguments and ignores a comma in
        brackets and quotes.

        @param argumentsText text containing the list of arguments
        @type str
        @return list of individual argument texts
        @rtype list of str
        """
        argumentsList = []
        indexFindStart = 0
        indexArgStart = 0

        try:
            posQuote = self.__findQuotePosition(argumentsText)
            posRound = self.__findBracketPosition(argumentsText, "(", ")", posQuote)
            posCurly = self.__findBracketPosition(argumentsText, "{", "}", posQuote)
            posSquare = self.__findBracketPosition(argumentsText, "[", "]", posQuote)
        except IndexError:
            return None

        while True:
            posComma = argumentsText.find(",", indexFindStart)

            if posComma == -1:
                break

            indexFindStart = posComma + 1

            if (
                self.__isCharInPairs(posComma, posRound)
                or self.__isCharInPairs(posComma, posCurly)
                or self.__isCharInPairs(posComma, posSquare)
                or self.__isCharInPairs(posComma, posQuote)
            ):
                continue

            argumentsList.append(argumentsText[indexArgStart:posComma])
            indexArgStart = posComma + 1

        if indexArgStart < len(argumentsText):
            argumentsList.append(argumentsText[indexArgStart:])

        return argumentsList

    def parseDefinition(self, text, quote, quoteReplace):
        """
        Public method to parse the function definition text.

        @param text text containing the function definition
        @type str
        @param quote quote string to be replaced
        @type str
        @param quoteReplace quote string to replace the original
        @type str
        """
        self.functionIndent = getIndentStr(text)

        textList = text.splitlines()
        if textList[0].lstrip().startswith("@"):
            # first line of function definition is a decorator
            decorator = textList.pop(0).strip()
            if decorator == "@staticmethod":
                self.functionType = "staticmethod"
            elif decorator == "@classmethod":
                self.functionType = "classmethod"
            elif re.match(r"@(PyQt[456]\.)?(QtCore\.)?pyqtSlot", decorator) or re.match(
                r"@(PySide[26]\.)?(QtCore\.)?Slot", decorator
            ):
                self.functionType = "qtslot"

        text = "".join(textList).strip()

        if text.startswith("async def "):
            self.isAsync = True

        returnType = re.search(r"->[ ]*([a-zA-Z0-9_,()\[\] ]*):$", text)
        if returnType:
            self.returnTypeAnnotated = returnType.group(1)
            textEnd = text.rfind(returnType.group(0))
        else:
            self.returnTypeAnnotated = None
            textEnd = len(text)

        positionArgumentsStart = text.find("(") + 1
        positionArgumentsEnd = text.rfind(")", positionArgumentsStart, textEnd)

        self.argumentsText = text[positionArgumentsStart:positionArgumentsEnd]

        argumentsList = self.__splitArgumentsTextToList(self.argumentsText)
        if argumentsList is not None:
            self.hasInfo = True
            self.__splitArgumentToNameTypeValue(argumentsList, quote, quoteReplace)

        self.functionName = (
            text[: positionArgumentsStart - 1]
            .replace("async def ", "")
            .replace("def ", "")
        )
        if self.functionName == "__init__":
            self.functionType = "constructor"
        elif self.functionName.startswith("__"):
            if self.functionName.endswith("__"):
                self.visibility = "special"
            else:
                self.visibility = "private"
        elif self.functionName.startswith("_"):
            self.visibility = "protected"
        else:
            self.visibility = "public"

        if self.functionName.endswith("Event") or self.functionName in ("eventFilter",):
            self.eventHandler = True
            # Qt event handlers are protected
            self.visibility = "protected"
        elif self.functionName in ("event",):
            self.eventHandler = True

    def parseBody(self, text):
        """
        Public method to parse the function body text.

        @param text function body text
        @type str
        """
        raiseRe = re.findall(r"[ \t]raise ([a-zA-Z0-9_]*)", text)
        if len(raiseRe) > 0:
            self.raiseList = [x.strip() for x in raiseRe]
            # remove duplicates from list while keeping it in the order
            self.raiseList = list(collections.OrderedDict.fromkeys(self.raiseList))

        yieldRe = re.search(r"[ \t]yield ", text)
        if yieldRe:
            self.hasYield = True

        # get return value
        returnPattern = r"return |yield "
        lineList = text.splitlines()
        returnFound = False
        returnTmpLine = ""

        for line in lineList:
            line = line.strip()

            if returnFound is False and re.match(returnPattern, line):
                returnFound = True

            if returnFound:
                returnTmpLine += line
                # check the integrity of line
                try:
                    quotePos = self.__findQuotePosition(returnTmpLine)

                    if returnTmpLine.endswith("\\"):
                        returnTmpLine = returnTmpLine[:-1]
                        continue

                    self.__findBracketPosition(returnTmpLine, "(", ")", quotePos)
                    self.__findBracketPosition(returnTmpLine, "{", "}", quotePos)
                    self.__findBracketPosition(returnTmpLine, "[", "]", quotePos)
                except IndexError:
                    continue

                returnValue = re.sub(returnPattern, "", returnTmpLine)
                self.returnValueInBody.append(returnValue)

                returnFound = False
                returnTmpLine = ""
