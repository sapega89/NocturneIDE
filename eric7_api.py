#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
eric API Generator.

This is the main Python script of the API generator. It is
this script that gets called via the API generation interface.
This script can be used via the commandline as well.
"""

import argparse
import fnmatch
import glob
import os
import sys

import DocumentationTools
from .__version__ import Version
from .DocumentationTools.APIGenerator import APIGenerator
from .SystemUtilities import FileSystemUtilities, OSUtilities
from .Utilities import ModuleParser


def createArgumentParser():
    """
    Function to create an argument parser.

    @return created argument parser object
    @rtype argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description=(
            "Create API files to be used by 'QScintilla' or the 'eric Assistant'"
            " plugin. It is part of the eric tool suite."
        ),
        epilog="Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>.",
    )

    parser.add_argument(
        "file",
        nargs="+",
        help="'file' can be either python modules, package directories or ordinary"
        " directories. At least one 'file' argument must be given.",
    )
    parser.add_argument(
        "-b",
        "--base",
        default="",
        help="Use the given name as the name of the base package.",
    )
    parser.add_argument(
        "-e",
        "--eol",
        choices=["cr", "lf", "crlf"],
        help="Use the given eol type to terminate lines.",
    )
    parser.add_argument(
        "--exclude-file",
        action="append",
        default=[],
        help="Specify a filename pattern of files to be excluded. This option may be"
        " repeated multiple times.",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        action="store_true",
        help="Ignore the set of builtin modules.",
    )
    parser.add_argument(
        "-l",
        "--language",
        action="append",
        default=[],
        choices=DocumentationTools.supportedExtensionsDictForApis.keys(),
        help="Generate an API file for the given programming language. The default"
        " is 'Python3'. This option may be repeated multiple times.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="Write the API information to the named file. A '%%L'"  # noqa: M601
        " placeholder is replaced by the language of the API file (see --language).",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--private",
        action="store_true",
        help="Include private methods and functions.",
    )
    parser.add_argument(
        "-R",
        "-r",
        "--recursive",
        action="store_true",
        help="Perform a recursive search for source files.",
    )
    parser.add_argument(
        "-t",
        "--extension",
        action="append",
        default=[],
        help="Add the given extension to the list of file extensions. This option may"
        " be given multiple times.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {0}".format(Version),
        help="Show version information and exit.",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        action="append",
        default=[],
        help="Specify a directory basename to be excluded. This option may be repeated"
        " multiple times.",
    )

    return parser


