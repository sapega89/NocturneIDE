#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
eric Documentation Generator.

This is the main Python script of the documentation generator. It is
this script that gets called via the source documentation interface.
This script can be used via the commandline as well.
"""

import argparse
import fnmatch
import glob
import os
import shutil
import sys

from __version__ import Version
from DocumentationTools import TemplatesListsStyleCSS
from DocumentationTools.Config import eric7docDefaultColors
from DocumentationTools.IndexGenerator import IndexGenerator
from DocumentationTools.ModuleDocumentor import ModuleDocument
from DocumentationTools.QtHelpGenerator import QtHelpGenerator
from SystemUtilities import FileSystemUtilities, OSUtilities
from Utilities import ModuleParser

# list of supported filename extensions
supportedExtensions = [".py", ".pyw", ".ptl", ".rb"]


def createArgumentParser():
    """
    Function to create an argument parser.

    @return created argument parser object
    @rtype argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Create source code documentation files.  It is part of the eric"
        " tool suite.",
        epilog="Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>.",
    )

    parser.add_argument(
        "file",
        nargs="+",
        help="'file' can be either python modules, package directories or ordinary"
        " directories. At least one 'file' argument must be given.",
    )
    parser.add_argument(
        "-c",
        "--style-sheet",
        default="",
        help="Specify a CSS style sheet file to be used.",
    )
    parser.add_argument(
        "-e",
        "--no-empty",
        action="store_true",
        help="Don't include empty modules.",
    )
    parser.add_argument(
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
        "--no-index",
        action="store_true",
        help="Don't generate index files.",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        default="doc",
        help="Generate files in the named directory.",
    )
    parser.add_argument(
        "-R",
        "-r",
        "--recursive",
        action="store_true",
        help="Perform a recursive search for source files.",
    )
    parser.add_argument(
        "-s",
        "--startdir",
        default="",
        help="Start the documentation generation in the given directory.",
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

    colorGroup = parser.add_argument_group(
        "Stylesheet Colors", "Parameters to define individual stylesheet colors."
    )
    colorGroup.add_argument(
        "--body-color",
        default=eric7docDefaultColors["BodyColor"],
        help="Specify the text color.",
    )
    colorGroup.add_argument(
        "--body-background-color",
        default=eric7docDefaultColors["BodyBgColor"],
        help="Specify the text background color.",
    )
    colorGroup.add_argument(
        "--l1header-color",
        default=eric7docDefaultColors["Level1HeaderColor"],
        help="Specify the text color of level 1 headers.",
    )
    colorGroup.add_argument(
        "--l1header-background-color",
        default=eric7docDefaultColors["Level1HeaderBgColor"],
        help="Specify the text background color of level 1 headers.",
    )
    colorGroup.add_argument(
        "--l2header-color",
        default=eric7docDefaultColors["Level2HeaderColor"],
        help="Specify the text color of level 2 headers.",
    )
    colorGroup.add_argument(
        "--l2header-background-color",
        default=eric7docDefaultColors["Level2HeaderBgColor"],
        help="Specify the text background color of level 2 headers.",
    )
    colorGroup.add_argument(
        "--cfheader-color",
        default=eric7docDefaultColors["CFColor"],
        help="Specify the text color of class and function headers.",
    )
    colorGroup.add_argument(
        "--cfheader-background-color",
        default=eric7docDefaultColors["CFBgColor"],
        help="Specify the text background color of class and function headers.",
    )
    colorGroup.add_argument(
        "--link-color",
        default=eric7docDefaultColors["LinkColor"],
        help="Specify the text color of hyperlinks.",
    )

    qtGroup = parser.add_argument_group(
        "QtHelp", "Parameters for QtHelp file creation."
    )
    qtGroup.add_argument(
        "--create-qhp",
        action="store_true",
        help="Enable generation of QtHelp files.",
    )
    qtGroup.add_argument(
        "--qhp-outdir",
        default="help",
        help="Store the QtHelp files in the named directory.",
    )
    qtGroup.add_argument(
        "--qhp-namespace",
        default="",
        help="Use the given namespace (required).",
    )
    qtGroup.add_argument(
        "--qhp-virtualfolder",
        default="source",
        help="Use the given virtual folder (mandatory). The virtual folder must not"
        " contain '/'.",
    )
    qtGroup.add_argument(
        "--qhp-filtername",
        default="unknown",
        help="Use the given name for the custom filter.",
    )
    qtGroup.add_argument(
        "--qhp-filterattribs",
        default="",
        help="Add the given attributes to the filter list. Attributes must be"
        " separated by ':'.",
    )
    qtGroup.add_argument(
        "--qhp-title",
        default="",
        help="Use this as the title for the generated help (mandatory).",
    )
    qtGroup.add_argument(
        "--create-qhc",
        action="store_true",
        help="Enable generation of QtHelp Collection files.",
    )

    return parser


def main():
    """
    Main entry point into the application.
    """
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
    startDir = args.startdir
    outputDir = args.outdir
    recursive = args.recursive
    doIndex = not args.no_index
    noempty = args.no_empty
    newline = {
        "cr": "\r",
        "lf": "\n",
        "crlf": "\r\n",
    }.get(args.eol)

    stylesheetFile = args.style_sheet
    colors = eric7docDefaultColors.copy()
    colors = {
        "BodyColor": args.body_color,
        "BodyBgColor": args.body_background_color,
        "Level1HeaderColor": args.l1header_color,
        "Level1HeaderBgColor": args.l1header_background_color,
        "Level2HeaderColor": args.l2header_color,
        "Level2HeaderBgColor": args.l2header_background_color,
        "CFColor": args.cfheader_color,
        "CFBgColor": args.cfheader_background_color,
        "LinkColor": args.link_color,
    }

    qtHelpCreation = args.create_qhp
    qtHelpOutputDir = args.qhp_outdir
    qtHelpNamespace = args.qhp_namespace
    qtHelpFolder = args.qhp_virtualfolder
    qtHelpFilterName = args.qhp_filtername
    qtHelpFilterAttribs = args.qhp_filterattribs
    qtHelpTitle = args.qhp_title
    qtHelpCreateCollection = args.create_qhc

    if qtHelpCreation and (
        qtHelpNamespace == ""
        or qtHelpFolder == ""
        or "/" in qtHelpFolder
        or qtHelpTitle == ""
    ):
        parser.error("Some required QtHelp arguments are missing.")

    basename = ""

    if outputDir:
        if not os.path.isdir(outputDir):
            try:
                os.makedirs(outputDir)
            except OSError:
                sys.stderr.write(
                    "Could not create output directory {0}.".format(outputDir)
                )
                sys.exit(3)
    else:
        outputDir = os.getcwd()
    outputDir = os.path.abspath(outputDir)

    if stylesheetFile:
        try:
            shutil.copy(stylesheetFile, os.path.join(outputDir, "styles.css"))
        except OSError:
            sys.stderr.write(
                "The CSS stylesheet '{0}' does not exist\n".format(stylesheetFile)
            )
            sys.exit(3)
    else:
        try:
            with open(os.path.join(outputDir, "styles.css"), "w") as sf:
                sf.write(TemplatesListsStyleCSS.cssTemplate.format(**colors))
        except OSError:
            sys.stderr.write(
                "The CSS stylesheet '{0}' could not be created\n".format(stylesheetFile)
            )
            sys.exit(3)

    indexGenerator = IndexGenerator(outputDir)

    if qtHelpCreation:
        if qtHelpOutputDir:
            if not os.path.isdir(qtHelpOutputDir):
                try:
                    os.makedirs(qtHelpOutputDir)
                except OSError:
                    sys.stderr.write(
                        "Could not create QtHelp output directory {0}.".format(
                            qtHelpOutputDir
                        )
                    )
                    sys.exit(3)
        else:
            qtHelpOutputDir = os.getcwd()
        qtHelpOutputDir = os.path.abspath(qtHelpOutputDir)

        qtHelpGenerator = QtHelpGenerator(
            outputDir,
            qtHelpOutputDir,
            qtHelpNamespace,
            qtHelpFolder,
            qtHelpFilterName,
            qtHelpFilterAttribs,
            qtHelpTitle,
            qtHelpCreateCollection,
        )

    if startDir:
        os.chdir(os.path.abspath(startDir))

    for argsfile in args.file:
        if os.path.isdir(argsfile):
            if os.path.exists(
                os.path.join(argsfile, FileSystemUtilities.joinext("__init__", ".py"))
            ):
                basename = os.path.dirname(argsfile)
                if argsfile == ".":
                    sys.stderr.write("The directory '.' is a package.\n")
                    sys.stderr.write("Please repeat the call giving its real name.\n")
                    sys.stderr.write("Ignoring the directory.\n")
                    continue
            else:
                basename = argsfile
            if basename:
                basename = "{0}{1}".format(basename, os.sep)

            if recursive and not os.path.islink(argsfile):
                names = [argsfile] + FileSystemUtilities.getDirs(argsfile, excludeDirs)
            else:
                names = [argsfile]
        else:
            basename = ""
            names = [argsfile]

        for filename in names:
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
                    print("Processing", file)
                    module = ModuleParser.readModule(
                        file,
                        basename=basename,
                        inpackage=inpackage,
                        extensions=supportedExtensions,
                    )
                    moduleDocument = ModuleDocument(module)
                    doc = moduleDocument.genDocument()
                except OSError as v:
                    sys.stderr.write("{0} error: {1}\n".format(file, v[1]))
                    continue
                except ImportError as v:
                    sys.stderr.write("{0} error: {1}\n".format(file, v))
                    continue
                except Exception as ex:
                    sys.stderr.write(
                        "{0} error while parsing: {1}\n".format(file, str(ex))
                    )
                    raise

                f = FileSystemUtilities.joinext(
                    os.path.join(outputDir, moduleDocument.name()), ".html"
                )

                # remember for index file generation
                indexGenerator.remember(file, moduleDocument, basename)

                # remember for QtHelp generation
                if qtHelpCreation:
                    qtHelpGenerator.remember(file, moduleDocument, basename)

                if (
                    noempty or file.endswith("__init__.py")
                ) and moduleDocument.isEmpty():
                    continue

                # generate output
                try:
                    with open(f, "w", encoding="utf-8", newline=newline) as out:
                        out.write(doc)
                except OSError as v:
                    sys.stderr.write("{0} error: {1}\n".format(file, v[1]))
                except Exception as ex:
                    sys.stderr.write(
                        "{0} error while writing: {1}\n".format(file, str(ex))
                    )
                    raise
                else:
                    sys.stdout.write("{0} ok\n".format(f))

                sys.stdout.flush()
                sys.stderr.flush()

    sys.stdout.write("code documentation generated")

    sys.stdout.flush()
    sys.stderr.flush()

    # write index files
    if doIndex:
        indexGenerator.writeIndices(basename, newline=newline)

    # generate the QtHelp files
    if qtHelpCreation:
        qtHelpGenerator.generateFiles(newline=newline)

    sys.exit(0)


if __name__ == "__main__":
    main()

#
# eflag: noqa = M801
