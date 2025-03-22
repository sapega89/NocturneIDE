# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the various plug-in templates.
"""

mainTemplate = '''# -*- coding: utf-8 -*-

# Copyright (c) {year} {author} <{email}>
#

"""
Module documentation goes here.
"""

{apiImports}\
from PyQt6.QtCore import QObject

{config0}\
# Start-Of-Header
__header__ = {{
    "name": "{name}",
    "author": "{author} <{email}>",
    "autoactivate": {autoactivate},
    "deactivateable": {deactivateable},
    "version": "{version}",
{onDemand}\
    "className": "{className}",
    "packageName": "{packageName}",
    "shortDescription": "{shortDescription}",
    "longDescription": (
        """{longDescription}"""
    ),
    "needsRestart": {needsRestart},
    "hasCompiledForms": {hasCompiledForms},
    "pyqtApi": 2,
}}
# End-Of-Header

error = ""  # noqa: U200


{modulesetup}\
{exeData}\
{apiFiles}\
{preview}\
{config1}\
{clearPrivateData}\
class {className}(QObject):
    """
    Class documentation goes here.
    """

{config2}\
    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UI.UserInterface
        """
        super().__init__(ui)
        self.__ui = ui

    def activate(self):
        """
        Public method to activate this plug-in.

        @return tuple of None and activation status
        @rtype bool
        """
        global error
        error = ""  # clear previous error

        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plug-in.
        """
        pass
{config3}\
{installDependencies}'''

configTemplate0 = """from eric7 import Preferences

"""

configTemplate1 = '''def pageCreationFunction(configDlg):
    """
    Function to create the Translator configuration page.

    @param configDlg reference to the configuration dialog
    @type ConfigurationWidget
    @return reference to the configuration page
    @rtype TranslatorPage
    """
    page = None  # change this line to create the configuration page
    return page


def getConfigData():
    """
    Function returning data as required by the configuration dialog.

    @return dictionary containing the relevant data
    @rtype dict
    """
    return {{
        "<unique key>": [
            "<display string>",
            "<pixmap filename>",
            pageCreationFunction,
            None,
            None,
        ],
    }}


def prepareUninstall():
    """
    Function to prepare for an un-installation.
    """
    Preferences.getSettings().remove({className}.PreferencesKey)


'''

configTemplate2 = """    PreferencesKey = "{preferencesKey}"

"""

configTemplate3 = '''
    def getPreferences(self, key):
        """
        Public method to retrieve the various settings values.

        @param key the key of the value to get
        @type str
        @return the requested setting value
        @rtype Any
        """
        return None

    def setPreferences(self, key, value):
        """
        Public method to store the various settings values.

        @param key the key of the setting to be set
        @type str
        @param value the value to be set
        @type Any
        """
        pass
'''

onDemandTemplate = """"    pluginType": "{pluginType}",
    "pluginTypename": "{pluginTypename}",
"""

previewPixmapTemplate = '''def previewPix():
    """
    Function to return a preview pixmap.

    @return preview pixmap
    @rtype QPixmap
    """
    from PyQt6.QtGui import QPixmap

    fname = "preview.png"
    return QPixmap(fname)


'''

exeDisplayDataListTemplate = '''def exeDisplayDataList():
    """
    Function to support the display of some executable info.

    @return list of dictionaries containing the data to query the presence of
        the executable
    @rtype list of dict
    """
    dataList = []
    data = {
        "programEntry": True,
        "header": "<translated header string>",
        "exe": "dummyExe",
        "versionCommand": "--version",
        "versionStartsWith": "dummyExe",
        "versionRe": "",
        "versionPosition": -1,
        "version": "",
        "versionCleanup": None,
        "exeModule": None,
    }
    for exePath in ["exe1", "exe2"]:
        data["exe"] = exePath
        data["versionStartsWith"] = "<identifier>"
        dataList.append(data.copy())
    return dataList


'''

exeDisplayDataTemplate = '''def exeDisplayData():
    """
    Function to support the display of some executable info.

    @return dictionary containing the data to query the presence of
        the executable
    @rtype dict
    """
    data = {
        "programEntry": True,
        "header": "<translated header string>",
        "exe": exe,
        "versionCommand": "--version",
        "versionStartsWith": "<identifier>",
        "versionRe": None,
        "versionPosition": -1,
        "version": "",
        "versionCleanup": None,
        "exeModule": None,
    }

    return data


'''

exeDisplayDataInfoTemplate = '''def exeDisplayData():
    """
    Function to support the display of some executable info.

    @return dictionary containing the data to be shown
    @rtype dict
    """
    data = {
        "programEntry": False,
        "header": "<translated header string>",
        "text": "<translated entry string>",
        "version": "",
    }

    return data


'''

moduleSetupTemplate = '''def moduleSetup():
    """
    Function to perform module level setup.
    """
    pass


'''

apiFilesTemplate = '''def apiFiles(language):
    """
    Function to return the API files made available by this plug-in.

    @param language language to get APIs for
    @type str
    @return list of API filenames
    @rtype list of str
    """
    if language in ("Python3", "Python"):
        apisDir = os.path.join(os.path.dirname(__file__), "APIs", "Python")
        apis = glob.glob(os.path.join(apisDir, "*.api"))
        apisDir = os.path.join(os.path.dirname(__file__), "APIs", "Python3")
        apis.extend(glob.glob(os.path.join(apisDir, "*.api")))
    else:
        apis = []
    return apis


'''

apiImportsTemplate = """import glob
import os

"""

installDependenciesTemplate = '''

def installDependencies(pipInstall):
    """
    Function to install dependencies of this plug-in.

    @param pipInstall function to be called with a list of package names.
    @type function
    """
    pass
'''

clearPrivateDataTemplate = '''def clearPrivateData():
    """
    Function to clear the private data of the plug-in.
    """
    pass


'''

#
# eflag: noqa = M841
