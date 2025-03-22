# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a previewer widget for HTML, Markdown and ReST files.
"""

import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
import threading

from PyQt6.QtCore import QEventLoop, QPoint, Qt, QThread, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QCursor, QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities


class PreviewerHTML(QWidget):
    """
    Class implementing a previewer widget for HTML, Markdown and ReST files.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__layout = QVBoxLayout(self)

        self.titleLabel = QLabel(self)
        self.titleLabel.setWordWrap(True)
        self.titleLabel.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        self.__layout.addWidget(self.titleLabel)

        self.__previewAvailable = True

        try:
            from PyQt6.QtWebEngineWidgets import (  # __IGNORE_WARNING_I10__
                QWebEngineView,
            )

            self.previewView = QWebEngineView(self)
            self.previewView.page().linkHovered.connect(self.__showLink)

            settings = self.previewView.settings()
            settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)
            # JavaScript needs to be enabled.
        except ImportError:
            self.__previewAvailable = False
            self.titleLabel.setText(
                self.tr(
                    "<b>HTML Preview is not available!<br/>"
                    "Install PyQt6-WebEngine.</b>"
                )
            )
            self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.__layout.addStretch()
            return

        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.previewView.sizePolicy().hasHeightForWidth())
        self.previewView.setSizePolicy(sizePolicy)
        self.previewView.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.previewView.setUrl(QUrl("about:blank"))
        self.__layout.addWidget(self.previewView)

        self.__footerLayout = QGridLayout()
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self.ssiCheckBox = QCheckBox(self.tr("Enable Server Side Includes"), self)
        self.ssiCheckBox.setToolTip(
            self.tr("Select to enable support for Server Side Includes")
        )
        self.ssiCheckBox.setSizePolicy(sizePolicy)
        self.__footerLayout.addWidget(self.ssiCheckBox, 1, 0)
        self.__htmlButton = QPushButton(self.tr("Copy HTML"), self)
        self.__htmlButton.setToolTip(
            self.tr("Press to copy the HTML text of the preview to the clipboard")
        )
        self.__htmlButton.setEnabled(False)
        self.__footerLayout.addWidget(self.__htmlButton, 1, 1)
        self.__layout.addLayout(self.__footerLayout)

        self.ssiCheckBox.clicked[bool].connect(self.on_ssiCheckBox_clicked)
        self.previewView.titleChanged.connect(self.on_previewView_titleChanged)
        self.__htmlButton.clicked.connect(self.on_htmlButton_clicked)

        self.ssiCheckBox.setChecked(Preferences.getUI("ShowFilePreviewSSI"))

        self.__scrollBarPositions = {}
        self.__vScrollBarAtEnd = {}
        self.__hScrollBarAtEnd = {}

        self.__processingThread = PreviewProcessingThread()
        self.__processingThread.htmlReady.connect(self.__setHtml)

        self.__previewedPath = None
        self.__previewedEditor = None
        self.__previewedHtml = ""

    def shutdown(self):
        """
        Public method to perform shutdown actions.
        """
        if self.__previewAvailable:
            self.__processingThread.wait()

    @pyqtSlot(bool)
    def on_ssiCheckBox_clicked(self, checked):
        """
        Private slot to enable/disable SSI.

        @param checked state of the checkbox
        @type bool
        """
        Preferences.setUI("ShowFilePreviewSSI", checked)
        self.processEditor()

    @pyqtSlot(str)
    def __showLink(self, urlStr):
        """
        Private slot to show the hovered link in a tooltip.

        @param urlStr hovered URL
        @type str
        """
        QToolTip.showText(QCursor.pos(), urlStr, self.previewView)

    def processEditor(self, editor=None):
        """
        Public slot to process an editor's text.

        @param editor editor to be processed
        @type Editor
        """
        if not self.__previewAvailable:
            return

        if editor is None:
            editor = self.__previewedEditor
        else:
            self.__previewedEditor = editor

        if editor is not None:
            fn = editor.getFileName()

            if fn:
                extension = os.path.normcase(os.path.splitext(fn)[1][1:])
            else:
                extension = ""
            if (
                extension in Preferences.getEditor("PreviewHtmlFileNameExtensions")
                or editor.getLanguage() == "HTML"
            ):
                language = "HTML"
            elif (
                extension in Preferences.getEditor("PreviewMarkdownFileNameExtensions")
                or editor.getLanguage().lower() == "markdown"
            ):
                language = "Markdown"
            elif (
                extension in Preferences.getEditor("PreviewRestFileNameExtensions")
                or editor.getLanguage().lower() == "restructuredtext"
            ):
                language = "ReST"
            else:
                self.__setHtml(
                    fn, self.tr("<p>No preview available for this type of file.</p>")
                )
                return

            if fn:
                rootPath = os.path.dirname(os.path.abspath(fn))
            else:
                rootPath = ""

            if bool(editor.text()):
                self.__processingThread.process(
                    fn,
                    language,
                    editor.text(),
                    self.ssiCheckBox.isChecked(),
                    rootPath,
                    Preferences.getEditor("PreviewRestUseSphinx"),
                    Preferences.getEditor("PreviewMarkdownNLtoBR"),
                    Preferences.getEditor("PreviewMarkdownUsePyMdownExtensions"),
                    Preferences.getEditor("PreviewMarkdownHTMLFormat"),
                    Preferences.getEditor("PreviewRestDocutilsHTMLFormat"),
                )

    def __setHtml(self, filePath, html, rootPath):
        """
        Private method to set the HTML to the view and restore the scroll bars
        positions.

        @param filePath file path of the previewed editor
        @type str
        @param html processed HTML text ready to be shown
        @type str
        @param rootPath path of the web site root
        @type str
        """
        self.__previewedPath = FileSystemUtilities.normcasepath(
            FileSystemUtilities.fromNativeSeparators(filePath)
        )
        self.__saveScrollBarPositions()
        self.previewView.page().loadFinished.connect(self.__restoreScrollBarPositions)
        if not filePath:
            filePath = "/"
        baseUrl = (
            QUrl.fromLocalFile(rootPath + "/index.html")
            if rootPath
            else QUrl.fromLocalFile(filePath)
        )
        self.__previewedHtml = html
        self.__htmlButton.setEnabled(bool(html))
        self.previewView.setHtml(html, baseUrl=baseUrl)
        if self.__previewedEditor:
            self.__previewedEditor.setFocus()

    @pyqtSlot(str)
    def on_previewView_titleChanged(self, title):
        """
        Private slot to handle a change of the title.

        @param title new title
        @type str
        """
        if title:
            self.titleLabel.setText(self.tr("Preview - {0}").format(title))
        else:
            self.titleLabel.setText(self.tr("Preview"))

    def __saveScrollBarPositions(self):
        """
        Private method to save scroll bar positions for a previewed editor.
        """
        try:
            pos = self.previewView.scrollPosition()
        except AttributeError:
            pos = self.__execJavaScript(
                "(function() {"
                "var res = {"
                "    x: 0,"
                "    y: 0,"
                "};"
                "res.x = window.scrollX;"
                "res.y = window.scrollY;"
                "return res;"
                "})()"
            )
            pos = QPoint(0, 0) if pos is None else QPoint(pos["x"], pos["y"])
        self.__scrollBarPositions[self.__previewedPath] = pos
        self.__hScrollBarAtEnd[self.__previewedPath] = False
        self.__vScrollBarAtEnd[self.__previewedPath] = False

    def __restoreScrollBarPositions(self):
        """
        Private method to restore scroll bar positions for a previewed editor.
        """
        if self.__previewedPath not in self.__scrollBarPositions:
            return

        pos = self.__scrollBarPositions[self.__previewedPath]
        self.previewView.page().runJavaScript(
            "window.scrollTo({0}, {1});".format(pos.x(), pos.y())
        )

    def __execJavaScript(self, script):
        """
        Private function to execute a JavaScript function Synchroneously.

        @param script JavaScript script source to be executed
        @type str
        @return result of the script
        @rtype depending upon script result
        """
        loop = QEventLoop()
        resultDict = {"res": None}

        def resultCallback(res, resDict=resultDict):
            if loop and loop.isRunning():
                resDict["res"] = res
                loop.quit()

        self.previewView.page().runJavaScript(script, resultCallback)

        loop.exec()
        return resultDict["res"]

    @pyqtSlot()
    def on_htmlButton_clicked(self):
        """
        Private slot to copy the HTML contents to the clipboard.
        """
        if self.__previewedHtml:
            QGuiApplication.clipboard().setText(self.__previewedHtml)


