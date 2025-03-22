# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Parse a Python file and retrieve classes, functions/methods and attributes.

Parse enough of a Python file to recognize class and method definitions and
to find out the superclasses of a class as well as its attributes.
"""

import keyword
import re
import sys

from dataclasses import dataclass
from functools import reduce

from PyQt6.QtCore import QRegularExpression

from eric7 import Utilities
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities
from eric7.Utilities import ClassBrowsers

from . import ClbrBaseClasses

TABWIDTH = 4

SUPPORTED_TYPES = [ClassBrowsers.PY_SOURCE, ClassBrowsers.PTL_SOURCE]

_getnext = QRegularExpression(
    r"""
   (?P<CodingLine>
        ^ \# \s* [*_-]* \s* coding[:=] \s* (?P<Coding> [-\w_.]+ ) \s* [*_-]* $
    )

|   (?P<String>
        \# .*? $   # ignore everything in comments
    |
        \""" [^"\\]* (?:
                        (?: \\. | "(?!"") )
                        [^"\\]*
                    )*
        \"""

    |   ''' [^'\\]* (?:
                        (?: \\. | '(?!'') )
                        [^'\\]*
                    )*
        '''

    |   " [^"\\\n]* (?: \\. [^"\\\n]*)* "

    |   ' [^'\\\n]* (?: \\. [^'\\\n]*)* '
    )

|   (?P<Publics>
        ^
        [ \t]* __all__ [ \t]* = [ \t]* \[
        (?P<Identifiers> [^\]]*? )
        \]
    )

|   (?P<MethodModifier>
        ^
        (?P<MethodModifierIndent> [ \t]* )
        (?P<MethodModifierType> @classmethod | @staticmethod )
    )

|   (?P<Method>
        ^
        (?P<MethodIndent> [ \t]* )
        (?: async [ \t]+ )? (?: cdef | cpdef | def) [ \t]+
        (?P<MethodName> [\pL_] \w* )
        (?: [ \t]* \[ [^\]]+ \] )?
        [ \t]* \(
        (?P<MethodSignature> (?: [^)] | \)[ \t]*,? )*? )
        \) [ \t]*
        (?P<MethodReturnAnnotation> (?: -> [ \t]* [^:]+ )? )
        [ \t]* :
    )

|   (?P<Class>
        ^
        (?P<ClassIndent> [ \t]* )
        (?: cdef [ \t]+ )?
        class [ \t]+
        (?P<ClassName> [\pL_] \w* )
        (?: [ \t]* \[ [^\]]+ \] )?
        [ \t]*
        (?P<ClassSupers> \( [^)]* \) )?
        [ \t]* :
    )

|   (?P<Attribute>
        ^
        (?P<AttributeIndent> [ \t]* )
        self [ \t]* \. [ \t]*
        (?P<AttributeName> [\pL_] \w* )
        [ \t]* =
    )

|   (?P<TypedAttribute>
        ^
        (?P<TypedAttributeIndent> [ \t]* )
        self [ \t]* \. [ \t]*
        (?P<TypedAttributeName> [\pL_] \w* )
        [ \t]* : [ \t]+
    )

|   (?P<Variable>
        ^
        (?P<VariableIndent> [ \t]* )
        (?P<VariableName> [\pL_] \w* )
        [ \t]* =
    )

|   (?P<TypedVariable>
        ^
        (?P<TypedVariableIndent> [ \t]* )
        (?P<TypedVariableName> [\pL_] \w* )
        [ \t]* :
    )

|   (?P<Main>
        ^
        if \s+ __name__ \s* == \s* [^:]+ : $
    )

|   (?P<ConditionalDefine>
        ^
        (?P<ConditionalDefineIndent> [ \t]* )
        (?: (?: if | elif ) [ \t]+ [^:]* | else [ \t]* ) :
        (?= \s* (?: async [ \t]+ )? def)
    )

|   (?P<Import>
        ^ [ \t]* (?: c? import | from [ \t]+ \. [ \t]+ c? import ) [ \t]+
        (?P<ImportList> (?: [^#;\\\n]* (?: \\\n )* )* )
    )

|   (?P<ImportFrom>
        ^ [ \t]* from [ \t]+
        (?P<ImportFromPath>
            \.* \w+
            (?:
                [ \t]* \. [ \t]* \w+
            )*
        )
        [ \t]+
        c? import [ \t]+
        (?P<ImportFromList>
            (?: \( \s* .*? \s* \) )
            |
            (?: [^#;\\\n]* (?: \\\n )* )* )
    )""",
    QRegularExpression.PatternOption.MultilineOption
    | QRegularExpression.PatternOption.DotMatchesEverythingOption
    | QRegularExpression.PatternOption.ExtendedPatternSyntaxOption
    | QRegularExpression.PatternOption.UseUnicodePropertiesOption,
).match

