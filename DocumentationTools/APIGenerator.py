# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the builtin API generator.
"""


class APIGenerator:
    """
    Class implementing the builtin documentation generator.
    """

    def __init__(self, module):
        """
        Constructor

        @param module information of the parsed Python file
        @type Module
        """
        self.module = module

    def genAPI(self, basePackage, includePrivate):
        """
        Public method to generate the API information.

        @param basePackage name of the base package
        @type str
        @param includePrivate flag indicating to include
            private methods/functions
        @type bool
        @return API information
        @rtype list of str
        """
        self.includePrivate = includePrivate
        modulePath = self.module.name.split(".")
        if modulePath[-1] == "__init__":
            del modulePath[-1]
        if basePackage:
            modulePath[0] = basePackage
        self.moduleName = "{0}.".format(".".join(modulePath))
        self.api = []
        self.__addGlobalsAPI()
        self.__addClassesAPI()
        self.__addFunctionsAPI()
        return self.api

    def genBases(self, includePrivate):
        """
        Public method to generate the base classes information.

        @param includePrivate flag indicating to include private classes
        @type bool
        @return base classes information
        @rtype dictionary of list of str
        """
        bases = {}
        self.includePrivate = includePrivate
        classNames = sorted(self.module.classes)
        for className in classNames:
            if (
                not self.__isPrivate(self.module.classes[className])
                and className not in bases
            ):
                bases[className] = [
                    b for b in self.module.classes[className].super if b != "object"
                ]
        return bases

    def __isPrivate(self, obj):
        """
        Private method to check, if an object is considered private.

        @param obj reference to the object to be checked
        @type ModuleParser.Attribute, ModuleParser.Class or ModuleParser.Function
        @return flag indicating, that object is considered private
        @rtype bool
        """
        private = obj.isPrivate() and not self.includePrivate
        return private

    def __addGlobalsAPI(self):
        """
        Private method to generate the api section for global variables.
        """
        from eric7.QScintilla.Editor import EditorIconId

        moduleNameStr = "{0}".format(self.moduleName)

        for globalName in sorted(self.module.globals):
            if not self.__isPrivate(self.module.globals[globalName]):
                if self.module.globals[globalName].isPublic():
                    iconId = EditorIconId.Attribute
                elif self.module.globals[globalName].isProtected():
                    iconId = EditorIconId.AttributeProtected
                else:
                    iconId = EditorIconId.AttributePrivate
                self.api.append(
                    "{0}{1}?{2:d}".format(moduleNameStr, globalName, iconId)
                )

    def __addClassesAPI(self):
        """
        Private method to generate the api section for classes.
        """
        classNames = sorted(self.module.classes)
        for className in classNames:
            if not self.__isPrivate(self.module.classes[className]):
                self.__addClassVariablesAPI(className)
                self.__addMethodsAPI(className)

    def __addMethodsAPI(self, className):
        """
        Private method to generate the api section for class methods.

        @param className name of the class containing the method
        @type str
        """
        from eric7.QScintilla.Editor import EditorIconId

        _class = self.module.classes[className]
        methods = sorted(_class.methods)
        if "__init__" in methods:
            methods.remove("__init__")
            if _class.isPublic():
                iconId = EditorIconId.Class
            elif _class.isProtected():
                iconId = EditorIconId.ClassProtected
            else:
                iconId = EditorIconId.ClassPrivate
            self.api.append(
                "{0}{1}?{2:d}({3})".format(
                    self.moduleName,
                    _class.name,
                    iconId,
                    ", ".join(_class.methods["__init__"].parameters[1:]),
                )
            )

        classNameStr = "{0}{1}.".format(self.moduleName, className)
        for method in methods:
            if not self.__isPrivate(_class.methods[method]):
                if _class.methods[method].isPublic():
                    iconId = EditorIconId.Method
                elif _class.methods[method].isProtected():
                    iconId = EditorIconId.MethodProtected
                else:
                    iconId = EditorIconId.MethodPrivate
                self.api.append(
                    "{0}{1}?{2:d}({3})".format(
                        classNameStr,
                        method,
                        iconId,
                        ", ".join(_class.methods[method].parameters[1:]),
                    )
                )

    def __addClassVariablesAPI(self, className):
        """
        Private method to generate class api section for class variables.

        @param className name of the class containing the class variables
        @type str
        """
        from eric7.QScintilla.Editor import EditorIconId

        _class = self.module.classes[className]
        classNameStr = "{0}{1}.".format(self.moduleName, className)
        for variable in sorted(_class.globals):
            if not self.__isPrivate(_class.globals[variable]):
                if _class.globals[variable].isPublic():
                    iconId = EditorIconId.Attribute
                elif _class.globals[variable].isProtected():
                    iconId = EditorIconId.AttributeProtected
                else:
                    iconId = EditorIconId.AttributePrivate
                self.api.append("{0}{1}?{2:d}".format(classNameStr, variable, iconId))

    def __addFunctionsAPI(self):
        """
        Private method to generate the api section for functions.
        """
        from eric7.QScintilla.Editor import EditorIconId

        funcNames = sorted(self.module.functions)
        for funcName in funcNames:
            if not self.__isPrivate(self.module.functions[funcName]):
                if self.module.functions[funcName].isPublic():
                    iconId = EditorIconId.Method
                elif self.module.functions[funcName].isProtected():
                    iconId = EditorIconId.MethodProtected
                else:
                    iconId = EditorIconId.MethodPrivate
                self.api.append(
                    "{0}{1}?{2:d}({3})".format(
                        self.moduleName,
                        self.module.functions[funcName].name,
                        iconId,
                        ", ".join(self.module.functions[funcName].parameters),
                    )
                )
