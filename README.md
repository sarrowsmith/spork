Spork
=====

Motivation
----------

Spork is a "little language" designed to facilitate the extraction and
processing of data held in XML or HTML files. The intent is to fulfil a
similar role to AWK, but with structured rather than line-oriented data. It
can be run as a program, either explicitly or with a `#!` line, following the
pattern of awk implementations, or used as a Python library.

A spork is not quite a fork, and a rather poor spoon. The Spork language is
not quite a declarative language (compare it to XSLT) and would make a poor
choice for a general purpose language (especially when you consider that Spork
code consists of Python expressions, and you could just be writing in Python
instead). However, there are times when a spork is exactly the right tool for
the job.

Running spork requires two inputs: a Spork program and XML or HTML data. There
is no implicit output: any output must be explicitly generated by the spork
code or command line options.

Installation
------------

spork depends on three Python packages which are not part of the standard
library:

  * lxml (http://lxml.de/)
  * cssselect (https://pythonhosted.org/cssselect/)
  * tinycss (https://pythonhosted.org/tinycss/)

These are all availale on PyPI and can be installed with

```$ pip install lxml cssselect tinycss```

Alternatively, most Linux distributions will have their own versions of these
packages.

Once you have the dependencies installed:

Copy `sporklib.py` to somewhere on your `$PYTHONPATH`.

Copy `spork` to somewhere on your `$PATH` and ensure it is executable.

Usage
-----

```
$ spork --help
usage: spork [-h] (-f progfile | -e program-text) [-w] [-X] [-H] [-s tag] [-p]
             [-d] [--attribute-defaults] [--dtd-validation] [--allow-network]
             [--recover] [--remove-blank-text] [--leave-cdata]
             [--leave-entities] [--forget-ids] [--huge-tree]
             [file]

Spork is a mark-up scanning and processing language

positional arguments:
  file                  document to be processed (default stdin)

optional arguments:
  -h, --help            show this help message and exit
  -f progfile, --file progfile
                        filename of spork program
  -e program-text, --source program-text
                        text of spork program
  -w, --warn            warn of program parsing errors
  -X, --xml             attempt XML parsing of document
  -H, --html            attempt HTML parsing of document
  -s tag, --select tag  process selected elements from document
  -p, --print           print result(s)
  -d, --debug           display debugging information

Document parser options:
  These options only apply if -X/--xml or -H/--html are given.

  --attribute-defaults  read the DTD (if referenced by the document) and add
                        the default attributes from it
  --dtd-validation      validate while parsing (if a DTD was referenced)
  --allow-network       allow network access when looking up external
                        documents
  --recover             try hard to parse through broken XML
  --remove-blank-text   discard blank text nodes (ignorable whitespace)
                        between tags
  --leave-cdata         don't replace CDATA sections by normal text content
  --leave-entities      don't replace entities by their text value
  --forget-ids          don't collect XML IDs (can speed up parsing if IDs not
                        used)
  --huge-tree           support deep trees and very long text content.
                        WARNING: disables security restrictions
```

Documentation
-------------

A Spork program uses essentially the same format as a CSS stylesheet, with
declaration lists replaced by lists of Python expressions. This structure
looks a lot like an AWK program, which is one of the observations behind the
creation of Spork. Comments are denoted by `/* ... */` as with CSS, except
that the first line only of a Spork file may be a comment starting with `#` to
allow the `#!` mechanism to work. Note that a `#!` line must end with `-f` (as
with awk) to indicate the Spork program is to be read from this file. This
means that Spork code consists of a series of stanzas of the form:

```
selector {
    name: expression;
    ...
}
```

Each stanza is evaluated in turn the order presented (note that this is unlike
AWK, where the order of evaluation is determined by the data). For each element
in the input data which matches selector, the expressions in body of the stanza
is executed in the context of that element in the order presented. In general,
the value of the evaluated expression is attached to the variable name.

A selector may be `_`, in which case the stanza is evaluated with no contextual
element.

As well as stanzas of this form, import statements of the form:

```
@import module
```

are permitted. These work exactly like Python import statements, importing the
module into the environment in which the expressions in subsequent stanzas are
evaluated. The sys, os and etree modules are automatically available, so there
is no need to `@import` these. A complex Spork application may consist of a
series of Python modules driven from a single piece of Spork code which
`@import`s them. (The alternative is to drive the application from Python code
using the sporklib module to extract data.)

Spork assigns expression values to variables by appending the value to a list
with that variable name. This facilitates aggregating data from repeating
elements. The list is created when the variable is first assigned to, and
may be referenced in any subsequent expression. If the name given is `_`, the
name of the contextual element will be used for the variable name, with any
`-`s appearing in this name being replaced by `_`s. If both the selector and
name are `_` (*ie* there is no contextual element) then the expression is
evaluated and the result discarded.

Expressions can take one of three forms:

  1. If the expression is the name of a variable, or `[]`, or ends `[:]`, the
     value of the expression is copied to the named variable, rather than
     being appended.
  2. If the expression contains `#`, it is interpreted as the left-most element
     of a list comprehension over the named variable, with occurrences of `#`
     being replaced by the iterating variable. The named variable is replaced
     by the result.
  3. Otherwise, the expression is evaluated as a Python expression, and the
     result appended to the named variable.

If an expression contains `[]` but does not soley consist of it, the `[]` is
interpreted as `[-1]`, *ie* a subscript to the last element of an array,
including spork variables.

The values of attributes of the contextual element can be insterted into the
expression as literal strings prior to evaluation by writing `$attr` where
*`attr`* is the name of the attribute to be inserted. If the contextual
element has no attribute named *attr*, its ancestors are searched until one is
found, or the document root is reached in which case an empty string is
inserted. In the same way, literal string versions of the element tag, textual
content (including the text of all sub-elements), and XML representation can
be inserted using `$_TAG`, `$_TEXT` and `$_XML` respectively.

The environment in which an expression is evaluated consists of:
  * builtins, including print as a function
  * the `sys`, `os`, `json` and `etree` modules
  * any modules previously imported using `@import`
  * the Spork object running the code as `self`
  * the contextual element (if present) as `_`
  * variables assigned by spork as lists

Extra flow control within Spork code can be acheived by calling `self.exit()`.
With no arguments, it restarts execution of the current stanza with the next
matching contextual element (or moves on to the next stanza if there is no
such element). Otherwise, it may be called with one of the following:
  * `Spork.SELECTOR`: abandons processing the current stanza and moves on to
    the next.
  * `Spork.ELEMENT`: abandons all processing, but moves on to the next root
    element as selected by the `-s` option on the command line or using
    `select()`. If there was no `-s` option or `run()` was called instead of
    `select()`, it is equivalent to `Spork.PROGRAM`.
  * `Spork.PROGRAM`: abandons all processing and returns control to the
    caller. Note this difference between calling `self.exit(Spork.PROGRAM)`
    and `sys.exit(0)` (which exits the program immediately). In particular,
    using `self.exit(Spork.PROGRAM)` in a spork program called from the
    command line with `-p -s ...` means the `-p` will still apply to all
    selected elements completely processed up to the point at which it was
    called.

Examples
--------

https://en.wikipedia.org/wiki/XSLT gives examples of XML-to-XML and
XML-to-HTML transformations. These could be written in Spork as:

```
person>name {
    users: ($username, $_TEXT)
}

persons {
    root: etree.Element("root");
    users: setattr(etree.SubElement(root[], "name", username=#[0]), "text", #[1]);
    _: print(etree.tostring(root[], encoding="UTF-8", xml_declaration=True, pretty_print=True));
}
```
and:

```
name, family-name {
    _: $_TEXT
}

persons {
    persons: sorted(zip(family_name, name))[:];
    persons: "      <li>%s, %s</li>" % #;
    head: "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
    head: "<html xmlns=\"http://www.w3.org/1999/xhtml\">";
    head: "  <head> <title>Testing XML Example</title> </head>";
    head: "  <body>";
    head: "    <h1>Persons</h1>";
    head: "    <ul>";
    tail: "    </ul>";
    tail: "  </body>";
    tail: "</html>";
    _: print("\n".join(head + persons + tail));
}
```

API
---

spork is entirely implemented by the Python module sporklib, and running a
Spork program within a Python program is one way of creating more complex
applications than could be achieved in a pure Spork program. (The other is to
`@import` complex Python code into a Spork program.) After `import sporklib`
there are three steps involved:

  1. Create a `Spork` object with `sporklib.Spork(source)` where `source` is a
     file-like object containing the Spork program.
  2. Obtain an lxml.etree element to be processed by the spork program.
     Typically you will call the `get_root(document)` method on the `Spork`
     object created in step 1. Again, `document` is a file-like object.
     `get_root()` uses lxml.etree parsers (by default, it tries first the XML
     parser, then the HTML parser) to obtain the document root element and, in
     the case of XML documents, establish the namespaces in use.
  3. Call the `run()` or `select(selector)` methods on the `Spork` object.

`run()` runs the Spork program on the given element, or by default the
document root obtained from the last call to `get_root()` and returns a dict
representing the final state of the Spork variables. If the program is
terminated by calling `self.exit(Spork.PROGRAM)`, `run()` returns an empty
dict.

`select(selector)` selects the subelements of the given element (or document
root as obtained from `get_root()`) identified by the CSS selector `selector`
and runs the Spork program over each of these subelements in turn. It returns
a list of 2-tuples, where the first item in the tuple is a selected element
and the second item the dict of Spork variables resulting from running the
program over that element. If the program terminates by calling
`self.exit(Spork.ELEMENT)` then no tuple is added to the return value and
processing continues. If the program terminates by calling
`self.exit(Spork.PROGRAM)` then `select()` returns immediately with the
results obtained up to that point.

`selector(selector)` is the generator form of `select()`. In fact, `select()`
is currently implemented as

```
def select(self, selector, document=None):
    return list(self.selector(selector, document))
````

so unless you really need the list it is probably better to use `selector()`.

S. Arrowsmith 2015-01-27
