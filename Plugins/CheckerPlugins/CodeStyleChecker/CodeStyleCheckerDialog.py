# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the results of the code style check.
"""

import collections
import copy
import fnmatch
import json
import os
import time

from PyQt6.QtCore import QCoreApplication, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QLineEdit,
    QListWidgetItem,
    QTreeWidgetItem,
)

from eric7 import EricUtilities, Preferences, Utilities
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.QScintilla.Editor import EditorWarningKind
from eric7.SystemUtilities import FileSystemUtilities

from . import CodeStyleCheckerUtilities, pycodestyle
from .Annotations.AnnotationsCheckerDefaults import AnnotationsCheckerDefaultArgs
from .Miscellaneous.MiscellaneousDefaults import MiscellaneousCheckerDefaultArgs
from .Security.SecurityDefaults import SecurityDefaults
from .Ui_CodeStyleCheckerDialog import Ui_CodeStyleCheckerDialog


class CodeStyleCheckerDialog(QDialog, Ui_CodeStyleCheckerDialog):
    """
    Class implementing a dialog to show the results of the code style check.
    """

    filenameRole = Qt.ItemDataRole.UserRole + 1
    lineRole = Qt.ItemDataRole.UserRole + 2
    positionRole = Qt.ItemDataRole.UserRole + 3
    messageRole = Qt.ItemDataRole.UserRole + 4
    fixableRole = Qt.ItemDataRole.UserRole + 5
    codeRole = Qt.ItemDataRole.UserRole + 6
    ignoredRole = Qt.ItemDataRole.UserRole + 7
    argsRole = Qt.ItemDataRole.UserRole + 8

    availableFutures = [
        "division",
        "absolute_import",
        "with_statement",
        "print_function",
        "unicode_literals",
        "generator_stop",
        "annotations",
    ]

    cryptoBitSelectionsDsaRsa = [
        "512",
        "1024",
        "2048",
        "4096",
        "8192",
        "16384",
        "32786",
    ]
    cryptoBitSelectionsEc = [
        "160",
        "224",
        "256",
        "384",
        "512",
    ]

    checkCategories = {
        "A": QCoreApplication.translate("CheckerCategories", "Annotations"),
        "ASY": QCoreApplication.translate("CheckerCategories", "Async Functions"),
        "C": QCoreApplication.translate("CheckerCategories", "Code Complexity"),
        "D": QCoreApplication.translate("CheckerCategories", "Documentation"),
        "E": QCoreApplication.translate("CheckerCategories", "Errors"),
        "I": QCoreApplication.translate("CheckerCategories", "Imports"),
        "L": QCoreApplication.translate("CheckerCategories", "Logging"),
        "M": QCoreApplication.translate("CheckerCategories", "Miscellaneous"),
        "N": QCoreApplication.translate("CheckerCategories", "Naming"),
        "NO": QCoreApplication.translate("CheckerCategories", "Name Order"),
        "P": QCoreApplication.translate("CheckerCategories", "'pathlib' Usage"),
        "S": QCoreApplication.translate("CheckerCategories", "Security"),
        "U": QCoreApplication.translate("CheckerCategories", "Unused"),
        "W": QCoreApplication.translate("CheckerCategories", "Warnings"),
        "Y": QCoreApplication.translate("CheckerCategories", "Simplify Code"),
    }

    noResults = 0
    noFiles = 1
    hasResults = 2

    def __init__(self, styleCheckService, project=None, parent=None):
        """
        Constructor

        @param styleCheckService reference to the service
        @type CodeStyleCheckService
        @param project reference to the project if called on project or project
            browser level
        @type Project
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__project = project

        self.optionsTabWidget.setCurrentIndex(0)

        self.excludeMessagesSelectButton.setIcon(EricPixmapCache.getIcon("select"))
        self.includeMessagesSelectButton.setIcon(EricPixmapCache.getIcon("select"))
        self.fixIssuesSelectButton.setIcon(EricPixmapCache.getIcon("select"))
        self.noFixIssuesSelectButton.setIcon(EricPixmapCache.getIcon("select"))

        self.docTypeComboBox.addItem(self.tr("PEP-257"), "pep257")
        self.docTypeComboBox.addItem(self.tr("Eric"), "eric")
        self.docTypeComboBox.addItem(self.tr("Eric (Blacked)"), "eric_black")

        for category, text in CodeStyleCheckerDialog.checkCategories.items():
            itm = QListWidgetItem(text, self.categoriesList)
            itm.setData(Qt.ItemDataRole.UserRole, category)
            itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            itm.setCheckState(Qt.CheckState.Unchecked)

        for future in CodeStyleCheckerDialog.availableFutures:
            itm = QListWidgetItem(future, self.futuresList)
            itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            itm.setCheckState(Qt.CheckState.Unchecked)

        self.dsaHighRiskCombo.addItems(CodeStyleCheckerDialog.cryptoBitSelectionsDsaRsa)
        self.dsaMediumRiskCombo.addItems(
            CodeStyleCheckerDialog.cryptoBitSelectionsDsaRsa
        )
        self.rsaHighRiskCombo.addItems(CodeStyleCheckerDialog.cryptoBitSelectionsDsaRsa)
        self.rsaMediumRiskCombo.addItems(
            CodeStyleCheckerDialog.cryptoBitSelectionsDsaRsa
        )
        self.ecHighRiskCombo.addItems(CodeStyleCheckerDialog.cryptoBitSelectionsEc)
        self.ecMediumRiskCombo.addItems(CodeStyleCheckerDialog.cryptoBitSelectionsEc)

        self.sortOrderComboBox.addItem("Natural", "natural")
        self.sortOrderComboBox.addItem("Native Python", "native")

        self.statisticsButton.setEnabled(False)
        self.showButton.setEnabled(False)
        self.cancelButton.setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)

        self.resultList.headerItem().setText(self.resultList.columnCount(), "")
        self.resultList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.addBuiltinButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.deleteBuiltinButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.addWhitelistButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.deleteWhitelistButton.setIcon(EricPixmapCache.getIcon("minus"))

        self.restartButton.setEnabled(False)
        self.fixButton.setEnabled(False)

        self.checkProgress.setVisible(False)

        self.styleCheckService = styleCheckService
        self.styleCheckService.styleChecked.connect(self.__processResult)
        self.styleCheckService.batchFinished.connect(self.__batchFinished)
        self.styleCheckService.error.connect(self.__processError)
        self.filename = None

        self.results = CodeStyleCheckerDialog.noResults
        self.cancelled = False
        self.__lastFileItem = None
        self.__batch = False
        self.__finished = True
        self.__errorItem = None
        self.__timenow = time.monotonic()

        self.__fileOrFileList = ""
        self.__forProject = False
        self.__data = {}
        self.__statistics = collections.defaultdict(self.__defaultStatistics)
        self.__onlyFixes = {}
        self.__noFixCodesList = []
        self.__detectedCodes = []

        self.on_loadDefaultButton_clicked()

        self.mainWidget.setCurrentWidget(self.configureTab)
        self.optionsTabWidget.setCurrentWidget(self.globalOptionsTab)

        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

    def __defaultStatistics(self):
        """
        Private method to return the default statistics entry.

        @return dictionary with default statistics entry
        @rtype dict
        """
        return {
            "total": 0,
            "ignored": 0,
        }

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.resultList.sortItems(
            self.resultList.sortColumn(), self.resultList.header().sortIndicatorOrder()
        )

    def __createErrorItem(self, filename, message):
        """
        Private slot to create a new error item in the result list.

        @param filename name of the file
        @type str
        @param message error message
        @type str
        """
        if self.__errorItem is None:
            self.__errorItem = QTreeWidgetItem(self.resultList, [self.tr("Errors")])
            self.__errorItem.setExpanded(True)
            self.__errorItem.setForeground(0, Qt.GlobalColor.red)

        msg = "{0} ({1})".format(self.__project.getRelativePath(filename), message)
        if not self.resultList.findItems(msg, Qt.MatchFlag.MatchExactly):
            itm = QTreeWidgetItem(self.__errorItem, [msg])
            itm.setForeground(0, Qt.GlobalColor.red)
            itm.setFirstColumnSpanned(True)

    def __createFileErrorItem(self, filename, message):
        """
        Private method to create an error entry for a given file.

        @param filename file name of the file
        @type str
        @param message error message text
        @type str
        """
        result = {
            "file": filename,
            "line": 1,
            "offset": 1,
            "code": "",
            "args": [],
            "display": self.tr("Error: {0}").format(message).rstrip(),
            "fixed": False,
            "autofixing": False,
            "ignored": False,
        }
        self.__createResultItem(filename, result)

    def __createResultItem(self, filename, result):
        """
        Private method to create an entry in the result list.

        @param filename file name of the file
        @type str
        @param result dictionary containing check result data
        @type dict
        @return reference to the created item
        @rtype QTreeWidgetItem
        """
        from .CodeStyleFixer import FixableCodeStyleIssues

        if self.__lastFileItem is None:
            # It's a new file
            self.__lastFileItem = QTreeWidgetItem(
                self.resultList, [self.__project.getRelativePath(filename)]
            )
            self.__lastFileItem.setFirstColumnSpanned(True)
            self.__lastFileItem.setExpanded(True)
            self.__lastFileItem.setData(0, self.filenameRole, filename)

        msgCode = result["code"].split(".", 1)[0]
        self.__detectedCodes.append(msgCode)

        fixable = False
        itm = QTreeWidgetItem(
            self.__lastFileItem,
            ["{0:6}".format(result["line"]), msgCode, result["display"]],
        )

        CodeStyleCheckerUtilities.setItemIcon(itm, 1, msgCode, result.get("severity"))

        if result["fixed"]:
            itm.setIcon(0, EricPixmapCache.getIcon("issueFixed"))
        elif (
            msgCode in FixableCodeStyleIssues
            and not result["autofixing"]
            and msgCode not in self.__noFixCodesList
        ):
            itm.setIcon(0, EricPixmapCache.getIcon("issueFixable"))
            fixable = True

        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter)

        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignVCenter)
        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignVCenter)
        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignVCenter)

        itm.setData(0, self.filenameRole, filename)
        itm.setData(0, self.lineRole, int(result["line"]))
        itm.setData(0, self.positionRole, int(result["offset"]))
        itm.setData(0, self.messageRole, result["display"])
        itm.setData(0, self.fixableRole, fixable)
        itm.setData(0, self.codeRole, msgCode)
        itm.setData(0, self.ignoredRole, result["ignored"])
        itm.setData(0, self.argsRole, result["args"])

        if result["ignored"]:
            font = itm.font(0)
            font.setItalic(True)
            for col in range(itm.columnCount()):
                itm.setFont(col, font)

        return itm

    def __modifyFixedResultItem(self, itm, result):
        """
        Private method to modify a result list entry to show its
        positive fixed state.

        @param itm reference to the item to modify
        @type QTreeWidgetItem
        @param result dictionary containing check result data
        @type dict
        """
        if result["fixed"]:
            itm.setText(2, result["display"])
            itm.setIcon(0, EricPixmapCache.getIcon("issueFixed"))

            itm.setData(0, self.messageRole, result["display"])
        else:
            itm.setIcon(0, QIcon())
        itm.setData(0, self.fixableRole, False)

    def __updateStatistics(self, statistics, fixer, ignoredErrors, securityOk):
        """
        Private method to update the collected statistics.

        @param statistics dictionary of statistical data with
            message code as key and message count as value
        @type dict
        @param fixer reference to the code style fixer
        @type CodeStyleFixer
        @param ignoredErrors number of ignored errors
        @type int
        @param securityOk number of acknowledged security reports
        @type int
        """
        self.__statistics["_FilesCount"] += 1
        stats = [k for k in statistics if k[0].isupper()]
        if stats:
            self.__statistics["_FilesIssues"] += 1
            for key in stats:
                self.__statistics[key]["total"] += statistics[key]
            for key in ignoredErrors:
                self.__statistics[key]["ignored"] += ignoredErrors[key]
        self.__statistics["_IssuesFixed"] += fixer
        self.__statistics["_SecurityOK"] += securityOk

    def __updateFixerStatistics(self, fixer):
        """
        Private method to update the collected fixer related statistics.

        @param fixer reference to the code style fixer
        @type CodeStyleFixer
        """
        self.__statistics["_IssuesFixed"] += fixer

    def __resetStatistics(self):
        """
        Private slot to reset the statistics data.
        """
        self.__statistics.clear()
        self.__statistics["_FilesCount"] = 0
        self.__statistics["_FilesIssues"] = 0
        self.__statistics["_IssuesFixed"] = 0
        self.__statistics["_SecurityOK"] = 0

    def __getBanRelativeImportsValue(self):
        """
        Private method to get the value corresponding the selected button.

        @return value for the BanRelativeImports argument
        @rtype str
        """
        if self.banParentsButton.isChecked():
            return "parents"
        elif self.banAllButton.isChecked():
            return "true"
        else:
            return ""

    def __setBanRelativeImports(self, value):
        """
        Private method to set the button according to the ban relative imports
        setting.

        @param value value of the ban relative imports setting
        @type str
        """
        if value == "parents":
            self.banParentsButton.setChecked(True)
        elif value == "true":
            self.banAllButton.setChecked(True)
        else:
            self.allowAllButton.setChecked(True)

    def getDefaults(self):
        """
        Public method to get a dictionary containing the default values.

        @return dictionary containing the default values
        @rtype dict
        """
        defaults = {
            # General
            "ExcludeFiles": "",
            "ExcludeMessages": pycodestyle.DEFAULT_IGNORE,
            "IncludeMessages": "",
            "RepeatMessages": False,
            "FixCodes": "",
            "FixIssues": False,
            "EnabledCheckerCategories": ",".join(
                CodeStyleCheckerDialog.checkCategories
            ),
            "MaxLineLength": 88,
            # better code formatting than pycodestyle.MAX_LINE_LENGTH
            # see the Black tool
            "MaxDocLineLength": 88,
            "BlankLines": (2, 1),  # top level, method
            "HangClosing": False,
            "NoFixCodes": "E501",
            "DocstringType": "pep257",
            "ShowIgnored": False,
            # Complexity
            "MaxCodeComplexity": 10,
            "LineComplexity": 15,
            "LineComplexityScore": 10,
            # Miscellaneous
            "ValidEncodings": MiscellaneousCheckerDefaultArgs["CodingChecker"],
            "CopyrightMinFileSize": MiscellaneousCheckerDefaultArgs["CopyrightChecker"][
                "MinFilesize"
            ],
            "CopyrightAuthor": MiscellaneousCheckerDefaultArgs["CopyrightChecker"][
                "Author"
            ],
            "FutureChecker": "",
            "BuiltinsChecker": copy.deepcopy(
                MiscellaneousCheckerDefaultArgs["BuiltinsChecker"]
            ),
            "CommentedCodeChecker": copy.deepcopy(
                MiscellaneousCheckerDefaultArgs["CommentedCodeChecker"]
            ),
            # Annotations
            "AnnotationsChecker": copy.deepcopy(AnnotationsCheckerDefaultArgs),
            # Security
            "SecurityChecker": {
                "HardcodedTmpDirectories": SecurityDefaults[
                    "hardcoded_tmp_directories"
                ],
                "InsecureHashes": SecurityDefaults["insecure_hashes"],
                "InsecureSslProtocolVersions": SecurityDefaults[
                    "insecure_ssl_protocol_versions"
                ],
                "WeakKeySizeDsaHigh": str(SecurityDefaults["weak_key_size_dsa_high"]),
                "WeakKeySizeDsaMedium": str(
                    SecurityDefaults["weak_key_size_dsa_medium"]
                ),
                "WeakKeySizeRsaHigh": str(SecurityDefaults["weak_key_size_rsa_high"]),
                "WeakKeySizeRsaMedium": str(
                    SecurityDefaults["weak_key_size_rsa_medium"]
                ),
                "WeakKeySizeEcHigh": str(SecurityDefaults["weak_key_size_ec_high"]),
                "WeakKeySizeEcMedium": str(SecurityDefaults["weak_key_size_ec_medium"]),
                "CheckTypedException": SecurityDefaults["check_typed_exception"],
            },
            # Imports
            "ImportsChecker": {
                "ApplicationPackageNames": [],
                "BannedModules": [],
                "BanRelativeImports": "",
            },
            # Name Order
            "NameOrderChecker": {
                "ApplicationPackageNames": [],
                "SortOrder": "natural",
                "SortCaseSensitive": False,
                "CombinedAsImports": False,
                "SortIgnoringStyle": False,
                "SortFromFirst": False,
            },
            # Unused
            "UnusedChecker": {
                "IgnoreAbstract": True,
                "IgnoreOverload": True,
                "IgnoreOverride": True,
                "IgnoreSlotMethods": False,
                "IgnoreEventHandlerMethods": False,
                "IgnoreStubs": True,
                "IgnoreVariadicNames": False,
                "IgnoreLambdas": False,
                "IgnoreNestedFunctions": False,
                "IgnoreDunderMethods": True,
                "IgnoreDunderGlobals": True,
            },
        }

        return defaults

    def prepare(self, fileList, project):
        """
        Public method to prepare the dialog with a list of filenames.

        @param fileList list of filenames
        @type list of str
        @param project reference to the project object
        @type Project
        """
        self.__fileOrFileList = fileList[:]
        self.__project = project
        self.__forProject = True

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.cancelButton.setEnabled(False)

        defaultParameters = self.getDefaults()
        self.__data = self.__project.getData("CHECKERSPARMS", "Pep8Checker")
        if self.__data is None or len(self.__data) < 6:
            # initialize the data structure
            self.__data = defaultParameters
        else:
            for key in defaultParameters:
                if key not in self.__data:
                    self.__data[key] = defaultParameters[key]

            if "WhiteList" not in self.__data["CommentedCodeChecker"]:
                self.__data["CommentedCodeChecker"]["WhiteList"] = defaultParameters[
                    "CommentedCodeChecker"
                ]["WhiteList"][:]

            # Upgrading AnnotationsChecker from older data structures
            if "MaximumLength" not in self.__data["AnnotationsChecker"]:
                # MaximumLength is the sentinel for the first extension
                self.__data["AnnotationsChecker"].update(
                    {
                        "MaximumLength": defaultParameters["AnnotationsChecker"][
                            "MaximumLength"
                        ],
                        "SuppressNoneReturning": defaultParameters[
                            "AnnotationsChecker"
                        ]["SuppressNoneReturning"],
                        "SuppressDummyArgs": defaultParameters["AnnotationsChecker"][
                            "SuppressDummyArgs"
                        ],
                        "AllowUntypedDefs": defaultParameters["AnnotationsChecker"][
                            "AllowUntypedDefs"
                        ],
                        "AllowUntypedNested": defaultParameters["AnnotationsChecker"][
                            "AllowUntypedNested"
                        ],
                        "MypyInitReturn": defaultParameters["AnnotationsChecker"][
                            "MypyInitReturn"
                        ],
                        "DispatchDecorators": defaultParameters["AnnotationsChecker"][
                            "DispatchDecorators"
                        ],
                        "OverloadDecorators": defaultParameters["AnnotationsChecker"][
                            "OverloadDecorators"
                        ],
                    }
                )
            if "AllowStarArgAny" not in self.__data["AnnotationsChecker"]:
                # AllowStarArgAny is the sentinel for the second extension
                self.__data["AnnotationsChecker"].update(
                    {
                        "AllowStarArgAny": defaultParameters["AnnotationsChecker"][
                            "AllowStarArgAny"
                        ],
                        "ForceFutureAnnotations": defaultParameters[
                            "AnnotationsChecker"
                        ]["ForceFutureAnnotations"],
                    }
                )
            if "CheckFutureAnnotations" not in self.__data["AnnotationsChecker"]:
                # third extension
                self.__data["AnnotationsChecker"]["CheckFutureAnnotations"] = (
                    defaultParameters["AnnotationsChecker"]["CheckFutureAnnotations"]
                )
            if "ExemptedTypingSymbols" not in self.__data["AnnotationsChecker"]:
                # fourth extension
                self.__data["AnnotationsChecker"]["ExemptedTypingSymbols"] = (
                    defaultParameters["AnnotationsChecker"]["ExemptedTypingSymbols"]
                )
            if "RespectTypeIgnore" not in self.__data["AnnotationsChecker"]:
                # fifth extension
                self.__data["AnnotationsChecker"]["RespectTypeIgnore"] = (
                    defaultParameters["AnnotationsChecker"]["RespectTypeIgnore"]
                )

        self.__initCategoriesList(self.__data["EnabledCheckerCategories"])
        self.excludeFilesEdit.setText(self.__data["ExcludeFiles"])
        self.excludeMessagesEdit.setText(self.__data["ExcludeMessages"])
        self.includeMessagesEdit.setText(self.__data["IncludeMessages"])
        self.repeatCheckBox.setChecked(self.__data["RepeatMessages"])
        self.fixIssuesEdit.setText(self.__data["FixCodes"])
        self.noFixIssuesEdit.setText(self.__data["NoFixCodes"])
        self.fixIssuesCheckBox.setChecked(self.__data["FixIssues"])
        self.ignoredCheckBox.setChecked(self.__data["ShowIgnored"])
        self.lineLengthSpinBox.setValue(self.__data["MaxLineLength"])
        self.docLineLengthSpinBox.setValue(self.__data["MaxDocLineLength"])
        self.blankBeforeTopLevelSpinBox.setValue(self.__data["BlankLines"][0])
        self.blankBeforeMethodSpinBox.setValue(self.__data["BlankLines"][1])
        self.hangClosingCheckBox.setChecked(self.__data["HangClosing"])
        self.docTypeComboBox.setCurrentIndex(
            self.docTypeComboBox.findData(self.__data["DocstringType"])
        )
        self.complexitySpinBox.setValue(self.__data["MaxCodeComplexity"])
        self.lineComplexitySpinBox.setValue(self.__data["LineComplexity"])
        self.lineComplexityScoreSpinBox.setValue(self.__data["LineComplexityScore"])
        self.encodingsEdit.setText(self.__data["ValidEncodings"])
        self.copyrightFileSizeSpinBox.setValue(self.__data["CopyrightMinFileSize"])
        self.copyrightAuthorEdit.setText(self.__data["CopyrightAuthor"])
        self.__initFuturesList(self.__data["FutureChecker"])
        self.__initBuiltinsIgnoreList(self.__data["BuiltinsChecker"])
        self.aggressiveCheckBox.setChecked(
            self.__data["CommentedCodeChecker"]["Aggressive"]
        )
        self.__initCommentedCodeCheckerWhiteList(
            self.__data["CommentedCodeChecker"]["WhiteList"]
        )

        # type annotations
        self.minAnnotationsCoverageSpinBox.setValue(
            self.__data["AnnotationsChecker"]["MinimumCoverage"]
        )
        self.maxAnnotationsComplexitySpinBox.setValue(
            self.__data["AnnotationsChecker"]["MaximumComplexity"]
        )
        self.maxAnnotationsLengthSpinBox.setValue(
            self.__data["AnnotationsChecker"]["MaximumLength"]
        )
        self.suppressNoneReturningCheckBox.setChecked(
            self.__data["AnnotationsChecker"]["SuppressNoneReturning"]
        )
        self.suppressDummyArgsCheckBox.setChecked(
            self.__data["AnnotationsChecker"]["SuppressDummyArgs"]
        )
        self.allowUntypedDefsCheckBox.setChecked(
            self.__data["AnnotationsChecker"]["AllowUntypedDefs"]
        )
        self.allowUntypedNestedCheckBox.setChecked(
            self.__data["AnnotationsChecker"]["AllowUntypedNested"]
        )
        self.mypyInitReturnCheckBox.setChecked(
            self.__data["AnnotationsChecker"]["MypyInitReturn"]
        )
        self.allowStarArgAnyCheckBox.setChecked(
            self.__data["AnnotationsChecker"]["AllowStarArgAny"]
        )
        self.forceFutureAnnotationsCheckBox.setChecked(
            self.__data["AnnotationsChecker"]["ForceFutureAnnotations"]
        )
        self.simplifiedTypesCheckBox.setChecked(
            self.__data["AnnotationsChecker"]["CheckFutureAnnotations"]
        )
        self.typeIgnoreCheckBox.setChecked(
            self.__data["AnnotationsChecker"]["RespectTypeIgnore"]
        )
        self.dispatchDecoratorEdit.setText(
            ", ".join(self.__data["AnnotationsChecker"]["DispatchDecorators"])
        )
        self.overloadDecoratorEdit.setText(
            ", ".join(self.__data["AnnotationsChecker"]["OverloadDecorators"])
        )
        self.exemptedTypingSymbolsEdit.setText(
            ", ".join(self.__data["AnnotationsChecker"]["ExemptedTypingSymbols"])
        )

        # security
        self.tmpDirectoriesEdit.setPlainText(
            "\n".join(self.__data["SecurityChecker"]["HardcodedTmpDirectories"])
        )
        self.hashesEdit.setText(
            ", ".join(self.__data["SecurityChecker"]["InsecureHashes"])
        )
        self.insecureSslProtocolsEdit.setPlainText(
            "\n".join(self.__data["SecurityChecker"]["InsecureSslProtocolVersions"])
        )
        self.dsaHighRiskCombo.setCurrentText(
            self.__data["SecurityChecker"]["WeakKeySizeDsaHigh"]
        )
        self.dsaMediumRiskCombo.setCurrentText(
            self.__data["SecurityChecker"]["WeakKeySizeDsaMedium"]
        )
        self.rsaHighRiskCombo.setCurrentText(
            self.__data["SecurityChecker"]["WeakKeySizeRsaHigh"]
        )
        self.rsaMediumRiskCombo.setCurrentText(
            self.__data["SecurityChecker"]["WeakKeySizeRsaMedium"]
        )
        self.ecHighRiskCombo.setCurrentText(
            self.__data["SecurityChecker"]["WeakKeySizeEcHigh"]
        )
        self.ecMediumRiskCombo.setCurrentText(
            self.__data["SecurityChecker"]["WeakKeySizeEcMedium"]
        )
        self.typedExceptionsCheckBox.setChecked(
            self.__data["SecurityChecker"]["CheckTypedException"]
        )

        # ImportsChecker
        self.appPackagesEdit.setPlainText(
            " ".join(sorted(self.__data["ImportsChecker"]["ApplicationPackageNames"]))
        )
        self.bannedModulesEdit.setPlainText(
            " ".join(sorted(self.__data["ImportsChecker"]["BannedModules"]))
        )
        self.__setBanRelativeImports(
            self.__data["ImportsChecker"]["BanRelativeImports"]
        )

        # NameOrderChecker
        self.sortOrderComboBox.setCurrentIndex(
            self.sortOrderComboBox.findData(
                self.__data["NameOrderChecker"]["SortOrder"]
            )
        )
        self.sortCaseSensitiveCheckBox.setChecked(
            self.__data["NameOrderChecker"]["SortCaseSensitive"]
        )
        self.combinedAsImpotsCheckBox.setChecked(
            self.__data["NameOrderChecker"]["CombinedAsImports"]
        )
        self.sortIgnoreStyleCheckBox.setChecked(
            self.__data["NameOrderChecker"]["SortIgnoringStyle"]
        )
        self.sortFromFirstCheckBox.setChecked(
            self.__data["NameOrderChecker"]["SortFromFirst"]
        )

        # UnusedChecker
        self.ignoreAbstractCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreAbstract"]
        )
        self.ignoreOverloadCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreOverload"]
        )
        self.ignoreOverrideCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreOverride"]
        )
        self.ignoreStubsCheckBox.setChecked(self.__data["UnusedChecker"]["IgnoreStubs"])
        self.ignoreVariadicNamesCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreVariadicNames"]
        )
        self.ignoreLambdasCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreLambdas"]
        )
        self.ignoreNestedFunctionsCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreNestedFunctions"]
        )
        self.ignoreDunderMethodsCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreDunderMethods"]
        )
        self.ignoreSlotsCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreSlotMethods"]
        )
        self.ignoreEventHandlersCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreEventHandlerMethods"]
        )
        self.ignoreDunderGlobalsCheckBox.setChecked(
            self.__data["UnusedChecker"]["IgnoreDunderGlobals"]
        )

        self.__cleanupData()

    def __prepareProgress(self):
        """
        Private method to prepare the progress tab for the next run.
        """
        self.progressList.clear()
        if len(self.files) > 0:
            self.checkProgress.setMaximum(len(self.files))
            self.checkProgress.setVisible(len(self.files) > 1)
            if len(self.files) > 1:
                if self.__project:
                    self.progressList.addItems(
                        [
                            os.path.join("...", self.__project.getRelativePath(f))
                            for f in self.files
                        ]
                    )
                else:
                    self.progressList.addItems(self.files)

        QApplication.processEvents()

    def start(self, fn, save=False, repeat=None):
        """
        Public slot to start the code style check.

        @param fn file or list of files or directory to be checked
        @type str or list of str
        @param save flag indicating to save the given file/file list/directory
        @type bool
        @param repeat state of the repeat check box if it is not None
        @type None or bool
        """
        if self.__project is None:
            self.__project = ericApp().getObject("Project")

        self.mainWidget.setCurrentWidget(self.progressTab)

        self.cancelled = False
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.cancelButton.setEnabled(True)
        self.cancelButton.setDefault(True)
        self.statisticsButton.setEnabled(False)
        self.showButton.setEnabled(False)
        self.fixButton.setEnabled(False)
        self.startButton.setEnabled(False)
        self.restartButton.setEnabled(False)
        if repeat is not None:
            self.repeatCheckBox.setChecked(repeat)
        self.checkProgress.setVisible(True)
        QApplication.processEvents()

        if save:
            self.__fileOrFileList = fn

        if isinstance(fn, list):
            self.files = fn[:]
        elif FileSystemUtilities.isRemoteFileName(
            fn
        ) and self.__remotefsInterface.isdir(fn):
            extensions = set(Preferences.getPython("Python3Extensions"))
            self.files = self.__remotefsInterface.direntries(
                fn, True, [f"*{ext}" for ext in extensions], False
            )
        elif FileSystemUtilities.isPlainFileName(fn) and os.path.isdir(fn):
            extensions = set(Preferences.getPython("Python3Extensions"))
            self.files = FileSystemUtilities.direntries(
                fn, True, [f"*{ext}" for ext in extensions], False
            )
        else:
            self.files = [fn]

        # filter the list depending on the filter string
        if self.files:
            filterString = self.excludeFilesEdit.text()
            filterList = [f.strip() for f in filterString.split(",") if f.strip()]
            for fileFilter in filterList:
                self.files = [
                    f for f in self.files if not fnmatch.fnmatch(f, fileFilter.strip())
                ]

        self.__errorItem = None
        self.__resetStatistics()
        self.__clearErrors(self.files)
        self.__cleanupData()
        self.__prepareProgress()

        # disable updates of the list for speed
        self.resultList.setUpdatesEnabled(False)
        self.resultList.setSortingEnabled(False)

        if len(self.files) > 0:
            self.securityNoteLabel.setVisible(
                "S" in self.__getCategories(True, asList=True)
            )

            # extract the configuration values
            excludeMessages = self.__assembleExcludeMessages()
            includeMessages = self.includeMessagesEdit.text()
            repeatMessages = self.repeatCheckBox.isChecked()
            fixCodes = self.fixIssuesEdit.text()
            noFixCodes = self.noFixIssuesEdit.text()
            self.__noFixCodesList = [
                c.strip() for c in noFixCodes.split(",") if c.strip()
            ]
            fixIssues = self.fixIssuesCheckBox.isChecked() and repeatMessages
            self.showIgnored = self.ignoredCheckBox.isChecked() and repeatMessages
            maxLineLength = self.lineLengthSpinBox.value()
            maxDocLineLength = self.docLineLengthSpinBox.value()
            blankLines = (
                self.blankBeforeTopLevelSpinBox.value(),
                self.blankBeforeMethodSpinBox.value(),
            )
            hangClosing = self.hangClosingCheckBox.isChecked()
            docType = self.docTypeComboBox.itemData(self.docTypeComboBox.currentIndex())
            codeComplexityArgs = {
                "McCabeComplexity": self.complexitySpinBox.value(),
                "LineComplexity": self.lineComplexitySpinBox.value(),
                "LineComplexityScore": self.lineComplexityScoreSpinBox.value(),
            }
            miscellaneousArgs = {
                "CodingChecker": self.encodingsEdit.text(),
                "CopyrightChecker": {
                    "MinFilesize": self.copyrightFileSizeSpinBox.value(),
                    "Author": self.copyrightAuthorEdit.text(),
                },
                "FutureChecker": self.__getSelectedFutureImports(),
                "BuiltinsChecker": self.__getBuiltinsIgnoreList(),
                "CommentedCodeChecker": {
                    "Aggressive": self.aggressiveCheckBox.isChecked(),
                    "WhiteList": self.__getCommentedCodeCheckerWhiteList(),
                },
            }

            annotationArgs = {
                "MinimumCoverage": self.minAnnotationsCoverageSpinBox.value(),
                "MaximumComplexity": self.maxAnnotationsComplexitySpinBox.value(),
                "MaximumLength": self.maxAnnotationsLengthSpinBox.value(),
                "SuppressNoneReturning": self.suppressNoneReturningCheckBox.isChecked(),
                "SuppressDummyArgs": self.suppressDummyArgsCheckBox.isChecked(),
                "AllowUntypedDefs": self.allowUntypedDefsCheckBox.isChecked(),
                "AllowUntypedNested": self.allowUntypedNestedCheckBox.isChecked(),
                "MypyInitReturn": self.mypyInitReturnCheckBox.isChecked(),
                "AllowStarArgAny": self.allowStarArgAnyCheckBox.isChecked(),
                "ForceFutureAnnotations": (
                    self.forceFutureAnnotationsCheckBox.isChecked()
                ),
                "CheckFutureAnnotations": self.simplifiedTypesCheckBox.isChecked(),
                "RespectTypeIgnore": self.typeIgnoreCheckBox.isChecked(),
                "DispatchDecorators": [
                    d.strip() for d in self.dispatchDecoratorEdit.text().split(",")
                ],
                "OverloadDecorators": [
                    d.strip() for d in self.overloadDecoratorEdit.text().split(",")
                ],
                "ExemptedTypingSymbols": [
                    d.strip() for d in self.exemptedTypingSymbolsEdit.text().split(",")
                ],
            }

            securityArgs = {
                "hardcoded_tmp_directories": [
                    t.strip()
                    for t in self.tmpDirectoriesEdit.toPlainText().splitlines()
                ],
                "insecure_hashes": [
                    h.strip() for h in self.hashesEdit.text().split(",")
                ],
                "insecure_ssl_protocol_versions": [
                    p.strip()
                    for p in self.insecureSslProtocolsEdit.toPlainText().splitlines()
                ],
                "weak_key_size_dsa_high": int(self.dsaHighRiskCombo.currentText()),
                "weak_key_size_dsa_medium": int(self.dsaMediumRiskCombo.currentText()),
                "weak_key_size_rsa_high": int(self.rsaHighRiskCombo.currentText()),
                "weak_key_size_rsa_medium": int(self.rsaMediumRiskCombo.currentText()),
                "weak_key_size_ec_high": int(self.ecHighRiskCombo.currentText()),
                "weak_key_size_ec_medium": int(self.ecMediumRiskCombo.currentText()),
                "check_typed_exception": self.typedExceptionsCheckBox.isChecked(),
            }

            importsArgs = {
                "ApplicationPackageNames": sorted(
                    self.appPackagesEdit.toPlainText().split()
                ),
                "BannedModules": sorted(self.bannedModulesEdit.toPlainText().split()),
                "BanRelativeImports": self.__getBanRelativeImportsValue(),
            }

            nameOrderArgs = {
                "ApplicationPackageNames": sorted(
                    self.appPackagesEdit.toPlainText().split()
                ),
                "SortOrder": self.sortOrderComboBox.currentData(),
                "SortCaseSensitive": self.sortCaseSensitiveCheckBox.isChecked(),
                "CombinedAsImports": self.combinedAsImpotsCheckBox.isChecked(),
                "SortIgnoringStyle": self.sortIgnoreStyleCheckBox.isChecked(),
                "SortFromFirst": self.sortFromFirstCheckBox.isChecked(),
            }

            unusedArgs = {
                "IgnoreAbstract": self.ignoreAbstractCheckBox.isChecked(),
                "IgnoreOverload": self.ignoreOverloadCheckBox.isChecked(),
                "IgnoreOverride": self.ignoreOverrideCheckBox.isChecked(),
                "IgnoreStubs": self.ignoreStubsCheckBox.isChecked(),
                "IgnoreVariadicNames": self.ignoreVariadicNamesCheckBox.isChecked(),
                "IgnoreLambdas": self.ignoreLambdasCheckBox.isChecked(),
                "IgnoreNestedFunctions": self.ignoreNestedFunctionsCheckBox.isChecked(),
                "IgnoreDunderMethods": self.ignoreDunderMethodsCheckBox.isChecked(),
                "IgnoreSlotMethods": self.ignoreSlotsCheckBox.isChecked(),
                "IgnoreEventHandlerMethods": (
                    self.ignoreEventHandlersCheckBox.isChecked()
                ),
                "IgnoreDunderGlobals": self.ignoreDunderGlobalsCheckBox.isChecked(),
            }

            self.__options = [
                excludeMessages,
                includeMessages,
                repeatMessages,
                fixCodes,
                noFixCodes,
                fixIssues,
                maxLineLength,
                maxDocLineLength,
                blankLines,
                hangClosing,
                docType,
                codeComplexityArgs,
                miscellaneousArgs,
                annotationArgs,
                securityArgs,
                importsArgs,
                nameOrderArgs,
                unusedArgs,
            ]

            # now go through all the files
            self.progress = 0
            self.files.sort()
            self.__timenow = time.monotonic()

            if len(self.files) == 1:
                self.__batch = False
                self.mainWidget.setCurrentWidget(self.resultsTab)
                self.check()
            else:
                self.__batch = True
                self.checkBatch()
        else:
            self.results = CodeStyleCheckerDialog.noFiles
            self.__finished = False
            self.__finish()

    def __modifyOptions(self, source):
        """
        Private method to modify the options based on eflag: entries.

        This method looks for comment lines like '# eflag: noqa = M601'
        at the end of the source in order to extend the list of excluded
        messages for one file only.

        @param source source text
        @type list of str or str
        @return list of checker options
        @rtype list
        """
        options = self.__options[:]
        flags = Utilities.extractFlags(source)
        if "noqa" in flags and isinstance(flags["noqa"], str):
            excludeMessages = options[0].strip().rstrip(",")
            if excludeMessages:
                excludeMessages += ","
            excludeMessages += flags["noqa"]
            options[0] = excludeMessages
        return options

    def check(self, codestring=""):
        """
        Public method to start a style check for one file.

        The results are reported to the __processResult slot.

        @param codestring optional sourcestring
        @type str
        """
        if not self.files:
            self.checkProgress.setMaximum(1)
            self.checkProgress.setValue(1)
            self.__finish()
            return

        self.filename = self.files.pop(0)
        self.checkProgress.setValue(self.progress)
        QApplication.processEvents()

        if self.cancelled:
            self.__resort()
            return

        self.__lastFileItem = None
        self.__finished = False

        if codestring:
            source = codestring.splitlines(True)
            encoding = Utilities.get_coding(source)
        else:
            try:
                if FileSystemUtilities.isRemoteFileName(self.filename):
                    source, encoding = self.__remotefsInterface.readEncodedFile(
                        self.filename
                    )
                else:
                    source, encoding = Utilities.readEncodedFile(self.filename)
                source = source.splitlines(True)
            except (OSError, UnicodeError) as msg:
                self.results = CodeStyleCheckerDialog.hasResults
                self.__createFileErrorItem(self.filename, str(msg))
                self.progress += 1
                # Continue with next file
                self.check()
                return
        if encoding.endswith(("-selected", "-default", "-guessed", "-ignore")):
            encoding = encoding.rsplit("-", 1)[0]

        options = self.__modifyOptions(source)

        errors = []
        self.__itms = []
        for error, itm in self.__onlyFixes.pop(self.filename, []):
            errors.append(error)
            self.__itms.append(itm)

        eol = self.__getEol(self.filename)
        args = options + [
            errors,
            eol,
            encoding,
            Preferences.getEditor("CreateBackupFile"),
        ]
        self.styleCheckService.styleCheck(None, self.filename, source, args)

    def checkBatch(self):
        """
        Public method to start a style check batch job.

        The results are reported to the __processResult slot.
        """
        self.__lastFileItem = None
        self.__finished = False

        argumentsList = []
        for progress, filename in enumerate(self.files, start=1):
            self.checkProgress.setValue(progress)
            if time.monotonic() - self.__timenow > 0.01:
                QApplication.processEvents()
                self.__timenow = time.monotonic()

            try:
                if FileSystemUtilities.isRemoteFileName(filename):
                    source, encoding = self.__remotefsInterface.readEncodedFile(
                        filename
                    )
                else:
                    source, encoding = Utilities.readEncodedFile(filename)
                source = source.splitlines(True)
            except (OSError, UnicodeError) as msg:
                self.results = CodeStyleCheckerDialog.hasResults
                self.__createFileErrorItem(filename, str(msg))
                continue

            if encoding.endswith(("-selected", "-default", "-guessed", "-ignore")):
                encoding = encoding.rsplit("-", 1)[0]

            options = self.__modifyOptions(source)

            errors = []
            self.__itms = []
            for error, itm in self.__onlyFixes.pop(filename, []):
                errors.append(error)
                self.__itms.append(itm)

            eol = self.__getEol(filename)
            args = options + [
                errors,
                eol,
                encoding,
                Preferences.getEditor("CreateBackupFile"),
            ]
            argumentsList.append((filename, source, args))

        # reset the progress bar to the checked files
        self.checkProgress.setValue(self.progress)
        QApplication.processEvents()

        self.styleCheckService.styleBatchCheck(argumentsList)

    def __batchFinished(self):
        """
        Private slot handling the completion of a batch job.
        """
        self.checkProgress.setMaximum(1)
        self.checkProgress.setValue(1)
        self.__finish()

    def __processError(self, fn, msg):
        """
        Private slot to process an error indication from the service.

        @param fn filename of the file
        @type str
        @param msg error message
        @type str
        """
        self.__createErrorItem(fn, msg)

        if not self.__batch:
            self.check()

    def __processResult(self, fn, codeStyleCheckerStats, fixes, results):
        """
        Private slot called after perfoming a style check on one file.

        @param fn filename of the just checked file
        @type str
        @param codeStyleCheckerStats stats of style and name check
        @type dict
        @param fixes number of applied fixes
        @type int
        @param results dictionary containing check result data
        @type dict
        """
        if self.__finished:
            return

        # Check if it's the requested file, otherwise ignore signal if not
        # in batch mode
        if not self.__batch and fn != self.filename:
            return

        fixed = None
        ignoredErrors = collections.defaultdict(int)
        securityOk = 0
        if self.__itms:
            for itm, result in zip(self.__itms, results):
                self.__modifyFixedResultItem(itm, result)
            self.__updateFixerStatistics(fixes)
        else:
            self.__lastFileItem = None

            for result in results:
                if result["ignored"]:
                    ignoredErrors[result["code"]] += 1
                    if self.showIgnored:
                        result["display"] = self.tr("{0} (ignored)").format(
                            result["display"]
                        )
                    else:
                        continue

                elif result["securityOk"]:
                    securityOk += 1
                    if result["code"].startswith("S"):
                        continue

                self.results = CodeStyleCheckerDialog.hasResults
                self.__createResultItem(fn, result)

            self.__updateStatistics(
                codeStyleCheckerStats, fixes, ignoredErrors, securityOk
            )

        if fixed:
            vm = ericApp().getObject("ViewManager")
            editor = vm.getOpenEditor(fn)
            if editor:
                editor.refresh()

        self.progress += 1
        self.__updateProgress(fn)

        if not self.__batch:
            self.check()

    def __updateProgress(self, fn):
        """
        Private method to update the progress tab.

        @param fn filename of the just checked file
        @type str
        """
        if self.__project:
            fn = os.path.join("...", self.__project.getRelativePath(fn))

        self.checkProgress.setValue(self.progress)

        # remove file from the list of jobs to do
        fileItems = self.progressList.findItems(fn, Qt.MatchFlag.MatchExactly)
        if fileItems:
            row = self.progressList.row(fileItems[0])
            self.progressList.takeItem(row)

        if time.monotonic() - self.__timenow > 0.01:
            QApplication.processEvents()
            self.__timenow = time.monotonic()

    def __finish(self):
        """
        Private slot called when the code style check finished or the user
        pressed the cancel button.
        """
        if not self.__finished:
            self.__finished = True

            self.cancelled = True
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(
                True
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(
                True
            )
            self.cancelButton.setEnabled(False)
            self.statisticsButton.setEnabled(True)
            self.showButton.setEnabled(True)
            self.startButton.setEnabled(True)
            self.restartButton.setEnabled(True)

            if self.results != CodeStyleCheckerDialog.hasResults:
                if self.results == CodeStyleCheckerDialog.noResults:
                    QTreeWidgetItem(self.resultList, [self.tr("No issues found.")])
                else:
                    QTreeWidgetItem(
                        self.resultList,
                        [self.tr("No files found (check your ignore list).")],
                    )
                QApplication.processEvents()
                self.showButton.setEnabled(False)
            else:
                self.showButton.setEnabled(True)
            for col in range(self.resultList.columnCount()):
                self.resultList.resizeColumnToContents(col)
            self.resultList.header().setStretchLastSection(True)

            if self.__detectedCodes:
                self.filterComboBox.addItem("")
                self.filterComboBox.addItems(sorted(set(self.__detectedCodes)))
                self.filterComboBox.setEnabled(True)
                self.filterButton.setEnabled(True)

            self.checkProgress.setVisible(False)

            self.__resort()
            self.resultList.setUpdatesEnabled(True)
            self.resultList.setSortingEnabled(True)

            self.mainWidget.setCurrentWidget(self.resultsTab)

    def __getEol(self, fn):
        """
        Private method to get the applicable eol string.

        @param fn filename where to determine the line ending
        @type str
        @return eol string
        @rtype str
        """
        eol = (
            self.__project.getEolString()
            if self.__project.isOpen() and self.__project.isProjectFile(fn)
            else Utilities.linesep()
        )
        return eol

    @pyqtSlot()
    def on_startButton_clicked(self):
        """
        Private slot to start a code style check run.
        """
        self.__cleanupData()

        if self.__forProject:
            data = {
                "EnabledCheckerCategories": self.__getCategories(True),
                "ExcludeFiles": self.excludeFilesEdit.text(),
                "ExcludeMessages": self.excludeMessagesEdit.text(),
                "IncludeMessages": self.includeMessagesEdit.text(),
                "RepeatMessages": self.repeatCheckBox.isChecked(),
                "FixCodes": self.fixIssuesEdit.text(),
                "NoFixCodes": self.noFixIssuesEdit.text(),
                "FixIssues": self.fixIssuesCheckBox.isChecked(),
                "ShowIgnored": self.ignoredCheckBox.isChecked(),
                "MaxLineLength": self.lineLengthSpinBox.value(),
                "MaxDocLineLength": self.docLineLengthSpinBox.value(),
                "BlankLines": (
                    self.blankBeforeTopLevelSpinBox.value(),
                    self.blankBeforeMethodSpinBox.value(),
                ),
                "HangClosing": self.hangClosingCheckBox.isChecked(),
                "DocstringType": self.docTypeComboBox.itemData(
                    self.docTypeComboBox.currentIndex()
                ),
                "MaxCodeComplexity": self.complexitySpinBox.value(),
                "LineComplexity": self.lineComplexitySpinBox.value(),
                "LineComplexityScore": self.lineComplexityScoreSpinBox.value(),
                "ValidEncodings": self.encodingsEdit.text(),
                "CopyrightMinFileSize": self.copyrightFileSizeSpinBox.value(),
                "CopyrightAuthor": self.copyrightAuthorEdit.text(),
                "FutureChecker": self.__getSelectedFutureImports(),
                "BuiltinsChecker": self.__getBuiltinsIgnoreList(),
                "CommentedCodeChecker": {
                    "Aggressive": self.aggressiveCheckBox.isChecked(),
                    "WhiteList": self.__getCommentedCodeCheckerWhiteList(),
                },
                "AnnotationsChecker": {
                    "MinimumCoverage": self.minAnnotationsCoverageSpinBox.value(),
                    "MaximumComplexity": self.maxAnnotationsComplexitySpinBox.value(),
                    "MaximumLength": self.maxAnnotationsLengthSpinBox.value(),
                    "SuppressNoneReturning": (
                        self.suppressNoneReturningCheckBox.isChecked()
                    ),
                    "SuppressDummyArgs": self.suppressDummyArgsCheckBox.isChecked(),
                    "AllowUntypedDefs": self.allowUntypedDefsCheckBox.isChecked(),
                    "AllowUntypedNested": self.allowUntypedNestedCheckBox.isChecked(),
                    "MypyInitReturn": self.mypyInitReturnCheckBox.isChecked(),
                    "AllowStarArgAny": self.allowStarArgAnyCheckBox.isChecked(),
                    "ForceFutureAnnotations": (
                        self.forceFutureAnnotationsCheckBox.isChecked()
                    ),
                    "CheckFutureAnnotations": self.simplifiedTypesCheckBox.isChecked(),
                    "RespectTypeIgnore": self.typeIgnoreCheckBox.isChecked(),
                    "DispatchDecorators": [
                        d.strip() for d in self.dispatchDecoratorEdit.text().split(",")
                    ],
                    "OverloadDecorators": [
                        d.strip() for d in self.overloadDecoratorEdit.text().split(",")
                    ],
                    "ExemptedTypingSymbols": [
                        d.strip()
                        for d in self.exemptedTypingSymbolsEdit.text().split(",")
                    ],
                },
                "SecurityChecker": {
                    "HardcodedTmpDirectories": [
                        t.strip()
                        for t in self.tmpDirectoriesEdit.toPlainText().splitlines()
                    ],
                    "InsecureHashes": [
                        h.strip() for h in self.hashesEdit.text().split(",")
                    ],
                    "InsecureSslProtocolVersions": [
                        p.strip()
                        for p in (
                            self.insecureSslProtocolsEdit.toPlainText().splitlines()
                        )
                    ],
                    "WeakKeySizeDsaHigh": self.dsaHighRiskCombo.currentText(),
                    "WeakKeySizeDsaMedium": self.dsaMediumRiskCombo.currentText(),
                    "WeakKeySizeRsaHigh": self.rsaHighRiskCombo.currentText(),
                    "WeakKeySizeRsaMedium": self.rsaMediumRiskCombo.currentText(),
                    "WeakKeySizeEcHigh": self.ecHighRiskCombo.currentText(),
                    "WeakKeySizeEcMedium": self.ecMediumRiskCombo.currentText(),
                    "CheckTypedException": self.typedExceptionsCheckBox.isChecked(),
                },
                "ImportsChecker": {
                    "ApplicationPackageNames": sorted(
                        self.appPackagesEdit.toPlainText().split()
                    ),
                    "BannedModules": sorted(
                        self.bannedModulesEdit.toPlainText().split()
                    ),
                    "BanRelativeImports": self.__getBanRelativeImportsValue(),
                },
                "NameOrderChecker": {
                    "ApplicationPackageNames": sorted(
                        self.appPackagesEdit.toPlainText().split()
                    ),
                    "SortOrder": self.sortOrderComboBox.currentData(),
                    "SortCaseSensitive": self.sortCaseSensitiveCheckBox.isChecked(),
                    "CombinedAsImports": self.combinedAsImpotsCheckBox.isChecked(),
                    "SortIgnoringStyle": self.sortIgnoreStyleCheckBox.isChecked(),
                    "SortFromFirst": self.sortFromFirstCheckBox.isChecked(),
                },
                "UnusedChecker": {
                    "IgnoreAbstract": self.ignoreAbstractCheckBox.isChecked(),
                    "IgnoreOverload": self.ignoreOverloadCheckBox.isChecked(),
                    "IgnoreOverride": self.ignoreOverrideCheckBox.isChecked(),
                    "IgnoreStubs": self.ignoreStubsCheckBox.isChecked(),
                    "IgnoreVariadicNames": self.ignoreVariadicNamesCheckBox.isChecked(),
                    "IgnoreLambdas": self.ignoreLambdasCheckBox.isChecked(),
                    "IgnoreNestedFunctions": (
                        self.ignoreNestedFunctionsCheckBox.isChecked()
                    ),
                    "IgnoreDunderMethods": self.ignoreDunderMethodsCheckBox.isChecked(),
                    "IgnoreSlotMethods": self.ignoreSlotsCheckBox.isChecked(),
                    "IgnoreEventHandlerMethods": (
                        self.ignoreEventHandlersCheckBox.isChecked()
                    ),
                    "IgnoreDunderGlobals": self.ignoreDunderGlobalsCheckBox.isChecked(),
                },
            }
            if json.dumps(data, sort_keys=True) != json.dumps(
                self.__data, sort_keys=True
            ):
                self.__data = data
                self.__project.setData("CHECKERSPARMS", "Pep8Checker", self.__data)

        self.resultList.clear()
        self.results = CodeStyleCheckerDialog.noResults
        self.cancelled = False
        self.__detectedCodes.clear()
        self.filterComboBox.clear()
        self.filterComboBox.setEnabled(False)
        self.filterButton.setEnabled(False)

        self.start(self.__fileOrFileList)

    @pyqtSlot()
    def on_restartButton_clicked(self):
        """
        Private slot to restart a code style check run.
        """
        self.on_startButton_clicked()

    def __selectCodes(self, edit, categories, showFixCodes):
        """
        Private method to select message codes via a selection dialog.

        @param edit reference of the line edit to be populated
        @type QLineEdit
        @param categories list of message categories to omit
        @type list of str
        @param showFixCodes flag indicating to show a list of fixable
            issues
        @type bool
        """
        from .CodeStyleCodeSelectionDialog import CodeStyleCodeSelectionDialog

        dlg = CodeStyleCodeSelectionDialog(
            edit.text(), categories, showFixCodes, parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            edit.setText(dlg.getSelectedCodes())

    @pyqtSlot()
    def on_excludeMessagesSelectButton_clicked(self):
        """
        Private slot to select the message codes to be excluded via a
        selection dialog.
        """
        self.__selectCodes(
            self.excludeMessagesEdit, self.__getCategories(False, asList=True), False
        )

    @pyqtSlot()
    def on_includeMessagesSelectButton_clicked(self):
        """
        Private slot to select the message codes to be included via a
        selection dialog.
        """
        self.__selectCodes(
            self.includeMessagesEdit, self.__getCategories(True, asList=True), False
        )

    @pyqtSlot()
    def on_fixIssuesSelectButton_clicked(self):
        """
        Private slot to select the issue codes to be fixed via a
        selection dialog.
        """
        self.__selectCodes(self.fixIssuesEdit, [], True)

    @pyqtSlot()
    def on_noFixIssuesSelectButton_clicked(self):
        """
        Private slot to select the issue codes not to be fixed via a
        selection dialog.
        """
        self.__selectCodes(self.noFixIssuesEdit, [], True)

    @pyqtSlot(QTreeWidgetItem, int)
    def on_resultList_itemActivated(self, item, _column):
        """
        Private slot to handle the activation of an item.

        @param item reference to the activated item
        @type QTreeWidgetItem
        @param _column column the item was activated in (unused)
        @type int
        """
        if (
            self.results != CodeStyleCheckerDialog.hasResults
            or item.data(0, self.filenameRole) is None
        ):
            return

        if item.parent():
            fn = item.data(0, self.filenameRole)
            lineno = item.data(0, self.lineRole)
            position = item.data(0, self.positionRole)
            message = item.data(0, self.messageRole)
            issueCode = item.data(0, self.codeRole)

            vm = ericApp().getObject("ViewManager")
            vm.openSourceFile(fn, lineno=lineno, pos=position + 1)
            editor = vm.getOpenEditor(fn)

            if issueCode in ["E901", "E902"]:
                editor.toggleSyntaxError(lineno, 0, True, message, True)
            else:
                editor.toggleWarning(
                    lineno,
                    0,
                    True,
                    self.tr("{0} - {1}", "issue code, message").format(
                        issueCode, message
                    ),
                    warningType=EditorWarningKind.Style,
                )

            editor.updateVerticalScrollBar()

    @pyqtSlot()
    def on_resultList_itemSelectionChanged(self):
        """
        Private slot to change the dialog state depending on the selection.
        """
        self.fixButton.setEnabled(len(self.__getSelectedFixableItems()) > 0)

    @pyqtSlot()
    def on_showButton_clicked(self):
        """
        Private slot to handle the "Show" button press.
        """
        vm = ericApp().getObject("ViewManager")

        selectedIndexes = []
        for index in range(self.resultList.topLevelItemCount()):
            if self.resultList.topLevelItem(index).isSelected():
                selectedIndexes.append(index)
        if len(selectedIndexes) == 0:
            selectedIndexes = list(range(self.resultList.topLevelItemCount()))
        for index in selectedIndexes:
            itm = self.resultList.topLevelItem(index)
            if itm.data(0, self.filenameRole) is not None:
                fn = itm.data(0, self.filenameRole)
                vm.openSourceFile(fn, 1)
                editor = vm.getOpenEditor(fn)
                editor.clearStyleWarnings()
                for cindex in range(itm.childCount()):
                    citm = itm.child(cindex)
                    editor.toggleWarning(
                        citm.data(0, self.lineRole),
                        0,
                        True,
                        self.tr("{0} - {1}", "issue code, message").format(
                            citm.data(0, self.codeRole),
                            citm.data(0, self.messageRole),
                        ),
                        warningType=EditorWarningKind.Style,
                    )

        # go through the list again to clear warning markers for files,
        # that are ok
        openFiles = vm.getOpenFilenames()
        errorFiles = []
        for index in range(self.resultList.topLevelItemCount()):
            itm = self.resultList.topLevelItem(index)
            errorFiles.append(itm.data(0, self.filenameRole))
        for file in openFiles:
            if file not in errorFiles:
                editor = vm.getOpenEditor(file)
                editor.clearStyleWarnings()

        editor = vm.activeWindow()
        editor.updateVerticalScrollBar()

    @pyqtSlot()
    def on_statisticsButton_clicked(self):
        """
        Private slot to show the statistics dialog.
        """
        from .CodeStyleStatisticsDialog import CodeStyleStatisticsDialog

        dlg = CodeStyleStatisticsDialog(self.__statistics, parent=self)
        dlg.exec()

    @pyqtSlot()
    def on_loadDefaultButton_clicked(self):
        """
        Private slot to load the default configuration values.
        """
        defaultParameters = self.getDefaults()
        settings = Preferences.getSettings()

        self.__initCategoriesList(
            settings.value(
                "PEP8/EnabledCheckerCategories",
                defaultParameters["EnabledCheckerCategories"],
            )
        )
        self.excludeFilesEdit.setText(
            settings.value(
                "PEP8/ExcludeFilePatterns", defaultParameters["ExcludeFiles"]
            )
        )
        self.excludeMessagesEdit.setText(
            settings.value("PEP8/ExcludeMessages", defaultParameters["ExcludeMessages"])
        )
        self.includeMessagesEdit.setText(
            settings.value("PEP8/IncludeMessages", defaultParameters["IncludeMessages"])
        )
        self.repeatCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/RepeatMessages", defaultParameters["RepeatMessages"]
                )
            )
        )
        self.fixIssuesEdit.setText(
            settings.value("PEP8/FixCodes", defaultParameters["FixCodes"])
        )
        self.noFixIssuesEdit.setText(
            settings.value("PEP8/NoFixCodes", defaultParameters["NoFixCodes"])
        )
        self.fixIssuesCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value("PEP8/FixIssues", defaultParameters["FixIssues"])
            )
        )
        self.ignoredCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value("PEP8/ShowIgnored", defaultParameters["ShowIgnored"])
            )
        )
        self.lineLengthSpinBox.setValue(
            int(
                settings.value("PEP8/MaxLineLength", defaultParameters["MaxLineLength"])
            )
        )
        self.docLineLengthSpinBox.setValue(
            int(
                settings.value(
                    "PEP8/MaxDocLineLength", defaultParameters["MaxDocLineLength"]
                )
            )
        )
        self.blankBeforeTopLevelSpinBox.setValue(
            int(
                settings.value(
                    "PEP8/BlankLinesBeforeTopLevel", defaultParameters["BlankLines"][0]
                )
            )
        )
        self.blankBeforeMethodSpinBox.setValue(
            int(
                settings.value(
                    "PEP8/BlankLinesBeforeMethod", defaultParameters["BlankLines"][1]
                )
            )
        )
        self.hangClosingCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value("PEP8/HangClosing", defaultParameters["HangClosing"])
            )
        )
        self.docTypeComboBox.setCurrentIndex(
            self.docTypeComboBox.findData(
                settings.value("PEP8/DocstringType", defaultParameters["DocstringType"])
            )
        )
        self.complexitySpinBox.setValue(
            int(
                settings.value(
                    "PEP8/MaxCodeComplexity", defaultParameters["MaxCodeComplexity"]
                )
            )
        )
        self.lineComplexitySpinBox.setValue(
            int(
                settings.value(
                    "PEP8/LineComplexity", defaultParameters["LineComplexity"]
                )
            )
        )
        self.lineComplexityScoreSpinBox.setValue(
            int(
                settings.value(
                    "PEP8/LineComplexityScore", defaultParameters["LineComplexityScore"]
                )
            )
        )
        self.encodingsEdit.setText(
            settings.value("PEP8/ValidEncodings", defaultParameters["ValidEncodings"])
        )
        self.copyrightFileSizeSpinBox.setValue(
            int(
                settings.value(
                    "PEP8/CopyrightMinFileSize",
                    defaultParameters["CopyrightMinFileSize"],
                )
            )
        )
        self.copyrightAuthorEdit.setText(
            settings.value("PEP8/CopyrightAuthor", defaultParameters["CopyrightAuthor"])
        )
        self.__initFuturesList(
            settings.value("PEP8/FutureChecker", defaultParameters["FutureChecker"])
        )
        self.__initBuiltinsIgnoreList(
            EricUtilities.toDict(
                settings.value(
                    "PEP8/BuiltinsChecker", defaultParameters["BuiltinsChecker"]
                )
            )
        )
        self.aggressiveCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/AggressiveSearch",
                    defaultParameters["CommentedCodeChecker"]["Aggressive"],
                )
            )
        )
        self.__initCommentedCodeCheckerWhiteList(
            EricUtilities.toList(
                settings.value(
                    "PEP8/CommentedCodeWhitelist",
                    defaultParameters["CommentedCodeChecker"]["WhiteList"],
                )
            )
        )

        # Type Annotations Checker
        self.minAnnotationsCoverageSpinBox.setValue(
            int(
                settings.value(
                    "PEP8/MinimumAnnotationsCoverage",
                    defaultParameters["AnnotationsChecker"]["MinimumCoverage"],
                )
            )
        )
        self.maxAnnotationsComplexitySpinBox.setValue(
            int(
                settings.value(
                    "PEP8/MaximumAnnotationComplexity",
                    defaultParameters["AnnotationsChecker"]["MaximumComplexity"],
                )
            )
        )
        self.maxAnnotationsLengthSpinBox.setValue(
            int(
                settings.value(
                    "PEP8/MaximumAnnotationLength",
                    defaultParameters["AnnotationsChecker"]["MaximumLength"],
                )
            )
        )
        self.suppressNoneReturningCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/SuppressNoneReturning",
                    defaultParameters["AnnotationsChecker"]["SuppressNoneReturning"],
                )
            )
        )
        self.suppressDummyArgsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/SuppressDummyArgs",
                    defaultParameters["AnnotationsChecker"]["SuppressDummyArgs"],
                )
            )
        )
        self.allowUntypedDefsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/AllowUntypedDefs",
                    defaultParameters["AnnotationsChecker"]["AllowUntypedDefs"],
                )
            )
        )
        self.allowUntypedNestedCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/AllowUntypedNested",
                    defaultParameters["AnnotationsChecker"]["AllowUntypedNested"],
                )
            )
        )
        self.mypyInitReturnCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/MypyInitReturn",
                    defaultParameters["AnnotationsChecker"]["MypyInitReturn"],
                )
            )
        )
        self.allowStarArgAnyCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/AllowStarArgAny",
                    defaultParameters["AnnotationsChecker"]["AllowStarArgAny"],
                )
            )
        )
        self.forceFutureAnnotationsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/ForceFutureAnnotations",
                    defaultParameters["AnnotationsChecker"]["ForceFutureAnnotations"],
                )
            )
        )
        self.simplifiedTypesCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/CheckFutureAnnotations",
                    defaultParameters["AnnotationsChecker"]["CheckFutureAnnotations"],
                )
            )
        )
        self.typeIgnoreCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/RespectTypeIgnore",
                    defaultParameters["AnnotationsChecker"]["RespectTypeIgnore"],
                )
            )
        )
        self.dispatchDecoratorEdit.setText(
            ", ".join(
                EricUtilities.toList(
                    settings.value(
                        "PEP8/DispatchDecorators",
                        defaultParameters["AnnotationsChecker"]["DispatchDecorators"],
                    )
                )
            )
        )
        self.overloadDecoratorEdit.setText(
            ", ".join(
                EricUtilities.toList(
                    settings.value(
                        "PEP8/OverloadDecorators",
                        defaultParameters["AnnotationsChecker"]["OverloadDecorators"],
                    )
                )
            )
        )
        self.exemptedTypingSymbolsEdit.setText(
            ", ".join(
                EricUtilities.toList(
                    settings.value(
                        "PEP8/ExemptedTypingSymbols",
                        defaultParameters["AnnotationsChecker"][
                            "ExemptedTypingSymbols"
                        ],
                    )
                )
            )
        )

        # Security Checker
        self.tmpDirectoriesEdit.setPlainText(
            "\n".join(
                EricUtilities.toList(
                    settings.value(
                        "PEP8/HardcodedTmpDirectories",
                        defaultParameters["SecurityChecker"]["HardcodedTmpDirectories"],
                    )
                )
            )
        )
        self.hashesEdit.setText(
            ", ".join(
                EricUtilities.toList(
                    settings.value(
                        "PEP8/InsecureHashes",
                        defaultParameters["SecurityChecker"]["InsecureHashes"],
                    )
                )
            )
        )
        self.insecureSslProtocolsEdit.setPlainText(
            "\n".join(
                EricUtilities.toList(
                    settings.value(
                        "PEP8/InsecureSslProtocolVersions",
                        defaultParameters["SecurityChecker"][
                            "InsecureSslProtocolVersions"
                        ],
                    )
                )
            )
        )
        self.dsaHighRiskCombo.setCurrentText(
            settings.value(
                "PEP8/WeakKeySizeDsaHigh",
                defaultParameters["SecurityChecker"]["WeakKeySizeDsaHigh"],
            )
        )
        self.dsaMediumRiskCombo.setCurrentText(
            settings.value(
                "PEP8/WeakKeySizeDsaMedium",
                defaultParameters["SecurityChecker"]["WeakKeySizeDsaMedium"],
            )
        )
        self.rsaHighRiskCombo.setCurrentText(
            settings.value(
                "PEP8/WeakKeySizeRsaHigh",
                defaultParameters["SecurityChecker"]["WeakKeySizeRsaHigh"],
            )
        )
        self.rsaMediumRiskCombo.setCurrentText(
            settings.value(
                "PEP8/WeakKeySizeRsaMedium",
                defaultParameters["SecurityChecker"]["WeakKeySizeRsaMedium"],
            )
        )
        self.ecHighRiskCombo.setCurrentText(
            settings.value(
                "PEP8/WeakKeySizeEcHigh",
                defaultParameters["SecurityChecker"]["WeakKeySizeEcHigh"],
            )
        )
        self.ecMediumRiskCombo.setCurrentText(
            settings.value(
                "PEP8/WeakKeySizeEcMedium",
                defaultParameters["SecurityChecker"]["WeakKeySizeEcMedium"],
            )
        )
        self.typedExceptionsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/CheckTypedException",
                    defaultParameters["SecurityChecker"]["CheckTypedException"],
                )
            )
        )

        # Imports Checker
        self.appPackagesEdit.setPlainText(
            " ".join(
                sorted(
                    EricUtilities.toList(
                        settings.value(
                            "PEP8/ApplicationPackageNames",
                            defaultParameters["ImportsChecker"][
                                "ApplicationPackageNames"
                            ],
                        )
                    )
                )
            )
        )
        self.bannedModulesEdit.setPlainText(
            " ".join(
                sorted(
                    EricUtilities.toList(
                        settings.value(
                            "PEP8/BannedModules",
                            defaultParameters["ImportsChecker"]["BannedModules"],
                        )
                    )
                )
            )
        )
        self.__setBanRelativeImports(
            settings.value(
                "PEP8/BanRelativeImports",
                defaultParameters["ImportsChecker"]["BanRelativeImports"],
            )
        )

        # Name Order Checker
        self.sortOrderComboBox.setCurrentIndex(
            self.sortOrderComboBox.findData(
                settings.value(
                    "PEP8/SortOrder", defaultParameters["NameOrderChecker"]["SortOrder"]
                )
            )
        )
        self.sortCaseSensitiveCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/SortCaseSensitive",
                    defaultParameters["NameOrderChecker"]["SortCaseSensitive"],
                )
            )
        )
        self.combinedAsImpotsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/CombinedAsImports",
                    defaultParameters["NameOrderChecker"]["CombinedAsImports"],
                )
            )
        )
        self.sortIgnoreStyleCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/SortIgnoringStyle",
                    defaultParameters["NameOrderChecker"]["SortIgnoringStyle"],
                )
            )
        )
        self.sortFromFirstCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/SortFromFirst",
                    defaultParameters["NameOrderChecker"]["SortFromFirst"],
                )
            )
        )

        # Unused Checker
        self.ignoreAbstractCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreAbstract",
                    defaultParameters["UnusedChecker"]["IgnoreAbstract"],
                )
            )
        )
        self.ignoreOverloadCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreOverload",
                    defaultParameters["UnusedChecker"]["IgnoreOverload"],
                )
            )
        )
        self.ignoreOverrideCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreOverride",
                    defaultParameters["UnusedChecker"]["IgnoreOverride"],
                )
            )
        )
        self.ignoreStubsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreStubs",
                    defaultParameters["UnusedChecker"]["IgnoreStubs"],
                )
            )
        )
        self.ignoreVariadicNamesCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreVariadicNames",
                    defaultParameters["UnusedChecker"]["IgnoreVariadicNames"],
                )
            )
        )
        self.ignoreLambdasCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreLambdas",
                    defaultParameters["UnusedChecker"]["IgnoreLambdas"],
                )
            )
        )
        self.ignoreNestedFunctionsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreNestedFunctions",
                    defaultParameters["UnusedChecker"]["IgnoreNestedFunctions"],
                )
            )
        )
        self.ignoreDunderMethodsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreDunderMethods",
                    defaultParameters["UnusedChecker"]["IgnoreDunderMethods"],
                )
            )
        )
        self.ignoreSlotsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreSlotMethods",
                    defaultParameters["UnusedChecker"]["IgnoreSlotMethods"],
                )
            )
        )
        self.ignoreEventHandlersCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PEP8/UnusedIgnoreEventHandlerMethods",
                    defaultParameters["UnusedChecker"]["IgnoreEventHandlerMethods"],
                )
            )
        )
        self.ignoreDunderGlobalsCheckBox.setChecked(
            EricUtilities.toBool(
                settings.value(
                    "PRP8/UnusedIgnoreDunderGlobals",
                    defaultParameters["UnusedChecker"]["IgnoreDunderGlobals"],
                )
            )
        )

        self.__cleanupData()

    @pyqtSlot()
    def on_storeDefaultButton_clicked(self):
        """
        Private slot to store the current configuration values as
        default values.
        """
        settings = Preferences.getSettings()

        settings.setValue("PEP8/EnabledCheckerCategories", self.__getCategories(True))
        settings.setValue("PEP8/ExcludeFilePatterns", self.excludeFilesEdit.text())
        settings.setValue("PEP8/ExcludeMessages", self.excludeMessagesEdit.text())
        settings.setValue("PEP8/IncludeMessages", self.includeMessagesEdit.text())
        settings.setValue("PEP8/RepeatMessages", self.repeatCheckBox.isChecked())
        settings.setValue("PEP8/FixCodes", self.fixIssuesEdit.text())
        settings.setValue("PEP8/NoFixCodes", self.noFixIssuesEdit.text())
        settings.setValue("PEP8/FixIssues", self.fixIssuesCheckBox.isChecked())
        settings.setValue("PEP8/ShowIgnored", self.ignoredCheckBox.isChecked())
        settings.setValue("PEP8/MaxLineLength", self.lineLengthSpinBox.value())
        settings.setValue("PEP8/MaxDocLineLength", self.docLineLengthSpinBox.value())
        settings.setValue(
            "PEP8/BlankLinesBeforeTopLevel", self.blankBeforeTopLevelSpinBox.value()
        )
        settings.setValue(
            "PEP8/BlankLinesBeforeMethod", self.blankBeforeMethodSpinBox.value()
        )
        settings.setValue("PEP8/HangClosing", self.hangClosingCheckBox.isChecked())
        settings.setValue(
            "PEP8/DocstringType",
            self.docTypeComboBox.itemData(self.docTypeComboBox.currentIndex()),
        )
        settings.setValue("PEP8/MaxCodeComplexity", self.complexitySpinBox.value())
        settings.setValue("PEP8/LineComplexity", self.lineComplexitySpinBox.value())
        settings.setValue(
            "PEP8/LineComplexityScore", self.lineComplexityScoreSpinBox.value()
        )
        settings.setValue("PEP8/ValidEncodings", self.encodingsEdit.text())
        settings.setValue(
            "PEP8/CopyrightMinFileSize", self.copyrightFileSizeSpinBox.value()
        )
        settings.setValue("PEP8/CopyrightAuthor", self.copyrightAuthorEdit.text())
        settings.setValue("PEP8/FutureChecker", self.__getSelectedFutureImports())
        settings.setValue("PEP8/BuiltinsChecker", self.__getBuiltinsIgnoreList())
        settings.setValue("PEP8/AggressiveSearch", self.aggressiveCheckBox.isChecked())
        settings.setValue(
            "PEP8/CommentedCodeWhitelist", self.__getCommentedCodeCheckerWhiteList()
        )

        # Type Annotations Checker
        settings.setValue(
            "PEP8/MinimumAnnotationsCoverage",
            self.minAnnotationsCoverageSpinBox.value(),
        )
        settings.setValue(
            "PEP8/MaximumAnnotationComplexity",
            self.maxAnnotationsComplexitySpinBox.value(),
        )
        settings.setValue(
            "PEP8/MaximumAnnotationLength", self.maxAnnotationsLengthSpinBox.value()
        )
        settings.setValue(
            "PEP8/SuppressNoneReturning", self.suppressNoneReturningCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/SuppressDummyArgs", self.suppressDummyArgsCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/AllowUntypedDefs", self.allowUntypedDefsCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/AllowUntypedNested", self.allowUntypedNestedCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/MypyInitReturn", self.mypyInitReturnCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/AllowStarArgAny", self.allowStarArgAnyCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/ForceFutureAnnotations",
            self.forceFutureAnnotationsCheckBox.isChecked(),
        )
        settings.setValue(
            "PEP8/CheckFutureAnnotations", self.simplifiedTypesCheckBox.isChecked()
        )
        settings.setValue("PEP8/RespectTypeIgnore", self.typeIgnoreCheckBox.isChecked())
        settings.setValue(
            "PEP8/DispatchDecorators",
            [d.strip() for d in self.dispatchDecoratorEdit.text().split(",")],
        )
        settings.setValue(
            "PEP8/OverloadDecorators",
            [d.strip() for d in self.overloadDecoratorEdit.text().split(",")],
        )
        settings.setValue(
            "PEP8/ExemptedTypingSymbols",
            [d.strip() for d in self.exemptedTypingSymbolsEdit.text().split(",")],
        )

        # Security Checker
        settings.setValue(
            "PEP8/HardcodedTmpDirectories",
            [t.strip() for t in self.tmpDirectoriesEdit.toPlainText().splitlines()],
        )
        settings.setValue(
            "PEP8/InsecureHashes",
            [h.strip() for h in self.hashesEdit.text().split(",")],
        )
        settings.setValue(
            "PEP8/InsecureSslProtocolVersions",
            [
                p.strip()
                for p in self.insecureSslProtocolsEdit.toPlainText().splitlines()
            ],
        )
        settings.setValue(
            "PEP8/WeakKeySizeDsaHigh", self.dsaHighRiskCombo.currentText()
        )
        settings.setValue(
            "PEP8/WeakKeySizeDsaMedium", self.dsaMediumRiskCombo.currentText()
        )
        settings.setValue(
            "PEP8/WeakKeySizeRsaHigh", self.rsaHighRiskCombo.currentText()
        )
        settings.setValue(
            "PEP8/WeakKeySizeRsaMedium", self.rsaMediumRiskCombo.currentText()
        )
        settings.setValue("PEP8/WeakKeySizeEcHigh", self.ecHighRiskCombo.currentText())
        settings.setValue(
            "PEP8/WeakKeySizeEcMedium", self.ecMediumRiskCombo.currentText()
        )
        settings.setValue(
            "PEP8/CheckTypedException", self.typedExceptionsCheckBox.isChecked()
        )

        # Imports Checker
        settings.setValue(
            "PEP8/ApplicationPackageNames",
            sorted(self.appPackagesEdit.toPlainText().split()),
        )
        settings.setValue(
            "PEP8/BannedModules", sorted(self.bannedModulesEdit.toPlainText().split())
        )
        settings.setValue(
            "PEP8/BanRelativeImports", self.__getBanRelativeImportsValue()
        )

        # Name Order Checker
        settings.setValue("PEP8/SortOrder", self.sortOrderComboBox.currentData())
        settings.setValue(
            "PEP8/SortCaseSensitive", self.sortCaseSensitiveCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/CombinedAsImports", self.combinedAsImpotsCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/SortIgnoringStyle", self.sortIgnoreStyleCheckBox.isChecked()
        )
        settings.setValue("PEP8/SortFromFirst", self.sortFromFirstCheckBox.isChecked())

        # Unused Checker
        settings.setValue(
            "PEP8/UnusedIgnoreAbstract", self.ignoreAbstractCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/UnusedIgnoreOverload", self.ignoreOverloadCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/UnusedIgnoreOverride", self.ignoreOverrideCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/UnusedIgnoreStubs", self.ignoreStubsCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/UnusedIgnoreVariadicNames",
            self.ignoreVariadicNamesCheckBox.isChecked(),
        )
        settings.setValue(
            "PEP8/UnusedIgnoreLambdas", self.ignoreLambdasCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/UnusedIgnoreNestedFunctions",
            self.ignoreNestedFunctionsCheckBox.isChecked(),
        )
        settings.setValue(
            "PEP8/UnusedIgnoreDunderMethods",
            self.ignoreDunderMethodsCheckBox.isChecked(),
        )
        settings.setValue(
            "PEP8/UnusedIgnoreSlotMethods", self.ignoreSlotsCheckBox.isChecked()
        )
        settings.setValue(
            "PEP8/UnusedIgnoreEventHandlerMethods",
            self.ignoreEventHandlersCheckBox.isChecked(),
        )
        settings.setValue(
            "PEP8/UnusedIgnoreDunderGlobals",
            self.ignoreDunderGlobalsCheckBox.isChecked(),
        )

    @pyqtSlot()
    def on_resetDefaultButton_clicked(self):
        """
        Private slot to reset the configuration values to their default values.
        """
        defaultParameters = self.getDefaults()
        settings = Preferences.getSettings()

        settings.setValue(
            "PEP8/EnabledCheckerCategories",
            defaultParameters["EnabledCheckerCategories"],
        )
        settings.setValue("PEP8/ExcludeFilePatterns", defaultParameters["ExcludeFiles"])
        settings.setValue("PEP8/ExcludeMessages", defaultParameters["ExcludeMessages"])
        settings.setValue("PEP8/IncludeMessages", defaultParameters["IncludeMessages"])
        settings.setValue("PEP8/RepeatMessages", defaultParameters["RepeatMessages"])
        settings.setValue("PEP8/FixCodes", defaultParameters["FixCodes"])
        settings.setValue("PEP8/NoFixCodes", defaultParameters["NoFixCodes"])
        settings.setValue("PEP8/FixIssues", defaultParameters["FixIssues"])
        settings.setValue("PEP8/ShowIgnored", defaultParameters["ShowIgnored"])
        settings.setValue("PEP8/MaxLineLength", defaultParameters["MaxLineLength"])
        settings.setValue(
            "PEP8/MaxDocLineLength", defaultParameters["MaxDocLineLength"]
        )
        settings.setValue(
            "PEP8/BlankLinesBeforeTopLevel", defaultParameters["BlankLines"][0]
        )
        settings.setValue(
            "PEP8/BlankLinesBeforeMethod", defaultParameters["BlankLines"][1]
        )
        settings.setValue("PEP8/HangClosing", defaultParameters["HangClosing"])
        settings.setValue("PEP8/DocstringType", defaultParameters["DocstringType"])
        settings.setValue(
            "PEP8/MaxCodeComplexity", defaultParameters["MaxCodeComplexity"]
        )
        settings.setValue("PEP8/LineComplexity", defaultParameters["LineComplexity"])
        settings.setValue(
            "PEP8/LineComplexityScore", defaultParameters["LineComplexityScore"]
        )
        settings.setValue("PEP8/ValidEncodings", defaultParameters["ValidEncodings"])
        settings.setValue(
            "PEP8/CopyrightMinFileSize", defaultParameters["CopyrightMinFileSize"]
        )
        settings.setValue("PEP8/CopyrightAuthor", defaultParameters["CopyrightAuthor"])
        settings.setValue("PEP8/FutureChecker", defaultParameters["FutureChecker"])
        settings.setValue("PEP8/BuiltinsChecker", defaultParameters["BuiltinsChecker"])
        settings.setValue(
            "PEP8/AggressiveSearch",
            defaultParameters["CommentedCodeChecker"]["Aggressive"],
        )
        settings.setValue(
            "PEP8/CommentedCodeWhitelist",
            defaultParameters["CommentedCodeChecker"]["WhiteList"],
        )

        # Type Annotations Checker
        settings.setValue(
            "PEP8/MinimumAnnotationsCoverage",
            defaultParameters["AnnotationsChecker"]["MinimumCoverage"],
        )
        settings.setValue(
            "PEP8/MaximumAnnotationComplexity",
            defaultParameters["AnnotationsChecker"]["MaximumComplexity"],
        )
        settings.setValue(
            "PEP8/MaximumAnnotationLength",
            defaultParameters["AnnotationsChecker"]["MaximumLength"],
        )
        settings.setValue(
            "PEP8/SuppressNoneReturning",
            defaultParameters["AnnotationsChecker"]["SuppressNoneReturning"],
        )
        settings.setValue(
            "PEP8/SuppressDummyArgs",
            defaultParameters["AnnotationsChecker"]["SuppressDummyArgs"],
        )
        settings.setValue(
            "PEP8/AllowUntypedDefs",
            defaultParameters["AnnotationsChecker"]["AllowUntypedDefs"],
        )
        settings.setValue(
            "PEP8/AllowUntypedNested",
            defaultParameters["AnnotationsChecker"]["AllowUntypedNested"],
        )
        settings.setValue(
            "PEP8/MypyInitReturn",
            defaultParameters["AnnotationsChecker"]["MypyInitReturn"],
        )
        settings.setValue(
            "PEP8/AllowStarArgAny",
            defaultParameters["AnnotationsChecker"]["AllowStarArgAny"],
        )
        settings.setValue(
            "PEP8/ForceFutureAnnotations",
            defaultParameters["AnnotationsChecker"]["ForceFutureAnnotations"],
        )
        settings.setValue(
            "PEP8/CheckFutureAnnotations",
            defaultParameters["AnnotationsChecker"]["CheckFutureAnnotations"],
        )
        settings.setValue(
            "PEP8/RespectTypeIgnore",
            defaultParameters["AnnotationsChecker"]["RespectTypeIgnore"],
        )
        settings.setValue(
            "PEP8/DispatchDecorators",
            defaultParameters["AnnotationsChecker"]["DispatchDecorators"],
        )
        settings.setValue(
            "PEP8/OverloadDecorators",
            defaultParameters["AnnotationsChecker"]["OverloadDecorators"],
        )
        settings.setValue(
            "PEP8/ExemptedTypingSymbols",
            defaultParameters["AnnotationsChecker"]["ExemptedTypingSymbols"],
        )

        # Security Checker
        settings.setValue(
            "PEP8/HardcodedTmpDirectories",
            defaultParameters["SecurityChecker"]["HardcodedTmpDirectories"],
        )
        settings.setValue(
            "PEP8/InsecureHashes",
            defaultParameters["SecurityChecker"]["InsecureHashes"],
        )
        settings.setValue(
            "PEP8/InsecureSslProtocolVersions",
            defaultParameters["SecurityChecker"]["InsecureSslProtocolVersions"],
        )
        settings.setValue(
            "PEP8/WeakKeySizeDsaHigh",
            defaultParameters["SecurityChecker"]["WeakKeySizeDsaHigh"],
        )
        settings.setValue(
            "PEP8/WeakKeySizeDsaMedium",
            defaultParameters["SecurityChecker"]["WeakKeySizeDsaMedium"],
        )
        settings.setValue(
            "PEP8/WeakKeySizeRsaHigh",
            defaultParameters["SecurityChecker"]["WeakKeySizeRsaHigh"],
        )
        settings.setValue(
            "PEP8/WeakKeySizeRsaMedium",
            defaultParameters["SecurityChecker"]["WeakKeySizeRsaMedium"],
        )
        settings.setValue(
            "PEP8/WeakKeySizeEcHigh",
            defaultParameters["SecurityChecker"]["WeakKeySizeEcHigh"],
        )
        settings.setValue(
            "PEP8/WeakKeySizeEcMedium",
            defaultParameters["SecurityChecker"]["WeakKeySizeEcMedium"],
        )
        settings.setValue(
            "PEP8/CheckTypedException",
            defaultParameters["SecurityChecker"]["CheckTypedException"],
        )

        # Imports Checker
        settings.setValue(
            "PEP8/ApplicationPackageNames",
            defaultParameters["ImportsChecker"]["ApplicationPackageNames"],
        )
        settings.setValue(
            "PEP8/BannedModules",
            defaultParameters["ImportsChecker"]["BannedModules"],
        )
        settings.setValue(
            "PEP8/BanRelativeImports",
            defaultParameters["ImportsChecker"]["BanRelativeImports"],
        )

        # Name Order Checker
        settings.setValue(
            "PEP8/SortOrder",
            defaultParameters["NameOrderChecker"]["SortOrder"],
        )
        settings.setValue(
            "PEP8/SortCaseSensitive",
            defaultParameters["NameOrderChecker"]["SortCaseSensitive"],
        )
        settings.setValue(
            "PEP8/CombinedAsImports",
            defaultParameters["NameOrderChecker"]["CombinedAsImports"],
        )
        settings.setValue(
            "PEP8/SortIgnoringStyle",
            defaultParameters["NameOrderChecker"]["SortIgnoringStyle"],
        )
        settings.setValue(
            "PEP8/SortFromFirst",
            defaultParameters["NameOrderChecker"]["SortFromFirst"],
        )

        # Unused Checker
        settings.setValue(
            "PEP8/UnusedIgnoreAbstract",
            defaultParameters["UnusedChecker"]["IgnoreAbstract"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreOverload",
            defaultParameters["UnusedChecker"]["IgnoreOverload"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreOverride",
            defaultParameters["UnusedChecker"]["IgnoreOverride"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreStubs",
            defaultParameters["UnusedChecker"]["IgnoreStubs"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreVariadicNames",
            defaultParameters["UnusedChecker"]["IgnoreVariadicNames"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreLambdas",
            defaultParameters["UnusedChecker"]["IgnoreLambdas"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreNestedFunctions",
            defaultParameters["UnusedChecker"]["IgnoreNestedFunctions"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreDunderMethods",
            defaultParameters["UnusedChecker"]["IgnoreDunderMethods"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreSlotMethods",
            defaultParameters["UnusedChecker"]["IgnoreSlotMethods"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreEventHandlerMethods",
            defaultParameters["UnusedChecker"]["IgnoreEventHandlerMethods"],
        )
        settings.setValue(
            "PEP8/UnusedIgnoreDunderGlobals",
            defaultParameters["UnusedChecker"]["IgnoreDunderGlobals"],
        )

        # Update UI with default values
        self.on_loadDefaultButton_clicked()

    def closeEvent(self, _evt):
        """
        Protected method to handle a close event.

        @param _evt reference to the close event (unused)
        @type QCloseEvent
        """
        self.on_cancelButton_clicked()

    @pyqtSlot()
    def on_cancelButton_clicked(self):
        """
        Private slot to handle the "Cancel" button press.
        """
        if self.__batch:
            self.styleCheckService.cancelStyleBatchCheck()
            QTimer.singleShot(1000, self.__finish)
        else:
            self.__finish()

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()

    def __clearErrors(self, files):
        """
        Private method to clear all warning markers of open editors to be
        checked.

        @param files list of files to be checked
        @type list of str
        """
        vm = ericApp().getObject("ViewManager")
        openFiles = vm.getOpenFilenames()
        for file in [f for f in openFiles if f in files]:
            editor = vm.getOpenEditor(file)
            editor.clearStyleWarnings()

    @pyqtSlot()
    def on_fixButton_clicked(self):
        """
        Private slot to fix selected issues.

        Build a dictionary of issues to fix. Update the initialized __options.
        Then call check with the dict as keyparam to fix selected issues.
        """
        fixableItems = self.__getSelectedFixableItems()
        # dictionary of lists of tuples containing the issue and the item
        fixesDict = {}
        for itm in fixableItems:
            filename = itm.data(0, self.filenameRole)
            if filename not in fixesDict:
                fixesDict[filename] = []
            fixesDict[filename].append(
                (
                    {
                        "file": filename,
                        "line": itm.data(0, self.lineRole),
                        "offset": itm.data(0, self.positionRole),
                        "code": itm.data(0, self.codeRole),
                        "display": itm.data(0, self.messageRole),
                        "args": itm.data(0, self.argsRole),
                    },
                    itm,
                )
            )

        # update the configuration values (3: fixCodes, 4: noFixCodes,
        # 5: fixIssues, 6: maxLineLength)
        self.__options[3] = self.fixIssuesEdit.text()
        self.__options[4] = self.noFixIssuesEdit.text()
        self.__options[5] = True
        self.__options[6] = self.lineLengthSpinBox.value()

        self.files = list(fixesDict)
        # now go through all the files
        self.progress = 0
        self.files.sort()
        self.cancelled = False
        self.__onlyFixes = fixesDict
        self.check()

    def __getSelectedFixableItems(self):
        """
        Private method to extract all selected items for fixable issues.

        @return selected items for fixable issues
        @rtype list of QTreeWidgetItem
        """
        fixableItems = []
        for itm in self.resultList.selectedItems():
            if itm.childCount() > 0:
                for index in range(itm.childCount()):
                    citm = itm.child(index)
                    if self.__itemFixable(citm) and citm not in fixableItems:
                        fixableItems.append(citm)
            elif self.__itemFixable(itm) and itm not in fixableItems:
                fixableItems.append(itm)

        return fixableItems

    def __itemFixable(self, itm):
        """
        Private method to check, if an item has a fixable issue.

        @param itm item to be checked
        @type QTreeWidgetItem
        @return flag indicating a fixable issue
        @rtype bool
        """
        return itm.data(0, self.fixableRole) and not itm.data(0, self.ignoredRole)

    def __initFuturesList(self, selectedFutures):
        """
        Private method to set the selected status of the future imports.

        @param selectedFutures comma separated list of expected future imports
        @type str
        """
        expectedImports = (
            [i.strip() for i in selectedFutures.split(",") if bool(i.strip())]
            if selectedFutures
            else []
        )
        for row in range(self.futuresList.count()):
            itm = self.futuresList.item(row)
            if itm.text() in expectedImports:
                itm.setCheckState(Qt.CheckState.Checked)
            else:
                itm.setCheckState(Qt.CheckState.Unchecked)

    def __getSelectedFutureImports(self):
        """
        Private method to get the expected future imports.

        @return expected future imports as a comma separated string
        @rtype str
        """
        selectedFutures = []
        for row in range(self.futuresList.count()):
            itm = self.futuresList.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                selectedFutures.append(itm.text())
        return ", ".join(selectedFutures)

    def __initBuiltinsIgnoreList(self, builtinsIgnoreDict):
        """
        Private method to populate the list of shadowed builtins to be ignored.

        @param builtinsIgnoreDict dictionary containing the builtins
            assignments to be ignored
        @type dict of list of str
        """
        self.builtinsAssignmentList.clear()
        for left, rightList in builtinsIgnoreDict.items():
            for right in rightList:
                QTreeWidgetItem(self.builtinsAssignmentList, [left, right])

        self.on_builtinsAssignmentList_itemSelectionChanged()

    def __getBuiltinsIgnoreList(self):
        """
        Private method to get a dictionary containing the builtins assignments
        to be ignored.

        @return dictionary containing the builtins assignments to be ignored
        @rtype dict of list of str
        """
        builtinsIgnoreDict = {}
        for row in range(self.builtinsAssignmentList.topLevelItemCount()):
            itm = self.builtinsAssignmentList.topLevelItem(row)
            left, right = itm.text(0), itm.text(1)
            if left not in builtinsIgnoreDict:
                builtinsIgnoreDict[left] = []
            builtinsIgnoreDict[left].append(right)

        return builtinsIgnoreDict

    @pyqtSlot()
    def on_builtinsAssignmentList_itemSelectionChanged(self):
        """
        Private slot to react upon changes of the selected builtin assignments.
        """
        self.deleteBuiltinButton.setEnabled(
            len(self.builtinsAssignmentList.selectedItems()) > 0
        )

    @pyqtSlot()
    def on_addBuiltinButton_clicked(self):
        """
        Private slot to add a built-in assignment to be ignored.
        """
        from .CodeStyleAddBuiltinIgnoreDialog import CodeStyleAddBuiltinIgnoreDialog

        dlg = CodeStyleAddBuiltinIgnoreDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            left, right = dlg.getData()
            QTreeWidgetItem(self.builtinsAssignmentList, [left, right])

    @pyqtSlot()
    def on_deleteBuiltinButton_clicked(self):
        """
        Private slot to delete the selected items from the list.
        """
        for itm in self.builtinsAssignmentList.selectedItems():
            index = self.builtinsAssignmentList.indexOfTopLevelItem(itm)
            self.builtinsAssignmentList.takeTopLevelItem(index)
            del itm

    def __initCategoriesList(self, enabledCategories):
        """
        Private method to set the enabled status of the checker categories.

        @param enabledCategories comma separated list of enabled checker
            categories
        @type str
        """
        enabledCategoriesList = (
            [c.strip() for c in enabledCategories.split(",") if bool(c.strip())]
            if enabledCategories
            else list(CodeStyleCheckerDialog.checkCategories)
        )
        for row in range(self.categoriesList.count()):
            itm = self.categoriesList.item(row)
            if itm.data(Qt.ItemDataRole.UserRole) in enabledCategoriesList:
                itm.setCheckState(Qt.CheckState.Checked)
            else:
                itm.setCheckState(Qt.CheckState.Unchecked)

    def __getCategories(self, enabled, asList=False):
        """
        Private method to get the enabled or disabled checker categories.

        @param enabled flag indicating to return enabled categories
        @type bool
        @param asList flag indicating to return the checker categories as a
            Python list
        @type bool
        @return checker categories as a list or comma separated string
        @rtype str or list of str
        """
        state = Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked

        checkerList = []
        for row in range(self.categoriesList.count()):
            itm = self.categoriesList.item(row)
            if itm.checkState() == state:
                checkerList.append(itm.data(Qt.ItemDataRole.UserRole))
        if asList:
            return checkerList
        else:
            return ", ".join(checkerList)

    def __assembleExcludeMessages(self):
        """
        Private method to assemble the list of excluded checks.

        @return list of excluded checks as a comma separated string.
        @rtype str
        """
        excludeMessages = self.excludeMessagesEdit.text()
        disabledCategories = self.__getCategories(False)

        if excludeMessages and disabledCategories:
            return disabledCategories + "," + excludeMessages
        elif disabledCategories:
            return disabledCategories
        elif excludeMessages:
            return excludeMessages
        else:
            return ""

    def __cleanupData(self):
        """
        Private method to clean the loaded/entered data of redundant entries.
        """
        # Migrate single letter exclude messages to disabled checker categories
        # and delete them from exclude messages
        excludedMessages = [
            m.strip() for m in self.excludeMessagesEdit.text().split(",") if bool(m)
        ]
        excludedMessageCategories = [c for c in excludedMessages if len(c) == 1]
        enabledCheckers = self.__getCategories(True, asList=True)
        for category in excludedMessageCategories:
            if category in enabledCheckers:
                enabledCheckers.remove(category)
            excludedMessages.remove(category)

        # Remove excluded messages of an already excluded category
        disabledCheckers = self.__getCategories(False, asList=True)
        for message in excludedMessages[:]:
            if message[0] in disabledCheckers:
                excludedMessages.remove(message)

        self.excludeMessagesEdit.setText(",".join(excludedMessages))
        self.__initCategoriesList(",".join(enabledCheckers))

    def __initCommentedCodeCheckerWhiteList(self, whitelist):
        """
        Private method to populate the list of commented code whitelist
        patterns.

        @param whitelist list of commented code whitelist patterns
        @type list of str
        """
        self.whitelistWidget.clear()

        for pattern in whitelist:
            QListWidgetItem(pattern, self.whitelistWidget)

        self.on_whitelistWidget_itemSelectionChanged()

    def __getCommentedCodeCheckerWhiteList(self):
        """
        Private method to get the list of commented code whitelist patterns.

        @return list of commented code whitelist patterns
        @rtype list of str
        """
        whitelist = []

        for row in range(self.whitelistWidget.count()):
            whitelist.append(self.whitelistWidget.item(row).text())

        return whitelist

    @pyqtSlot()
    def on_whitelistWidget_itemSelectionChanged(self):
        """
        Private slot to react upon changes of the selected whitelist patterns.
        """
        self.deleteWhitelistButton.setEnabled(
            len(self.whitelistWidget.selectedItems()) > 0
        )

    @pyqtSlot()
    def on_addWhitelistButton_clicked(self):
        """
        Private slot to add a commented code whitelist pattern.
        """
        pattern, ok = QInputDialog.getText(
            self,
            self.tr("Commented Code Whitelist Pattern"),
            self.tr("Enter a Commented Code Whitelist Pattern"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and pattern:
            QListWidgetItem(pattern, self.whitelistWidget)

    @pyqtSlot()
    def on_deleteWhitelistButton_clicked(self):
        """
        Private slot to delete the selected items from the list.
        """
        for itm in self.whitelistWidget.selectedItems():
            row = self.whitelistWidget.row(itm)
            self.whitelistWidget.takeItem(row)
            del itm

    @pyqtSlot()
    def on_filterButton_clicked(self):
        """
        Private slot to filter the list of messages based on selected message
        code.
        """
        selectedMessageCode = self.filterComboBox.currentText()

        for topRow in range(self.resultList.topLevelItemCount()):
            topItem = self.resultList.topLevelItem(topRow)
            topItem.setExpanded(True)
            visibleChildren = topItem.childCount()
            for childIndex in range(topItem.childCount()):
                childItem = topItem.child(childIndex)
                hideChild = (
                    childItem.data(0, self.codeRole) != selectedMessageCode
                    if selectedMessageCode
                    else False
                )
                childItem.setHidden(hideChild)
                if hideChild:
                    visibleChildren -= 1
            topItem.setHidden(visibleChildren == 0)
