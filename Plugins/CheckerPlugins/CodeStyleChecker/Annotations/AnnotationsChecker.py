# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a checker for function type annotations.
"""

import ast
import contextlib
import copy
import sys

from functools import lru_cache

import AstUtilities

from .AnnotationsCheckerDefaults import AnnotationsCheckerDefaultArgs
from .AnnotationsEnums import AnnotationType, ClassDecoratorType, FunctionType


class AnnotationsChecker:
    """
    Class implementing a checker for function type annotations.
    """

    Codes = [
        ## Function Annotations
        "A001",
        "A002",
        "A003",
        ## Method Annotations
        "A101",
        "A102",
        ## Return Annotations
        "A201",
        "A202",
        "A203",
        "A204",
        "A205",
        "A206",
        ## Dynamically typed annotations
        "A401",
        ## Type comments
        "A402",
        ## Annotations Future
        "A871",
        "A872",
        "A873",
        ## Annotation Coverage
        "A881",
        ## Annotation Complexity
        "A891",
        "A892",
        ## use of typing.Union (PEP 604)
        "A901",
        ## deprecated 'typing' symbols (PEP 585)
        "A911",
    ]

    def __init__(self, source, filename, tree, select, ignore, expected, repeat, args):
        """
        Constructor

        @param source source code to be checked
        @type list of str
        @param filename name of the source file
        @type str
        @param tree AST tree of the source code
        @type ast.Module
        @param select list of selected codes
        @type list of str
        @param ignore list of codes to be ignored
        @type list of str
        @param expected list of expected codes
        @type list of str
        @param repeat flag indicating to report each occurrence of a code
        @type bool
        @param args dictionary of arguments for the annotation checks
        @type dict
        """
        self.__select = tuple(select)
        self.__ignore = ("",) if select else tuple(ignore)
        self.__expected = expected[:]
        self.__repeat = repeat
        self.__filename = filename
        self.__source = source[:]
        self.__tree = copy.deepcopy(tree)
        self.__args = args

        # statistics counters
        self.counters = {}

        # collection of detected errors
        self.errors = []

        checkersWithCodes = [
            (
                self.__checkFunctionAnnotations,
                (
                    "A001",
                    "A002",
                    "A003",
                    "A101",
                    "A102",
                    "A201",
                    "A202",
                    "A203",
                    "A204",
                    "A205",
                    "A206",
                    "A401",
                    "A402",
                ),
            ),
            (self.__checkAnnotationsFuture, ("A871", "A872", "A873")),
            (self.__checkAnnotationsCoverage, ("A881",)),
            (self.__checkAnnotationComplexity, ("A891", "A892")),
            (self.__checkAnnotationPep604, ("A901",)),
            (self.__checkDeprecatedTypingSymbols, ("A911",)),
        ]

        self.__checkers = []
        for checker, codes in checkersWithCodes:
            if any(not (code and self.__ignoreCode(code)) for code in codes):
                self.__checkers.append(checker)

    def __ignoreCode(self, code):
        """
        Private method to check if the message code should be ignored.

        @param code message code to check for
        @type str
        @return flag indicating to ignore the given code
        @rtype bool
        """
        return code.startswith(self.__ignore) and not code.startswith(self.__select)

    def __error(self, lineNumber, offset, code, *args):
        """
        Private method to record an issue.

        @param lineNumber line number of the issue
        @type int
        @param offset position within line of the issue
        @type int
        @param code message code
        @type str
        @param args arguments for the message
        @type list
        """
        if self.__ignoreCode(code):
            return

        if code in self.counters:
            self.counters[code] += 1
        else:
            self.counters[code] = 1

        # Don't care about expected codes
        if code in self.__expected:
            return

        if code and (self.counters[code] == 1 or self.__repeat):
            # record the issue with one based line number
            self.errors.append(
                {
                    "file": self.__filename,
                    "line": lineNumber + 1,
                    "offset": offset,
                    "code": code,
                    "args": args,
                }
            )

    def run(self):
        """
        Public method to check the given source against annotation issues.
        """
        if not self.__filename:
            # don't do anything, if essential data is missing
            return

        if not self.__checkers:
            # don't do anything, if no codes were selected
            return

        for check in self.__checkers:
            check()

    #######################################################################
    ## Annotations
    ##
    ## adapted from: flake8-annotations v3.1.1
    #######################################################################

    def __checkFunctionAnnotations(self):
        """
        Private method to check for function annotation issues.
        """
        from .AnnotationsFunctionVisitor import FunctionVisitor

        # Type ignores are provided by ast at the module level & we'll need them later
        # when deciding whether or not to emit errors for a given function
        typeIgnoreLineno = {ti.lineno for ti in self.__tree.type_ignores}
        hasMypyIgnoreErrors = any(
            "# mypy: ignore-errors" in line for line in self.__source[:5]
        )

        suppressNoneReturning = self.__args.get(
            "SuppressNoneReturning",
            AnnotationsCheckerDefaultArgs["SuppressNoneReturning"],
        )
        suppressDummyArgs = self.__args.get(
            "SuppressDummyArgs", AnnotationsCheckerDefaultArgs["SuppressDummyArgs"]
        )
        allowUntypedDefs = self.__args.get(
            "AllowUntypedDefs", AnnotationsCheckerDefaultArgs["AllowUntypedDefs"]
        )
        allowUntypedNested = self.__args.get(
            "AllowUntypedNested", AnnotationsCheckerDefaultArgs["AllowUntypedNested"]
        )
        mypyInitReturn = self.__args.get(
            "MypyInitReturn", AnnotationsCheckerDefaultArgs["MypyInitReturn"]
        )
        allowStarArgAny = self.__args.get(
            "AllowStarArgAny", AnnotationsCheckerDefaultArgs["AllowStarArgAny"]
        )
        respectTypeIgnore = self.__args.get(
            "RespectTypeIgnore", AnnotationsCheckerDefaultArgs["RespectTypeIgnore"]
        )

        # Store decorator lists as sets for easier lookup
        dispatchDecorators = set(
            self.__args.get(
                "DispatchDecorators",
                AnnotationsCheckerDefaultArgs["DispatchDecorators"],
            )
        )
        overloadDecorators = set(
            self.__args.get(
                "OverloadDecorators",
                AnnotationsCheckerDefaultArgs["OverloadDecorators"],
            )
        )

        visitor = FunctionVisitor(self.__source)
        visitor.visit(self.__tree)

        # Keep track of the last encountered function decorated by
        # `typing.overload`, if any. Per the `typing` module documentation,
        # a series of overload-decorated definitions must be followed by
        # exactly one non-overload-decorated definition of the same function.
        lastOverloadDecoratedFunctionName = None

        # Iterate over the arguments with missing type hints, by function.
        for function in visitor.functionDefinitions:
            if function.hasTypeComment:
                self.__error(function.lineno - 1, function.col_offset, "A402")

            if function.isDynamicallyTyped() and (
                allowUntypedDefs or (function.isNested and allowUntypedNested)
            ):
                # Skip recording errors from dynamically typed functions
                # or nested functions
                continue

            # Skip recording errors for configured dispatch functions, such as
            # (by default) `functools.singledispatch` and
            # `functools.singledispatchmethod`
            if function.hasDecorator(dispatchDecorators):
                continue

            # Iterate over the annotated args to look for opinionated warnings
            annotatedArgs = function.getAnnotatedArguments()
            for arg in annotatedArgs:
                if arg.isDynamicallyTyped:
                    if allowStarArgAny and arg.annotationType in {
                        AnnotationType.VARARG,
                        AnnotationType.KWARG,
                    }:
                        continue

                    self.__error(function.lineno - 1, function.col_offset, "A401")

            # Before we iterate over the function's missing annotations, check
            # to see if it's the closing function def in a series of
            # `typing.overload` decorated functions.
            if lastOverloadDecoratedFunctionName == function.name:
                continue

            # If it's not, and it is overload decorated, store it for the next
            # iteration
            if function.hasDecorator(overloadDecorators):
                lastOverloadDecoratedFunctionName = function.name

            # Optionally respect a 'type: ignore' comment
            # These are considered at the function level & tags are not considered
            if respectTypeIgnore:
                if function.lineno in typeIgnoreLineno:
                    # function-level ignore
                    continue
                elif (
                    any(lineno in typeIgnoreLineno for lineno in range(1, 6))
                    or hasMypyIgnoreErrors
                ):
                    # module-level ignore
                    # lineno from ast is 1-indexed
                    # check first five lines
                    continue

            # Record explicit errors for arguments that are missing annotations
            for arg in function.getMissedAnnotations():
                # Check for type comments here since we're not considering them as
                # typed args
                if arg.hasTypeComment:
                    self.__error(arg.lineno - 1, arg.col_offset, "A402")

                if arg.argname == "return":
                    # return annotations have multiple possible short-circuit
                    # paths
                    if (
                        suppressNoneReturning
                        and not arg.hasTypeAnnotation
                        and function.hasOnlyNoneReturns
                    ):
                        # Skip recording return errors if the function has only
                        # `None` returns. This includes the case of no returns.
                        continue

                    if (
                        mypyInitReturn
                        and function.isClassMethod
                        and function.name == "__init__"
                        and annotatedArgs
                    ):
                        # Skip recording return errors for `__init__` if at
                        # least one argument is annotated
                        continue

                # If the `suppressDummyArgs` flag is `True`, skip recording
                # errors for any arguments named `_`
                if arg.argname == "_" and suppressDummyArgs:
                    continue

                self.__classifyError(function, arg)

    def __classifyError(self, function, arg):
        """
        Private method to classify the missing type annotation based on the
        Function & Argument metadata.

        For the currently defined rules & program flow, the assumption can be
        made that an argument passed to this method will match a linting error,
        and will only match a single linting error

        This function provides an initial classificaton, then passes relevant
        attributes to cached helper function(s).

        @param function reference to the Function object
        @type Function
        @param arg reference to the Argument object
        @type Argument
        """
        # Check for return type
        # All return "arguments" have an explicitly defined name "return"
        if arg.argname == "return":
            errorCode = self.__returnErrorClassifier(
                function.isClassMethod,
                function.classDecoratorType,
                function.functionType,
            )
        else:
            # Otherwise, classify function argument error
            isFirstArg = arg == function.args[0]
            errorCode = self.__argumentErrorClassifier(
                function.isClassMethod,
                isFirstArg,
                function.classDecoratorType,
                arg.annotationType,
            )

        if errorCode in ("A001", "A002", "A003"):
            self.__error(arg.lineno - 1, arg.col_offset, errorCode, arg.argname)
        else:
            self.__error(arg.lineno - 1, arg.col_offset, errorCode)

    @lru_cache()  # __IGNORE_WARNING_M519__
    def __returnErrorClassifier(self, isClassMethod, classDecoratorType, functionType):
        """
        Private method to classify a return type annotation issue.

        @param isClassMethod flag indicating a classmethod type function
        @type bool
        @param classDecoratorType type of class decorator
        @type ClassDecoratorType
        @param functionType type of function
        @type FunctionType
        @return error code
        @rtype str
        """
        # Decorated class methods (@classmethod, @staticmethod) have a higher
        # priority than the rest
        if isClassMethod:
            if classDecoratorType == ClassDecoratorType.CLASSMETHOD:
                return "A206"
            elif classDecoratorType == ClassDecoratorType.STATICMETHOD:
                return "A205"

        if functionType == FunctionType.SPECIAL:
            return "A204"
        elif functionType == FunctionType.PRIVATE:
            return "A203"
        elif functionType == FunctionType.PROTECTED:
            return "A202"
        else:
            return "A201"

    @lru_cache()  # __IGNORE_WARNING_M519__
    def __argumentErrorClassifier(
        self, isClassMethod, isFirstArg, classDecoratorType, annotationType
    ):
        """
        Private method to classify an argument type annotation issue.

        @param isClassMethod flag indicating a classmethod type function
        @type bool
        @param isFirstArg flag indicating the first argument
        @type bool
        @param classDecoratorType type of class decorator
        @type enums.ClassDecoratorType
        @param annotationType type of annotation
        @type AnnotationType
        @return error code
        @rtype str
        """
        # Check for regular class methods and @classmethod, @staticmethod is
        # deferred to final check
        if isClassMethod and isFirstArg:
            # The first function argument here would be an instance of self or
            # class
            if classDecoratorType == ClassDecoratorType.CLASSMETHOD:
                return "A102"
            elif classDecoratorType != ClassDecoratorType.STATICMETHOD:
                # Regular class method
                return "A101"

        # Check for remaining codes
        if annotationType == AnnotationType.KWARG:
            return "A003"
        elif annotationType == AnnotationType.VARARG:
            return "A002"
        else:
            # Combine PosOnlyArgs, Args, and KwOnlyArgs
            return "A001"

    #######################################################################
    ## Annotations Coverage
    ##
    ## adapted from: flake8-annotations-coverage v0.0.6
    #######################################################################

    def __checkAnnotationsCoverage(self):
        """
        Private method to check for function annotation coverage.
        """
        minAnnotationsCoverage = self.__args.get(
            "MinimumCoverage", AnnotationsCheckerDefaultArgs["MinimumCoverage"]
        )
        if minAnnotationsCoverage == 0:
            # 0 means it is switched off
            return

        functionDefs = [
            f
            for f in ast.walk(self.__tree)
            if isinstance(f, (ast.AsyncFunctionDef, ast.FunctionDef))
        ]
        if not functionDefs:
            # no functions/methods at all
            return

        functionDefAnnotationsInfo = [
            self.__hasTypeAnnotations(f) for f in functionDefs
        ]
        if not bool(functionDefAnnotationsInfo):
            return

        annotationsCoverage = int(
            len(list(filter(None, functionDefAnnotationsInfo)))
            / len(functionDefAnnotationsInfo)
            * 100
        )
        if annotationsCoverage < minAnnotationsCoverage:
            self.__error(0, 0, "A881", annotationsCoverage)

    def __hasTypeAnnotations(self, funcNode):
        """
        Private method to check for type annotations.

        @param funcNode reference to the function definition node to be checked
        @type ast.AsyncFunctionDef or ast.FunctionDef
        @return flag indicating the presence of type annotations
        @rtype bool
        """
        hasReturnAnnotation = funcNode.returns is not None
        hasArgsAnnotations = any(
            a for a in funcNode.args.args if a.annotation is not None
        )
        hasKwargsAnnotations = (
            funcNode.args
            and funcNode.args.kwarg
            and funcNode.args.kwarg.annotation is not None
        )
        hasKwonlyargsAnnotations = any(
            a for a in funcNode.args.kwonlyargs if a.annotation is not None
        )

        return any(
            (
                hasReturnAnnotation,
                hasArgsAnnotations,
                hasKwargsAnnotations,
                hasKwonlyargsAnnotations,
            )
        )

    #######################################################################
    ## Annotations Complexity
    ##
    ## adapted from: flake8-annotations-complexity v0.0.8
    #######################################################################

    def __checkAnnotationComplexity(self):
        """
        Private method to check the type annotation complexity.
        """
        maxAnnotationComplexity = self.__args.get(
            "MaximumComplexity", AnnotationsCheckerDefaultArgs["MaximumComplexity"]
        )
        maxAnnotationLength = self.__args.get(
            "MaximumLength", AnnotationsCheckerDefaultArgs["MaximumLength"]
        )
        typeAnnotations = []

        functionDefs = [
            f
            for f in ast.walk(self.__tree)
            if isinstance(f, (ast.AsyncFunctionDef, ast.FunctionDef))
        ]
        for functionDef in functionDefs:
            typeAnnotations += list(
                filter(None, (a.annotation for a in functionDef.args.args))
            )
            if functionDef.returns:
                typeAnnotations.append(functionDef.returns)
        typeAnnotations += [
            a.annotation
            for a in ast.walk(self.__tree)
            if isinstance(a, ast.AnnAssign) and a.annotation
        ]
        for annotation in typeAnnotations:
            complexity = self.__getAnnotationComplexity(annotation)
            if complexity > maxAnnotationComplexity:
                self.__error(
                    annotation.lineno - 1,
                    annotation.col_offset,
                    "A891",
                    complexity,
                    maxAnnotationComplexity,
                )

            annotationLength = self.__getAnnotationLength(annotation)
            if annotationLength > maxAnnotationLength:
                self.__error(
                    annotation.lineno - 1,
                    annotation.col_offset,
                    "A892",
                    annotationLength,
                    maxAnnotationLength,
                )

    def __getAnnotationComplexity(self, annotationNode, defaultComplexity=1):
        """
        Private method to determine the annotation complexity.

        @param annotationNode reference to the node to determine the annotation
            complexity for
        @type ast.AST
        @param defaultComplexity default complexity value
        @type int
        @return annotation complexity
        @rtype = int
        """
        if AstUtilities.isString(annotationNode):
            try:
                annotationNode = ast.parse(annotationNode.value).body[0].value
            except (IndexError, SyntaxError):
                return defaultComplexity

        complexity = defaultComplexity
        if isinstance(annotationNode, ast.Subscript):
            if sys.version_info >= (3, 9):
                complexity = defaultComplexity + self.__getAnnotationComplexity(
                    annotationNode.slice
                )
            else:
                complexity = defaultComplexity + self.__getAnnotationComplexity(
                    annotationNode.slice.value
                )

        if isinstance(annotationNode, ast.Tuple):
            complexity = max(
                (self.__getAnnotationComplexity(n) for n in annotationNode.elts),
                default=defaultComplexity,
            )

        return complexity

    def __getAnnotationLength(self, annotationNode):
        """
        Private method to determine the annotation length.

        @param annotationNode reference to the node to determine the annotation
            length for
        @type ast.AST
        @return annotation length
        @rtype = int
        """
        annotationLength = 0
        if AstUtilities.isString(annotationNode):
            try:
                annotationNode = ast.parse(annotationNode.value).body[0].value
            except (IndexError, SyntaxError):
                return annotationLength

        if isinstance(annotationNode, ast.Subscript):
            with contextlib.suppress(AttributeError):
                annotationLength = (
                    len(annotationNode.slice.elts)
                    if sys.version_info >= (3, 9)
                    else len(annotationNode.slice.value.elts)
                )

        return annotationLength

    #######################################################################
    ## 'from __future__ import annotations' check
    ##
    ## adapted from: flake8-future-annotations v1.1.0
    #######################################################################

    def __checkAnnotationsFuture(self):
        """
        Private method to check the use of __future__ and typing imports.
        """
        from .AnnotationsFutureVisitor import AnnotationsFutureVisitor

        if sys.version_info >= (3, 9):
            # the __future__ typing import is only needed before Python 3.9
            return

        forceFutureAnnotations = self.__args.get(
            "ForceFutureAnnotations",
            AnnotationsCheckerDefaultArgs["ForceFutureAnnotations"],
        )
        checkFutureAnnotations = self.__args.get(
            "CheckFutureAnnotations",
            AnnotationsCheckerDefaultArgs["CheckFutureAnnotations"],
        )

        visitor = AnnotationsFutureVisitor()
        visitor.visit(self.__tree)

        if visitor.importsFutureAnnotations():
            return

        if visitor.hasTypingImports():
            imports = ", ".join(visitor.getTypingImports())
            self.__error(0, 0, "A871", imports)
        elif forceFutureAnnotations:
            self.__error(0, 0, "A872")

        if checkFutureAnnotations and visitor.hasSimplifiedTypes():
            simplifiedTypes = ", ".join(sorted(visitor.getSimplifiedTypes()))
            self.__error(0, 0, "A873", simplifiedTypes)

    #######################################################################
    ## check use of 'typing.Union' (see PEP 604)
    ##
    ## adapted from: flake8-pep604 v1.1.0
    #######################################################################

    def __checkAnnotationPep604(self):
        """
        Private method to check the use of typing.Union.
        """
        from .AnnotationsUnionVisitor import AnnotationsUnionVisitor

        if sys.version_info < (3, 10):
            # the union operator was introduced with Python 3.10
            return

        visitor = AnnotationsUnionVisitor()
        visitor.visit(self.__tree)

        for node in visitor.getIssues():
            self.__error(node.lineno - 1, node.col_offset, "A901")

    #######################################################################
    ## check use of 'typing.Union' (see PEP 604)
    ##
    ## adapted from: flake8-pep585 v0.1.7
    #######################################################################

    def __checkDeprecatedTypingSymbols(self):
        """
        Private method to check the use of deprecated 'typing' symbols.
        """
        from .AnnotationsDeprecationsVisitor import (
            AnnotationsDeprecationsVisitor,
            AnnotationsFutureImportVisitor,
        )

        if sys.version_info < (3, 9):
            # py 3.8: only if activated via __future__ import
            visitor = AnnotationsFutureImportVisitor()
            visitor.visit(self.__tree)
            if not visitor.futureImportPresent():
                return

        visitor = AnnotationsDeprecationsVisitor(
            self.__args.get(
                "ExemptedTypingSymbols",
                AnnotationsCheckerDefaultArgs["ExemptedTypingSymbols"],
            )
        )
        visitor.visit(self.__tree)

        for node, (name, replacement) in visitor.getIssues():
            self.__error(node.lineno - 1, node.col_offset, "A911", name, replacement)
