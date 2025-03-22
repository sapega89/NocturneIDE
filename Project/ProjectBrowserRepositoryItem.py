# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a data structure holding the data associated with a project browser
type.
"""

from dataclasses import dataclass
from typing import Callable

from .ProjectBaseBrowser import ProjectBaseBrowser


@dataclass
class ProjectBrowserRepositoryItem:
    """
    Class holding the data associated with a project browser type.
    """

    projectBrowser: ProjectBaseBrowser
    projectBrowserUserString: str
    priority: int  # should be 0..100
    fileCategory: str
    fileFilter: str
    getIcon: Callable
