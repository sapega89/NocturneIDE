# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the UML diagram builder base class.
"""

from PyQt6.QtCore import QObject


class UMLDiagramBuilder(QObject):
    """
    Class implementing the UML diagram builder base class.
    """

    def __init__(self, dialog, view, project):
        """
        Constructor

        @param dialog reference to the UML dialog
        @type UMLDialog
        @param view reference to the view object
        @type UMLGraphicsView
        @param project reference to the project object
        @type Project
        """
        super().__init__(dialog)

        self.umlView = view
        self.scene = self.umlView.scene()
        self.project = project

    def initialize(self):
        """
        Public method to initialize the object.
        """
        return

    def buildErrorMessage(self, msg):
        """
        Public method to build an error string to be included in the scene.

        @param msg error message
        @type str
        @return prepared error string
        @rtype str
        """
        return (
            "<font color='{0}'>".format(self.umlView.getDrawingColors()[0].name())
            + msg
            + "</font>"
        )

    def buildDiagram(self):
        """
        Public method to build the diagram.

        This class must be implemented in subclasses.

        @exception NotImplementedError raised to indicate that this class
            must be subclassed
        """
        raise NotImplementedError(
            "Method 'buildDiagram' must be implemented in subclasses."
        )

    def parsePersistenceData(self, version, data):  # noqa: U100
        """
        Public method to parse persisted data.

        @param version version of the data (unused)
        @type str
        @param data persisted data to be parsed (unused)
        @type str
        @return flag indicating success
        @rtype bool
        """
        return True

    def toDict(self):
        """
        Public method to collect data to be persisted.

        @return dictionary containing data to be persisted
        @rtype dict
        """
        return {}

    def fromDict(self, version, data):  # noqa: U100
        """
        Public method to populate the class with data persisted by 'toDict()'.

        @param version version of the data (unused)
        @type str
        @param data dictionary containing the persisted data (unused)
        @type dict
        @return tuple containing a flag indicating success and an info
            message in case the diagram belongs to a different project
        @rtype tuple of (bool, str)
        """
        return True, ""
