# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the interface to CycloneDX.
"""

import contextlib
import json
import os

from xml.etree import ElementTree  # secok

from cyclonedx.model import (
    ExternalReference,
    ExternalReferenceType,
    LicenseChoice,
    OrganizationalContact,
    OrganizationalEntity,
    Tool,
    XsUri,
)
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component
from cyclonedx.model.vulnerability import Vulnerability, VulnerabilitySource
from cyclonedx.output import (
    OutputFormat,
    SchemaVersion,
    get_instance as get_output_instance,
)
from cyclonedx.parser import BaseParser
from cyclonedx_py.parser.pipenv import PipEnvFileParser
from cyclonedx_py.parser.poetry import PoetryFileParser
from cyclonedx_py.parser.requirements import RequirementsFileParser
from packageurl import PackageURL
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.PipInterface.PipVulnerabilityChecker import Package, VulnerabilityCheckError


class CycloneDXEnvironmentParser(BaseParser):
    """
    Class implementing a parser to get package data for a named environment.
    """

    def __init__(self, venvName):
        """
        Constructor

        @param venvName name of the virtual environment
        @type str
        """
        super().__init__()

        pip = ericApp().getObject("Pip")
        packages = pip.getLicenses(venvName)
        for package in packages:
            comp = Component(
                name=package["Name"],
                version=package["Version"],
                author=package["Author"],
                description=package["Description"],
                purl=PackageURL(
                    type="pypi", name=package["Name"], version=package["Version"]
                ),
            )
            for lic in package["License"].split(";"):
                comp.licenses.add(LicenseChoice(license_expression=lic.strip()))

            self._components.append(comp)


def createCycloneDXFile(venvName, parent=None):
    """
    Function to create a CyccloneDX SBOM file.

    @param venvName name of the virtual environment
    @type str
    @param parent referent to a parent widget (defaults to None)
    @type QWidget (optional)
    @exception RuntimeError raised to indicate illegal creation parameters
    """
    from .CycloneDXConfigDialog import CycloneDXConfigDialog

    dlg = CycloneDXConfigDialog(venvName, parent=parent)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        (
            inputSource,
            inputFile,
            fileFormat,
            schemaVersion,
            sbomFile,
            withVulnerabilities,
            withDependencies,
            readableOutput,
            metadataDict,
        ) = dlg.getData()

        # check error conditions first
        if inputSource not in ("environment", "pipenv", "poetry", "requirements"):
            raise RuntimeError("Unsupported input source given.")
        if fileFormat not in ("XML", "JSON"):
            raise RuntimeError("Unsupported SBOM file format given.")

        if inputSource == "environment":
            parser = CycloneDXEnvironmentParser(venvName)
        else:
            # all other parsers need an input file
            if not os.path.isfile(inputFile):
                EricMessageBox.warning(
                    None,
                    QCoreApplication.translate(
                        "CycloneDX", "CycloneDX - SBOM Creation"
                    ),
                    QCoreApplication.translate(
                        "CycloneDX",
                        "<p>The configured input file <b>{0}</b> does not"
                        " exist. Aborting...</p>",
                    ).format(inputFile),
                )
                return

            if inputSource == "pipenv":
                parser = PipEnvFileParser(pipenv_lock_filename=inputFile)
            elif inputSource == "poetry":
                parser = PoetryFileParser(poetry_lock_filename=inputFile)
            elif inputSource == "requirements":
                parser = RequirementsFileParser(requirements_file=inputFile)

        if withVulnerabilities:
            addCycloneDXVulnerabilities(parser)

        if withDependencies:
            addCycloneDXDependencies(parser, venvName)

        if fileFormat == "XML":
            outputFormat = OutputFormat.XML
        elif fileFormat == "JSON":
            outputFormat = OutputFormat.JSON

        if parser.has_warnings():
            excludedList = [
                "<li>{0}</li>".format(warning.get_item())
                for warning in parser.get_warnings()
            ]
            EricMessageBox.warning(
                None,
                QCoreApplication.translate("CycloneDX", "CycloneDX - SBOM Creation"),
                QCoreApplication.translate(
                    "CycloneDX",
                    "<p>Some of the dependencies do not have pinned version"
                    " numbers.<ul>{0}</ul>The above listed packages will NOT"
                    " be included in the generated CycloneDX SBOM file as"
                    " version is a mandatory field.</p>",
                ).format("".join(excludedList)),
            )

        bom = Bom.from_parser(parser=parser)
        _amendMetaData(bom.metadata, metadataDict)
        output = get_output_instance(
            bom=bom,
            output_format=outputFormat,
            schema_version=SchemaVersion[
                "V{0}".format(schemaVersion.replace(".", "_"))
            ],
        )
        outputStr = output.output_as_string()
        if readableOutput:
            if fileFormat == "XML":
                outputStr = _prettifyXML(outputStr)
            elif fileFormat == "JSON":
                outputStr = _prettifyJSON(outputStr)

        try:
            with open(sbomFile, "w", encoding="utf-8") as f:
                f.write(outputStr)
            EricMessageBox.information(
                None,
                QCoreApplication.translate("CycloneDX", "CycloneDX - SBOM Creation"),
                QCoreApplication.translate(
                    "CycloneDX", "<p>The SBOM data was written to file <b>{0}</b>.</p>"
                ).format(sbomFile),
            )
        except OSError as err:
            EricMessageBox.critical(
                None,
                QCoreApplication.translate("CycloneDX", "CycloneDX - SBOM Creation"),
                QCoreApplication.translate(
                    "CycloneDX",
                    "<p>The SBOM file <b>{0}</b> could not be written.</p>"
                    "<p>Reason: {1}</p>",
                ).format(sbomFile, str(err)),
            )


def _prettifyXML(inputStr):
    """
    Function to prettify the SBOM XML output generated by CycloneDX.

    Note: Prettifying an XML tree works only with Python 3.9 and above!

    @param inputStr output generated by CycloneDX
    @type str
    @return prettified SBOM string
    @rtype str
    """
    tree = ElementTree.fromstring(inputStr)  # secok
    with contextlib.suppress(AttributeError):
        ElementTree.indent(tree)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ElementTree.tostring(
            tree, encoding="unicode"
        )

    return inputStr


def _prettifyJSON(inputStr):
    """
    Function to prettify the SBOM JSON output generated by CycloneDX.

    @param inputStr output generated by CycloneDX
    @type str
    @return prettified SBOM string
    @rtype str
    """
    sbom = json.loads(inputStr)
    return json.dumps(sbom, indent="  ")


def addCycloneDXVulnerabilities(parser):
    """
    Function to add vulnerability data to the list of created components.

    @param parser reference to the parser object containing the list of
        components
    @type BaseParser
    """
    components = parser.get_components()

    packages = [
        Package(name=component.name, version=component.version)
        for component in components
    ]

    pip = ericApp().getObject("Pip")
    error, vulnerabilities = pip.getVulnerabilityChecker().check(packages)

    if error == VulnerabilityCheckError.OK:
        for package in vulnerabilities:
            component = findCyccloneDXComponent(components, package)
            if component:
                for vuln in vulnerabilities[package]:
                    component.add_vulnerability(
                        Vulnerability(
                            id=vuln.cve,
                            description=vuln.advisory,
                            recommendation="upgrade required",
                            source=VulnerabilitySource(name="pyup.io"),
                        )
                    )


def addCycloneDXDependencies(parser, venvName):
    """
    Function to add dependency data to the list of created components.

    @param parser reference to the parser object containing the list of
        components
    @type BaseParser
    @param venvName name of the virtual environment
    @type str
    """
    components = parser.get_components()

    pip = ericApp().getObject("Pip")
    dependencies = pip.getDependencyTree(venvName)
    for dependency in dependencies:
        _addCycloneDXDependency(dependency, components)


def _addCycloneDXDependency(dependency, components):
    """
    Function to add a dependency to the given list of components.

    @param dependency dependency to be added
    @type dict
    @param components list of components
    @type list of Component
    """
    component = findCyccloneDXComponent(components, dependency["package_name"])
    if component is not None:
        bomRefs = component.dependencies
        for dep in dependency["dependencies"]:
            depComponent = findCyccloneDXComponent(components, dep["package_name"])
            if depComponent is not None:
                bomRefs.add(depComponent.bom_ref)
                # recursively add sub-dependencies
                _addCycloneDXDependency(dep, components)
        component.dependencies = bomRefs


def findCyccloneDXComponent(components, name):
    """
    Function to find a component in a given list of components.

    @param components list of components to scan
    @type list of Component
    @param name name of the component to search for
    @type str
    @return reference to the found component or None
    @rtype Component or None
    """
    for component in components:
        if component.name == name:
            return component

    return None


def _amendMetaData(bomMetaData, metadataDict):
    """
    Function to amend the SBOM meta data according the given data.

    The modifications done are:
    <ul>
    <li>add eric7 to the tools</li>
    </ul>

    @param bomMetaData reference to the SBOM meta data object
    @type BomMetaData
    @param metadataDict dictionary containing additional meta data
    @type dict
    @return reference to the modified SBOM meta data object
    @rtype BomMetaData
    """
    # add a Tool entry for eric7
    try:
        from importlib.metadata import version as meta_version  # __IGNORE_WARNING_I10__

        __EricToolVersion = str(meta_version("eric-ide"))
    except Exception:
        from eric7.__version__ import Version  # __IGNORE_WARNING_I101__

        __EricToolVersion = Version

    EricTool = Tool(
        vendor="python-projects.org", name="eric-ide", version=__EricToolVersion
    )
    EricTool.external_references.update(
        [
            ExternalReference(
                reference_type=ExternalReferenceType.DISTRIBUTION,
                url=XsUri("https://pypi.org/project/eric-ide/"),
            ),
            ExternalReference(
                reference_type=ExternalReferenceType.DOCUMENTATION,
                url=XsUri("https://pypi.org/project/eric-ide/"),
            ),
            ExternalReference(
                reference_type=ExternalReferenceType.ISSUE_TRACKER,
                url=XsUri("https://tracker.die-offenbachs.homelinux.org"),
            ),
            ExternalReference(
                reference_type=ExternalReferenceType.LICENSE,
                url=XsUri(
                    "https://hg.die-offenbachs.homelinux.org/eric/file/tip/docs/"
                    "LICENSE.txt"
                ),
            ),
            ExternalReference(
                reference_type=ExternalReferenceType.RELEASE_NOTES,
                url=XsUri(
                    "https://hg.die-offenbachs.homelinux.org/eric/file/tip/docs/"
                    "changelog"
                ),
            ),
            ExternalReference(
                reference_type=ExternalReferenceType.VCS,
                url=XsUri("https://hg.die-offenbachs.homelinux.org/eric"),
            ),
            ExternalReference(
                reference_type=ExternalReferenceType.WEBSITE,
                url=XsUri("https://eric-ide.python-projects.org"),
            ),
        ]
    )
    bomMetaData.tools.add(EricTool)

    # add the meta data info entered by the user (if any)
    if metadataDict is not None:
        if metadataDict["AuthorName"]:
            bomMetaData.authors = [
                OrganizationalContact(
                    name=metadataDict["AuthorName"], email=metadataDict["AuthorEmail"]
                )
            ]
        if metadataDict["Manufacturer"]:
            bomMetaData.manufacture = OrganizationalEntity(
                name=metadataDict["Manufacturer"]
            )
        if metadataDict["Supplier"]:
            bomMetaData.supplier = OrganizationalEntity(name=metadataDict["Supplier"])
        if metadataDict["License"]:
            bomMetaData.licenses = [
                LicenseChoice(license_expression=metadataDict["License"])
            ]
        if metadataDict["Name"]:
            bomMetaData.component = Component(
                name=metadataDict["Name"],
                component_type=metadataDict["Type"],
                version=metadataDict["Version"],
                description=metadataDict["Description"],
                author=metadataDict["AuthorName"],
                licenses=[LicenseChoice(license_expression=metadataDict["License"])],
            )

    return bomMetaData
