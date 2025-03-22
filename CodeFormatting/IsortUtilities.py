# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some utility functions for the isort import statement formatting
tool.
"""

import isort

from PyQt6.QtCore import QCoreApplication, pyqtSlot

from eric7.EricWidgets import EricMessageBox


@pyqtSlot()
def aboutIsort():
    """
    Slot to show an 'About isort' dialog.
    """
    EricMessageBox.information(
        None,
        QCoreApplication.translate("IsortUtilities", "About isort"),
        QCoreApplication.translate(
            "IsortUtilities",
            """<p><b>isort Version {0}</b></p>"""
            """<p><i>isort</i> is a Python utility / library to sort imports"""
            """ alphabetically, and automatically separated into sections and by"""
            """ type.</p>""",
        ).format(isort.__version__),
    )