def main():
    """
    Main entry point into the application.
    """
    global supportedExtensions

    parser = createArgumentParser()
    args = parser.parse_args()

    excludeDirs = [
        ".svn",
        ".hg",
        ".git",
        ".ropeproject",
        ".eric7project",
        ".jedi",
        "dist",
        "build",
        "doc",
        "docs",
        "__pycache__",
    ] + args.exclude
    excludePatterns = args.exclude_file
    outputFileName = args.output
    recursive = args.recursive
    basePackage = args.base
    includePrivate = args.private
    progLanguages = args.language
    extensions = [
        ext if ext.startswith(".") else ".{0}".format(ext) for ext in args.extension
    ]
    ignoreBuiltinModules = args.ignore
    newline = {
        "cr": "\r",
        "lf": "\n",
        "crlf": "\r\n",
    }.get(args.eol)

    if len(progLanguages) == 0:
        progLanguages = ["Python3"]

    for progLanguage in sorted(progLanguages):
        basename = ""
        apis = []
        basesDict = {}

        supportedExtensions = DocumentationTools.supportedExtensionsDictForApis[
            progLanguage
        ]
        supportedExtensions.extend(
            e for e in extensions if e not in supportedExtensions
        )

        if not outputFileName.endswith(".api"):
            # append the .api extension, if not given by the user
            outputFileName += ".api"
        if "%L" in outputFileName:
            outputFile = outputFileName.replace("%L", progLanguage)
        else:
            if len(progLanguages) == 1:
                outputFile = outputFileName
            else:
                root, ext = os.path.splitext(outputFileName)
                outputFile = "{0}-{1}{2}".format(root, progLanguage.lower(), ext)
        basesFile = os.path.splitext(outputFile)[0] + ".bas"

        for argsfile in args.file:
            if os.path.isdir(argsfile):
                if os.path.exists(
                    os.path.join(
                        argsfile, FileSystemUtilities.joinext("__init__", ".py")
                    )
                ):
                    basename = os.path.dirname(argsfile)
                    if argsfile == ".":
                        sys.stderr.write("The directory '.' is a package.\n")
                        sys.stderr.write(
                            "Please repeat the call giving its real name.\n"
                        )
                        sys.stderr.write("Ignoring the directory.\n")
                        continue
                else:
                    basename = argsfile
                if basename:
                    basename = "{0}{1}".format(basename, os.sep)

                if recursive and not os.path.islink(argsfile):
                    names = [argsfile] + FileSystemUtilities.getDirs(
                        argsfile, excludeDirs
                    )
                else:
                    names = [argsfile]
            else:
                basename = ""
                names = [argsfile]

            for filename in sorted(names):
                inpackage = False
                if os.path.isdir(filename):
                    files = []
                    for ext in supportedExtensions:
                        files.extend(
                            glob.glob(
                                os.path.join(
                                    filename, FileSystemUtilities.joinext("*", ext)
                                )
                            )
                        )
                        initFile = os.path.join(
                            filename, FileSystemUtilities.joinext("__init__", ext)
                        )
                        if initFile in files:
                            inpackage = True
                            files.remove(initFile)
                            files.insert(0, initFile)
                        elif progLanguage != "Python3":
                            # assume package
                            inpackage = True
                else:
                    if OSUtilities.isWindowsPlatform() and glob.has_magic(filename):
                        files = glob.glob(filename)
                    else:
                        files = [filename]

                for file in files:
                    skipIt = False
                    for pattern in excludePatterns:
                        if fnmatch.fnmatch(os.path.basename(file), pattern):
                            skipIt = True
                            break
                    if skipIt:
                        continue

                    try:
                        module = ModuleParser.readModule(
                            file,
                            basename=basename,
                            inpackage=inpackage,
                            ignoreBuiltinModules=ignoreBuiltinModules,
                        )
                        apiGenerator = APIGenerator(module)
                        api = apiGenerator.genAPI(basePackage, includePrivate)
                        bases = apiGenerator.genBases(includePrivate)
                    except OSError as v:
                        sys.stderr.write("{0} error: {1}\n".format(file, v[1]))
                        continue
                    except ImportError as v:
                        sys.stderr.write("{0} error: {1}\n".format(file, v))
                        continue

                    for apiEntry in api:
                        if apiEntry not in apis:
                            apis.append(apiEntry)
                    for basesEntry in bases:
                        if bases[basesEntry]:
                            basesDict[basesEntry] = bases[basesEntry][:]
                    sys.stdout.write("-- {0} -- {1} ok\n".format(progLanguage, file))

        outdir = os.path.dirname(outputFile)
        if outdir and not os.path.exists(outdir):
            os.makedirs(outdir)
        try:
            with open(outputFile, "w", encoding="utf-8", newline=newline) as out:
                out.write("\n".join(sorted(apis)) + "\n")
        except OSError as v:
            sys.stderr.write("{0} error: {1}\n".format(outputFile, v[1]))
            sys.exit(3)
        try:
            with open(basesFile, "w", encoding="utf-8", newline=newline) as out:
                for baseEntry in sorted(basesDict):
                    out.write(
                        "{0} {1}\n".format(
                            baseEntry, " ".join(sorted(basesDict[baseEntry]))
                        )
                    )
        except OSError as v:
            sys.stderr.write("{0} error: {1}\n".format(basesFile, v[1]))
            sys.exit(3)

    sys.stdout.write("\nDone.\n")
    sys.exit(0)


if __name__ == "__main__":
    main()

#
# eflag: noqa = M801
