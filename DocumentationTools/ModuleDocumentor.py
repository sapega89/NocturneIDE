# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the builtin documentation generator.

The different parts of the module document are assembled from the parsed
Python file. The appearance is determined by several templates defined within
this module.
"""

import contextlib
import re
import sys

from eric7.EricUtilities import html_uencode
from eric7.Utilities.ModuleParser import RB_SOURCE, Function

from . import TemplatesListsStyleCSS

_signal = re.compile(
    r"""
    ^@signal [ \t]+
    (?P<SignalName1>
        [a-zA-Z_] \w* [ \t]* \( [^)]* \)
    )
    [ \t]* (?P<SignalDescription1> .*)
|
    ^@signal [ \t]+
    (?P<SignalName2>
        [a-zA-Z_] \w*
    )
    [ \t]+ (?P<SignalDescription2> .*)
    """,
    re.VERBOSE | re.DOTALL | re.MULTILINE,
).search

_event = re.compile(
    r"""
    ^@event [ \t]+
    (?P<EventName1>
        [a-zA-Z_] \w* [ \t]* \( [^)]* \)
    )
    [ \t]* (?P<EventDescription1> .*)
|
    ^@event [ \t]+
    (?P<EventName2>
        [a-zA-Z_] \w*
    )
    [ \t]+ (?P<EventDescription2> .*)
    """,
    re.VERBOSE | re.DOTALL | re.MULTILINE,
).search


class TagError(Exception):
    """
    Exception class raised, if an invalid documentation tag was found.
    """

    pass


class ModuleDocument:
    """
    Class implementing the builtin documentation generator.
    """

    def __init__(self, module):
        """
        Constructor

        @param module information of the parsed Python file
        @type str
        """
        self.module = module
        self.empty = True

        self.keywords = []
        # list of tuples containing the name (string) and
        # the ref (string). The ref is without the filename part.
        self.generated = False

    def isEmpty(self):
        """
        Public method to determine, if the module contains any classes or
        functions.

        @return flag indicating an empty module (i.e. __init__.py without
            any contents)
        @rtype bool
        """
        return self.empty

    def name(self):
        """
        Public method used to get the module name.

        @return name of the module
        @rtype str
        """
        return self.module.name

    def description(self):
        """
        Public method used to get the description of the module.

        @return description of the module
        @rtype str
        """
        return self.__formatDescription(self.module.description)

    def shortDescription(self):
        """
        Public method used to get the short description of the module.

        The short description is just the first line of the modules
        description.

        @return short description of the module
        @rtype str
        """
        return self.__getShortDescription(self.module.description)

    def genDocument(self):
        """
        Public method to generate the source code documentation.

        @return source code documentation
        @rtype str
        """
        doc = (
            TemplatesListsStyleCSS.headerTemplate.format(**{"Title": self.module.name})
            + self.__genModuleSection()
            + TemplatesListsStyleCSS.footerTemplate
        )
        self.generated = True
        return doc

    def __genModuleSection(self):
        """
        Private method to generate the body of the document.

        @return body of the document
        @rtype str
        """
        globalsList = self.__genGlobalsListSection()
        classList = self.__genClassListSection()
        functionList = self.__genFunctionListSection()
        try:
            if self.module.type == RB_SOURCE:
                rbModulesList = self.__genRbModulesListSection()
                modBody = TemplatesListsStyleCSS.rbFileTemplate.format(
                    **{
                        "Module": self.module.name,
                        "ModuleDescription": self.__formatDescription(
                            self.module.description
                        ),
                        "GlobalsList": globalsList,
                        "ClassList": classList,
                        "RbModulesList": rbModulesList,
                        "FunctionList": functionList,
                    }
                )
            else:
                modBody = TemplatesListsStyleCSS.moduleTemplate.format(
                    **{
                        "Module": self.module.name,
                        "ModuleDescription": self.__formatDescription(
                            self.module.description
                        ),
                        "GlobalsList": globalsList,
                        "ClassList": classList,
                        "FunctionList": functionList,
                    }
                )
        except TagError as e:
            sys.stderr.write("Error processing {0}.\n".format(self.module.file))
            sys.stderr.write(
                "Error in tags of description of module {0}.\n".format(self.module.name)
            )
            sys.stderr.write("{0}\n".format(e))
            return ""

        classesSection = self.__genClassesSection()
        functionsSection = self.__genFunctionsSection()
        rbModulesSection = (
            self.__genRbModulesSection() if self.module.type == RB_SOURCE else ""
        )
        return "{0}{1}{2}{3}".format(
            modBody, classesSection, rbModulesSection, functionsSection
        )

    def __genListSection(self, names, sectionDict, kwSuffix=""):
        """
        Private method to generate a list section of the document.

        @param names names to appear in the list
        @type list of str
        @param sectionDict dictionary containing all relevant information
        @type dict
        @param kwSuffix suffix to be used for the QtHelp keywords
        @type str
        @return list section
        @rtype str
        """
        lst = []
        for name in names:
            lst.append(
                TemplatesListsStyleCSS.listEntryTemplate.format(
                    **{
                        "Link": "{0}".format(name),
                        "Name": sectionDict[name].name,
                        "Description": self.__getShortDescription(
                            sectionDict[name].description
                        ),
                        "Deprecated": (
                            TemplatesListsStyleCSS.listEntryDeprecatedTemplate
                            if self.__checkDeprecated(sectionDict[name].description)
                            else ""
                        ),
                    }
                )
            )
            n = "{0} ({1})".format(name, kwSuffix) if kwSuffix else "{0}".format(name)
            self.keywords.append((n, "#{0}".format(name)))
        return "\n".join(lst)

    def __genGlobalsListSection(self, class_=None):
        """
        Private method to generate the section listing all global attributes of
        the module.

        @param class_ reference to a class object
        @type class
        @return globals list section
        @rtype str
        """
        attrNames = []
        scope = class_ if class_ is not None else self.module
        attrNames = sorted(
            attr for attr in scope.globals if not scope.globals[attr].isSignal
        )
        s = (
            "\n".join(
                [
                    TemplatesListsStyleCSS.listEntrySimpleTemplate.format(
                        **{"Name": name}
                    )
                    for name in attrNames
                ]
            )
            if attrNames
            else TemplatesListsStyleCSS.listEntryNoneTemplate
        )
        return TemplatesListsStyleCSS.listTemplate.format(**{"Entries": s})

    def __genClassListSection(self):
        """
        Private method to generate the section listing all classes of the
        module.

        @return classes list section
        @rtype str
        """
        names = sorted(self.module.classes)
        if names:
            self.empty = False
            s = self.__genListSection(names, self.module.classes)
        else:
            s = TemplatesListsStyleCSS.listEntryNoneTemplate
        return TemplatesListsStyleCSS.listTemplate.format(**{"Entries": s})

    def __genRbModulesListSection(self):
        """
        Private method to generate the section listing all modules of the file
        (Ruby only).

        @return modules list section
        @rtype str
        """
        names = sorted(self.module.modules)
        if names:
            self.empty = False
            s = self.__genListSection(names, self.module.modules)
        else:
            s = TemplatesListsStyleCSS.listEntryNoneTemplate
        return TemplatesListsStyleCSS.listTemplate.format(**{"Entries": s})

    def __genFunctionListSection(self):
        """
        Private method to generate the section listing all functions of the
        module.

        @return functions list section
        @rtype str
        """
        names = sorted(self.module.functions)
        if names:
            self.empty = False
            s = self.__genListSection(names, self.module.functions)
        else:
            s = TemplatesListsStyleCSS.listEntryNoneTemplate
        return TemplatesListsStyleCSS.listTemplate.format(**{"Entries": s})

    def __genClassesSection(self):
        """
        Private method to generate the document section with details about
        classes.

        @return classes details section
        @rtype str
        """
        classNames = sorted(self.module.classes)
        classes = []
        for className in classNames:
            _class = self.module.classes[className]
            supers = _class.super
            supers = ", ".join(supers) if len(supers) > 0 else "None"

            globalsList = self.__genGlobalsListSection(_class)
            classMethList, classMethBodies = self.__genMethodSection(
                _class, className, Function.Class
            )
            methList, methBodies = self.__genMethodSection(
                _class, className, Function.General
            )
            staticMethList, staticMethBodies = self.__genMethodSection(
                _class, className, Function.Static
            )

            try:
                clsBody = TemplatesListsStyleCSS.classTemplate.format(
                    **{
                        "Anchor": className,
                        "Class": _class.name,
                        "ClassSuper": supers,
                        "ClassDescription": self.__formatDescription(
                            _class.description
                        ),
                        "GlobalsList": globalsList,
                        "ClassMethodList": classMethList,
                        "MethodList": methList,
                        "StaticMethodList": staticMethList,
                        "MethodDetails": classMethBodies
                        + methBodies
                        + staticMethBodies,
                    }
                )
            except TagError as e:
                sys.stderr.write("Error processing {0}.\n".format(self.module.file))
                sys.stderr.write(
                    "Error in tags of description of class {0}.\n".format(className)
                )
                sys.stderr.write("{0}\n".format(e))
                clsBody = ""

            classes.append(clsBody)

        return "".join(classes)

    def __genMethodsListSection(
        self, names, sectionDict, className, clsName, includeInit=True
    ):
        """
        Private method to generate the methods list section of a class.

        @param names names to appear in the list
        @type list of str
        @param sectionDict dictionary containing all relevant information
        @type dict
        @param className class name containing the names
        @type str
        @param clsName visible class name containing the names
        @type str
        @param includeInit flag indicating to include the __init__ method
        @type bool
        @return methods list section
        @rtype str
        """
        lst = []
        if includeInit:
            with contextlib.suppress(KeyError):
                lst.append(
                    TemplatesListsStyleCSS.listEntryTemplate.format(
                        **{
                            "Link": "{0}.{1}".format(className, "__init__"),
                            "Name": clsName,
                            "Description": self.__getShortDescription(
                                sectionDict["__init__"].description
                            ),
                            "Deprecated": (
                                TemplatesListsStyleCSS.listEntryDeprecatedTemplate
                                if self.__checkDeprecated(
                                    sectionDict["__init__"].description
                                )
                                else ""
                            ),
                        }
                    )
                )
                self.keywords.append(
                    (
                        "{0} (Constructor)".format(className),
                        "#{0}.{1}".format(className, "__init__"),
                    )
                )

        for name in names:
            lst.append(
                TemplatesListsStyleCSS.listEntryTemplate.format(
                    **{
                        "Link": "{0}.{1}".format(className, name),
                        "Name": sectionDict[name].name,
                        "Description": self.__getShortDescription(
                            sectionDict[name].description
                        ),
                        "Deprecated": (
                            TemplatesListsStyleCSS.listEntryDeprecatedTemplate
                            if self.__checkDeprecated(sectionDict[name].description)
                            else ""
                        ),
                    }
                )
            )
            self.keywords.append(
                ("{0}.{1}".format(className, name), "#{0}.{1}".format(className, name))
            )
        return "\n".join(lst)

    def __genMethodSection(self, obj, className, modifierFilter):
        """
        Private method to generate the method details section.

        @param obj reference to the object being formatted
        @type class
        @param className name of the class containing the method
        @type str
        @param modifierFilter filter value designating the method types
        @type str
        @return method list and method details section
        @rtype tuple of (str, str)
        """
        methList = []
        methBodies = []
        methods = sorted(
            k for k in obj.methods if obj.methods[k].modifier == modifierFilter
        )
        if "__init__" in methods:
            methods.remove("__init__")
            try:
                methBody = TemplatesListsStyleCSS.constructorTemplate.format(
                    **{
                        "Anchor": className,
                        "Class": obj.name,
                        "Method": "__init__",
                        "MethodDescription": self.__formatDescription(
                            obj.methods["__init__"].description
                        ),
                        "Params": ", ".join(obj.methods["__init__"].parameters[1:]),
                    }
                )
            except TagError as e:
                sys.stderr.write("Error processing {0}.\n".format(self.module.file))
                sys.stderr.write(
                    "Error in tags of description of method {0}.{1}.\n".format(
                        className, "__init__"
                    )
                )
                sys.stderr.write("{0}\n".format(e))
                methBody = ""
            methBodies.append(methBody)

        if modifierFilter == Function.Class:
            methodClassifier = " (class method)"
        elif modifierFilter == Function.Static:
            methodClassifier = " (static)"
        else:
            methodClassifier = ""
        for method in methods:
            try:
                methBody = TemplatesListsStyleCSS.methodTemplate.format(
                    **{
                        "Anchor": className,
                        "Class": obj.name,
                        "Method": obj.methods[method].name,
                        "MethodClassifier": methodClassifier,
                        "MethodDescription": self.__formatDescription(
                            obj.methods[method].description
                        ),
                        "Params": ", ".join(obj.methods[method].parameters[1:]),
                    }
                )
            except TagError as e:
                sys.stderr.write("Error processing {0}.\n".format(self.module.file))
                sys.stderr.write(
                    "Error in tags of description of method {0}.{1}.\n".format(
                        className, method
                    )
                )
                sys.stderr.write("{0}\n".format(e))
                methBody = ""
            methBodies.append(methBody)

        methList = self.__genMethodsListSection(
            methods,
            obj.methods,
            className,
            obj.name,
            includeInit=modifierFilter == Function.General,
        )

        if not methList:
            methList = TemplatesListsStyleCSS.listEntryNoneTemplate
        return (
            TemplatesListsStyleCSS.listTemplate.format(**{"Entries": methList}),
            "".join(methBodies),
        )

    def __genRbModulesSection(self):
        """
        Private method to generate the document section with details about
        Ruby modules.

        @return Ruby modules details section
        @rtype str
        """
        rbModulesNames = sorted(self.module.modules)
        rbModules = []
        for rbModuleName in rbModulesNames:
            rbModule = self.module.modules[rbModuleName]
            globalsList = self.__genGlobalsListSection(rbModule)
            methList, methBodies = self.__genMethodSection(
                rbModule, rbModuleName, Function.General
            )
            classList, classBodies = self.__genRbModulesClassesSection(
                rbModule, rbModuleName
            )

            try:
                rbmBody = TemplatesListsStyleCSS.rbModuleTemplate.format(
                    **{
                        "Anchor": rbModuleName,
                        "Module": rbModule.name,
                        "ModuleDescription": self.__formatDescription(
                            rbModule.description
                        ),
                        "GlobalsList": globalsList,
                        "ClassesList": classList,
                        "ClassesDetails": classBodies,
                        "FunctionsList": methList,
                        "FunctionsDetails": methBodies,
                    }
                )
            except TagError as e:
                sys.stderr.write("Error processing {0}.\n".format(self.module.file))
                sys.stderr.write(
                    "Error in tags of description of Ruby module {0}.\n".format(
                        rbModuleName
                    )
                )
                sys.stderr.write("{0}\n".format(e))
                rbmBody = ""

            rbModules.append(rbmBody)

        return "".join(rbModules)

    def __genRbModulesClassesSection(self, obj, modName):
        """
        Private method to generate the Ruby module classes details section.

        @param obj reference to the object being formatted
        @type class
        @param modName name of the Ruby module containing the classes
        @type str
        @return classes list and classes details section
        @rtype tuple of (str, str)
        """
        classNames = sorted(obj.classes)
        classes = []
        for className in classNames:
            _class = obj.classes[className]
            supers = _class.super
            supers = ", ".join(supers) if len(supers) > 0 else "None"

            methList, methBodies = self.__genMethodSection(
                _class, className, Function.General
            )

            try:
                clsBody = TemplatesListsStyleCSS.rbModulesClassTemplate.format(
                    **{
                        "Anchor": className,
                        "Class": _class.name,
                        "ClassSuper": supers,
                        "ClassDescription": self.__formatDescription(
                            _class.description
                        ),
                        "MethodList": methList,
                        "MethodDetails": methBodies,
                    }
                )
            except TagError as e:
                sys.stderr.write("Error processing {0}.\n".format(self.module.file))
                sys.stderr.write(
                    "Error in tags of description of class {0}.\n".format(className)
                )
                sys.stderr.write("{0}\n".format(e))
                clsBody = ""

            classes.append(clsBody)

        classesList = self.__genRbModulesClassesListSection(
            classNames, obj.classes, modName
        )

        if not classesList:
            classesList = TemplatesListsStyleCSS.listEntryNoneTemplate
        return (
            TemplatesListsStyleCSS.listTemplate.format(**{"Entries": classesList}),
            "".join(classes),
        )

    def __genRbModulesClassesListSection(self, names, sectionDict, moduleName):
        """
        Private method to generate the classes list section of a Ruby module.

        @param names names to appear in the list
        @type list of str
        @param sectionDict dictionary containing all relevant information
        @type dict
        @param moduleName name of the Ruby module containing the classes
        @type str
        @return list section
        @rtype str
        """
        lst = []
        for name in names:
            lst.append(
                TemplatesListsStyleCSS.listEntryTemplate.format(
                    **{
                        "Link": "{0}.{1}".format(moduleName, name),
                        "Name": sectionDict[name].name,
                        "Description": self.__getShortDescription(
                            sectionDict[name].description
                        ),
                        "Deprecated": (
                            TemplatesListsStyleCSS.listEntryDeprecatedTemplate
                            if self.__checkDeprecated(sectionDict[name].description)
                            else ""
                        ),
                    }
                )
            )
            self.keywords.append(
                (
                    "{0}.{1}".format(moduleName, name),
                    "#{0}.{1}".format(moduleName, name),
                )
            )
        return "\n".join(lst)

    def __genFunctionsSection(self):
        """
        Private method to generate the document section with details about
        functions.

        @return functions details section
        @rtype str
        """
        funcBodies = []
        funcNames = sorted(self.module.functions)
        for funcName in funcNames:
            try:
                funcBody = TemplatesListsStyleCSS.functionTemplate.format(
                    **{
                        "Anchor": funcName,
                        "Function": self.module.functions[funcName].name,
                        "FunctionDescription": self.__formatDescription(
                            self.module.functions[funcName].description
                        ),
                        "Params": ", ".join(self.module.functions[funcName].parameters),
                    }
                )
            except TagError as e:
                sys.stderr.write("Error processing {0}.\n".format(self.module.file))
                sys.stderr.write(
                    "Error in tags of description of function {0}.\n".format(funcName)
                )
                sys.stderr.write("{0}\n".format(e))
                funcBody = ""

            funcBodies.append(funcBody)

        return "".join(funcBodies)

    def __getShortDescription(self, desc):
        """
        Private method to determine the short description of an object.

        The short description is just the first non empty line of the
        documentation string.

        @param desc documentation string
        @type str
        @return short description
        @rtype str
        """
        dlist = desc.splitlines()
        sdlist = []
        descfound = 0
        for desc in dlist:
            desc = desc.strip()
            if desc:
                descfound = 1
                dotpos = desc.find(".")
                if dotpos == -1:
                    sdlist.append(desc.strip())
                else:
                    while dotpos + 1 < len(desc) and not desc[dotpos + 1].isspace():
                        # don't recognize '.' inside a number or word as
                        # stop condition
                        dotpos = desc.find(".", dotpos + 1)
                        if dotpos == -1:
                            break
                    if dotpos == -1:
                        sdlist.append(desc.strip())
                    else:
                        sdlist.append(desc[: dotpos + 1].strip())
                        break  # break if a '.' is found
            else:
                if descfound:
                    break  # break if an empty line is found
        if sdlist:
            return html_uencode(" ".join(sdlist))
        else:
            return ""

    def __checkDeprecated(self, descr):
        """
        Private method to check, if the object to be documented contains a
        deprecated flag.

        @param descr documentation string
        @type str
        @return flag indicating the deprecation status
        @rtype bool
        """
        dlist = descr.splitlines()
        for desc in dlist:
            desc = desc.strip()
            if desc.startswith("@deprecated"):
                return True
        return False

    def __genParagraphs(self, lines):
        """
        Private method to assemble the descriptive paragraphs of a docstring.

        A paragraph is made up of a number of consecutive lines without
        an intermediate empty line. Empty lines are treated as a paragraph
        delimiter.

        @param lines list of individual lines
        @type list of str
        @return formatted paragraphs
        @rtype str
        """
        lst = []
        linelist = []
        for line in lines:
            if line.strip():
                if line == ".":
                    linelist.append("")
                else:
                    linelist.append(html_uencode(line))
            else:
                lst.append(
                    TemplatesListsStyleCSS.paragraphTemplate.format(
                        **{"Lines": "\n".join(linelist)}
                    )
                )
                linelist = []
        if linelist:
            lst.append(
                TemplatesListsStyleCSS.paragraphTemplate.format(
                    **{"Lines": "\n".join(linelist)}
                )
            )
        return "".join(lst)

    def __genDescriptionListSection(self, dictionary, template):
        """
        Private method to generate the list section of a description.

        @param dictionary dictionary containing the info for the
            list section
        @type dict
        @param template template to be used for the list
        @type str
        @return list section
        @rtype str
        """
        lst = []
        keys = sorted(dictionary)
        for key in keys:
            lst.append(
                template.format(
                    **{
                        "Name": key,
                        "Description": html_uencode("\n".join(dictionary[key])),
                    }
                )
            )
        return "".join(lst)

    def __genParamDescriptionListSection(self, _list):
        """
        Private method to generate the list section of a description.

        @param _list list containing the info for the parameter description
            list section
        @type list of lists with three elements
        @return formatted list section
        @rtype str
        """
        lst = []
        for name, type_, lines in _list:
            if type_:
                lst.append(
                    TemplatesListsStyleCSS.parameterTypesListEntryTemplate.format(
                        **{
                            "Name": name,
                            "Type": type_,
                            "Description": html_uencode("\n".join(lines)),
                        }
                    )
                )
            else:
                lst.append(
                    TemplatesListsStyleCSS.parametersListEntryTemplate.format(
                        **{
                            "Name": name,
                            "Description": html_uencode("\n".join(lines)),
                        }
                    )
                )
        return "".join(lst)

    def __formatCrossReferenceEntry(self, entry):
        """
        Private method to format a cross reference entry.

        This cross reference entry looks like "package.module#member label".

        @param entry entry to be formatted
        @type str
        @return formatted entry
        @rtype str
        """
        if entry.startswith('"'):
            return entry
        elif entry.startswith("<"):
            entry = entry[3:]
        else:
            try:
                reference, label = entry.split(None, 1)
            except ValueError:
                reference = entry
                label = entry
            try:
                path, anchor = reference.split("#", 1)
            except ValueError:
                path = reference
                anchor = ""
            reference = path and "{0}.html".format(path) or ""
            if anchor:
                reference = "{0}#{1}".format(reference, anchor)
            entry = 'href="{0}">{1}</a>'.format(reference, label)

        return TemplatesListsStyleCSS.seeLinkTemplate.format(**{"Link": entry})

    def __genSeeListSection(self, _list, template):
        """
        Private method to generate the "see also" list section of a
        description.

        @param _list list containing the info for the section
        @type list
        @param template template to be used for the list
        @type str
        @return list section
        @rtype str
        """
        lst = []
        for seeEntry in _list:
            seeEntryString = "".join(seeEntry)
            lst.append(
                template.format(
                    **{
                        "Link": html_uencode(
                            self.__formatCrossReferenceEntry(seeEntryString)
                        ),
                    }
                )
            )
        return "\n".join(lst)

    def __processInlineTags(self, desc):
        """
        Private method to process inline tags.

        @param desc one line of the description
        @type str
        @return processed line with inline tags expanded
        @rtype str
        @exception TagError raised to indicate an invalid tag
        """
        start = desc.find("{@")
        while start != -1:
            stop = desc.find("}", start + 2)
            if stop == -1:
                raise TagError("Unterminated inline tag.\n{0}".format(desc))

            tagText = desc[start + 1 : stop]
            if tagText.startswith("@link"):
                parts = tagText.split(None, 1)
                if len(parts) < 2:
                    raise TagError(
                        "Wrong format in inline tag {0}.\n{1}".format(parts[0], desc)
                    )

                formattedTag = self.__formatCrossReferenceEntry(parts[1])
                desc = desc.replace("{{{0}}}".format(tagText), formattedTag)
            else:
                tag = tagText.split(None, 1)[0]
                raise TagError(
                    "Unknown inline tag encountered, {0}.\n{1}".format(tag, desc)
                )

            start = desc.find("{@")

        return desc

    def __formatDescription(self, descr):
        """
        Private method to format the contents of the documentation string.

        @param descr contents of the documentation string
        @type str
        @return formatted contents of the documentation string
        @rtype str
        @exception TagError A tag doesn't have the correct number of arguments.
        """
        if not descr:
            return ""

        paragraphs = []
        paramList = []
        returns = []
        returnTypes = []
        yields = []
        yieldTypes = []
        exceptionDict = {}
        signalDict = {}
        eventDict = {}
        deprecated = []
        authorInfo = []
        sinceInfo = []
        seeList = []
        lastItem = paragraphs
        inTagSection = False

        dlist = descr.splitlines()
        while dlist and not dlist[0]:
            del dlist[0]
        lastTag = ""
        buffer = ""
        for ditem in dlist:
            ditem = self.__processInlineTags(ditem)
            desc = ditem.strip()
            if buffer:
                if desc.startswith("@"):
                    buffer = ""
                    raise TagError("Wrong format in {0} line.\n".format(lastTag))
                else:
                    desc = buffer + desc
            if desc:
                if desc.startswith(("@param", "@keyparam")):
                    inTagSection = True
                    parts = desc.split(None, 2)
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    paramName = parts[1]
                    if parts[0] == "@keyparam":
                        paramName += "="
                    try:
                        paramList.append([paramName, "", [parts[2]]])
                    except IndexError:
                        paramList.append([paramName, "", []])
                    lastItem = paramList[-1][2]
                elif desc.startswith("@type"):
                    parts = desc.split(None, 1)
                    if lastTag not in ["@param", "@keyparam"]:
                        raise TagError(
                            "{0} line must be preceded by a parameter line\n".format(
                                parts[0]
                            )
                        )
                    inTagSection = True
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    paramList[-1][1] = parts[1]
                elif desc.startswith("@ptype"):
                    raise TagError("Tag '@ptype' is deprecated, use '@type' instead\n")
                elif desc.startswith("@ireturn"):
                    raise TagError(
                        "Tag '@ireturn' is deprecated, use '@return' instead\n"
                    )
                elif desc.startswith("@return"):
                    inTagSection = True
                    parts = desc.split(None, 1)
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    returns = [parts[1]]
                    lastItem = returns
                elif desc.startswith("@rtype"):
                    parts = desc.split(None, 1)
                    if lastTag != "@return":
                        raise TagError(
                            "{0} line must be preceded by a @return line\n".format(
                                parts[0]
                            )
                        )
                    inTagSection = True
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    returnTypes = [parts[1]]
                    lastItem = returnTypes
                elif desc.startswith("@yield"):
                    inTagSection = True
                    parts = desc.split(None, 1)
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    yields = [parts[1]]
                    lastItem = yields
                elif desc.startswith("@ytype"):
                    parts = desc.split(None, 1)
                    if lastTag != "@yield":
                        raise TagError(
                            "{0} line must be preceded by a @yield line\n".format(
                                parts[0]
                            )
                        )
                    inTagSection = True
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    yieldTypes = [parts[1]]
                    lastItem = yieldTypes
                elif desc.startswith(("@throws", "@raise")):
                    tag = desc.split(None, 1)[0]
                    raise TagError(
                        "Tag '{0}' is deprecated, use '@exception' instead\n".format(
                            tag
                        )
                    )
                elif desc.startswith("@exception"):
                    inTagSection = True
                    parts = desc.split(None, 2)
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    excName = parts[1]
                    try:
                        exceptionDict[excName] = [parts[2]]
                    except IndexError:
                        exceptionDict[excName] = []
                    lastItem = exceptionDict[excName]
                elif desc.startswith("@signal"):
                    inTagSection = True
                    lastTag = desc.split(None, 1)[0]
                    m = _signal(desc, 0)
                    if m is None:
                        buffer = desc
                    else:
                        buffer = ""
                        signalName = m.group("SignalName1") or m.group("SignalName2")
                        signalDesc = m.group("SignalDescription1") or m.group(
                            "SignalDescription2"
                        )
                        signalDict[signalName] = []
                        if signalDesc is not None:
                            signalDict[signalName].append(signalDesc)
                        lastItem = signalDict[signalName]
                elif desc.startswith("@event"):
                    inTagSection = True
                    lastTag = desc.split(None, 1)[0]
                    m = _event(desc, 0)
                    if m is None:
                        buffer = desc
                    else:
                        buffer = ""
                        eventName = m.group("EventName1") or m.group("EventName2")
                        eventDesc = m.group("EventDescription1") or m.group(
                            "EventDescription2"
                        )
                        eventDict[eventName] = []
                        if eventDesc is not None:
                            eventDict[eventName].append(eventDesc)
                        lastItem = eventDict[eventName]
                elif desc.startswith("@deprecated"):
                    inTagSection = True
                    parts = desc.split(None, 1)
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    deprecated = [parts[1]]
                    lastItem = deprecated
                elif desc.startswith("@author"):
                    inTagSection = True
                    parts = desc.split(None, 1)
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    authorInfo = [parts[1]]
                    lastItem = authorInfo
                elif desc.startswith("@since"):
                    inTagSection = True
                    parts = desc.split(None, 1)
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    sinceInfo = [parts[1]]
                    lastItem = sinceInfo
                elif desc.startswith("@see"):
                    inTagSection = True
                    parts = desc.split(None, 1)
                    lastTag = parts[0]
                    if len(parts) < 2:
                        raise TagError("Wrong format in {0} line.\n".format(parts[0]))
                    seeList.append([parts[1]])
                    lastItem = seeList[-1]
                elif desc.startswith("@@"):
                    lastItem.append(desc[1:])
                elif desc.startswith("@"):
                    tag = desc.split(None, 1)[0]
                    raise TagError("Unknown tag encountered, {0}.\n".format(tag))
                else:
                    lastItem.append(ditem)
            elif not inTagSection:
                lastItem.append(ditem)

        description = self.__genParagraphs(paragraphs) if paragraphs else ""

        parameterSect = (
            TemplatesListsStyleCSS.parametersListTemplate.format(
                **{"Parameters": self.__genParamDescriptionListSection(paramList)}
            )
            if paramList
            else ""
        )

        returnSect = (
            TemplatesListsStyleCSS.returnsTemplate.format(
                html_uencode("\n".join(returns))
            )
            if returns
            else ""
        )

        returnTypesSect = (
            TemplatesListsStyleCSS.returnTypesTemplate.format(
                html_uencode("\n".join(returnTypes))
            )
            if returnTypes
            else ""
        )

        yieldSect = (
            TemplatesListsStyleCSS.yieldsTemplate.format(
                html_uencode("\n".join(yields))
            )
            if yields
            else ""
        )

        yieldTypesSect = (
            TemplatesListsStyleCSS.yieldTypesTemplate.format(
                html_uencode("\n".join(yieldTypes))
            )
            if yieldTypes
            else ""
        )

        exceptionSect = (
            TemplatesListsStyleCSS.exceptionsListTemplate.format(
                **{
                    "Exceptions": self.__genDescriptionListSection(
                        exceptionDict,
                        TemplatesListsStyleCSS.exceptionsListEntryTemplate,
                    )
                }
            )
            if exceptionDict
            else ""
        )

        signalSect = (
            TemplatesListsStyleCSS.signalsListTemplate.format(
                **{
                    "Signals": self.__genDescriptionListSection(
                        signalDict, TemplatesListsStyleCSS.signalsListEntryTemplate
                    )
                }
            )
            if signalDict
            else ""
        )

        eventSect = (
            TemplatesListsStyleCSS.eventsListTemplate.format(
                **{
                    "Events": self.__genDescriptionListSection(
                        eventDict, TemplatesListsStyleCSS.eventsListEntryTemplate
                    )
                }
            )
            if eventDict
            else ""
        )

        deprecatedSect = (
            TemplatesListsStyleCSS.deprecatedTemplate.format(
                **{"Lines": html_uencode("\n".join(deprecated))}
            )
            if deprecated
            else ""
        )

        authorInfoSect = (
            TemplatesListsStyleCSS.authorInfoTemplate.format(
                **{"Authors": html_uencode("\n".join(authorInfo))}
            )
            if authorInfo
            else ""
        )

        sinceInfoSect = (
            TemplatesListsStyleCSS.sinceInfoTemplate.format(
                **{"Info": html_uencode(sinceInfo[0])}
            )
            if sinceInfo
            else ""
        )

        seeSect = (
            TemplatesListsStyleCSS.seeListTemplate.format(
                **{
                    "Links": self.__genSeeListSection(
                        seeList, TemplatesListsStyleCSS.seeListEntryTemplate
                    )
                }
            )
            if seeList
            else ""
        )

        return "".join(
            [
                deprecatedSect,
                description,
                parameterSect,
                returnSect,
                returnTypesSect,
                yieldSect,
                yieldTypesSect,
                exceptionSect,
                signalSect,
                eventSect,
                authorInfoSect,
                seeSect,
                sinceInfoSect,
            ]
        )

    def getQtHelpKeywords(self):
        """
        Public method to retrieve the parts for the QtHelp keywords section.

        @return list of tuples containing the name and the ref. The ref is without
            the filename part.
        @rtype list of tuples of (str, str)
        """
        if not self.generated:
            self.genDocument()

        return self.keywords
