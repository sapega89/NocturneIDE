# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a data structure holding the data associated with a file type
category.
"""

from dataclasses import dataclass


@dataclass
class FileCategoryRepositoryItem:
    """
    Class holding the data associated with a file type category.
    """

    fileCategoryFilterTemplate: str
    fileCategoryUserString: str
    fileCategoryTyeString: str
    fileCategoryExtensions: list
