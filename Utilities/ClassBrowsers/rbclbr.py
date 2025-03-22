# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Parse a Ruby file and retrieve classes, modules, methods and attributes.

Parse enough of a Ruby file to recognize class, module and method definitions
and to find out the superclasses of a class as well as its attributes.

It is based on the Python class browser found in this package.
"""

import re

from PyQt6.QtCore import QRegularExpression

from eric7 import Utilities
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities
from eric7.Utilities import ClassBrowsers

from . import ClbrBaseClasses

SUPPORTED_TYPES = [ClassBrowsers.RB_SOURCE]

_getnext = QRegularExpression(
    r"""
    (?P<String>
        =begin .*? =end
    
    |   <<-? (?P<HereMarker1> [a-zA-Z0-9_]+? ) [ \t]* .*? (?P=HereMarker1)

    |   <<-? ['"] (?P<HereMarker2> [^'"]+? ) ['"] [ \t]* .*? (?P=HereMarker2)

    |   " [^"\\\n]* (?: \\. [^"\\\n]*)* "

    |   ' [^'\\\n]* (?: \\. [^'\\\n]*)* '
    )

|   (?P<CodingLine>
        ^ \# \s* [*_-]* \s* coding[:=] \s* (?P<Coding> [-\w_.]+ ) \s* [*_-]* $
    )

|   (?P<Comment>
        ^
        [ \t]* \#+ .*? $
    )

|   (?P<Method>
        ^
        (?P<MethodIndent> [ \t]* )
        def [ \t]+
        (?:
            (?P<MethodName2> [a-zA-Z0-9_]+ (?: \. | :: )
            [a-zA-Z_] [a-zA-Z0-9_?!=]* )
        |
            (?P<MethodName> [a-zA-Z_] [a-zA-Z0-9_?!=]* )
        |
            (?P<MethodName3> [^( \t]{1,3} )
        )
        [ \t]*
        (?:
            \( (?P<MethodSignature> (?: [^)] | \)[ \t]*,? )*? ) \)
        )?
        [ \t]*
    )

|   (?P<Class>
        ^
        (?P<ClassIndent> [ \t]* )
        class
        (?:
            [ \t]+
            (?P<ClassName> [A-Z] [a-zA-Z0-9_]* )
            [ \t]*
            (?P<ClassSupers> < [ \t]* [A-Z] [a-zA-Z0-9_:]* )?
        |
            [ \t]* << [ \t]*
            (?P<ClassName2> [a-zA-Z_] [a-zA-Z0-9_:]* )
        )
        [ \t]*
    )

|   (?P<ClassIgnored>
        \(
        [ \t]*
        class
        .*?
        end
        [ \t]*
        \)
    )

|   (?P<Module>
        ^
        (?P<ModuleIndent> [ \t]* )
        module [ \t]+
        (?P<ModuleName> [A-Z] [a-zA-Z0-9_:]* )
        [ \t]*
    )

|   (?P<AccessControl>
        ^
        (?P<AccessControlIndent> [ \t]* )
        (?:
            (?P<AccessControlType> private | public | protected ) [^_]
        |
            (?P<AccessControlType2>
            private_class_method | public_class_method )
        )
        \(?
        [ \t]*
        (?P<AccessControlList> (?: : [a-zA-Z0-9_]+ , \s* )*
        (?: : [a-zA-Z0-9_]+ )+ )?
        [ \t]*
        \)?
    )

|   (?P<Attribute>
        ^
        (?P<AttributeIndent> [ \t]* )
        (?P<AttributeName> (?: @ | @@ ) [a-zA-Z0-9_]* )
        [ \t]* =
    )

|   (?P<Attr>
        ^
        (?P<AttrIndent> [ \t]* )
        attr
        (?P<AttrType> (?: _accessor | _reader | _writer ) )?
        \(?
        [ \t]*
        (?P<AttrList> (?: : [a-zA-Z0-9_]+ , \s* )*
        (?: : [a-zA-Z0-9_]+ | true | false )+ )
        [ \t]*
        \)?
    )

|   (?P<Begin>
            ^
            [ \t]*
            (?: def | if | unless | case | while | until | for | begin )
            \b [^_]
        |
            [ \t]* do [ \t]* (?: \| .*? \| )? [ \t]* $
    )

|   (?P<BeginEnd>
        \b (?: if ) \b [^_] .*? $
        |
        \b (?: if ) \b [^_] .*? end [ \t]* $
    )

|   (?P<End>
        [ \t]*
        (?:
            end [ \t]* $
        |
            end \b [^_]
        )
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
        self.setPublic()


class Class(ClbrBaseClasses.Class, VisibilityMixin):
    """
    Class to represent a Ruby class.
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


class Module(ClbrBaseClasses.Module, VisibilityMixin):
    """
    Class to represent a Ruby module.
    """

    def __init__(self, module, name, file, lineno, col_offset=0):
        """
        Constructor

        @param module name of the module containing this module
        @type str
        @param name name of this module
        @type str
        @param file file name containing this module
        @type str
        @param lineno linenumber of the module definition
        @type int
        @param col_offset column number of the module definition (defaults to 0)
        @type int (optional)
        """
        ClbrBaseClasses.Module.__init__(
            self, module, name, file, lineno, col_offset=col_offset
        )
        VisibilityMixin.__init__(self)


class Function(ClbrBaseClasses.Function, VisibilityMixin):
    """
    Class to represent a Ruby function.
    """

    def __init__(
        self, module, name, file, lineno, col_offset=0, signature="", separator=","
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
        )
        VisibilityMixin.__init__(self)


class Attribute(ClbrBaseClasses.Attribute, VisibilityMixin):
    """
    Class to represent a class or module attribute.
    """

    def __init__(self, module, name, file, lineno, col_offset=0):
        """
        Constructor

        @param module name of the module containing this attribute
        @type str
        @param name name of this attribute
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
        self.setPrivate()


def readmodule_ex(module, searchPath=None, isTypeFile=False):  # noqa: U100
    """
    Read a Ruby file and return a dictionary of classes, functions and modules.

    @param module name of the Ruby file
    @type str
    @param searchPath path the file should be searched in
    @type list of str
    @param isTypeFile flag indicating a file of this type (unused)
    @type bool
    @return the resulting dictionary
    @rtype dict
    """
    fsInterface = ericApp().getObject("EricServer").getServiceInterface("FileSystem")

    if searchPath and FileSystemUtilities.isRemoteFileName(searchPath[0]):
        sourceType = ClassBrowsers.determineSourceType(module)
        file = fsInterface.join(searchPath[0], module)
    else:
        # search the path for the module
        fullpath = [] if searchPath is None else searchPath[:]
        f, file, (_suff, _mode, sourceType) = ClassBrowsers.find_module(
            module, fullpath
        )
        if f:
            f.close()

    if sourceType not in SUPPORTED_TYPES:
        # not Ruby source, can't do anything with this module
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
    # convert eol markers the Python style
    src = src.replace("\r\n", "\n").replace("\r", "\n")

    dictionary = {}
    dict_counts = {}

    classstack = []  # stack of (class, indent) pairs
    acstack = []  # stack of (access control, indent) pairs
    indent = 0

    lineno, last_lineno_pos = 1, 0
    cur_obj = None
    lastGlobalEntry = None
    i = 0
    while True:
        m = _getnext(src, i)
        if not m.hasMatch():
            break
        start, i = m.capturedStart(), m.capturedEnd()

        if m.captured("Method"):
            # found a method definition or function
            thisindent = indent
            indent += 1
            meth_name = (
                m.captured("MethodName")
                or m.captured("MethodName2")
                or m.captured("MethodName3")
            )
            meth_sig = m.captured("MethodSignature")
            meth_sig = meth_sig and meth_sig.replace("\\\n", "") or ""
            meth_sig = _commentsub("", meth_sig)
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            if m.captured("MethodName"):
                col_offset = m.capturedStart("MethodName") - m.capturedStart()
            elif m.captured("MethodName2"):
                col_offset = m.capturedStart("MethodName2") - m.capturedStart()
            elif m.captured("MethodName3"):
                col_offset = m.capturedStart("MethodName3") - m.capturedStart()
            if meth_name.startswith("self."):
                meth_name = meth_name[5:]
            elif meth_name.startswith("self::"):
                meth_name = meth_name[6:]
            # close all classes/modules indented at least as much
            while classstack and classstack[-1][1] >= thisindent:
                if classstack[-1][0] is not None:
                    # record the end line
                    classstack[-1][0].setEndLine(lineno - 1)
                del classstack[-1]
            while acstack and acstack[-1][1] >= thisindent:
                del acstack[-1]
            if classstack:
                # it's a class/module method
                cur_class = classstack[-1][0]
                if isinstance(cur_class, (Class, Module)):
                    # it's a method
                    f = Function(
                        None,
                        meth_name,
                        file,
                        lineno,
                        col_offset=col_offset,
                        signature=meth_sig,
                    )
                    cur_class._addmethod(meth_name, f)
                else:
                    f = cur_class
                # set access control
                if acstack:
                    accesscontrol = acstack[-1][0]
                    if accesscontrol == "private":
                        f.setPrivate()
                    elif accesscontrol == "protected":
                        f.setProtected()
                    elif accesscontrol == "public":
                        f.setPublic()
                # else it's a nested def
            else:
                # it's a function
                f = Function(
                    module,
                    meth_name,
                    file,
                    lineno,
                    col_offset=col_offset,
                    signature=meth_sig,
                )
                if meth_name in dict_counts:
                    dict_counts[meth_name] += 1
                    meth_name = "{0}_{1:d}".format(meth_name, dict_counts[meth_name])
                else:
                    dict_counts[meth_name] = 0
                dictionary[meth_name] = f
            if not classstack:
                if lastGlobalEntry:
                    lastGlobalEntry.setEndLine(lineno - 1)
                lastGlobalEntry = f
            if cur_obj and isinstance(cur_obj, Function):
                cur_obj.setEndLine(lineno - 1)
            cur_obj = f
            classstack.append((f, thisindent))  # Marker for nested fns

        elif (
            m.captured("String")
            or m.captured("Comment")
            or m.captured("ClassIgnored")
            or m.captured("BeginEnd")
        ):
            pass

        elif m.captured("Class"):
            # we found a class definition
            thisindent = indent
            indent += 1
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            # close all classes/modules indented at least as much
            while classstack and classstack[-1][1] >= thisindent:
                if classstack[-1][0] is not None:
                    # record the end line
                    classstack[-1][0].setEndLine(lineno - 1)
                del classstack[-1]
            class_name = m.captured("ClassName") or m.captured("ClassName2")
            col_offset = m.capturedStart("ClassName") - m.capturedStart()
            inherit = m.captured("ClassSupers")
            if inherit:
                # the class inherits from other classes
                inherit = inherit[1:].strip()
                inherit = [_commentsub("", inherit)]
            # remember this class
            cur_class = Class(
                module, class_name, inherit, file, lineno, col_offset=col_offset
            )
            if not classstack:
                if class_name in dictionary:
                    cur_class = dictionary[class_name]
                else:
                    dictionary[class_name] = cur_class
            else:
                cls = classstack[-1][0]
                if class_name in cls.classes:
                    cur_class = cls.classes[class_name]
                elif class_name in (cls.name, "self"):
                    cur_class = cls
                else:
                    cls._addclass(class_name, cur_class)
            if not classstack:
                if lastGlobalEntry:
                    lastGlobalEntry.setEndLine(lineno - 1)
                lastGlobalEntry = cur_class
            cur_obj = cur_class
            classstack.append((cur_class, thisindent))
            while acstack and acstack[-1][1] >= thisindent:
                del acstack[-1]
            acstack.append(["public", thisindent])
            # default access control is 'public'

        elif m.captured("Module"):
            # we found a module definition
            thisindent = indent
            indent += 1
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            # close all classes/modules indented at least as much
            while classstack and classstack[-1][1] >= thisindent:
                if classstack[-1][0] is not None:
                    # record the end line
                    classstack[-1][0].setEndLine(lineno - 1)
                del classstack[-1]
            module_name = m.captured("ModuleName")
            col_offset = m.capturedStart("ModuleName") - m.capturedStart()
            # remember this class
            cur_class = Module(module, module_name, file, lineno, col_offset=col_offset)
            if not classstack:
                if module_name in dictionary:
                    cur_class = dictionary[module_name]
                else:
                    dictionary[module_name] = cur_class
            else:
                cls = classstack[-1][0]
                if module_name in cls.classes:
                    cur_class = cls.classes[module_name]
                elif cls.name == module_name:
                    cur_class = cls
                else:
                    cls._addclass(module_name, cur_class)
            if not classstack:
                if lastGlobalEntry:
                    lastGlobalEntry.setEndLine(lineno - 1)
                lastGlobalEntry = cur_class
            cur_obj = cur_class
            classstack.append((cur_class, thisindent))
            while acstack and acstack[-1][1] >= thisindent:
                del acstack[-1]
            acstack.append(["public", thisindent])
            # default access control is 'public'

        elif m.captured("AccessControl"):
            aclist = m.captured("AccessControlList")
            if not aclist:
                index = -1
                while index >= -len(acstack):
                    if acstack[index][1] < indent:
                        actype = (
                            m.captured("AccessControlType")
                            or m.captured("AccessControlType2").split("_")[0]
                        )
                        acstack[index][0] = actype.lower()
                        break
                    else:
                        index -= 1
            else:
                index = -1
                while index >= -len(classstack):
                    if (
                        classstack[index][0] is not None
                        and not isinstance(classstack[index][0], Function)
                        and classstack[index][1] < indent
                    ):
                        parent = classstack[index][0]
                        actype = (
                            m.captured("AccessControlType")
                            or m.captured("AccessControlType2").split("_")[0]
                        )
                        actype = actype.lower()
                        for name in aclist.split(","):
                            name = name.strip()[1:]  # get rid of leading ':'
                            acmeth = parent._getmethod(name)
                            if acmeth is None:
                                continue
                            if actype == "private":
                                acmeth.setPrivate()
                            elif actype == "protected":
                                acmeth.setProtected()
                            elif actype == "public":
                                acmeth.setPublic()
                        break
                    else:
                        index -= 1

        elif m.captured("Attribute"):
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            col_offset = m.capturedStart("AttributeName") - m.capturedStart()
            index = -1
            while index >= -len(classstack):
                if (
                    classstack[index][0] is not None
                    and not isinstance(classstack[index][0], Function)
                    and classstack[index][1] < indent
                ):
                    attr = Attribute(
                        module,
                        m.captured("AttributeName"),
                        file,
                        lineno,
                        col_offset=col_offset,
                    )
                    classstack[index][0]._addattribute(attr)
                    break
                else:
                    index -= 1
                    if lastGlobalEntry:
                        lastGlobalEntry.setEndLine(lineno - 1)
                    lastGlobalEntry = None

        elif m.captured("Attr"):
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            index = -1
            while index >= -len(classstack):
                if (
                    classstack[index][0] is not None
                    and not isinstance(classstack[index][0], Function)
                    and classstack[index][1] < indent
                ):
                    parent = classstack[index][0]
                    if not m.captured("AttrType"):
                        nv = m.captured("AttrList").split(",")
                        if not nv:
                            break
                        name = nv[0].strip()[1:]  # get rid of leading ':'
                        attr = (
                            parent._getattribute("@" + name)
                            or parent._getattribute("@@" + name)
                            or Attribute(module, "@" + name, file, lineno)
                        )
                        if len(nv) == 1 or nv[1].strip() == "false":
                            attr.setProtected()
                        elif nv[1].strip() == "true":
                            attr.setPublic()
                        parent._addattribute(attr)
                    else:
                        access = m.captured("AttrType")
                        for name in m.captured("AttrList").split(","):
                            name = name.strip()[1:]  # get rid of leading ':'
                            attr = (
                                parent._getattribute("@" + name)
                                or parent._getattribute("@@" + name)
                                or Attribute(module, "@" + name, file, lineno)
                            )
                            if access == "_accessor":
                                attr.setPublic()
                            elif access in ("_reader", "_writer"):
                                if attr.isPrivate():
                                    attr.setProtected()
                                elif attr.isProtected():
                                    attr.setPublic()
                            parent._addattribute(attr)
                    break
                else:
                    index -= 1

        elif m.captured("Begin"):
            # a begin of a block we are not interested in
            indent += 1

        elif m.captured("End"):
            # an end of a block
            indent -= 1
            if indent < 0:
                # no negative indent allowed
                if classstack:
                    # it's a class/module method
                    indent = classstack[-1][1]
                else:
                    indent = 0

        elif m.captured("CodingLine"):
            # a coding statement
            coding = m.captured("Coding")
            lineno += src.count("\n", last_lineno_pos, start)
            last_lineno_pos = start
            if "@@Coding@@" not in dictionary:
                dictionary["@@Coding@@"] = ClbrBaseClasses.Coding(
                    module, file, lineno, coding
                )

    return dictionary