_commentsub = re.compile(r"""#[^\n]*\n|#[^\n]*$""").sub


class VisibilityMixin(ClbrBaseClasses.ClbrVisibilityMixinBase):
    """
    Mixin class implementing the notion of visibility.
    """

    def __init__(self):
        """
        Constructor
        """
        if self.name.startswith("__"):
            self.setPrivate()
        elif self.name.startswith("_"):
            self.setProtected()
        else:
            self.setPublic()


class Class(ClbrBaseClasses.Class, VisibilityMixin):
    """
    Class to represent a Python class.
    """

    def __init__(self, module, name, superClasses, file, lineno, col_offset=0):
        """
        Constructor

        @param module name of the module containing this class
        @type str
        @param name name of this class
        @type str
        @param superClasses list of class names this class is inherited from
        @type list of str
        @param file file name containing this class
        @type str
        @param lineno line number of the class definition
        @type int
        @param col_offset column number of the class definition (defaults to 0)
        @type int (optional)
        """
        ClbrBaseClasses.Class.__init__(
            self, module, name, superClasses, file, lineno, col_offset=col_offset
        )
        VisibilityMixin.__init__(self)


class Function(ClbrBaseClasses.Function, VisibilityMixin):
    """
    Class to represent a Python function.
    """

    def __init__(
        self,
        module,
        name,
        file,
        lineno,
        col_offset=0,
        signature="",
        separator=",",
        modifierType=ClbrBaseClasses.Function.General,
        annotation="",
    ):
        """
        Constructor

        @param module name of the module containing this function
        @type str
        @param name name of this function
        @type str
        @param file file name containing this function
        @type str
        @param lineno line number of the function definition
        @type int
        @param col_offset column number of the function definition (defaults to 0)
        @type int (optional)
        @param signature parameter list of the function
        @type str
        @param separator string separating the parameters
        @type str
        @param modifierType type of the function
        @type int
        @param annotation return annotation
        @type str
        """
        ClbrBaseClasses.Function.__init__(
            self,
            module,
            name,
            file,
            lineno,
            col_offset=col_offset,
            signature=signature,
            separator=separator,
            modifierType=modifierType,
            annotation=annotation,
        )
        VisibilityMixin.__init__(self)


class Attribute(ClbrBaseClasses.Attribute, VisibilityMixin):
    """
    Class to represent a class attribute.
    """

    def __init__(self, module, name, file, lineno, col_offset=0):
        """
        Constructor

        @param module name of the module containing this class
        @type str
        @param name name of this class
        @type str
        @param file file name containing this attribute
        @type str
        @param lineno line number of the attribute definition
        @type int
        @param col_offset column number of the attribute definition (defaults to 0)
        @type int (optional)
        """
        ClbrBaseClasses.Attribute.__init__(
            self, module, name, file, lineno, col_offset=col_offset
        )
        VisibilityMixin.__init__(self)


@dataclass
class Publics:
    """
    Class to represent the list of public identifiers.
    """

    module: str
    file: str
    lineno: int
    identifiers: list
    name: str = "__all__"


