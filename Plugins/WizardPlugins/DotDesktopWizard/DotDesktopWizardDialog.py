# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the .desktop wizard dialog.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Utilities
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from .Ui_DotDesktopWizardDialog import Ui_DotDesktopWizardDialog


class DotDesktopWizardDialog(QDialog, Ui_DotDesktopWizardDialog):
    """
    Class implementing the .desktop wizard dialog.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.__mainCategories = [
            "AudioVideo",
            "Audio",
            "Video",
            "Development",
            "Education",
            "Game",
            "Graphics",
            "Network",
            "Office",
            "Science",
            "Settings",
            "System",
            "Utility",
        ]

        self.__subCategories = [
            "Building",
            "Debugger",
            "IDE",
            "GUIDesigner",
            "Profiling",
            "RevisionControl",
            "Translation",
            "Calendar",
            "ContactManagement",
            "Database",
            "Dictionary",
            "Chart",
            "Email",
            "Finance",
            "FlowChart",
            "PDA",
            "ProjectManagement",
            "Presentation",
            "Spreadsheet",
            "WordProcessor",
            "2DGraphics",
            "VectorGraphics",
            "RasterGraphics",
            "3DGraphics",
            "Scanning",
            "OCR",
            "Photography",
            "Publishing",
            "Viewer",
            "TextTools",
            "DesktopSettings",
            "HardwareSettings",
            "Printing",
            "PackageManager",
            "Dialup",
            "InstantMessaging",
            "Chat",
            "IRCClient",
            "Feed",
            "FileTransfer",
            "HamRadio",
            "News",
            "P2P",
            "RemoteAccess",
            "Telephony",
            "TelephonyTools",
            "VideoConference",
            "WebBrowser",
            "WebDevelopment",
            "Midi",
            "Mixer",
            "Sequencer",
            "Tuner",
            "TV",
            "AudioVideoEditing",
            "Player",
            "Recorder",
            "DiscBurning",
            "ActionGame",
            "AdventureGame",
            "ArcadeGame",
            "BoardGame",
            "BlocksGame",
            "CardGame",
            "KidsGame",
            "LogicGame",
            "RolePlaying",
            "Shooter",
            "Simulation",
            "SportsGame",
            "StrategyGame",
            "Art",
            "Construction",
            "Music",
            "Languages",
            "ArtificialIntelligence",
            "Astronomy",
            "Biology",
            "Chemistry",
            "ComputerScience",
            "DataVisualization",
            "Economy",
            "Electricity",
            "Geography",
            "Geology",
            "Geoscience",
            "History",
            "Humanities",
            "ImageProcessing",
            "Literature",
            "Maps",
            "Math",
            "NumericalAnalysis",
            "MedicalSoftware",
            "Physics",
            "Robotics",
            "Spirituality",
            "Sports",
            "ParallelComputing",
            "Amusement",
            "Archiving",
            "Compression",
            "Electronics",
            "Emulator",
            "Engineering",
            "FileTools",
            "FileManager",
            "TerminalEmulator",
            "Filesystem",
            "Monitor",
            "Security",
            "Accessibility",
            "Calculator",
            "Clock",
            "TextEditor",
            "Documentation",
            "Adult",
            "Core",
            "KDE",
            "GNOME",
            "XFCE",
            "GTK",
            "Qt",
            "Motif",
            "Java",
            "ConsoleOnly",
        ]

        self.__showinEnvironments = [
            "GNOME",
            "KDE",
            "LXDE",
            "LXQt",
            "MATE",
            "Razor",
            "ROX",
            "TDE",
            "Unity",
            "XFCE",
            "EDE",
            "Cinnamon",
            "Pantheon",
            "Old",
        ]

        self.typeComboBox.addItems(
            [
                self.tr("FreeDesktop Standard .desktop"),
                self.tr("KDE Plasma MetaData .desktop"),
                self.tr("Ubuntu Unity QuickList .desktop"),
            ]
        )

        self.kdeCategoryComboBox.addItems(
            [
                "",
                "Application Launchers",
                "Accessibility",
                "Astronomy",
                "Date and Time",
                "Development Tools",
                "Education",
                "Environment",
                "Examples",
                "File System",
                "Fun and Games",
                "Graphics",
                "Language",
                "Mapping",
                "Multimedia",
                "Online Services",
                "System Information",
                "Utilities",
                "Windows and Tasks",
                "Miscelaneous",
            ]
        )

        self.kdeApiComboBox.addItems(
            ["Python", "Javascript", "Ruby", "C++", "HTML5", "QML"]
        )

        self.kdeEncodingComboBox.addItems(sorted(Utilities.supportedCodecs))
        self.kdeEncodingComboBox.setCurrentIndex(
            self.kdeEncodingComboBox.findText("utf-8")
        )

        projectOpen = ericApp().getObject("Project").isOpen()
        self.projectButton.setEnabled(projectOpen)

        icon = EricPixmapCache.getIcon("listSelection")
        self.categoriesButton.setIcon(icon)
        self.onlyShowButton.setIcon(icon)
        self.notShowButton.setIcon(icon)

    def getCode(self):
        """
        Public method to get the source code.

        @return generated code
        @rtype str
        """
        # step 1: standard desktop entries
        code = [
            "[Desktop Entry]",
            "Type=" + self.typeEdit.text(),
        ]
        if self.versionEdit.text():
            code.append("Version=" + self.versionEdit.text())
        code.append("Name=" + self.nameEdit.text())
        if self.genericNameEdit.text():
            code.append("GenericName=" + self.genericNameEdit.text())
        if self.commentEdit.text():
            code.append("Comment=" + self.commentEdit.text())
        if self.iconFileEdit.text():
            code.append("Icon=" + self.iconFileEdit.text())
        if self.onlyShowEdit.text():
            code.append("OnlyShowIn=" + self.onlyShowEdit.text())
        if self.notShowEdit.text():
            code.append("NotShowIn=" + self.notShowEdit.text())
        if self.tryExecEdit.text():
            code.append("TryExec=" + self.tryExecEdit.text())
        if self.execEdit.text():
            code.append("Exec=" + self.execEdit.text())
        if self.pathEdit.text():
            code.append("Path=" + self.pathEdit.text())
        if self.terminalCheckBox.isChecked():
            code.append("Terminal=true")
        if self.actionsEdit.text():
            code.append("Actions=" + self.actionsEdit.text())
        if self.mimetypeEdit.text():
            code.append("MimeType=" + self.mimetypeEdit.text())
        if self.categoriesEdit.text():
            code.append("Categories=" + self.categoriesEdit.text())

        # step 2a: KDE Plasma entries
        if self.typeComboBox.currentIndex() == 1:
            if self.kdeEncodingComboBox.currentText():
                code.append("Encoding=" + self.kdeEncodingComboBox.currentText())
            if self.kdeServiceTypeEdit.text():
                code.append("ServiceTypes=" + self.kdeServiceTypeEdit.text())
            if self.kdeApiComboBox.currentText():
                code.append("X-Plasma-API=" + self.kdeApiComboBox.currentText())
            if self.kdeMainScriptEdit.text():
                code.append("X-Plasma-MainScript=" + self.kdeMainScriptEdit.text())
            if self.kdeAuthorEdit.text():
                code.append("X-KDE-PluginInfo-Author=" + self.kdeAuthorEdit.text())
            if self.kdeEmailEdit.text():
                code.append("X-KDE-PluginInfo-Email=" + self.kdeEmailEdit.text())
            if self.kdeNameEdit.text():
                code.append("X-KDE-PluginInfo-Name=" + self.kdeNameEdit.text())
            if self.kdeVersionEdit.text():
                code.append("X-KDE-PluginInfo-Version=" + self.kdeVersionEdit.text())
            if self.kdeWebsiteEdit.text():
                code.append("X-KDE-PluginInfo-Website=" + self.kdeWebsiteEdit.text())
            if self.kdeCategoryComboBox.currentText():
                code.append(
                    "X-KDE-PluginInfo-Category="
                    + self.kdeCategoryComboBox.currentText()
                )
            if self.kdeDependsEdit.text():
                code.append("X-KDE-PluginInfo-Depends=" + self.kdeDependsEdit.text())
            if self.kdeLicensEdit.text():
                code.append("X-KDE-PluginInfo-License=" + self.kdeLicensEdit.text())
            if self.kdeEnabledDefaultCheckBox.isChecked():
                code.append("X-KDE-PluginInfo-EnabledByDefault=true")

        # step 2b: Unity entries
        if self.typeComboBox.currentIndex() == 2 and self.unityShortcutsEdit.text():
            code.append("X-Ayatana-Desktop-Shortcuts=" + self.unityShortcutsEdit.text())

        # step 3: action entries
        actions = [act for act in self.actionsEdit.text().split(";") if act]
        for act in actions:
            code.append("")
            code.append("[Desktop Action {0}]".format(act))
            code.append("Name={0}".format(act))
            code.append("Icon=<Icon Path>")
            code.append("Exec=<Executable command>")

        # step 4: add empty last line
        code.append("")

        return os.linesep.join(code)

    def __checkOK(self):
        """
        Private slot to check, if the OK button should be enabled.
        """
        enable = bool(self.nameEdit.text()) and bool(self.typeEdit.text())
        if bool(self.onlyShowEdit.text()) and bool(self.notShowEdit.text()):
            enable = False
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(int)
    def on_typeComboBox_currentIndexChanged(self, index):
        """
        Private slot to handle a change of the .desktop type.

        @param index index of the selected entry
        @type int
        """
        self.dataTabWidget.setTabEnabled(1, index == 1)
        self.dataTabWidget.setTabEnabled(2, index == 2)

    @pyqtSlot()
    def on_projectButton_clicked(self):
        """
        Private slot to populate some fields with data retrieved from the
        current project.
        """
        project = ericApp().getObject("Project")

        self.nameEdit.setText(project.getProjectName())
        self.genericNameEdit.setText(project.getProjectName())
        self.kdeNameEdit.setText(project.getProjectName())
        try:
            self.kdeVersionEdit.setText(project.getProjectVersion())
            self.kdeAuthorEdit.setText(project.getProjectAuthor())
            self.kdeEmailEdit.setText(project.getProjectAuthorEmail())
        except AttributeError:
            self.kdeVersionEdit.setText(project.getProjectData(dataKey="VERSION")[0])
            self.kdeAuthorEdit.setText(project.getProjectData(dataKey="AUTHOR")[0])
            self.kdeEmailEdit.setText(project.getProjectData(dataKey="EMAIL")[0])
        mainscript = project.getMainScript(True)
        if mainscript:
            self.kdeMainScriptEdit.setText(mainscript)
            self.execEdit.setText(mainscript)
            self.tryExecEdit.setText(mainscript)

        # prevent overwriting of entries by disabling the button
        self.projectButton.setEnabled(False)

    @pyqtSlot()
    def on_categoriesButton_clicked(self):
        """
        Private slot to select the categories.
        """
        from .DotDesktopListSelectionDialog import DotDesktopListSelectionDialog

        dlg = DotDesktopListSelectionDialog(
            self.__mainCategories,
            self.categoriesEdit.text(),
            ";",
            subEntries=self.__subCategories,
            allowMultiMain=False,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            categories = dlg.getData(";", True)
            self.categoriesEdit.setText(categories)

    @pyqtSlot(str)
    def on_onlyShowEdit_textChanged(self, _txt):
        """
        Private slot to check the contents of the onlyShowEdit field.

        @param _txt text of the entry field (unused)
        @type str
        """
        self.__checkOK()
        if bool(self.onlyShowEdit.text()) and bool(self.notShowEdit.text()):
            EricMessageBox.critical(
                self,
                self.tr(".desktop Wizard"),
                self.tr("""Only one of 'Only Show In' or  'Not Show In' allowed."""),
            )

    @pyqtSlot()
    def on_onlyShowButton_clicked(self):
        """
        Private slot to select the OnlyShowIn environments.
        """
        from .DotDesktopListSelectionDialog import DotDesktopListSelectionDialog

        dlg = DotDesktopListSelectionDialog(
            self.__showinEnvironments, self.onlyShowEdit.text(), ";", parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            environments = dlg.getData(";", True)
            self.onlyShowEdit.setText(environments)

    @pyqtSlot(str)
    def on_notShowEdit_textChanged(self, _txt):
        """
        Private slot to check the contents of the notShowEdit field.

        @param _txt text of the entry field (unused)
        @type str
        """
        self.__checkOK()
        if bool(self.onlyShowEdit.text()) and bool(self.notShowEdit.text()):
            EricMessageBox.critical(
                self,
                self.tr(".desktop Wizard"),
                self.tr("""Only one of 'Only Show In' or  'Not Show In' allowed."""),
            )

    @pyqtSlot()
    def on_notShowButton_clicked(self):
        """
        Private slot to select the NotShowIn environments.
        """
        from .DotDesktopListSelectionDialog import DotDesktopListSelectionDialog

        dlg = DotDesktopListSelectionDialog(
            self.__showinEnvironments, self.notShowEdit.text(), ";", parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            environments = dlg.getData(";", True)
            self.notShowEdit.setText(environments)

    @pyqtSlot(str)
    def on_typeEdit_textChanged(self, _txt):
        """
        Private slot to check, if the typeEdit field is empty.

        @param _txt text of the entry field (unused)
        @type str
        """
        self.__checkOK()

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, _txt):
        """
        Private slot to check, if the nameEdit field is empty.

        @param _txt text of the entry field (unused)
        @type str
        """
        self.__checkOK()
