# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing class browsers for various languages.

Currently it offers class browser support for the following
programming languages.

<ul>
<li>CORBA IDL</li>
<li>JavaScript</li>
<li>ProtoBuf</li>
<li>Python 3</li>
<li>Ruby</li>
</ul>
"""

import importlib
import importlib.machinery
import os

from eric7 import Preferences

# The class browser registry
# Dictionary with class browser name as key. Each entry is a dictionary with
#       0. 'Extensions': list of associated file extensions with leading dot
#       1. 'ReadModule': function to read and parse a module file
#       2. 'Scan': function to parse a given source text
#       3. 'FileIcon': function to get an icon name for the file type
ClassBrowserRegistry = {}

PY_SOURCE = 1
PTL_SOURCE = 128
RB_SOURCE = 129
UNKNOWN_SOURCE = 255

__extensions = {
    "Python": [".py", ".pyw", ".ptl"],  # currently not used
    "Ruby": [".rb"],
}


def registerClassBrowser(name, readModuleFunc, scanFunc, iconFunc, extensions):
    """
    Function to register a class browser type.

    @param name name of the class browser
    @type str
    @param readModuleFunc function to read and parse a file returning  a dictionary
        with the parsing result
    @type function
    @param scanFunc function to scan a given source text returning  a dictionary with
        the parsing result
    @type function
    @param iconFunc function returning an icon name for the supported files
    @type function
    @param extensions list of associated file extensions
    @type list of str
    @exception KeyError raised if the class browser to be registered is already
    """
    global ClassBrowserRegistry

    if name in ClassBrowserRegistry:
        raise KeyError('Class Browser "{0}" already registered.'.format(name))
    else:
        ClassBrowserRegistry[name] = {
            "ReadModule": readModuleFunc,
            "Scan": scanFunc,
            "FileIcon": iconFunc,
            "Extensions": extensions,
        }


def unregisterClassBrowser(name):
    """
    Function to unregister a class browser type.

    @param name name of the class browser
    @type str
    """
    global ClassBrowserRegistry

    if name in ClassBrowserRegistry:
        del ClassBrowserRegistry[name]


def getClassBrowserModule(moduleType):
    """
    Function to import a class browser module.

    @param moduleType type of class browser to load
    @type str
    @return reference to the imported class browser module
    @rtype module
    """
    typeMapping = {
        "python": ".pyclbr",
        "ruby": ".rbclbr",
    }

    if moduleType in typeMapping:
        mod = importlib.import_module(typeMapping[moduleType], __package__)
        return mod

    return None


def readmodule(module, searchPath=None, isPyFile=False):
    """
    Function to read a source file and return a dictionary of classes, functions,
    modules, etc. .

    The real work of parsing the source file is delegated to the individual
    file parsers.

    @param module name of the source file
    @type str
    @param searchPath list of paths the file should be searched in
    @type list of str
    @param isPyFile flag indicating a Python file
    @type bool
    @return the resulting dictionary
    @rtype dict
    """
    ext = os.path.splitext(module)[1].lower()
    searchPath = [] if searchPath is None else searchPath[:]

    if not isPyFile:
        for classBrowserName in ClassBrowserRegistry:
            if ext in ClassBrowserRegistry[classBrowserName]["Extensions"]:
                return ClassBrowserRegistry[classBrowserName]["ReadModule"](
                    module, searchPath
                )

    if ext in __extensions["Ruby"]:
        moduleType = "ruby"
    elif ext in Preferences.getPython("Python3Extensions") or isPyFile:
        moduleType = "python"
    else:
        # try Python if it is without extension
        moduleType = "python"

    classBrowserModule = getClassBrowserModule(moduleType)
    dictionary = (
        classBrowserModule.readmodule_ex(module, searchPath, isTypeFile=isPyFile)
        if classBrowserModule
        else {}
    )

    return dictionary


def scan(src, filename, module, isPyFile=False):
    """
    Function to scan the given source text.

    @param src source text to be scanned
    @type str
    @param filename file name associated with the source text
    @type str
    @param module module name associated with the source text
    @type str
    @param isPyFile flag indicating a Python file
    @type bool
    @return dictionary containing the extracted data
    @rtype dict
    """
    ext = os.path.splitext(filename)[1]
    for classBrowserName in ClassBrowserRegistry:
        if ext in ClassBrowserRegistry[classBrowserName]["Extensions"]:
            return ClassBrowserRegistry[classBrowserName]["Scan"](src, filename, module)

    if ext in __extensions["Ruby"]:
        moduleType = "ruby"
    elif ext in Preferences.getPython("Python3Extensions") or isPyFile:
        moduleType = "python"
    else:
        # try Python if it is without extension
        moduleType = "python"

    classBrowserModule = getClassBrowserModule(moduleType)
    dictionary = (
        classBrowserModule.scan(src, filename, module) if classBrowserModule else None
    )

    return dictionary


def find_module(name, path, isPyFile=False):
    """
    Function to extend the Python module finding mechanism.

    This function searches for files in the given list of paths. If the
    file name doesn't have an extension or an extension of .py, the normal
    Python search implemented in the imp module is used. For all other
    supported files only the paths list is searched.

    @param name file name or module name to search for
    @type str
    @param path search paths
    @type list of str
    @param isPyFile flag indicating a Python file
    @type bool
    @return tuple of the open file, pathname and description. Description
        is a tuple of file suffix, file mode and file type)
    @rtype tuple
    @exception ImportError The file or module wasn't found.
    """
    ext = os.path.splitext(name)[1].lower()

    if ext in __extensions["Ruby"]:
        sourceType = RB_SOURCE
    elif ext == ".ptl":
        sourceType = PTL_SOURCE
    elif (
        name.lower().endswith(tuple(Preferences.getPython("Python3Extensions")))
        or isPyFile
    ):
        sourceType = PY_SOURCE
    else:
        sourceType = UNKNOWN_SOURCE

    if sourceType != UNKNOWN_SOURCE:
        for p in path:  # search in path
            pathname = os.path.join(p, name)
            if os.path.exists(pathname):
                return (open(pathname), pathname, (ext, "r", sourceType))  # noqa: Y115
        raise ImportError
    else:
        # standard Python module file
        if name.lower().endswith(".py"):
            name = name[:-3]

        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None:
            raise ImportError
        if isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            ext = os.path.splitext(spec.origin)[-1]
            return (open(spec.origin), spec.origin, (ext, "r", PY_SOURCE))  # noqa: Y115

    raise ImportError


def determineSourceType(name, isPyFile=False):
    """
    Function to determine the type of a source file given its name.

    @param name file name or module name
    @type str
    @param isPyFile flag indicating a Python file (defaults to False)
    @type bool (optional)
    @return source file type
    @rtype int
    """
    ext = os.path.splitext(name)[1].lower()

    if ext in __extensions["Ruby"]:
        sourceType = RB_SOURCE
    elif ext == ".ptl":
        sourceType = PTL_SOURCE
    elif (
        name.lower().endswith(tuple(Preferences.getPython("Python3Extensions")))
        or isPyFile
    ):
        sourceType = PY_SOURCE
    else:
        sourceType = UNKNOWN_SOURCE

    return sourceType


def getIcon(filename):
    """
    Function to get an icon name for the given file (only for class browsers provided
    via plugins).

    @param filename name of the file
    @type str
    @return icon name
    @rtype str
    """
    ext = os.path.splitext(filename)[1].lower()

    for classBrowserRegistryEntry in ClassBrowserRegistry.values():
        if ext in classBrowserRegistryEntry["Extensions"]:
            return classBrowserRegistryEntry["FileIcon"](filename)

    return "fileMisc"


def isSupportedType(fileext):
    """
    Function to check, if the given file extension indicates a supported file type.

    @param fileext file extension
    @type str
    @return flag indicating a supported file type
    @rtype bool
    """
    supported = any(fileext in exts for exts in __extensions.values())
    supported |= any(
        fileext in cb["Extensions"] for cb in ClassBrowserRegistry.values()
    )
    return supported