class Imports:
    """
    Class to represent the list of imported modules.
    """

    def __init__(self, module, file):
        """
        Constructor

        @param module name of the module containing the import
        @type str
        @param file file name containing the import
        @type str
        """
        self.module = module
        self.name = "import"
        self.file = file
        self.imports = {}

    def addImport(self, moduleName, names, lineno):
        """
        Public method to add a list of imported names.

        @param moduleName name of the imported module
        @type str
        @param names list of names
        @type list of str
        @param lineno line number of the import
        @type int
        """
        if moduleName not in self.imports:
            module = ImportedModule(self.module, self.file, moduleName)
            self.imports[moduleName] = module
        else:
            module = self.imports[moduleName]
        module.addImport(lineno, names)

    def getImport(self, moduleName):
        """
        Public method to get an imported module item.

        @param moduleName name of the imported module
        @type str
        @return imported module item
        @rtype ImportedModule
        """
        if moduleName in self.imports:
            return self.imports[moduleName]
        else:
            return None

    def getImports(self):
        """
        Public method to get all imported module names.

        @return dictionary of imported module names with name as key and list
            of line numbers of imports as value
        @rtype dict
        """
        return self.imports


class ImportedModule:
    """
    Class to represent an imported module.
    """

    def __init__(self, module, file, importedModule):
        """
        Constructor

        @param module name of the module containing the import
        @type str
        @param file file name containing the import
        @type str
        @param importedModule name of the imported module
        @type str
        """
        self.module = module
        self.name = "import"
        self.file = file
        self.importedModuleName = importedModule
        self.linenos = []
        self.importedNames = {}
        # dictionary of imported names with name as key and list of line
        # numbers as value

    def addImport(self, lineno, importedNames):
        """
        Public method to add a list of imported names.

        @param lineno line number of the import
        @type int
        @param importedNames list of imported names
        @type list of str
        """
        if lineno not in self.linenos:
            self.linenos.append(lineno)

        for name in importedNames:
            if name not in self.importedNames:
                self.importedNames[name] = [lineno]
            else:
                self.importedNames[name].append(lineno)


def readmodule_ex(module, searchPath=None, isTypeFile=False):
    """
    Read a module file and return a dictionary of classes.

    Search for MODULE in PATH and sys.path, read and parse the
    module and return a dictionary with one entry for each class
    found in the module.

    @param module name of the module file
    @type str
    @param searchPath path the module should be searched in
    @type list of str
    @param isTypeFile flag indicating a file of this type
    @type bool
    @return the resulting dictionary
    @rtype dict
    """
    fsInterface = ericApp().getObject("EricServer").getServiceInterface("FileSystem")

    if searchPath and FileSystemUtilities.isRemoteFileName(searchPath[0]):
        sourceType = ClassBrowsers.determineSourceType(module, isTypeFile)
        file = fsInterface.join(searchPath[0], module)
    else:
        # search the path for the module
        searchPath = [] if searchPath is None else searchPath[:]
        fullpath = searchPath[:] + sys.path[:]
        f, file, (_suff, mode, sourceType) = ClassBrowsers.find_module(
            module, fullpath, isTypeFile
        )
        if f:
            f.close()

    if sourceType not in SUPPORTED_TYPES:
        # not Python source, can't do anything with this module
        return {}

    try:
        src = (
            fsInterface.readEncodedFile(file)[0]
            if FileSystemUtilities.isRemoteFileName(file)
            else Utilities.readEncodedFile(file)[0]
        )
    except (OSError, UnicodeError):
        # can't do anything with this module
        return {}

    return scan(src, file, module)


