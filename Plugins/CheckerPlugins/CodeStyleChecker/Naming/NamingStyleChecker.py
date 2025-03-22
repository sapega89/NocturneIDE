# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a checker for naming conventions.
"""

import ast
import collections
import functools
import os

try:
    ast.AsyncFunctionDef  # __IGNORE_EXCEPTION__
except AttributeError:
    ast.AsyncFunctionDef = ast.FunctionDef


class NamingStyleChecker:
    """
    Class implementing a checker for naming conventions.
    """

    Codes = [
        "N801",
        "N802",
        "N803",
        "N804",
        "N805",
        "N806",
        "N807",
        "N808",
        "N809",
        "N811",
        "N812",
        "N813",
        "N814",
        "N815",
        "N818",
        "N821",
        "N822",
        "N823",
        "N831",
    ]

    def __init__(self, tree, filename, options):
        """
        Constructor (according to 'extended' pycodestyle.py API)

        @param tree AST tree of the source file
        @type ast.AST
        @param filename name of the source file
        @type str
        @param options options as parsed by pycodestyle.StyleGuide
        @type optparse.Option
        """
        self.__parents = collections.deque()
        self.__tree = tree
        self.__filename = filename

        self.__checkersWithCodes = {
            "classdef": [
                (self.__checkClassName, ("N801", "N818")),
                (self.__checkNameToBeAvoided, ("N831",)),
            ],
            "module": [
                (self.__checkModule, ("N807", "N808")),
            ],
        }
        for name in ("functiondef", "asyncfunctiondef"):
            self.__checkersWithCodes[name] = [
                (self.__checkFunctionName, ("N802", "N809")),
                (self.__checkFunctionArgumentNames, ("N803", "N804", "N805", "N806")),
                (self.__checkNameToBeAvoided, ("N831",)),
            ]
        for name in ("assign", "namedexpr", "annassign"):
            self.__checkersWithCodes[name] = [
                (self.__checkVariableNames, ("N821",)),
                (self.__checkNameToBeAvoided, ("N831",)),
            ]
        for name in (
            "with",
            "asyncwith",
            "for",
            "asyncfor",
            "excepthandler",
            "generatorexp",
            "listcomp",
            "dictcomp",
            "setcomp",
        ):
            self.__checkersWithCodes[name] = [
                (self.__checkVariableNames, ("N821",)),
            ]
        for name in ("import", "importfrom"):
            self.__checkersWithCodes[name] = [
                (self.__checkImportAs, ("N811", "N812", "N813", "N814", "N815")),
            ]

        self.__checkers = {}
        for key, checkers in self.__checkersWithCodes.items():
            for checker, codes in checkers:
                if any(not (code and options.ignore_code(code)) for code in codes):
                    if key not in self.__checkers:
                        self.__checkers[key] = []
                    self.__checkers[key].append(checker)

    def run(self):
        """
        Public method run by the pycodestyle.py checker.

        @return tuple giving line number, offset within line, code and
            checker function
        @rtype tuple of (int, int, str, function)
        """
        if self.__tree and self.__checkers:
            return self.__visitTree(self.__tree)
        else:
            return ()

    def __visitTree(self, node):
        """
        Private method to scan the given AST tree.

        @param node AST tree node to scan
        @type ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        yield from self.__visitNode(node)
        self.__parents.append(node)
        for child in ast.iter_child_nodes(node):
            yield from self.__visitTree(child)
        self.__parents.pop()

    def __visitNode(self, node):
        """
        Private method to inspect the given AST node.

        @param node AST tree node to inspect
        @type ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        if isinstance(node, ast.ClassDef):
            self.__tagClassFunctions(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.__findGlobalDefs(node)

        checkerName = node.__class__.__name__.lower()
        if checkerName in self.__checkers:
            for checker in self.__checkers[checkerName]:
                for error in checker(node, self.__parents):
                    yield error + (self.__checkers[checkerName],)

    def __tagClassFunctions(self, classNode):
        """
        Private method to tag functions if they are methods, class methods or
        static methods.

        @param classNode AST tree node to tag
        @type ast.ClassDef
        """
        # try to find all 'old style decorators'
        # like m = staticmethod(m)
        lateDecoration = {}
        for node in ast.iter_child_nodes(classNode):
            if not (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
            ):
                continue
            funcName = node.value.func.id
            if funcName in ("classmethod", "staticmethod"):
                meth = len(node.value.args) == 1 and node.value.args[0]
                if isinstance(meth, ast.Name):
                    lateDecoration[meth.id] = funcName

        # iterate over all functions and tag them
        for node in ast.iter_child_nodes(classNode):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            node.function_type = "method"
            if node.name == "__new__":
                node.function_type = "classmethod"

            if node.name in lateDecoration:
                node.function_type = lateDecoration[node.name]
            elif node.decorator_list:
                names = [
                    d.id
                    for d in node.decorator_list
                    if isinstance(d, ast.Name)
                    and d.id in ("classmethod", "staticmethod")
                ]
                if names:
                    node.function_type = names[0]

    def __findGlobalDefs(self, functionNode):
        """
        Private method amend a node with global definitions information.

        @param functionNode AST tree node to amend
        @type ast.FunctionDef or ast.AsyncFunctionDef
        """
        globalNames = set()
        nodesToCheck = collections.deque(ast.iter_child_nodes(functionNode))
        while nodesToCheck:
            node = nodesToCheck.pop()
            if isinstance(node, ast.Global):
                globalNames.update(node.names)

            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                nodesToCheck.extend(ast.iter_child_nodes(node))
        functionNode.global_names = globalNames

    def __getArgNames(self, node):
        """
        Private method to get the argument names of a function node.

        @param node AST node to extract arguments names from
        @type ast.FunctionDef or ast.AsyncFunctionDef
        @return list of argument names
        @rtype list of str
        """
        posArgs = [arg.arg for arg in node.args.args]
        kwOnly = [arg.arg for arg in node.args.kwonlyargs]
        return posArgs + kwOnly

    def __error(self, node, code):
        """
        Private method to build the error information.

        @param node AST node to report an error for
        @type ast.AST
        @param code error code to report
        @type str
        @return tuple giving line number, offset within line and error code
        @rtype tuple of (int, int, str)
        """
        if isinstance(node, ast.Module):
            lineno = 0
            offset = 0
        else:
            lineno = node.lineno
            offset = node.col_offset
            if isinstance(node, ast.ClassDef):
                lineno += len(node.decorator_list)
                offset += 6
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lineno += len(node.decorator_list)
                offset += 4
        return (lineno, offset, code)

    def __isNameToBeAvoided(self, name):
        """
        Private method to check, if the given name should be avoided.

        @param name name to be checked
        @type str
        @return flag indicating to avoid it
        @rtype bool
        """
        return name in ("l", "O", "I")

    def __checkNameToBeAvoided(self, node, _parents):
        """
        Private class to check the given node for a name to be avoided (N831).

        @param node AST note to check
        @type ast.Ast
        @param _parents list of parent nodes (unused)
        @type list of ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if self.__isNameToBeAvoided(name):
                yield self.__error(node, "N831")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            argNames = self.__getArgNames(node)
            for arg in argNames:
                if self.__isNameToBeAvoided(arg):
                    yield self.__error(node, "N831")

        elif isinstance(node, (ast.Assign, ast.NamedExpr, ast.AnnAssign)):
            if isinstance(node, ast.Assign):
                targets = node.targets
            else:
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if bool(name) and self.__isNameToBeAvoided(name):
                        yield self.__error(node, "N831")

                elif isinstance(target, (ast.Tuple, ast.List)):
                    for element in target.elts:
                        if isinstance(element, ast.Name):
                            name = element.id
                            if bool(name) and self.__isNameToBeAvoided(name):
                                yield self.__error(node, "N831")

    def __getClassdef(self, name, parents):
        """
        Private method to extract the class definition.

        @param name name of the class
        @type str
        @param parents list of parent nodes
        @type list of ast.AST
        @return node containing the class definition
        @rtype ast.ClassDef
        """
        for parent in parents:
            for node in parent.body:
                if isinstance(node, ast.ClassDef) and node.name == name:
                    return node

        return None

    def __superClassNames(self, name, parents, names=None):
        """
        Private method to extract the names of all super classes.

        @param name name of the class
        @type str
        @param parents list of parent nodes
        @type list of ast.AST
        @param names set of collected class names (defaults to None)
        @type set of str (optional)
        @return set of class names
        @rtype set of str
        """
        if names is None:
            # initialize recursive search with empty set
            names = set()

        classdef = self.__getClassdef(name, parents)
        if not classdef:
            return names

        for base in classdef.bases:
            if isinstance(base, ast.Name) and base.id not in names:
                names.add(base.id)
                names.update(self.__superClassNames(base.id, parents, names))
        return names

    def __checkClassName(self, node, parents):
        """
        Private class to check the given node for class name
        conventions (N801, N818).

        Almost without exception, class names use the CapWords convention.
        Classes for internal use have a leading underscore in addition.

        @param node AST note to check
        @type ast.ClassDef
        @param parents list of parent nodes
        @type list of ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        name = node.name
        strippedName = name.strip("_")
        if not strippedName[:1].isupper() or "_" in strippedName:
            yield self.__error(node, "N801")

        superClasses = self.__superClassNames(name, parents)
        if "Exception" in superClasses and not name.endswith("Error"):
            yield self.__error(node, "N818")

    def __checkFunctionName(self, node, _parents):
        """
        Private class to check the given node for function name
        conventions (N802, N809).

        Function names should be lowercase, with words separated by underscores
        as necessary to improve readability. Functions <b>not</b> being
        methods '__' in front and back are not allowed. Mixed case is allowed
        only in contexts where that's already the prevailing style
        (e.g. threading.py), to retain backwards compatibility.

        @param node AST note to check
        @type ast.FunctionDef or ast.AsynFunctionDef
        @param _parents list of parent nodes (unused)
        @type list of ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        functionType = getattr(node, "function_type", "function")
        name = node.name

        if name in ("__dir__", "__getattr__"):
            return

        if name.lower() != name:
            yield self.__error(node, "N802")
        if functionType == "function" and name[:2] == "__" and name[-2:] == "__":
            yield self.__error(node, "N809")

    def __checkFunctionArgumentNames(self, node, _parents):
        """
        Private class to check the argument names of functions
        (N803, N804, N805, N806).

        The argument names of a function should be lowercase, with words
        separated by underscores. A class method should have 'cls' as the
        first argument. A method should have 'self' as the first argument.

        @param node AST note to check
        @type ast.FunctionDef or ast.AsynFunctionDef
        @param _parents list of parent nodes (unused)
        @type list of ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        if node.args.kwarg is not None:
            kwarg = node.args.kwarg.arg
            if kwarg.lower() != kwarg:
                yield self.__error(node, "N803")

        elif node.args.vararg is not None:
            vararg = node.args.vararg.arg
            if vararg.lower() != vararg:
                yield self.__error(node, "N803")

        else:
            argNames = self.__getArgNames(node)
            functionType = getattr(node, "function_type", "function")

            if not argNames:
                if functionType == "method":
                    yield self.__error(node, "N805")
                elif functionType == "classmethod":
                    yield self.__error(node, "N804")

            elif functionType == "method" and argNames[0] != "self":
                yield self.__error(node, "N805")
            elif functionType == "classmethod" and argNames[0] != "cls":
                yield self.__error(node, "N804")
            elif functionType == "staticmethod" and argNames[0] in ("cls", "self"):
                yield self.__error(node, "N806")
            for arg in argNames:
                if arg.lower() != arg:
                    yield self.__error(node, "N803")
                    break

    def __checkVariableNames(self, node, parents):
        """
        Private method to check variable names in function, class and global scope
        (N821, N822, N823).

        Local variables in functions should be lowercase.

        @param node AST note to check
        @type ast.AST
        @param parents list of parent nodes
        @type list of ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        nodeType = type(node)
        if nodeType is ast.Assign:
            if self.__isNamedTupel(node.value):
                return
            for target in node.targets:
                yield from self.__findVariableNameErrors(target, parents)

        elif nodeType in (ast.NamedExpr, ast.AnnAssign):
            if self.__isNamedTupel(node.value):
                return
            yield from self.__findVariableNameErrors(node.target, parents)

        elif nodeType in (ast.With, ast.AsyncWith):
            for item in node.items:
                yield from self.__findVariableNameErrors(item.optional_vars, parents)

        elif nodeType in (ast.For, ast.AsyncFor):
            yield from self.__findVariableNameErrors(node.target, parents)

        elif nodeType is ast.ExceptHandler:
            if node.name:
                yield from self.__findVariableNameErrors(node, parents)

        elif nodeType in (ast.GeneratorExp, ast.ListComp, ast.DictComp, ast.SetComp):
            for gen in node.generators:
                yield from self.__findVariableNameErrors(gen.target, parents)

    def __findVariableNameErrors(self, assignmentTarget, parents):
        """
        Private method to check, if there is a variable name error.

        @param assignmentTarget target node of the assignment
        @type ast.Name, ast.Tuple, ast.List or ast.ExceptHandler
        @param parents list of parent nodes
        @type ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        for parentFunc in reversed(parents):
            if isinstance(parentFunc, ast.ClassDef):
                checker = self.__classVariableCheck
                break
            if isinstance(parentFunc, (ast.FunctionDef, ast.AsyncFunctionDef)):
                checker = functools.partial(self.__functionVariableCheck, parentFunc)
                break
        else:
            checker = self.__globalVariableCheck
        for name in self.__extractNames(assignmentTarget):
            errorCode = checker(name)
            if errorCode:
                yield self.__error(assignmentTarget, errorCode)

    def __extractNames(self, assignmentTarget):
        """
        Private method to extract the names from the target node.

        @param assignmentTarget target node of the assignment
        @type ast.Name, ast.Tuple, ast.List or ast.ExceptHandler
        @yield name of the variable
        @ytype str
        """
        targetType = type(assignmentTarget)
        if targetType is ast.Name:
            yield assignmentTarget.id
        elif targetType in (ast.Tuple, ast.List):
            for element in assignmentTarget.elts:
                elementType = type(element)
                if elementType is ast.Name:
                    yield element.id
                elif elementType in (ast.Tuple, ast.List):
                    yield from self.__extractNames(element)
                elif elementType is ast.Starred:  # PEP 3132
                    yield from self.__extractNames(element.value)
        elif isinstance(assignmentTarget, ast.ExceptHandler):
            yield assignmentTarget.name

    def __isMixedCase(self, name):
        """
        Private method to check, if the given name is mixed case.

        @param name variable name to be checked
        @type str
        @return flag indicating mixed case
        @rtype bool
        """
        return name.lower() != name and name.lstrip("_")[:1].islower()

    def __globalVariableCheck(self, name):
        """
        Private method to determine the error code for a variable in global scope.

        @param name variable name to be checked
        @type str
        @return error code or None
        @rtype str or None
        """
        if self.__isMixedCase(name):
            return "N823"

        return None

    def __classVariableCheck(self, name):
        """
        Private method to determine the error code for a variable in class scope.

        @param name variable name to be checked
        @type str
        @return error code or None
        @rtype str or None
        """
        if self.__isMixedCase(name):
            return "N822"

        return None

    def __functionVariableCheck(self, func, varName):
        """
        Private method to determine the error code for a variable in class scope.

        @param func reference to the function definition node
        @type ast.FunctionDef or ast.AsyncFunctionDef
        @param varName variable name to be checked
        @type str
        @return error code or None
        @rtype str or None
        """
        if varName not in func.global_names and varName.lower() != varName:
            return "N821"

        return None

    def __isNamedTupel(self, nodeValue):
        """
        Private method to check, if a node is a named tuple.

        @param nodeValue node to be checked
        @type ast.AST
        @return flag indicating a nemd tuple
        @rtype bool
        """
        return isinstance(nodeValue, ast.Call) and (
            (
                isinstance(nodeValue.func, ast.Attribute)
                and nodeValue.func.attr == "namedtuple"
            )
            or (
                isinstance(nodeValue.func, ast.Name)
                and nodeValue.func.id == "namedtuple"
            )
        )

    def __checkModule(self, node, _parents):
        """
        Private method to check module naming conventions (N807, N808).

        Module and package names should be lowercase.

        @param node AST node to check
        @type ast.AST
        @param _parents list of parent nodes (unused)
        @type list of ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        if self.__filename:
            moduleName = os.path.splitext(os.path.basename(self.__filename))[0]
            if moduleName.lower() != moduleName:
                yield self.__error(node, "N807")

            if moduleName == "__init__":
                # we got a package
                packageName = os.path.split(os.path.dirname(self.__filename))[1]
                if packageName.lower() != packageName:
                    yield self.__error(node, "N808")

    def __checkImportAs(self, node, _parents):
        """
        Private method to check that imports don't change the
        naming convention (N811, N812, N813, N814, N815).

        @param node AST node to check
        @type ast.Import
        @param _parents list of parent nodes (unused)
        @type list of ast.AST
        @yield tuple giving line number, offset within line and error code
        @ytype tuple of (int, int, str)
        """
        for name in node.names:
            asname = name.asname
            if not asname:
                continue

            originalName = name.name
            if originalName.isupper():
                if not asname.isupper():
                    yield self.__error(node, "N811")
            elif originalName.islower():
                if asname.lower() != asname:
                    yield self.__error(node, "N812")
            elif asname.islower():
                yield self.__error(node, "N813")
            elif asname.isupper():
                if "".join(filter(str.isupper, originalName)) == asname:
                    yield self.__error(node, "N815")
                else:
                    yield self.__error(node, "N814")
