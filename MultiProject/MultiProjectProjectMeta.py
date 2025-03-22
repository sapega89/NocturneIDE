# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module defining a class containing the individual project metadata.
"""

from dataclasses import asdict, dataclass


@dataclass
class MultiProjectProjectMeta:
    """
    Class containing the individual project metadata.
    """

    name: str  # name of the project
    file: str  # project file name
    uid: str  # unique identifier
    main: bool = False  # flag indicating the main project
    description: str = ""  # description of the project
    category: str = ""  # name of the group
    removed: bool = False  # flag indicating a (re-)moved project

    def as_dict(self):
        """
        Public method to convert the metadata into a dictionary.

        @return dictionary containing the metadata
        @rtype dict
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """
        Class method to create a metadata object from the given dictionary.

        @param data dictionary containing the metadata
        @type dict
        @return created project metadata object
        @rtype MultiProjectProjectMeta
        """
        return cls(
            name=data["name"],
            file=data["file"],
            uid=data["uid"],
            main=data.get("main", False),
            description=data.get("description", ""),
            category=data.get("category", ""),
            removed=data.get("removed", False),
        )