class PreviewProcessingThread(QThread):
    """
    Class implementing a thread to process some text into HTML usable by the
    previewer view.

    @signal htmlReady(str, str, str) emitted with the file name, the processed
        HTML and the web site root path to signal the availability of the
        processed HTML
    """

    htmlReady = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__()

        self.__lock = threading.Lock()

    def process(
        self,
        filePath,
        language,
        text,
        ssiEnabled,
        rootPath,
        useSphinx,
        convertNewLineToBreak,
        usePyMdownExtensions,
        markdownHtmlFormat,
        restDocutilsHtmlFormat,
    ):
        """
        Public method to convert the given text to HTML.

        @param filePath file path of the text
        @type str
        @param language language of the text
        @type str
        @param text text to be processed
        @type str
        @param ssiEnabled flag indicating to do some (limited) SSI processing
        @type bool
        @param rootPath root path to be used for SSI processing
        @type str
        @param useSphinx flag indicating to use Sphinx to generate the
            ReST preview
        @type bool
        @param convertNewLineToBreak flag indicating to convert new lines
            to HTML break (Markdown only)
        @type bool
        @param usePyMdownExtensions flag indicating to enable the PyMdown
            extensions, if they are available
        @type bool
        @param markdownHtmlFormat HTML format to be generated by markdown
        @type str
        @param restDocutilsHtmlFormat HTML format to be generated by docutils
        @type str
        """
        with self.__lock:
            self.__filePath = filePath
            self.__language = language
            self.__text = text
            self.__ssiEnabled = ssiEnabled
            self.__rootPath = rootPath
            self.__haveData = True
            self.__useSphinx = useSphinx
            self.__convertNewLineToBreak = convertNewLineToBreak
            self.__usePyMdownExtensions = usePyMdownExtensions
            self.__markdownHtmlFormat = markdownHtmlFormat
            self.__restDocutilsHtmlFormat = restDocutilsHtmlFormat
            if not self.isRunning():
                self.start(QThread.Priority.LowPriority)

    def run(self):
        """
        Public thread method to convert the stored data.
        """
        while True:
            # exits with break
            with self.__lock:
                filePath = self.__filePath
                language = self.__language
                text = self.__text
                ssiEnabled = self.__ssiEnabled
                rootPath = self.__rootPath
                useSphinx = self.__useSphinx
                convertNewLineToBreak = self.__convertNewLineToBreak
                usePyMdownExtensions = self.__usePyMdownExtensions
                markdownHtmlFormat = self.__markdownHtmlFormat
                restDocutilsHtmlFormat = self.__restDocutilsHtmlFormat

                self.__haveData = False

            html = self.__getHtml(
                language,
                text,
                ssiEnabled,
                filePath,
                rootPath,
                useSphinx,
                convertNewLineToBreak,
                usePyMdownExtensions,
                markdownHtmlFormat,
                restDocutilsHtmlFormat,
            )

            with self.__lock:
                if not self.__haveData:
                    self.htmlReady.emit(filePath, html, rootPath)
                    break
                # else - next iteration

    def __getHtml(
        self,
        language,
        text,
        ssiEnabled,
        filePath,
        rootPath,
        useSphinx,
        convertNewLineToBreak,
        usePyMdownExtensions,
        markdownHtmlFormat,
        restDocutilsHtmlFormat,
    ):
        """
        Private method to process the given text depending upon the given
        language.

        @param language language of the text
        @type str
        @param text to be processed
        @type str
        @param ssiEnabled flag indicating to do some (limited) SSI processing
        @type bool
        @param filePath file path of the text
        @type str
        @param rootPath root path to be used for SSI processing
        @type str
        @param useSphinx flag indicating to use Sphinx to generate the
            ReST preview
        @type bool
        @param convertNewLineToBreak flag indicating to convert new lines
            to HTML break (Markdown only)
        @type bool
        @param usePyMdownExtensions flag indicating to enable the PyMdown
            extensions, if they are available
        @type bool
        @param markdownHtmlFormat HTML format to be generated by markdown
        @type str
        @param restDocutilsHtmlFormat HTML format to be generated by docutils
        @type str
        @return processed HTML text
        @rtype str
        """
        if language == "HTML":
            if ssiEnabled:
                html = self.__processSSI(text, filePath, rootPath)
            else:
                html = text
            return self.__processRootPath(html, rootPath)
        elif language == "Markdown":
            return self.__convertMarkdown(
                text, convertNewLineToBreak, usePyMdownExtensions, markdownHtmlFormat
            )
        elif language == "ReST":
            return self.__convertReST(text, useSphinx, restDocutilsHtmlFormat)
        else:
            return self.tr("<p>No preview available for this type of file.</p>")

    def __processSSI(self, txt, filename, root):
        """
        Private method to process the given text for SSI statements.

        Note: Only a limited subset of SSI statements are supported.

        @param txt text to be processed
        @type str
        @param filename name of the file associated with the given text
        @type str
        @param root directory of the document root
        @type str
        @return processed HTML
        @rtype str
        """
        if not filename:
            return txt

        # SSI include
        incRe = re.compile(
            r"""<!--#include[ \t]+(virtual|file)=[\"']([^\"']+)[\"']\s*-->""",
            re.IGNORECASE,
        )
        baseDir = os.path.dirname(os.path.abspath(filename))
        docRoot = root if root != "" else baseDir
        while True:
            incMatch = incRe.search(txt)
            if incMatch is None:
                break

            if incMatch.group(1) == "virtual":
                incFile = FileSystemUtilities.normjoinpath(docRoot, incMatch.group(2))
            elif incMatch.group(1) == "file":
                incFile = FileSystemUtilities.normjoinpath(baseDir, incMatch.group(2))
            else:
                incFile = ""
            if os.path.exists(incFile):
                try:
                    with open(incFile, "r") as f:
                        incTxt = f.read()
                except OSError:
                    # remove SSI include
                    incTxt = ""
            else:
                # remove SSI include
                incTxt = ""
            txt = txt[: incMatch.start(0)] + incTxt + txt[incMatch.end(0) :]

        return txt

    def __processRootPath(self, txt, root):
        """
        Private method to adjust absolute references to the given root path.

        @param txt text to be processed
        @type str
        @param root directory of the document root
        @type str
        @return processed HTML
        @rtype str
        """
        if not root:
            return txt

        root = FileSystemUtilities.fromNativeSeparators(root)
        if not root.endswith("/"):
            root += "/"
        rootLen = len(root)

        refRe = re.compile(r"""(href|src)=[\\"']/([^\\"']+)[\\"']""", re.IGNORECASE)
        pos = 0
        while True:
            refMatch = refRe.search(txt, pos)
            if refMatch is None:
                break

            txt = (
                txt[: refMatch.start(0)]
                + refMatch.group(1)
                + '="'
                + root
                + refMatch.group(2)
                + '"'
                + txt[refMatch.end(0) :]
            )
            pos = refMatch.end(0) + rootLen

        return txt

    def __convertReST(self, text, useSphinx, restDocutilsHtmlFormat):
        """
        Private method to convert ReST text into HTML.

        @param text text to be processed
        @type str
        @param useSphinx flag indicating to use Sphinx to generate the
            ReST preview
        @type bool
        @param restDocutilsHtmlFormat HTML format to be generated by docutils
        @type str
        @return processed HTML
        @rtype str
        """
        if useSphinx:
            return self.__convertReSTSphinx(text)
        else:
            return self.__convertReSTDocutils(text, restDocutilsHtmlFormat)

    def __convertReSTSphinx(self, text):
        """
        Private method to convert ReST text into HTML using 'sphinx'.

        @param text text to be processed
        @type str
        @return processed HTML
        @rtype str
        """
        try:
            from sphinx.application import (  # __IGNORE_EXCEPTION__ __IGNORE_WARNING__
                Sphinx,
            )
        except ImportError:
            return self.tr(
                """<p>ReStructuredText preview requires the"""
                """ <b>sphinx</b> package.<br/>Install it with"""
                """ your package manager,'pip install Sphinx' or see"""
                """ <a href="http://pypi.python.org/pypi/Sphinx">"""
                """this page.</a></p>"""
                """<p>Alternatively you may disable Sphinx usage"""
                """ on the Editor, Filehandling configuration page.</p>"""
            )

        srcTempDir = tempfile.mkdtemp(prefix="eric-rest-src-")
        outTempDir = tempfile.mkdtemp(prefix="eric-rest-out-")
        doctreeTempDir = tempfile.mkdtemp(prefix="eric-rest-doctree-")
        try:
            filename = "sphinx_preview"
            basePath = os.path.join(srcTempDir, filename)
            with open(basePath + ".rst", "w", encoding="utf-8") as fh:
                fh.write(text)

            overrides = {
                "html_add_permalinks": False,
                "html_copy_source": False,
                "html_title": "Sphinx preview",
                "html_use_index": False,
                "html_use_modindex": False,
                "html_use_smartypants": True,
                "master_doc": filename,
            }
            app = Sphinx(
                srcdir=srcTempDir,
                confdir=None,
                outdir=outTempDir,
                doctreedir=doctreeTempDir,
                buildername="html",
                confoverrides=overrides,
                status=None,
                warning=io.StringIO(),
            )
            app.build(force_all=True, filenames=None)

            basePath = os.path.join(outTempDir, filename)
            with open(basePath + ".html", "r", encoding="utf-8") as fh:
                html = fh.read()
        finally:
            shutil.rmtree(srcTempDir)
            shutil.rmtree(outTempDir)
            shutil.rmtree(doctreeTempDir)

        return html

    def __convertReSTDocutils(self, text, htmlFormat):
        """
        Private method to convert ReST text into HTML using 'docutils'.

        @param text text to be processed
        @type str
        @param htmlFormat HTML format to be generated
        @type str
        @return processed HTML
        @rtype str
        """
        if "sphinx" in sys.modules:
            # Make sure any Sphinx polution of docutils has been removed.
            unloadKeys = [
                k for k in sys.modules if k.startswith(("docutils", "sphinx"))
            ]
            for key in unloadKeys:
                sys.modules.pop(key)

        try:
            import docutils.core  # __IGNORE_EXCEPTION__ __IGNORE_WARNING_I10__
            import docutils.utils  # __IGNORE_EXCEPTION__ __IGNORE_WARNING_I10__
        except ImportError:
            return self.tr(
                """<p>ReStructuredText preview requires the"""
                """ <b>python-docutils</b> package.<br/>Install it with"""
                """ your package manager, 'pip install docutils' or see"""
                """ <a href="http://pypi.python.org/pypi/docutils">"""
                """this page.</a></p>"""
            )

        # redirect sys.stderr because we are not interested in it here
        origStderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            html = docutils.core.publish_string(
                text, writer_name=htmlFormat.lower()
            ).decode("utf-8")
        except docutils.utils.SystemMessage as err:
            errStr = str(err).split(":")[-1].replace("\n", "<br/>")
            return self.tr("""<p>Docutils returned an error:</p><p>{0}</p>""").format(
                errStr
            )

        sys.stderr = origStderr
        return html

    def __convertMarkdown(
        self, text, convertNewLineToBreak, usePyMdownExtensions, htmlFormat
    ):
        """
        Private method to convert Markdown text into HTML.

        @param text text to be processed
        @type str
        @param convertNewLineToBreak flag indicating to convert new lines
            to HTML break (Markdown only)
        @type bool
        @param usePyMdownExtensions flag indicating to enable the PyMdown
            extensions, if they are available
        @type bool
        @param htmlFormat HTML format to be generated by markdown
        @type str
        @return processed HTML
        @rtype str
        """
        try:
            import markdown  # __IGNORE_EXCEPTION__ __IGNORE_WARNING_I10__
        except ImportError:
            return self.tr(
                """<p>Markdown preview requires the <b>Markdown</b> """
                """package.<br/>Install it with your package manager,"""
                """ 'pip install Markdown' or see """
                """<a href="http://pythonhosted.org/Markdown/install.html">"""
                """installation instructions.</a></p>"""
            )

        from . import MarkdownExtensions, PreviewerHTMLStyles  # __IGNORE_WARNING_I101__

        extensions = []

        mermaidNeeded = False
        if Preferences.getEditor(
            "PreviewMarkdownMermaid"
        ) and MarkdownExtensions.MermaidRegexFullText.search(text):
            extensions.append(MarkdownExtensions.MermaidExtension())
            mermaidNeeded = True

        if convertNewLineToBreak:
            extensions.append("nl2br")

        pyMdown = False
        if usePyMdownExtensions and bool(importlib.util.find_spec("pymdownx")):
            # PyPI package is 'pymdown-extensions'

            extensions.extend(
                [
                    "toc",
                    "pymdownx.extra",
                    "pymdownx.caret",
                    "pymdownx.emoji",
                    "pymdownx.mark",
                    "pymdownx.tilde",
                    "pymdownx.keys",
                    "pymdownx.tasklist",
                    "pymdownx.smartsymbols",
                ]
            )
            pyMdown = True

        if not pyMdown:
            extensions.extend(["extra", "toc"])
            extensions.append(MarkdownExtensions.SimplePatternExtension())

        if Preferences.getEditor("PreviewMarkdownMathJax"):
            mathjax = (
                "<script type='text/javascript' id='MathJax-script' async"
                " src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/"
                "tex-chtml.js'>\n"
                "</script>\n"
            )
            # prepare text for mathjax
            text = (
                text.replace(r"\(", r"\\(")
                .replace(r"\)", r"\\)")
                .replace(r"\[", r"\\[")
                .replace(r"\]", r"\\]")
            )
        else:
            mathjax = ""

        if mermaidNeeded:
            mermaid = (
                "<script type='text/javascript' id='Mermaid-script'"
                " src='https://unpkg.com/mermaid@8/dist/mermaid.min.js'>\n"
                "</script>\n"
            )
            if ericApp().usesDarkPalette():
                mermaid_initialize = (
                    "<script>mermaid.initialize({"
                    "theme: 'dark', "
                    "startOnLoad:true"
                    "});</script>"
                )
            else:
                mermaid_initialize = (
                    "<script>mermaid.initialize({"
                    "theme: 'default', "
                    "startOnLoad:true"
                    "});</script>"
                )
        else:
            mermaid = ""
            mermaid_initialize = ""

        htmlFormat = Preferences.getEditor("PreviewMarkdownHTMLFormat").lower()
        body = markdown.markdown(
            text, extensions=extensions, output_format=htmlFormat.lower()
        )
        style = (
            (
                PreviewerHTMLStyles.css_markdown_dark
                + PreviewerHTMLStyles.css_pygments_dark
            )
            if ericApp().usesDarkPalette()
            else (
                PreviewerHTMLStyles.css_markdown_light
                + PreviewerHTMLStyles.css_pygments_light
            )
        )

        if htmlFormat == "xhtml1":
            head = (
                """<!DOCTYPE html PUBLIC "-//W3C//DTD"""
                """ XHTML 1.0 Transitional//EN"\n"""
                """ "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional"""
                """.dtd">\n"""
                """<html xmlns="http://www.w3.org/1999/xhtml">\n"""
            )
        elif htmlFormat == "html5":
            head = """<!DOCTYPE html>\n<html lang="EN">\n"""
        else:
            head = '<html lang="EN">\n'
        head += """<head>\n"""
        head += (
            """<meta name="Generator" content="eric" />\n"""
            """<meta http-equiv="Content-Type" """
            """content="text/html; charset=utf-8" />\n"""
            """{0}"""
            """{1}"""
            """<style type="text/css">"""
            """{2}"""
            """</style>\n"""
            """</head>\n"""
            """<body>\n"""
        ).format(mathjax, mermaid, style)

        foot = """\n</body>\n</html>\n"""

        return head + body + mermaid_initialize + foot
