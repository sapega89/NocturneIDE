# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing CSS styles for the Markdown preview.
"""

###########################################################################
## Styles for light window schemes below
###########################################################################

css_markdown_light = """
html {
    background-color: #ffffff;
}

body {
    background-color: #ffffff;
    color: #000000;
    font-family: sans-serif;
    font-size:12px;
    line-height:1.7;
    word-wrap:break-word
}

body>*:first-child {
    margin-top:0 !important
}

body>*:last-child {
    margin-bottom:0 !important
}

a.absent {
    color:#c00
}

a.anchor {
    display:block;
    padding-right:6px;
    padding-left:30px;
    margin-left:-30px;
    cursor:pointer;
    position:absolute;
    top:0;
    left:0;
    bottom:0
}

a.anchor:focus {
    outline:none
}

tt, code, pre {
    font-family: Consolas, "Liberation Mono", Courier, monospace;
    font-size: 12px;
}

h1, h2, h3, h4, h5, h6 {
    margin:1em 0 6px;
    padding:0;
    font-weight:bold;
    line-height:1.7;
    cursor:text;
    position:relative
}

h1 .octicon-link, h2 .octicon-link, h3 .octicon-link, h4 .octicon-link,
h5 .octicon-link, h6 .octicon-link {
    display:none;
    color: #000000;
}

h1:hover a.anchor, h2:hover a.anchor, h3:hover a.anchor, h4:hover a.anchor,
h5:hover a.anchor, h6:hover a.anchor {
    text-decoration:none;
    line-height:1;
    padding-left:8px;
    margin-left:-30px;
    top:15%
}

h1:hover a.anchor .octicon-link, h2:hover a.anchor .octicon-link,
h3:hover a.anchor .octicon-link, h4:hover a.anchor .octicon-link,
h5:hover a.anchor .octicon-link, h6:hover a.anchor .octicon-link {
    display:inline-block
}

h1 tt, h1 code, h2 tt, h2 code, h3 tt, h3 code, h4 tt, h4 code,
h5 tt, h5 code, h6 tt, h6 code {
    font-size:inherit
}

h1 {
    font-size:2em;
    border-bottom:1px solid #ddd
}

h2 {
    font-size:1.6em;
    border-bottom:1px solid #eee
}

h3 {
    font-size:1.4em
}

h4 {
    font-size:1.2em
}

h5 {
    font-size:1em
}

h6 {
    color:#777;
    font-size:1em
}

p, blockquote, ul, ol, dl, table, pre {
    margin:8px 0
}

hr {
    background: rgba(216, 216, 216, 1);
    border: 0 none;
    color: #ccc;
    height: 2px;
    padding: 0;
    margin: 8px 0;
}

ul, ol {
    padding-left:15px
}

ul.no-list, ul.task-list, ol.no-list, ol.task-list {
    list-style-type:none;
}

ul ul, ul ol, ol ol, ol ul {
    margin-top:0;
    margin-bottom:0
}


dl {
    padding:0
}

dl dt {
    font-size:14px;
    font-weight:bold;
    font-style:italic;
    padding:0;
    margin-top:8px
}

dl dd {
    margin-bottom:15px;
    padding:0 8px
}

blockquote {
    border-left:4px solid #DDD;
    padding:0 8px;
    color:#777
}

blockquote>:first-child {
    margin-top:0px
}

blockquote>:last-child {
    margin-bottom:0px
}

table {
    border-collapse: collapse;
    border-spacing: 0;
    overflow:auto;
    display:block
}

table th {
    font-weight:bold
}

table th, table td {
    border:1px solid #ddd;
    padding:3px 3px
}

table tr {
    border-top:1px solid #ccc;
    background-color: #ffffff;
}

table tr:nth-child(2n) {
    background-color:#f8f8f8;
}

img {
    max-width:100%;
    -moz-box-sizing:border-box;
    box-sizing:border-box
}

span.frame {
    display:block;
    overflow:hidden
}

span.frame>span {
    border:1px solid #ddd;
    display:block;
    float:left;
    overflow:hidden;
    margin:6px 0 0;
    padding:7px;
    width:auto
}

span.frame span img {
    display:block;
    float:left
}

span.frame span span {
    clear:both;
    color:#333333;
    display:block;
    padding:5px 0 0
}

span.align-center {
    display:block;
    overflow:hidden;
    clear:both
}