def scan(src, file, module):
    """
    Public method to scan the given source text.

    @param src source text to be scanned
    @type str
    @param file file name associated with the source text
    @type str
    @param module module name associated with the source text
    @type str
    @return dictionary containing the extracted data
    @rtype dict
    """

    def calculateEndline(lineno, lines, indent):
        """
        Function to calculate the end line of a class or method/function.

        @param lineno line number to start at (one based)
        @type int
        @param lines list of source lines
        @type list of str
        @param indent indent length the class/method/function definition
        @type int
        @return end line of the class/method/function (one based)
        @rtype int
        """
        # start with zero based line after start line
        while lineno < len(lines):
            line = lines[lineno]
            if line.strip() and not line.lstrip().startswith("#"):
                # line contains some text and does not start with
                # a comment sign
                lineIndent = _indent(line.replace(line.lstrip(), ""))
                if lineIndent <= indent:
                    return lineno
            lineno += 1

        # nothing found
        return -1

    # convert eol markers the Python style
    src = src.replace("\r\n", "\n").replace("\r", "\n")
    srcLines = src.splitlines()

    dictionary = {}
    dict_counts = {}

    modules = {}

    classstack = []  # stack of (class, indent) pairs
    conditionalsstack = []  # stack of indents of conditional defines
    deltastack = []
    deltaindent = 0
    deltaindentcalculated = False

    lineno, last_lineno_pos = 1, 0
    i = 0
    modifierType = ClbrBaseClasses.Function.General
    modifierIndent = -1
    while True:
        m = _getnext(src, i)
        if not m.hasMatch():
            break
        start, i = m.capturedStart(), m.capturedEnd()

        if m.captured("MethodModifier"):
            modifierIndent = _indent(m.captured("MethodModifierIndent"))
            modifierType = m.captured("MethodModifierType")

        elif m.captured("Method"):
            # found a method definition or function
            thisindent = _indent(m.captured("MethodIndent"))
            meth_name = m.captured("MethodName")
            meth_sig = m.captured("MethodSignature")
            meth_sig = meth_sig.replace("\\\n", "")
            meth_sig = _commentsub("", meth_sig)
            meth_ret = m.captured("MethodReturnAnnotation")
            meth_ret = meth_ret.replace("\\\n", "")
            meth_ret = _commentsub("", meth_ret)
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            col_offset = m.capturedStart("MethodName") - m.capturedStart()
            if modifierType and modifierIndent == thisindent:
                if modifierType == "@staticmethod":
                    modifier = ClbrBaseClasses.Function.Static
                elif modifierType == "@classmethod":
                    modifier = ClbrBaseClasses.Function.Class
                else:
                    modifier = ClbrBaseClasses.Function.General
            else:
                modifier = ClbrBaseClasses.Function.General
            # modify indentation level for conditional defines
            if conditionalsstack:
                if thisindent > conditionalsstack[-1]:
                    if not deltaindentcalculated:
                        deltastack.append(thisindent - conditionalsstack[-1])
                        deltaindent = reduce(lambda x, y: x + y, deltastack)
                        deltaindentcalculated = True
                    thisindent -= deltaindent
                else:
                    while conditionalsstack and conditionalsstack[-1] >= thisindent:
                        del conditionalsstack[-1]
                        if deltastack:
                            del deltastack[-1]
                    deltaindentcalculated = False
            # close all classes indented at least as much
            while classstack and classstack[-1][1] >= thisindent:
                classstack.pop()
            if classstack:
                # it's a class method
                cur_class = classstack[-1][0]
                if cur_class:
                    # it's a method/nested def
                    f = Function(
                        None,
                        meth_name,
                        file,
                        lineno,
                        col_offset=col_offset,
                        signature=meth_sig,
                        annotation=meth_ret,
                        modifierType=modifier,
                    )
                    cur_class._addmethod(meth_name, f)
                else:
                    f = None
            else:
                # it's a function
                f = Function(
                    module,
                    meth_name,
                    file,
                    lineno,
                    col_offset=col_offset,
                    signature=meth_sig,
                    annotation=meth_ret,
                    modifierType=modifier,
                )
                if meth_name in dict_counts:
                    dict_counts[meth_name] += 1
                    meth_name = "{0}_{1:d}".format(meth_name, dict_counts[meth_name])
                else:
                    dict_counts[meth_name] = 0
                dictionary[meth_name] = f
            if f:
                endlineno = calculateEndline(lineno, srcLines, thisindent)
                f.setEndLine(endlineno)
                classstack.append((f, thisindent))  # Marker for nested fns

            # reset the modifier settings
            modifierType = ClbrBaseClasses.Function.General
            modifierIndent = -1

        elif m.captured("String"):
            pass

        elif m.captured("Class"):
            # we found a class definition
            thisindent = _indent(m.captured("ClassIndent"))
            # close all classes indented at least as much
            while classstack and classstack[-1][1] >= thisindent:
                classstack.pop()
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            col_offset = m.capturedStart("ClassName") - m.capturedStart()
            class_name = m.captured("ClassName")
            inherit = m.captured("ClassSupers")
            if inherit:
                # the class inherits from other classes
                inherit = inherit[1:-1].strip()
                inherit = _commentsub("", inherit)
                names = []
                for n in inherit.split(","):
                    n = n.strip()
                    if n in dictionary:
                        # we know this super class
                        n = dictionary[n]
                    else:
                        c = n.split(".")
                        if len(c) > 1:
                            # super class
                            # is of the
                            # form module.class:
                            # look in
                            # module for class
                            m = c[-2]
                            c = c[-1]
                            if m in modules:
                                d = modules[m]
                                n = d.get(c, n)
                    names.append(n)
                inherit = names
            # modify indentation level for conditional defines
            if conditionalsstack:
                if thisindent > conditionalsstack[-1]:
                    if not deltaindentcalculated:
                        deltastack.append(thisindent - conditionalsstack[-1])
                        deltaindent = reduce(lambda x, y: x + y, deltastack)
                        deltaindentcalculated = True
                    thisindent -= deltaindent
                else:
                    while conditionalsstack and conditionalsstack[-1] >= thisindent:
                        del conditionalsstack[-1]
                        if deltastack:
                            del deltastack[-1]
                    deltaindentcalculated = False
            # remember this class
            cur_class = Class(
                module, class_name, inherit, file, lineno, col_offset=col_offset
            )
            endlineno = calculateEndline(lineno, srcLines, thisindent)
            cur_class.setEndLine(endlineno)
            if not classstack:
                if class_name in dict_counts:
                    dict_counts[class_name] += 1
                    class_name = "{0}_{1:d}".format(class_name, dict_counts[class_name])
                else:
                    dict_counts[class_name] = 0
                dictionary[class_name] = cur_class
            else:
                classstack[-1][0]._addclass(class_name, cur_class)
            classstack.append((cur_class, thisindent))

        elif m.captured("Attribute") or m.captured("TypedAttribute"):
            if m.captured("Attribute"):
                attribute_name = m.captured("AttributeName")
                col_offset = m.capturedStart("AttributeName") - m.capturedStart()
            else:
                attribute_name = m.captured("TypedAttributeName")
                col_offset = m.capturedStart("TypedAttributeName") - m.capturedStart()
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            index = -1
            while index >= -len(classstack):
                if classstack[index][0] is not None and not isinstance(
                    classstack[index][0], Function
                ):
                    attr = Attribute(
                        module, attribute_name, file, lineno, col_offset=col_offset
                    )
                    classstack[index][0]._addattribute(attr)
                    break
                else:
                    index -= 1

        elif m.captured("Main"):
            # 'main' part of the script, reset class stack
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            classstack = []

        elif m.captured("Variable") or m.captured("TypedVariable"):
            if m.captured("Variable"):
                thisindent = _indent(m.captured("VariableIndent"))
                variable_name = m.captured("VariableName")
                col_offset = m.capturedStart("VariableName") - m.capturedStart()
            else:
                thisindent = _indent(m.captured("TypedVariableIndent"))
                variable_name = m.captured("TypedVariableName")
                if keyword.iskeyword(variable_name):
                    # only if the determined name is not a keyword (e.g. else, except)
                    continue
                col_offset = m.capturedStart("TypedVariableName") - m.capturedStart()
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            if thisindent == 0 or not classstack:
                # global variable, reset class stack first
                classstack = []

                if "@@Globals@@" not in dictionary:
                    dictionary["@@Globals@@"] = ClbrBaseClasses.ClbrBase(
                        module, "Globals", file, lineno
                    )
                dictionary["@@Globals@@"]._addglobal(
                    Attribute(
                        module, variable_name, file, lineno, col_offset=col_offset
                    )
                )
            else:
                index = -1
                while index >= -len(classstack):
                    if classstack[index][1] >= thisindent:
                        index -= 1
                    else:
                        if isinstance(classstack[index][0], Class):
                            classstack[index][0]._addglobal(
                                Attribute(
                                    module,
                                    variable_name,
                                    file,
                                    lineno,
                                    col_offset=col_offset,
                                )
                            )
                        elif isinstance(classstack[index][0], Function):
                            classstack[index][0]._addattribute(
                                Attribute(
                                    module,
                                    variable_name,
                                    file,
                                    lineno,
                                    col_offset=col_offset,
                                )
                            )
                        break

        elif m.captured("Publics"):
            idents = m.captured("Identifiers")
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            pubs = Publics(
                module=module,
                file=file,
                lineno=lineno,
                identifiers=[
                    e.replace('"', "").replace("'", "").strip()
                    for e in idents.split(",")
                ],
            )
            dictionary["__all__"] = pubs

        elif m.captured("Import"):
            # - import module
            names = [
                n.strip()
                for n in "".join(m.captured("ImportList").splitlines())
                .replace("\\", "")
                .split(",")
            ]
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            if "@@Import@@" not in dictionary:
                dictionary["@@Import@@"] = Imports(module, file)
            for name in names:
                dictionary["@@Import@@"].addImport(name, [], lineno)

        elif m.captured("ImportFrom"):
            # - from module import stuff
            mod = m.captured("ImportFromPath")
            namesLines = (
                m.captured("ImportFromList")
                .replace("(", "")
                .replace(")", "")
                .replace("\\", "")
                .strip()
                .splitlines()
            )
            namesLines = [line.split("#")[0].strip() for line in namesLines]
            names = [n.strip() for n in "".join(namesLines).split(",")]
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            if "@@Import@@" not in dictionary:
                dictionary["@@Import@@"] = Imports(module, file)
            dictionary["@@Import@@"].addImport(mod, names, lineno)

        elif m.captured("ConditionalDefine"):
            # a conditional function/method definition
            thisindent = _indent(m.captured("ConditionalDefineIndent"))
            while conditionalsstack and conditionalsstack[-1] >= thisindent:
                del conditionalsstack[-1]
                if deltastack:
                    del deltastack[-1]
            conditionalsstack.append(thisindent)
            deltaindentcalculated = False

        elif m.captured("CodingLine"):
            # a coding statement
            coding = m.captured("Coding")
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            if "@@Coding@@" not in dictionary:
                dictionary["@@Coding@@"] = ClbrBaseClasses.Coding(
                    module, file, lineno, coding
                )

    if "__all__" in dictionary:
        # set visibility of all top level elements
        pubs = dictionary["__all__"]
        for key in dictionary:
            if key == "__all__" or key.startswith("@@"):
                continue
            if key in pubs.identifiers:
                dictionary[key].setPublic()
            else:
                dictionary[key].setPrivate()
        del dictionary["__all__"]

    return dictionary


def _indent(ws):
    """
    Module function to return the indentation depth.

    @param ws the whitespace to be checked
    @type str
    @return length of the whitespace string
    @rtype int
    """
    return len(ws.expandtabs(TABWIDTH))
