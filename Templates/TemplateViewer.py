# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a template viewer and associated classes.
"""

import datetime
import os
import pathlib
import re

from PyQt6.QtCore import QCoreApplication, Qt, pyqtSlot
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QTreeWidget, QTreeWidgetItem

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from .TemplatePropertiesDialog import TemplatePropertiesDialog
from .TemplatesFile import TemplatesFile


class TemplateGroup(QTreeWidgetItem):
    """
    Class implementing a template group.
    """

    def __init__(self, parent, name, language="All"):
        """
        Constructor

        @param parent parent widget of the template group
        @type QWidget
        @param name name of the group
        @type str
        @param language programming language for the group
        @type str
        """
        self.name = name
        self.language = language
        self.entries = {}

        super().__init__(parent, [name])

        if Preferences.getTemplates("ShowTooltip"):
            self.setToolTip(0, language)

    def setName(self, name):
        """
        Public method to update the name of the group.

        @param name name of the group
        @type str
        """
        self.name = name
        self.setText(0, name)

    def getName(self):
        """
        Public method to get the name of the group.

        @return name of the group
        @rtype str
        """
        return self.name

    def setLanguage(self, language):
        """
        Public method to update the name of the group.

        @param language programming language for the group
        @type str
        """
        self.language = language
        if Preferences.getTemplates("ShowTooltip"):
            self.setToolTip(0, language)

    def getLanguage(self):
        """
        Public method to get the name of the group.

        @return language of the group
        @rtype str
        """
        return self.language

    def addEntry(self, name, description, template, quiet=False):
        """
        Public method to add a template entry to this group.

        @param name name of the entry
        @type str
        @param description description of the entry to add
        @type str
        @param template template text of the entry
        @type str
        @param quiet flag indicating quiet operation
        @type bool
        """
        if name in self.entries:
            if not quiet:
                EricMessageBox.critical(
                    None,
                    QCoreApplication.translate("TemplateGroup", "Add Template"),
                    QCoreApplication.translate(
                        "TemplateGroup",
                        """<p>The group <b>{0}</b> already contains a"""
                        """ template named <b>{1}</b>.</p>""",
                    ).format(self.name, name),
                )
            return

        self.entries[name] = TemplateEntry(self, name, description, template)

        if Preferences.getTemplates("AutoOpenGroups") and not self.isExpanded():
            self.setExpanded(True)

    def removeEntry(self, name):
        """
        Public method to remove a template entry from this group.

        @param name name of the entry to be removed
        @type str
        """
        if name in self.entries:
            index = self.indexOfChild(self.entries[name])
            self.takeChild(index)
            del self.entries[name]

            if (
                len(self.entries) == 0
                and Preferences.getTemplates("AutoOpenGroups")
                and self.isExpanded()
            ):
                self.setExpanded(False)

    def removeAllEntries(self):
        """
        Public method to remove all template entries of this group.
        """
        for name in list(self.entries):
            self.removeEntry(name)

    def hasEntry(self, name):
        """
        Public method to check, if the group has an entry with the given name.

        @param name name of the entry to check for
        @type str
        @return flag indicating existence
        @rtype bool
        """
        return name in self.entries

    def getEntry(self, name):
        """
        Public method to get an entry.

        @param name name of the entry to retrieve
        @type str
        @return reference to the entry
        @rtype TemplateEntry
        """
        try:
            return self.entries[name]
        except KeyError:
            return None

    def getEntryNames(self, beginning):
        """
        Public method to get the names of all entries, who's name starts with
        the given string.

        @param beginning string denoting the beginning of the template name
        @type str
        @return list of entry names found
        @rtype list of str
        """
        names = []
        for name in self.entries:
            if name.startswith(beginning):
                names.append(name)

        return names

    def getAllEntries(self):
        """
        Public method to retrieve all entries.

        @return list of all entries
        @rtype list of TemplateEntry
        """
        return list(self.entries.values())


class TemplateEntry(QTreeWidgetItem):
    """
    Class immplementing a template entry.
    """

    def __init__(self, parent, name, description, templateText):
        """
        Constructor

        @param parent parent widget of the template entry
        @type QWidget
        @param name name of the entry
        @type str
        @param description descriptive text for the template
        @type str
        @param templateText text of the template entry
        @type str
        """
        self.name = name
        self.description = description
        self.template = templateText
        self.__extractVariables()

        super().__init__(parent, [self.__displayText()])
        if Preferences.getTemplates("ShowTooltip"):
            self.setToolTip(0, self.template)

    def __displayText(self):
        """
        Private method to generate the display text.

        @return display text
        @rtype str
        """
        txt = (
            "{0} - {1}".format(self.name, self.description)
            if self.description
            else self.name
        )
        return txt

    def setName(self, name):
        """
        Public method to update the name of the entry.

        @param name name of the entry
        @type str
        """
        self.name = name
        self.setText(0, self.__displayText())

    def getName(self):
        """
        Public method to get the name of the entry.

        @return name of the entry
        @rtype str
        """
        return self.name

    def setDescription(self, description):
        """
        Public method to update the description of the entry.

        @param description description of the entry
        @type str
        """
        self.description = description
        self.setText(0, self.__displayText())

    def getDescription(self):
        """
        Public method to get the description of the entry.

        @return description of the entry
        @rtype str
        """
        return self.description

    def getGroupName(self):
        """
        Public method to get the name of the group this entry belongs to.

        @return name of the group containing this entry
        @rtype str
        """
        return self.parent().getName()

    def setTemplateText(self, templateText):
        """
        Public method to update the template text.

        @param templateText text of the template entry
        @type str
        """
        self.template = templateText
        self.__extractVariables()
        if Preferences.getTemplates("ShowTooltip"):
            self.setToolTip(0, self.template)

    def getTemplateText(self):
        """
        Public method to get the template text.

        @return the template text
        @rtype str
        """
        return self.template

    def getExpandedText(self, varDict, indent):
        """
        Public method to get the template text with all variables expanded.

        @param varDict dictionary containing the texts of each variable
            with the variable name as key
        @type dict
        @param indent indentation of the line receiving he expanded
            template text
        @type str
        @return a tuple of the expanded template text, the number of lines
            and the length of the last line
        @rtype tuple of (str, int, int)
        """
        txt = self.template
        for var, val in varDict.items():
            txt = (
                self.__expandFormattedVariable(var, val, txt)
                if var in self.formatedVariables
                else txt.replace(var, val)
            )
        sepchar = Preferences.getTemplates("SeparatorChar")
        txt = txt.replace("{0}{1}".format(sepchar, sepchar), sepchar)
        prefix = "{0}{1}".format(os.linesep, indent)
        trailingEol = txt.endswith(os.linesep)
        lines = txt.splitlines()
        lineCount = len(lines)
        lineLen = len(lines[-1])
        txt = prefix.join(lines).lstrip()
        if trailingEol:
            txt = "{0}{1}".format(txt, os.linesep)
            lineCount += 1
            lineLen = 0
        return txt, lineCount, lineLen

    def __expandFormattedVariable(self, var, val, txt):
        """
        Private method to expand a template variable with special formatting.

        @param var template variable name
        @type str
        @param val value of the template variable
        @type str
        @param txt template text
        @type str
        @return expanded and formatted variable
        @rtype str
        """
        t = ""
        for line in txt.splitlines():
            ind = line.find(var)
            if ind >= 0:
                variableFormat = var[1:-1].split(":", 1)[1]
                if variableFormat == "rl":
                    prefix = line[:ind]
                    postfix = line[ind + len(var) :]
                    for v in val.splitlines():
                        t = "{0}{1}{2}{3}{4}".format(t, os.linesep, prefix, v, postfix)
                elif variableFormat == "ml":
                    indent = line.replace(line.lstrip(), "")
                    prefix = line[:ind]
                    postfix = line[ind + len(var) :]
                    for count, v in enumerate(val.splitlines()):
                        t = (
                            "{0}{1}{2}{3}".format(t, os.linesep, indent, v)
                            if count
                            else "{0}{1}{2}{3}".format(t, os.linesep, prefix, v)
                        )
                    t = "{0}{1}".format(t, postfix)
                else:
                    t = "{0}{1}{2}".format(t, os.linesep, line)
            else:
                t = "{0}{1}{2}".format(t, os.linesep, line)
        return "".join(t.splitlines(1)[1:])

    def getVariables(self):
        """
        Public method to get the list of variables.

        @return list of variables
        @rtype list of str
        """
        return self.variables

    def __extractVariables(self):
        """
        Private method to retrieve the list of variables.
        """
        sepchar = Preferences.getTemplates("SeparatorChar")
        variablesPattern = re.compile(
            r"""\{0}[a-zA-Z][a-zA-Z0-9_]*(?::(?:ml|rl))?\{1}""".format(sepchar, sepchar)
        )
        variables = variablesPattern.findall(self.template)
        self.variables = []
        self.formatedVariables = []
        for var in variables:
            if var not in self.variables:
                self.variables.append(var)
            if var.find(":") >= 0 and var not in self.formatedVariables:
                self.formatedVariables.append(var)


class TemplateViewer(QTreeWidget):
    """
    Class implementing the template viewer.
    """

    def __init__(self, parent, viewmanager):
        """
        Constructor

        @param parent the parent
        @type QWidget
        @param viewmanager reference to the viewmanager object
        @type ViewManager
        """
        super().__init__(parent)

        self.viewmanager = viewmanager
        self.groups = {}

        self.setHeaderLabels(["Template"])
        self.header().hide()
        self.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)

        self.__menu = QMenu(self)
        self.applyAct = self.__menu.addAction(
            self.tr("Apply"), self.__templateItemActivated
        )
        self.__menu.addSeparator()
        self.__menu.addAction(self.tr("Add entry..."), self.__addEntry)
        self.__menu.addAction(self.tr("Add group..."), self.__addGroup)
        self.__menu.addAction(self.tr("Edit..."), self.__edit)
        self.__menu.addAction(self.tr("Remove"), self.__remove)
        self.__menu.addSeparator()
        self.saveAct = self.__menu.addAction(self.tr("Save"), self.save)
        self.__menu.addAction(self.tr("Import..."), self.__import)
        self.__menu.addAction(self.tr("Export..."), self.__export)
        self.__menu.addAction(self.tr("Reload"), self.__reload)
        self.__menu.addSeparator()
        self.__menu.addAction(self.tr("Help about Templates..."), self.__showHelp)
        self.__menu.addSeparator()
        self.__menu.addAction(self.tr("Configure..."), self.__configure)

        self.__backMenu = QMenu(self)
        self.__backMenu.addAction(self.tr("Add group..."), self.__addGroup)
        self.__backMenu.addSeparator()
        self.bmSaveAct = self.__backMenu.addAction(self.tr("Save"), self.save)
        self.__backMenu.addAction(self.tr("Import..."), self.__import)
        self.bmExportAct = self.__backMenu.addAction(
            self.tr("Export..."), self.__export
        )
        self.__backMenu.addAction(self.tr("Reload"), self.__reload)
        self.__backMenu.addSeparator()
        self.__backMenu.addAction(self.tr("Help about Templates..."), self.__showHelp)
        self.__backMenu.addSeparator()
        self.__backMenu.addAction(self.tr("Configure..."), self.__configure)

        self.__activating = False
        self.__dirty = False

        self.__templatesFile = TemplatesFile(self)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)
        self.itemActivated.connect(self.__templateItemActivated)

        self.setWindowIcon(EricPixmapCache.getIcon("eric"))

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.sortItems(self.sortColumn(), self.header().sortIndicatorOrder())

    @pyqtSlot()
    @pyqtSlot(QTreeWidgetItem, int)
    def __templateItemActivated(self, itm=None, _col=0):
        """
        Private slot to handle the activation of an item.

        @param itm reference to the activated item
        @type QTreeWidgetItem
        @param _col column the item was activated in (unused)
        @type int
        """
        if not self.__activating:
            self.__activating = True
            itm = self.currentItem()
            if isinstance(itm, TemplateEntry):
                self.applyTemplate(itm)
            self.__activating = False

    def __showContextMenu(self, coord):
        """
        Private slot to show the context menu of the list.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        itm = self.itemAt(coord)
        coord = self.mapToGlobal(coord)
        if itm is None:
            self.bmSaveAct.setEnabled(self.__dirty)
            self.bmExportAct.setEnabled(self.topLevelItemCount() != 0)
            self.__backMenu.popup(coord)
        else:
            self.applyAct.setEnabled(
                self.viewmanager.activeWindow() is not None
                and isinstance(itm, TemplateEntry)
            )
            self.saveAct.setEnabled(self.__dirty)
            self.__menu.popup(coord)

    def __addEntry(self):
        """
        Private slot to handle the Add Entry context menu action.
        """
        itm = self.currentItem()
        groupName = (
            itm.getName() if isinstance(itm, TemplateGroup) else itm.getGroupName()
        )

        dlg = TemplatePropertiesDialog(parent=self)
        dlg.setSelectedGroup(groupName)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, description, groupName, template = dlg.getData()
            self.addEntry(groupName, name, description, template)
            self.__dirty = True

    def __addGroup(self):
        """
        Private slot to handle the Add Group context menu action.
        """
        dlg = TemplatePropertiesDialog(parent=self, groupMode=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, language = dlg.getData()
            self.addGroup(name, language)
            self.__dirty = True

    def __edit(self):
        """
        Private slot to handle the Edit context menu action.
        """
        itm = self.currentItem()
        editGroup = not isinstance(itm, TemplateEntry)

        dlg = TemplatePropertiesDialog(parent=self, groupMode=editGroup, itm=itm)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if editGroup:
                name, language = dlg.getData()
                self.changeGroup(itm.getName(), name, language)
            else:
                name, description, groupName, template = dlg.getData()
                self.changeEntry(itm, name, groupName, description, template)
            self.__dirty = True

    def __remove(self):
        """
        Private slot to handle the Remove context menu action.
        """
        itm = self.currentItem()
        res = EricMessageBox.yesNo(
            self,
            self.tr("Remove Template"),
            self.tr("""<p>Do you really want to remove <b>{0}</b>?</p>""").format(
                itm.getName()
            ),
        )
        if not res:
            return

        if isinstance(itm, TemplateGroup):
            self.removeGroup(itm)
        else:
            self.removeEntry(itm)
        self.__dirty = True

    def save(self):
        """
        Public slot to save the templates.
        """
        if self.__dirty:
            ok = self.writeTemplates()
            if ok:
                self.__dirty = False

    def __import(self):
        """
        Private slot to handle the Import context menu action.
        """
        fn = EricFileDialog.getOpenFileName(
            self,
            self.tr("Import Templates"),
            "",
            self.tr("Templates Files (*.ecj);;All Files (*)"),
        )

        if fn:
            self.readTemplates(fn)
            self.__dirty = True

    def __export(self):
        """
        Private slot to handle the Export context menu action.
        """
        fn, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Export Templates"),
            "",
            self.tr("Templates Files (*.ecj);;All Files (*)"),
            "",
            EricFileDialog.DontConfirmOverwrite,
        )

        if fn:
            fpath = pathlib.Path(fn)
            if not fpath.suffix:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fpath = fpath.with_suffix(ex)
            if fpath.exists():
                ok = EricMessageBox.yesNo(
                    self,
                    self.tr("Export Templates"),
                    self.tr(
                        """<p>The templates file <b>{0}</b> exists"""
                        """ already. Overwrite it?</p>"""
                    ).format(fpath),
                )
            else:
                ok = True

            if ok:
                self.writeTemplates(str(fpath))

    def __reload(self):
        """
        Private slot to reload the templates.
        """
        if self.__dirty:
            res = EricMessageBox.yesNo(
                self,
                self.tr("Reload Templates"),
                self.tr(
                    """The templates contain unsaved changes. Shall these"""
                    """ changes be discarded?"""
                ),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return

        self.clear()
        self.groups = {}

        self.readTemplates()

    def __showHelp(self):
        """
        Private method to show some help.
        """
        EricMessageBox.information(
            self,
            self.tr("Template Help"),
            self.tr(
                """<p><b>Template groups</b> are a means of grouping"""
                """ individual templates. Groups have an attribute that"""
                """ specifies, which programming language they apply for."""
                """ In order to add template entries, at least one group"""
                """ has to be defined.</p>"""
                """<p><b>Template entries</b> are the actual templates."""
                """ They are grouped by the template groups. Help about"""
                """ how to define them is available in the template edit"""
                """ dialog.</p>"""
            ),
        )

    def __getPredefinedVars(self):
        """
        Private method to return predefined variables.

        @return dictionary of predefined variables and their values
        @rtype dict
        """
        project = ericApp().getObject("Project")
        editor = self.viewmanager.activeWindow()
        now = datetime.datetime.now()  # noqa: M305
        sepchar = Preferences.getTemplates("SeparatorChar")
        keyfmt = sepchar + "{0}" + sepchar
        varValues = {
            keyfmt.format("date"): now.date().isoformat(),
            keyfmt.format("year"): str(now.date().year),
            keyfmt.format("time"): now.time().strftime("%H:%M:%S"),
        }

        if project.name:
            varValues[keyfmt.format("project_name")] = project.name

        if project.ppath:
            varValues[keyfmt.format("project_path")] = project.ppath

        path_name = editor.getFileName()
        if path_name:
            dir_name, file_name = os.path.split(path_name)
            base_name, ext = os.path.splitext(file_name)
            if ext:
                ext = ext[1:]
            path_name_rel = project.getRelativePath(path_name)
            dir_name_rel = project.getRelativePath(dir_name)
            varValues.update(
                {
                    keyfmt.format("path_name"): path_name,
                    keyfmt.format("path_name_rel"): path_name_rel,
                    keyfmt.format("dir_name"): dir_name,
                    keyfmt.format("dir_name_rel"): dir_name_rel,
                    keyfmt.format("file_name"): file_name,
                    keyfmt.format("base_name"): base_name,
                    keyfmt.format("ext"): ext,
                }
            )

        varValues[keyfmt.format("clipboard:ml")] = QApplication.clipboard().text()
        varValues[keyfmt.format("clipboard")] = QApplication.clipboard().text()

        if editor.hasSelectedText():
            varValues[keyfmt.format("cur_select:ml")] = editor.selectedText()
            varValues[keyfmt.format("cur_select")] = editor.selectedText()
        else:
            varValues[keyfmt.format("cur_select:ml")] = os.linesep
            varValues[keyfmt.format("cur_select")] = ""

        varValues[keyfmt.format("insertion")] = "i_n_s_e_r_t_i_o_n"

        varValues[keyfmt.format("select_start")] = "s_e_l_e_c_t_s_t_a_r_t"
        varValues[keyfmt.format("select_end")] = "s_e_l_e_c_t_e_n_d"

        return varValues

    def applyTemplate(self, itm):
        """
        Public method to apply the template.

        @param itm reference to the template item to apply
        @type TemplateEntry
        """
        from .TemplateMultipleVariablesDialog import TemplateMultipleVariablesDialog
        from .TemplateSingleVariableDialog import TemplateSingleVariableDialog

        editor = self.viewmanager.activeWindow()
        if editor is None:
            return

        ok = False
        variables = itm.getVariables()
        varValues = self.__getPredefinedVars()

        # Remove predefined variables from list so user doesn't have to fill
        # these values out in the dialog.
        for v in varValues:
            if v in variables:
                variables.remove(v)

        if variables:
            if Preferences.getTemplates("SingleDialog"):
                dlg = TemplateMultipleVariablesDialog(variables, parent=self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    varValues.update(dlg.getVariables())
                    ok = True
            else:
                for var in variables:
                    dlg = TemplateSingleVariableDialog(var, parent=self)
                    if dlg.exec() == QDialog.DialogCode.Accepted:
                        varValues[var] = dlg.getVariable()
                    else:
                        return
                    del dlg
                ok = True
        else:
            ok = True

        if ok:
            line = editor.text(editor.getCursorPosition()[0]).replace(os.linesep, "")
            indent = line.replace(line.lstrip(), "")
            txt, lines, count = itm.getExpandedText(varValues, indent)
            # It should be done in this way to allow undo
            editor.beginUndoAction()
            if editor.hasSelectedText():
                line, index = editor.getSelection()[0:2]
                editor.removeSelectedText()
            else:
                line, index = editor.getCursorPosition()

            if lines == 1:
                count += index
            else:
                if len(indent) > 0:
                    count += len(indent)

            if "i_n_s_e_r_t_i_o_n" in txt and "s_e_l_e_c_t" in txt:
                txt = "'Insertion and selection can not be in template together'"

            if "i_n_s_e_r_t_i_o_n" in txt:
                lines = 1
                for aline in txt.splitlines():
                    count = aline.find("i_n_s_e_r_t_i_o_n")
                    if count >= 0:
                        txt = txt.replace("i_n_s_e_r_t_i_o_n", "")
                        if lines == 1:
                            count += index
                        else:
                            if len(indent) > 0:
                                count += len(indent)
                        break
                    else:
                        lines += 1

            setselect = False
            if "s_e_l_e_c_t_s_t_a_r_t" in txt and "s_e_l_e_c_t_e_n_d" in txt:
                setselect = True
                linea = 1
                for aline in txt.splitlines():
                    posa = aline.find("s_e_l_e_c_t_s_t_a_r_t")
                    if posa >= 0:
                        txt = txt.replace("s_e_l_e_c_t_s_t_a_r_t", "")
                        break
                    else:
                        linea += 1
                lineb = 1
                for aline in txt.splitlines():
                    posb = aline.find("s_e_l_e_c_t_e_n_d")
                    if posb >= 0:
                        txt = txt.replace("s_e_l_e_c_t_e_n_d", "")
                        break
                    else:
                        lineb += 1

            editor.insert(txt)

            if setselect:
                editor.setSelection(line + linea - 1, posa, line + lineb - 1, posb)
            else:
                editor.setCursorPosition(line + lines - 1, count)

            editor.endUndoAction()
            editor.setFocus()

    def applyNamedTemplate(self, templateName, groupName=None):
        """
        Public method to apply a template given a template name.

        @param templateName name of the template item to apply
        @type str
        @param groupName name of the group to get the entry from. None or empty means
            to apply the first template found with the given name.
        @type str
        """
        if groupName:
            if self.hasGroup(groupName):
                groups = [self.groups[groupName]]
            else:
                return
        else:
            groups = list(self.groups.values())
        for group in groups:
            template = group.getEntry(templateName)
            if template is not None:
                self.applyTemplate(template)
                break

    def addEntry(self, groupName, name, description, template, quiet=False):
        """
        Public method to add a template entry.

        @param groupName name of the group to add to
        @type str
        @param name name of the entry to add
        @type str
        @param description description of the entry to add
        @type str
        @param template template text of the entry
        @type str
        @param quiet flag indicating quiet operation
        @type bool
        """
        self.groups[groupName].addEntry(name, description, template, quiet=quiet)
        self.__resort()

    def hasGroup(self, name):
        """
        Public method to check, if a group with the given name exists.

        @param name name of the group to be checked for
        @type str
        @return flag indicating an existing group
        @rtype bool
        """
        return name in self.groups

    def addGroup(self, name, language="All"):
        """
        Public method to add a group.

        @param name name of the group to be added
        @type str
        @param language programming language for the group
        @type str
        """
        if name not in self.groups:
            self.groups[name] = TemplateGroup(self, name, language)
        self.__resort()

    def changeGroup(self, oldname, newname, language="All"):
        """
        Public method to rename a group.

        @param oldname old name of the group
        @type str
        @param newname new name of the group
        @type str
        @param language programming language for the group
        @type str
        """
        if oldname != newname:
            if newname in self.groups:
                EricMessageBox.warning(
                    self,
                    self.tr("Edit Template Group"),
                    self.tr(
                        """<p>A template group with the name"""
                        """ <b>{0}</b> already exists.</p>"""
                    ).format(newname),
                )
                return

            self.groups[newname] = self.groups[oldname]
            del self.groups[oldname]
            self.groups[newname].setName(newname)

        self.groups[newname].setLanguage(language)
        self.__resort()

    def getAllGroups(self):
        """
        Public method to get all groups.

        @return list of all groups
        @rtype list of TemplateGroup
        """
        return list(self.groups.values())

    def getGroupNames(self):
        """
        Public method to get all group names.

        @return list of all group names
        @rtype list of str
        """
        groups = sorted(self.groups)
        return groups

    def removeGroup(self, itm):
        """
        Public method to remove a group.

        @param itm template group to be removed
        @type TemplateGroup
        """
        name = itm.getName()
        itm.removeAllEntries()
        index = self.indexOfTopLevelItem(itm)
        self.takeTopLevelItem(index)
        del self.groups[name]

    def removeEntry(self, itm):
        """
        Public method to remove a template entry.

        @param itm template entry to be removed
        @type TemplateEntry
        """
        groupName = itm.getGroupName()
        self.groups[groupName].removeEntry(itm.getName())

    def changeEntry(self, itm, name, groupName, description, template):
        """
        Public method to change a template entry.

        @param itm template entry to be changed
        @type TemplateEntry
        @param name new name for the entry
        @type str
        @param groupName name of the group the entry should belong to
        @type str
        @param description description of the entry
        @type str
        @param template template text of the entry
        @type str
        """
        if itm.getGroupName() != groupName:
            # move entry to another group
            self.groups[itm.getGroupName()].removeEntry(itm.getName())
            self.groups[groupName].addEntry(name, description, template)
            return

        if itm.getName() != name:
            # entry was renamed
            self.groups[groupName].removeEntry(itm.getName())
            self.groups[groupName].addEntry(name, description, template)
            return

        tmpl = self.groups[groupName].getEntry(name)
        tmpl.setDescription(description)
        tmpl.setTemplateText(template)
        self.__resort()

    def writeTemplates(self, filename=None):
        """
        Public method to write the templates data to a JSON file (.ecj).

        @param filename name of a templates file to write
        @type str
        @return flag indicating success
        @rtype bool
        """
        if filename is None:
            filename = os.path.join(EricUtilities.getConfigDir(), "eric7templates.ecj")

        return self.__templatesFile.writeFile(filename)

    def readTemplates(self, filename=None):
        """
        Public method to read in the templates file (.ecj).

        @param filename name of a templates file to read
        @type str
        """
        if filename is None:
            filename = os.path.join(EricUtilities.getConfigDir(), "eric7templates.ecj")
            if not os.path.exists(filename):
                return

        self.__templatesFile.readFile(filename)

        self.resizeColumnToContents(0)

    def __configure(self):
        """
        Private method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("templatesPage")

    def hasTemplate(self, entryName, groupName=None):
        """
        Public method to check, if an entry of the given name exists.

        @param entryName name of the entry to check for
        @type str
        @param groupName name of the group to check for the entry. None or empty means
            to check all groups.
        @type str
        @return flag indicating the existence
        @rtype bool
        """
        if groupName:
            if self.hasGroup(groupName):
                groups = [self.groups[groupName]]
            else:
                groups = []
        else:
            groups = list(self.groups.values())

        return any(group.hasEntry(entryName) for group in groups)

    def getTemplateNames(self, start, groupName=None):
        """
        Public method to get the names of templates starting with the
        given string.

        @param start start string of the name
        @type str
        @param groupName name of the group to get the entry from. None or empty
            means to look in all groups.
        @type str
        @return sorted list of matching template names
        @rtype list of str
        """
        names = []
        if groupName:
            if self.hasGroup(groupName):
                groups = [self.groups[groupName]]
            else:
                groups = []
        else:
            groups = list(self.groups.values())
        for group in groups:
            names.extend(group.getEntryNames(start))
        return sorted(names)
