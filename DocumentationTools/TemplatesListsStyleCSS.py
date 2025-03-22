# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing templates for the documentation generator (lists style).
"""

#################################################
## Template for the CSS style sheet file       ##
#################################################

cssTemplate = """body {{
    color: {BodyColor};
    background: {BodyBgColor};
    margin: 0em 1em 10em 1em;
}}

h1 {{
    color: {Level1HeaderColor};
    background: {Level1HeaderBgColor};
}}

h2 {{
    color: {CFColor};
    background: {CFBgColor};
}}

h3 {{
    color: {Level2HeaderColor};
    background: {Level2HeaderBgColor};
}}

h4 {{
    color: {Level2HeaderColor};
    background: {Level2HeaderBgColor};
}}
    
a {{
    color: {LinkColor};
}}
"""

#################################################
##  Common templates for index and docu files  ##
#################################################

headerTemplate = """<!DOCTYPE html>
<html><head>
<title>{Title}</title>
<meta charset="UTF-8">
<link rel="stylesheet" href="styles.css">
</head>
<body>"""

footerTemplate = """
</body></html>
"""

#########################################
##  Templates for documentation files  ##
#########################################

moduleTemplate = """
<a NAME="top" ID="top"></a>
<h1>{Module}</h1>
{ModuleDescription}
<h3>Global Attributes</h3>
{GlobalsList}
<h3>Classes</h3>
{ClassList}
<h3>Functions</h3>
{FunctionList}
<hr />"""

rbFileTemplate = """
<a NAME="top" ID="top"></a>
<h1>{Module}</h1>
{ModuleDescription}
<h3>Global Attributes</h3>
{GlobalsList}
<h3>Classes</h3>
{ClassList}
<h3>Modules</h3>
{RbModulesList}
<h3>Functions</h3>
{FunctionList}
<hr />"""

classTemplate = """
<hr />
<a NAME="{Anchor}" ID="{Anchor}"></a>
<h2>{Class}</h2>
{ClassDescription}
<h3>Derived from</h3>
{ClassSuper}
<h3>Class Attributes</h3>
{GlobalsList}
<h3>Class Methods</h3>
{ClassMethodList}
<h3>Methods</h3>
{MethodList}
<h3>Static Methods</h3>
{StaticMethodList}
{MethodDetails}
<div align="right"><a href="#top">Up</a></div>
<hr />"""

methodTemplate = """
<a NAME="{Anchor}.{Method}" ID="{Anchor}.{Method}"></a>
<h4>{Class}.{Method}{MethodClassifier}</h4>
<b>{Method}</b>(<i>{Params}</i>)
{MethodDescription}"""

constructorTemplate = """
<a NAME="{Anchor}.{Method}" ID="{Anchor}.{Method}"></a>
<h4>{Class} (Constructor)</h4>
<b>{Class}</b>(<i>{Params}</i>)
{MethodDescription}"""

rbModuleTemplate = """
<hr />
<a NAME="{Anchor}" ID="{Anchor}"></a>
<h2>{Module}</h2>
{ModuleDescription}
<h3>Module Attributes</h3>
{GlobalsList}
<h3>Classes</h3>
{ClassesList}
<h3>Functions</h3>
{FunctionsList}
<hr />
{ClassesDetails}
{FunctionsDetails}
<div align="right"><a href="#top">Up</a></div>
<hr />"""

rbModulesClassTemplate = """
<a NAME="{Anchor}" ID="{Anchor}"></a>
<h2>{Class}</h2>
{ClassDescription}
<h3>Derived from</h3>
{ClassSuper}
<h3>Methods</h3>
{MethodList}
{MethodDetails}
<div align="right"><a href="#top">Up</a></div>
<hr />"""

functionTemplate = """
<hr />
<a NAME="{Anchor}" ID="{Anchor}"></a>
<h2>{Function}</h2>
<b>{Function}</b>(<i>{Params}</i>)
{FunctionDescription}
<div align="right"><a href="#top">Up</a></div>
<hr />"""

listTemplate = """<table>
{Entries}
</table>
"""

listEntryTemplate = """<tr>
<td><a href="#{Link}">{Name}</a></td>
<td>{Deprecated}{Description}</td>
</tr>"""

listEntryNoneTemplate = """<tr><td>None</td></tr>"""

listEntryDeprecatedTemplate = """<b>Deprecated.</b>"""

listEntrySimpleTemplate = """<tr><td>{Name}</td></tr>"""

paragraphTemplate = """<p>
{Lines}
</p>
"""

parametersListTemplate = """
<dl>
{Parameters}
</dl>"""

parametersListEntryTemplate = """
<dt><i>{Name}</i></dt>
<dd>
{Description}
</dd>"""

parameterTypesListEntryTemplate = """
<dt><i>{Name}</i> ({Type})</dt>
<dd>
{Description}
</dd>"""

returnsTemplate = """
<dl>
<dt>Return:</dt>
<dd>
{0}
</dd>
</dl>"""

returnTypesTemplate = """
<dl>
<dt>Return Type:</dt>
<dd>
{0}
</dd>
</dl>"""

yieldsTemplate = """
<dl>
<dt>Yield:</dt>
<dd>
{0}
</dd>
</dl>"""

yieldTypesTemplate = """
<dl>
<dt>Yield Type:</dt>
<dd>
{0}
</dd>
</dl>"""

exceptionsListTemplate = """
<dl>
{Exceptions}
</dl>"""

exceptionsListEntryTemplate = """
<dt>Raises <b>{Name}</b>:</dt>
<dd>
{Description}
</dd>"""

signalsListTemplate = """
<h3>Signals</h3>
<dl>
{Signals}
</dl>"""

signalsListEntryTemplate = """
<dt>{Name}</dt>
<dd>
{Description}
</dd>"""

eventsListTemplate = """
<h3>Events</h3>
<dl>
{Events}
</dl>"""

eventsListEntryTemplate = """
<dt>{Name}</dt>
<dd>
{Description}
</dd>"""

deprecatedTemplate = """
<p>
<b>Deprecated.</b>
{Lines}
</p>"""

authorInfoTemplate = """
<p>
<i>Author(s)</i>:
{Authors}
</p>"""

seeListTemplate = """
<dl>
<dt><b>See Also:</b></dt>
{Links}
</dl>"""

seeListEntryTemplate = """
<dd>
{Link}
</dd>"""

seeLinkTemplate = """<a {Link}"""

sinceInfoTemplate = """
<p>
<b>since</b> {Info}
</p>"""

#################################
##  Templates for index files  ##
#################################

indexBodyTemplate = """
<h1>{Title}</h1>
{Description}
{Subpackages}
{Modules}"""

indexListPackagesTemplate = """
<h3>Packages</h3>
<table>
{Entries}
</table>"""

indexListModulesTemplate = """
<h3>Modules</h3>
<table>
{Entries}
</table>"""

indexListEntryTemplate = """
<tr>
<td><a href="{Link}">{Name}</a></td>
<td>{Description}</td>
</tr>"""

#
# eflag: noqa = E122
