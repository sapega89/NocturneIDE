# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the conda information dialog.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from eric7.EricGui import EricPixmapCache

from .Ui_CondaInfoDialog import Ui_CondaInfoDialog


class CondaInfoDialog(QDialog, Ui_CondaInfoDialog):
    """
    Class implementing the conda information dialog.
    """

    def __init__(self, infoDict, parent=None):
        """
        Constructor

        @param infoDict dictionary containing the information to be shown
        @type dict
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.iconLabel.setPixmap(EricPixmapCache.getPixmap("miniconda48"))

        # version information
        if "conda_version" in infoDict:
            self.condaVersionLabel.setText(infoDict["conda_version"])
        if "conda_build_version" in infoDict:
            self.condaBuildVersionLabel.setText(infoDict["conda_build_version"])
        if "conda_env_version" in infoDict:
            self.condaEnvVersionLabel.setText(infoDict["conda_env_version"])
        if "python_version" in infoDict:
            self.pythonVersionLabel.setText(infoDict["python_version"])

        # prefixes
        if "active_prefix" in infoDict or "active_prefix_name" in infoDict:
            if infoDict["active_prefix_name"] and infoDict["active_prefix"]:
                self.activeEnvironmentEdit.setText(
                    "{0} ({1})".format(
                        infoDict["active_prefix_name"], infoDict["active_prefix"]
                    )
                )
            elif infoDict["active_prefix"]:
                self.activeEnvironmentEdit.setText(infoDict["active_prefix"])
            elif infoDict["active_prefix_name"]:
                self.activeEnvironmentEdit.setText(infoDict["active_prefix_name"])
            else:
                self.activeEnvironmentEdit.setText(self.tr("None"))
        else:
            self.activeEnvironmentLabel.hide()
            self.activeEnvironmentEdit.hide()
        if "root_prefix" in infoDict:
            if "root_writable" in infoDict and infoDict["root_writable"]:
                self.baseEnvironmentEdit.setText(
                    self.tr("{0} (writable)").format(infoDict["root_prefix"])
                )
            else:
                self.baseEnvironmentEdit.setText(infoDict["root_prefix"])
        if "envs_dirs" in infoDict:
            self.envDirsEdit.setPlainText("\n".join(infoDict["envs_dirs"]))

        # configurations
        if "rc_path" in infoDict:
            self.userConfigEdit.setText(infoDict["rc_path"])
        if "user_rc_path" in infoDict:
            # overwrite with more specific info
            self.userConfigEdit.setText(infoDict["user_rc_path"])
        if "sys_rc_path" in infoDict:
            self.systemConfigEdit.setText(infoDict["sys_rc_path"])
        if "config_files" in infoDict:
            self.configurationsEdit.setPlainText("\n".join(infoDict["config_files"]))
        else:
            self.configurationsLabel.hide()
            self.configurationsEdit.hide()

        # channels
        if "channels" in infoDict:
            self.channelsEdit.setPlainText("\n".join(infoDict["channels"]))

        # various
        if "pkgs_dirs" in infoDict:
            self.cachesEdit.setPlainText("\n".join(infoDict["pkgs_dirs"]))
        if "platform" in infoDict:
            self.platformLabel.setText(infoDict["platform"])
        if "user_agent" in infoDict:
            self.useragentEdit.setText(infoDict["user_agent"])
        else:
            self.useragentLabel.hide()
            self.useragentEdit.hide()
        if "UID" in infoDict and "GID" in infoDict:
            self.uidGidDataLabel.setText(
                "{0}:{1}".format(infoDict["UID"], infoDict["GID"])
            )
        else:
            self.uidGidLabel.hide()
            self.uidGidDataLabel.hide()
        if "netrc_file" in infoDict:
            if infoDict["netrc_file"]:
                self.netrcEdit.setText(infoDict["netrc_file"])
            else:
                self.netrcEdit.setText(self.tr("None"))
        else:
            self.netrcLabel.hide()
            self.netrcEdit.hide()
        if "offline" in infoDict:
            self.offlineCheckBox.setChecked(infoDict["offline"])
