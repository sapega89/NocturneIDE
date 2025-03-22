# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module containing some JavaScript resources.
"""


bootstrap_js = """
var GM = {
    info: {
        script: {
            description: "",
            excludes: [],
            includes: [],
            matches: [],
            name: "",
            namespace: "",
            resources: {},
            'run-at': "document-end",
            version: ""
        },
        scriptMetaStr: "",
        scriptHandler: "eric Browser GreaseMonkey",
        version: "4.0"
    }
};
window.GM = GM;

function GM_info() {
    return GM.info;
}

function GM_xmlhttpRequest(/* object */ details) {
    details.method = details.method.toUpperCase() || "GET";

    if (!details.url) {
        throw("GM_xmlhttpRequest requires an URL.");
    }

    // build XMLHttpRequest object
    var oXhr = new XMLHttpRequest;
    // run it
    if("onreadystatechange" in details)
        oXhr.onreadystatechange = function() {
            details.onreadystatechange(oXhr) };
    if("onload" in details)
        oXhr.onload = function() { details.onload(oXhr) };
    if("onerror" in details)
        oXhr.onerror = function() { details.onerror(oXhr) };

    oXhr.open(details.method, details.url, true);

    if("headers" in details)
        for(var header in details.headers)
            oXhr.setRequestHeader(header, details.headers[header]);

    if("data" in details)
        oXhr.send(details.data);
    else
        oXhr.send();
}

function GM_addStyle(/* string */ styles) {
    var head = document.getElementsByTagName("head")[0];
    if (head === undefined) {
        document.onreadystatechange = function() {
            if (document.readyState == "interactive") {
                var oStyle = document.createElement("style");
                oStyle.setAttribute("type", "text/css");
                oStyle.appendChild(document.createTextNode(styles));
                document.getElementsByTagName("head")[0].appendChild(oStyle);
            }
        }
    }
    else {
        var oStyle = document.createElement("style");
        oStyle.setAttribute("type", "text/css");
        oStyle.appendChild(document.createTextNode(styles));
        head.appendChild(oStyle);
    }
}

function GM_log(log) {
    if(console)
        console.log(log);
}

function GM_openInTab(url) {
    return window.open(url);
}

function GM_setClipboard(text) {
    external.extra.greasemonkey.setClipboard(text);
}

// GM_registerMenuCommand not supported
function GM_registerMenuCommand(caption, commandFunc, accessKey) { }

// GM_getResourceUrl not supported
function GM_getResourceUrl(resourceName) { }

// GreaseMonkey 4.0 support
GM.openInTab = GM_openInTab;
GM.setClipboard = GM_setClipboard;
GM.xmlhttpRequest = GM_xmlhttpRequest;

// GM_getResourceUrl not supported
GM.getResourceUrl = function(resourceName) {
    return new Promise((resolve, reject) => {
        reject();
    });
};
"""


# {0} - unique script id
values_js = """
function GM_deleteValue(aKey) {{
    localStorage.removeItem("{0}" + aKey);
}}

function GM_getValue(aKey, aDefault) {{
    var val = localStorage.getItem("{0}" + aKey)
    if (null === val) return aDefault;
    return val;
}}

function GM_listValues() {{
    var values = [];
    for (var i = 0; i < localStorage.length; i++) {{
        var k = localStorage.key(i);
        if (k.indexOf("{0}") === 0) {{
            values.push(k.replace("{0}", ""));
        }}
    }}
    return values;
}}

function GM_setValue(aKey, aVal) {{
    localStorage.setItem("{0}" + aKey, aVal);
}}

// GreaseMonkey 4.0 support
var asyncCall = (func) => {{
    if (window._eric_external) {{
        func();
    }} else {{
        document.addEventListener("_eric_external_created", func);
    }}
}};

var decode = (val) => {{
    val = String(val);
    if (!val.length) {{
        return val;
    }}
    var v = val.substr(1);
    if (val[0] == "b") {{
        return Boolean(v == "true" ? true : false);
    }} else if (val[0] == "i") {{
        return Number(v);
    }} else if (val[0] == "s") {{
        return v;
    }} else {{
        return undefined;
    }}
}};

var encode = (val) => {{
    if (typeof val == "boolean") {{
        return "b" + (val ? "true" : "false");
    }} else if (typeof val == "number") {{
        return "i" + String(val);
    }} else if (typeof val == "string") {{
        return "s" + val;
    }} else {{
        return "";
    }}
}};

GM.deleteValue = function(name) {{
    return new Promise((resolve, reject) => {{
        asyncCall(() => {{
            external.extra.greasemonkey.deleteValue("{0}", name, (res) => {{
                if (res) {{
                    resolve();
                }} else {{
                    reject();
                }}
            }});
        }});
    }});
}};

GM.getValue = function(name, value) {{
    return new Promise((resolve) => {{
        asyncCall(() => {{
            external.extra.greasemonkey.getValue("{0}", name, encode(value),
                                                 (res) => {{
                resolve(decode(res));
            }});
        }});
    }});
}};

GM.setValue = function(name, value) {{
    return new Promise((resolve, reject) => {{
        asyncCall(() => {{
            external.extra.greasemonkey.setValue("{0}", name, encode(value),
                                                 (res) => {{
                if (res) {{
                    resolve();
                }} else {{
                    reject();
                }}
            }});
        }});
    }});
}};

GM.listValues = function() {{
    return new Promise((resolve) => {{
        asyncCall(() => {{
            external.extra.greasemonkey.listValues("{0}", resolve);
        }});
    }});
}};
"""
