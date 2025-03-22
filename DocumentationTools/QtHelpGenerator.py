# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the QtHelp generator for the builtin documentation
generator.
"""

import os
import shutil
import subprocess  # secok
import sys

from eric7 import Preferences
from eric7.EricUtilities import html_encode
from eric7.SystemUtilities import FileSystemUtilities, QtUtilities

HelpCollection = r"""<?xml version="1.0" encoding="utf-8" ?>
<QHelpCollectionProject version="1.0">
  <docFiles>
    <register>
      <file>{helpfile}</file>
    </register>
  </docFiles>
</QHelpCollectionProject>
"""

HelpProject = r"""<?xml version="1.0" encoding="UTF-8"?>
<QtHelpProject version="1.0">
  <namespace>{namespace}</namespace>
  <virtualFolder>{folder}</virtualFolder>
  <customFilter name="{filter_name}">
{filter_attributes}
  </customFilter>
  <filterSection>
{filter_attributes}
    <toc>
{sections}
    </toc>
    <keywords>
{keywords}
    </keywords>
    <files>
{files}
    </files>
  </filterSection>
</QtHelpProject>
"""

HelpProjectFile = "source.qhp"
HelpHelpFile = "source.qch"
HelpCollectionProjectFile = "source.qhcp"
HelpCollectionFile = "collection.qhc"


class QtHelpGenerator:
    """
    Class implementing the QtHelp generator for the builtin documentation
    generator.
    """

    def __init__(
        self,
        htmlDir,
        outputDir,
        namespace,
        virtualFolder,
        filterName,
        filterAttributes,
        title,
        createCollection,
    ):
        """
        Constructor

        @param htmlDir directory containing the HTML files
        @type str
        @param outputDir output directory for the files
        @type str
        @param namespace namespace to be used
        @type str
        @param virtualFolder virtual folder to be used
        @type str
        @param filterName name of the custom filter
        @type str
        @param filterAttributes ':' separated list of filter attributes
        @type str
        @param title title to be used for the generated help
        @type str
        @param createCollection flag indicating the generation of the
            collection files
        @type bool
        """
        self.htmlDir = htmlDir
        self.outputDir = outputDir
        self.namespace = namespace
        self.virtualFolder = virtualFolder
        self.filterName = filterName
        self.filterAttributes = filterAttributes and filterAttributes.split(":") or []
        self.relPath = os.path.relpath(self.htmlDir, self.outputDir)
        self.title = title
        self.createCollection = createCollection

        self.packages = {"00index": {"subpackages": {}, "modules": {}}}
        self.remembered = False
        self.keywords = []

    def remember(self, file, moduleDocument, basename=""):
        """
        Public method to remember a documentation file.

        @param file The filename to be remembered.
        @type str
        @param moduleDocument module documentation object containing the
            information for the file.
        @type ModuleDocument
        @param basename base name of the file hierarchy to be documented.
            The base name is stripped off the filename if it starts with
            the base name.
        @type str
        """
        self.remembered = True
        if basename:
            file = file.replace(basename, "")

        if "__init__" in file:
            dirName = os.path.dirname(file)
            udir = os.path.dirname(dirName)
            if udir:
                upackage = udir.replace(os.sep, ".")
                try:
                    elt = self.packages[upackage]
                except KeyError:
                    elt = self.packages["00index"]
            else:
                elt = self.packages["00index"]
            package = dirName.replace(os.sep, ".")
            elt["subpackages"][package] = moduleDocument.name()

            self.packages[package] = {"subpackages": {}, "modules": {}}

            kwEntry = (
                "{0} (Package)".format(package.split(".")[-1]),
                FileSystemUtilities.joinext("index-{0}".format(package), ".html"),
            )
            if kwEntry not in self.keywords:
                self.keywords.append(kwEntry)

            if moduleDocument.isEmpty():
                return

        package = os.path.dirname(file).replace(os.sep, ".")
        try:
            elt = self.packages[package]
        except KeyError:
            elt = self.packages["00index"]
        elt["modules"][moduleDocument.name()] = moduleDocument.name()

        if "__init__" not in file:
            kwEntry = (
                "{0} (Module)".format(moduleDocument.name().split(".")[-1]),
                FileSystemUtilities.joinext(moduleDocument.name(), ".html"),
            )
            if kwEntry not in self.keywords:
                self.keywords.append(kwEntry)
        for kw in moduleDocument.getQtHelpKeywords():
            kwEntry = (
                kw[0],
                "{0}{1}".format(
                    FileSystemUtilities.joinext(moduleDocument.name(), ".html"), kw[1]
                ),
            )
            if kwEntry not in self.keywords:
                self.keywords.append(kwEntry)

    def __generateSections(self, package, level):
        """
        Private method to generate the sections part.

        @param package name of the package to process
        @type str
        @param level indentation level
        @type int
        @return sections part
        @rtype str
        """
        indent = level * "  "
        indent1 = indent + "  "
        s = indent + '<section title="{0}" ref="{1}">\n'.format(
            package == "00index" and self.title or package,
            package == "00index"
            and FileSystemUtilities.joinext("index", ".html")
            or FileSystemUtilities.joinext("index-{0}".format(package), ".html"),
        )
        for subpack in sorted(self.packages[package]["subpackages"]):
            s += self.__generateSections(subpack, level + 1) + "\n"
        for mod in sorted(self.packages[package]["modules"]):
            s += indent1 + '<section title="{0}" ref="{1}" />\n'.format(
                mod, FileSystemUtilities.joinext(mod, ".html")
            )
        s += indent + "</section>"
        return s

    def __convertEol(self, txt, newline):
        """
        Private method to convert the newline characters.

        @param txt text to be converted
        @type str
        @param newline newline character to be used
        @type str
        @return converted text
        @rtype str
        """
        # step 1: normalize eol to '\n'
        txt = txt.replace("\r\n", "\n").replace("\r", "\n")

        # step 2: convert to the target eol
        if newline is None:
            return txt.replace("\n", os.linesep)
        elif newline in ["\r", "\r\n"]:
            return txt.replace("\n", newline)
        else:
            return txt

    def generateFiles(self, basename="", newline=None):
        """
        Public method to generate all index files.

        @param basename base name of the file hierarchy to be documented.
            The base name is stripped off the filename if it starts with
            the base name.
        @type str
        @param newline newline character to be used
        @type str
        """
        if not self.remembered:
            sys.stderr.write("No QtHelp to generate.\n")
            return

        if basename:
            basename = basename.replace(os.sep, ".")
            if not basename.endswith("."):
                basename = "{0}.".format(basename)

        sections = self.__generateSections("00index", level=3)
        filesList = sorted(e for e in os.listdir(self.htmlDir) if e.endswith(".html"))
        filesList.append("styles.css")
        files = "\n".join(["      <file>{0}</file>".format(f) for f in filesList])
        filterAttribs = "\n".join(
            [
                "    <filterAttribute>{0}</filterAttribute>".format(a)
                for a in sorted(self.filterAttributes)
            ]
        )
        keywords = "\n".join(
            [
                '      <keyword name="{0}" id="{1}" ref="{2}" />'.format(
                    html_encode(kw[0]), html_encode(kw[0]), html_encode(kw[1])
                )
                for kw in sorted(self.keywords)
            ]
        )

        helpAttribs = {
            "namespace": self.namespace,
            "folder": self.virtualFolder,
            "filter_name": self.filterName,
            "filter_attributes": filterAttribs,
            "sections": sections,
            "keywords": keywords,
            "files": files,
        }

        txt = self.__convertEol(HelpProject.format(**helpAttribs), newline)
        with open(
            os.path.join(self.outputDir, HelpProjectFile),
            "w",
            encoding="utf-8",
            newline=newline,
        ) as f:
            f.write(txt)

        if self.createCollection and not os.path.exists(
            os.path.join(self.outputDir, HelpCollectionProjectFile)
        ):
            collectionAttribs = {
                "helpfile": HelpHelpFile,
            }

            txt = self.__convertEol(HelpCollection.format(**collectionAttribs), newline)
            with open(
                os.path.join(self.outputDir, HelpCollectionProjectFile),
                "w",
                encoding="utf-8",
                newline=newline,
            ) as f:
                f.write(txt)

        sys.stdout.write("QtHelp files written.\n")
        sys.stdout.write("Generating QtHelp documentation...\n")
        sys.stdout.flush()
        sys.stderr.flush()

        cwd = os.getcwd()
        # generate the compressed files
        qhelpgeneratorExe = Preferences.getQt("QHelpGenerator")
        if not qhelpgeneratorExe:
            qhelpgeneratorExe = os.path.join(
                QtUtilities.getQtBinariesPath(libexec=True),
                QtUtilities.generateQtToolName("qhelpgenerator"),
            )
            if not os.path.exists(qhelpgeneratorExe):
                qhelpgeneratorExe = os.path.join(
                    QtUtilities.getQtBinariesPath(libexec=False),
                    QtUtilities.generateQtToolName("qhelpgenerator"),
                )
        shutil.copy(os.path.join(self.outputDir, HelpProjectFile), self.htmlDir)
        os.chdir(self.htmlDir)
        subprocess.run(  # secok
            [
                qhelpgeneratorExe,
                HelpProjectFile,
                "-o",
                os.path.join(self.outputDir, HelpHelpFile),
            ]
        )
        os.remove(HelpProjectFile)

        if self.createCollection:
            sys.stdout.write("Generating QtHelp collection...\n")
            sys.stdout.flush()
            sys.stderr.flush()
            os.chdir(self.outputDir)
            subprocess.run(  # secok
                [
                    qhelpgeneratorExe,
                    HelpCollectionProjectFile,
                    "-o",
                    HelpCollectionFile,
                ]
            )

        os.chdir(cwd)