span.align-center>span {
    display:block;
    overflow:hidden;
    margin:6px auto 0;
    text-align:center
}

span.align-center span img {
    margin:0 auto;
    text-align:center
}

span.align-right {
    display:block;
    overflow:hidden;
    clear:both
}

span.align-right>span {
    display:block;
    overflow:hidden;
    margin:6px 0 0;
    text-align:right
}

span.align-right span img {
    margin:0;
    text-align:right
}

span.float-left {
    display:block;
    margin-right:6px;
    overflow:hidden;
    float:left
}

span.float-left span {
    margin:6px 0 0
}

span.float-right {
    display:block;
    margin-left:6px;
    overflow:hidden;
    float:right
}

span.float-right>span {
    display:block;
    overflow:hidden;
    margin:6px auto 0;
    text-align:right
}

code, tt {
    margin:0;
    border:1px solid #ddd;
    background-color:#f8f8f8;
    border-radius:3px;
    max-width:100%;
    display:inline-block;
    overflow:auto;
    vertical-align:middle;
    line-height:1.1;
    padding:0
}

code {
    white-space:nowrap
}

pre>code {
    margin:0;
    padding:0;
    white-space:pre;
    border:none;
    background:transparent
}

.highlight pre, pre {
    background-color:#f8f8f8;
    border:1px solid #ddd;
    font-size:12px;
    line-height:16px;
    overflow:auto;
    padding:6px 6px;
    border-radius:3px
}

pre {
    word-wrap:normal
}

pre code, pre tt {
    margin:0;
    padding:0;
    background-color:transparent;
    border:none;
    word-wrap:normal;
    max-width:initial;
    display:inline;
    overflow:initial;
    line-height:inherit
}

pre code:before, pre code:after, pre tt:before, pre tt:after {
    content:normal
}

kbd {
    border:1px solid gray;
    font-size:1.2em;
    box-shadow:1px 0 1px 0 #eee, 0 1px 0 1px #ccc, 0 2px 0 2px #444;
    -webkit-border-radius:2px;
    -moz-border-radius:2px;
    border-radius:2px;
    margin:2px 3px;
    padding:1px 5px;
    color: #000;
    background-color: #fff
}
"""


css_pygments_light = """
pre .hll { background-color: #ffffcc }

/* Comment */
pre .c { color: #999988; font-style: italic }

/* Error */
pre .err { color: #a61717; background-color: #e3d2d2 }

/* Keyword */
pre .k { font-weight: bold }

/* Operator */
pre .o { font-weight: bold }

/* Comment.Multiline */
pre .cm { color: #999988; font-style: italic }

/* Comment.Preproc */
pre .cp { color: #999999; font-weight: bold; font-style: italic }

/* Comment.Single */
pre .c1 { color: #999988; font-style: italic }

/* Comment.Special */
pre .cs { color: #999999; font-weight: bold; font-style: italic }

/* Generic.Deleted */
pre .gd { color: #000000; background-color: #ffdddd }

/* Generic.Emph */
pre .ge { font-style: italic }

/* Generic.Error */
pre .gr { color: #aa0000 }

/* Generic.Heading */
pre .gh { color: #999999 }

/* Generic.Inserted */
pre .gi { color: #000000; background-color: #ddffdd }

/* Generic.Output */
pre .go { color: #888888 }

/* Generic.Prompt */
pre .gp { color: #555555 }

/* Generic.Strong */
pre .gs { font-weight: bold }

/* Generic.Subheading */
pre .gu { color: #aaaaaa }

/* Generic.Traceback */
pre .gt { color: #aa0000 }

/* Keyword.Constant */
pre .kc { font-weight: bold }

/* Keyword.Declaration */
pre .kd { font-weight: bold }

/* Keyword.Namespace */
pre .kn { font-weight: bold }

/* Keyword.Pseudo */
pre .kp { font-weight: bold }

/* Keyword.Reserved */
pre .kr { font-weight: bold }

/* Keyword.Type */
pre .kt { color: #445588; font-weight: bold }

/* Literal.Number */
pre .m { color: #009999 }

/* Literal.String */
pre .s { color: #d01040 }

/* Name.Attribute */
pre .na { color: #008080 }

/* Name.Builtin */
pre .nb { color: #0086B3 }

/* Name.Class */
pre .nc { color: #445588; font-weight: bold }

/* Name.Constant */
pre .no { color: #008080 }

/* Name.Decorator */
pre .nd { color: #3c5d5d; font-weight: bold }

/* Name.Entity */
pre .ni { color: #800080 }

/* Name.Exception */
pre .ne { color: #990000; font-weight: bold }

/* Name.Function */
pre .nf { color: #990000; font-weight: bold }

/* Name.Label */
pre .nl { color: #990000; font-weight: bold }

/* Name.Namespace */
pre .nn { color: #555555 }

/* Name.Tag */
pre .nt { color: #000080 }

/* Name.Variable */
pre .nv { color: #008080 }

/* Operator.Word */
pre .ow { font-weight: bold }

/* Text.Whitespace */
pre .w { color: #bbbbbb }

/* Literal.Number.Float */
pre .mf { color: #009999 }

/* Literal.Number.Hex */
pre .mh { color: #009999 }

/* Literal.Number.Integer */
pre .mi { color: #009999 }

/* Literal.Number.Oct */
pre .mo { color: #009999 }

/* Literal.String.Backtick */
pre .sb { color: #d01040 }

/* Literal.String.Char */
pre .sc { color: #d01040 }

/* Literal.String.Doc */
pre .sd { color: #d01040 }

/* Literal.String.Double */
pre .s2 { color: #d01040 }

/* Literal.String.Escape */
pre .se { color: #d01040 }

/* Literal.String.Heredoc */
pre .sh { color: #d01040 }

/* Literal.String.Interpol */
pre .si { color: #d01040 }

/* Literal.String.Other */
pre .sx { color: #d01040 }

/* Literal.String.Regex */
pre .sr { color: #009926 }

/* Literal.String.Single */
pre .s1 { color: #d01040 }

/* Literal.String.Symbol */
pre .ss { color: #990073 }

/* Name.Builtin.Pseudo */
pre .bp { color: #999999 }

/* Name.Variable.Class */
pre .vc { color: #008080 }

/* Name.Variable.Global */
pre .vg { color: #008080 }

/* Name.Variable.Instance */
pre .vi { color: #008080 }

/* Literal.Number.Integer.Long */
pre .il { color: #009999 }

"""

###########################################################################
## Styles for dark window schemes below
###########################################################################

css_markdown_dark = """
html {
    background-color: #262626;
}

body {
    background-color: #262626);
    color: #ffffff;
    font-family: sans-serif;
    font-size:12px;
    line-height:1.7;
    word-wrap:break-word
}

body>*:first-child {
    margin-top:0 !important
}

body>*:last-child {
    margin-bottom:0 !important
}

a {
    color:#8ebfff
}

a.absent {
    color:#dd0000
}

a.anchor {
    display:block;
    padding-right:6px;
    padding-left:30px;
    margin-left:-30px;
    cursor:pointer;
    position:absolute;
    top:0;
    left:0;
    bottom:0
}

a.anchor:focus {
    outline:none
}

tt, code, pre {
    font-family: Consolas, "Liberation Mono", Courier, monospace;
    font-size: 12px;
}

h1, h2, h3, h4, h5, h6 {
    margin:1em 0 6px;
    padding:0;
    font-weight:bold;
    line-height:1.7;
    cursor:text;
    position:relative
}

h1 .octicon-link, h2 .octicon-link, h3 .octicon-link, h4 .octicon-link,
h5 .octicon-link, h6 .octicon-link {
    display:none;
    color: #ffffff;
}

h1:hover a.anchor, h2:hover a.anchor, h3:hover a.anchor, h4:hover a.anchor,
h5:hover a.anchor, h6:hover a.anchor {
    text-decoration:none;
    line-height:1;
    padding-left:8px;
    margin-left:-30px;
    top:15%
}

h1:hover a.anchor .octicon-link, h2:hover a.anchor .octicon-link,
h3:hover a.anchor .octicon-link, h4:hover a.anchor .octicon-link,
h5:hover a.anchor .octicon-link, h6:hover a.anchor .octicon-link {
    display:inline-block
}

h1 tt, h1 code, h2 tt, h2 code, h3 tt, h3 code, h4 tt, h4 code,
h5 tt, h5 code, h6 tt, h6 code {
    font-size:inherit
}

h1 {
    font-size:2em;
    border-bottom:1px solid #ddd
}

h2 {
    font-size:1.6em;
    border-bottom:1px solid #eee
}

h3 {
    font-size:1.4em
}

h4 {
    font-size:1.2em
}

h5 {
    font-size:1em
}

h6 {
    color:#aaaaaa;
    font-size:1em
}

p, blockquote, ul, ol, dl, table, pre {
    margin:8px 0
}

hr {
    background: rgba(120, 120, 120, 1);
    border: 0 none;
    color: #ccc;
    height: 2px;
    padding: 0;
    margin: 8px 0;
}

ul, ol {
    padding-left:15px
}

ul.no-list, ul.task-list, ol.no-list, ol.task-list {
    list-style-type:none;
}

ul ul, ul ol, ol ol, ol ul {
    margin-top:0;
    margin-bottom:0
}


dl {
    padding:0
}

dl dt {
    font-size:14px;
    font-weight:bold;
    font-style:italic;
    padding:0;
    margin-top:8px
}

dl dd {
    margin-bottom:15px;
    padding:0 8px
}

blockquote {
    border-left:4px solid #DDD;
    padding:0 8px;
    color:#aaaaaa
}

blockquote>:first-child {
    margin-top:0px
}

blockquote>:last-child {
    margin-bottom:0px
}

table {
    border-collapse: collapse;
    border-spacing: 0;
    overflow:auto;
    display:block
}

table th {
    font-weight:bold
}

table th, table td {
    border:1px solid #ddd;
    padding:3px 3px
}

table tr {
    border-top:1px solid #cccccc;
    background-color: #262626;
}

table tr:nth-child(2n) {
    background-color:#404040;
}

img {
    max-width:100%;
    -moz-box-sizing:border-box;
    box-sizing:border-box
}

span.frame {
    display:block;
    overflow:hidden
}

span.frame>span {
    border:1px solid #464646;
    display:block;
    float:left;
    overflow:hidden;
    margin:6px 0 0;
    padding:7px;
    width:auto
}

span.frame span img {
    display:block;
    float:left
}

span.frame span span {
    clear:both;
    color:#565656;
    display:block;
    padding:5px 0 0
}

span.align-center {
    display:block;
    overflow:hidden;
    clear:both
}

span.align-center>span {
    display:block;
    overflow:hidden;
    margin:6px auto 0;
    text-align:center
}

span.align-center span img {
    margin:0 auto;
    text-align:center
}

span.align-right {
    display:block;
    overflow:hidden;
    clear:both
}

span.align-right>span {
    display:block;
    overflow:hidden;
    margin:6px 0 0;
    text-align:right
}

span.align-right span img {
    margin:0;
    text-align:right
}

span.float-left {
    display:block;
    margin-right:6px;
    overflow:hidden;
    float:left
}

span.float-left span {
    margin:6px 0 0
}

span.float-right {
    display:block;
    margin-left:6px;
    overflow:hidden;
    float:right
}

span.float-right>span {
    display:block;
    overflow:hidden;
    margin:6px auto 0;
    text-align:right
}

code, tt {
    margin:0;
    border:1px solid #ddd;
    background-color:#404040;
    border-radius:3px;
    max-width:100%;
    display:inline-block;
    overflow:auto;
    vertical-align:middle;
    line-height:1.1;
    padding:0
}

code {
    white-space:nowrap
}

pre>code {
    margin:0;
    padding:0;
    white-space:pre;
    border:none;
    background:transparent
}

.highlight pre, pre {
    background-color:#404040;
    border:1px solid #ddd;
    font-size:12px;
    line-height:16px;
    overflow:auto;
    padding:6px 6px;
    border-radius:3px
}

pre {
    word-wrap:normal
}

pre code, pre tt {
    margin:0;
    padding:0;
    background-color:transparent;
    border:none;
    word-wrap:normal;
    max-width:initial;
    display:inline;
    overflow:initial;
    line-height:inherit
}

pre code:before, pre code:after, pre tt:before, pre tt:after {
    content:normal
}

kbd {
    border:1px solid gray;
    font-size:1.2em;
    box-shadow:1px 0 1px 0 #eee, 0 1px 0 1px #ccc, 0 2px 0 2px #444;
    -webkit-border-radius:2px;
    -moz-border-radius:2px;
    border-radius:2px;
    margin:2px 3px;
    padding:1px 5px;
    color: #000;
    background-color: #fff
}
"""


css_pygments_dark = """
pre .hll { background-color: #464646 }

/* Comment */
pre .c { color: #74cc66; font-style: italic }

/* Error */
pre .err { color: #a61717; background-color: #e3d2d2 }

/* Keyword */
pre .k { font-weight: bold }

/* Operator */
pre .o { font-weight: bold }

/* Comment.Multiline */
pre .cm { color: #74cc66; font-style: italic }

/* Comment.Preproc */
pre .cp { color: #74cc66; font-weight: bold; font-style: italic }

/* Comment.Single */
pre .c1 { color: #74cc66; font-style: italic }

/* Comment.Special */
pre .cs { color: #74cc66; font-weight: bold; font-style: italic }

/* Generic.Deleted */
pre .gd { color: #ffffff; background-color: #843d3d }

/* Generic.Emph */
pre .ge { font-style: italic }

/* Generic.Error */
pre .gr { color: #ff0000 }

/* Generic.Heading */
pre .gh { color: #dadada }

/* Generic.Inserted */
pre .gi { color: #ffffff; background-color: #4e8750 }

/* Generic.Output */
pre .go { color: #bbbbbb }

/* Generic.Prompt */
pre .gp { color: #999999 }

/* Generic.Strong */
pre .gs { font-weight: bold }

/* Generic.Subheading */
pre .gu { color: #dd60dd }

/* Generic.Traceback */
pre .gt { color: #ff0000 }

/* Keyword.Constant */
pre .kc { font-weight: bold }

/* Keyword.Declaration */
pre .kd { font-weight: bold }

/* Keyword.Namespace */
pre .kn { font-weight: bold }

/* Keyword.Pseudo */
pre .kp { font-weight: bold }

/* Keyword.Reserved */
pre .kr { font-weight: bold }

/* Keyword.Type */
pre .kt { color: #b3efad; font-weight: bold }

/* Literal.Number */
pre .m { color: #00c8c8 }

/* Literal.String */
pre .s { color: #f46b6b }

/* Name.Attribute */
pre .na { color: #b6d13b }

/* Name.Builtin */
pre .nb { color: #b3efad }

/* Name.Class */
pre .nc { color: #00aaff; font-weight: bold }

/* Name.Constant */
pre .no { color: #dd3131 }

/* Name.Decorator */
pre .nd { color: #e19bff; font-weight: bold }

/* Name.Entity */
pre .ni { color: #dedede }

/* Name.Exception */
pre .ne { color: #e75555; font-weight: bold }

/* Name.Function */
pre .nf { color: #00aaff; font-weight: bold }

/* Name.Label */
pre .nl { color: #e1e100; font-weight: bold }

/* Name.Namespace */
pre .nn { color: #00aaff }

/* Name.Tag */
pre .nt { color: #b3efad }

/* Name.Variable */
pre .nv { color: #00aaff }

/* Operator.Word */
pre .ow { font-weight: bold }

/* Text.Whitespace */
pre .w { color: #bbbbbb }

/* Literal.Number.Float */
pre .mf { color: #00aaff }

/* Literal.Number.Hex */
pre .mh { color: #00aaff }

/* Literal.Number.Integer */
pre .mi { color: #00aaff }

/* Literal.Number.Oct */
pre .mo { color: #00aaff }

/* Literal.String.Backtick */
pre .sb { color: #f46b6b }

/* Literal.String.Char */
pre .sc { color: #f46b6b }

/* Literal.String.Doc */
pre .sd { color: #f46b6b }

/* Literal.String.Double */
pre .s2 { color: #f46b6b }

/* Literal.String.Escape */
pre .se { color: #f46b6b }

/* Literal.String.Heredoc */
pre .sh { color: #f46b6b }

/* Literal.String.Interpol */
pre .si { color: #f46b6b }

/* Literal.String.Other */
pre .sx { color: #f46b6b }

/* Literal.String.Regex */
pre .sr { color: #bb6688 }

/* Literal.String.Single */
pre .s1 { color: #f46b6b }

/* Literal.String.Symbol */
pre .ss { color: #00aaff }

/* Name.Builtin.Pseudo */
pre .bp { color: #b3efad }

/* Name.Variable.Class */
pre .vc { color: #00aaff }

/* Name.Variable.Global */
pre .vg { color: #00aaff }

/* Name.Variable.Instance */
pre .vi { color: #00aaff }

/* Literal.Number.Integer.Long */
pre .il { color: #00c8c8 }

"""
