spork is a "little language" designed to facilitate the extraction and processing of data held in XML or HTML files. The intent is to fulfil a similar role to AWK, but with structured rather than line-oriented data. It can be run as a program, either explicitly or with a #! line, following the pattern of awk implementations, or used as a Python library.

A spork is not quite a fork, and a rather poor spoon. The spork language is not quite a declarative language (compare it to XSLT) and would make a poor choice for a general purpose language (especially when you consider that spork code consists of Python expressions, and you could just be writing in Python instead). However, there are times when a spork is exactly the right tool for the job.

Running spork requires two inputs: spork code and XML or HTML data. There is no implicit output: any output must be explicitly generated by the spork code.

spork code uses essentially the same format as a CSS stylesheet, with declaration lists replaced by lists of Python expressions. This structure looks a lot like an AWK program, which is one of the observations behind the creation of spork. Comments are denoted by /* ... */ as with CSS, except that the first line only of a spork file may be a comment starting with # to allow the #! mechanism to work. Note that a #! line must end with -f (as with awk) to indicate the spork source is to be read from this file. This means that spork code consists of a series of stanzas of the form:

selector {
    name: expression;
    ...
}

Each stanza is evaluated in turn the order presented (note that this is unlike AWK, where the order of evaluation is determined by the data). For each element in the input data which matches selector, the expressions in body of the stanza is executed in the context of that element in the order presented. In general, the value of the evaluated expression is attached to the variable name.

A selector may be _, in which case the stanza is evaluated with no contextual element.

As well as stanzas of this form, import statements of the form:

@import module

are permitted. These work exactly like Python import statements, importing the module into the environment in which the expressions in subsequent stanzas are evaluated. The sys, os and etree modules are automatically available, so there is no need to @import these. A complex spork application may consist of a series of Python modules driven from a single piece of spork code which @imports them. (The alternative is to drive the application from Python code using the spork module to extract data.)

spork assigns expression values to variables by appending the value to a list with that variable name. This facilitates aggregating data from repeating elements. The list is created when the variable is first assigned to, and may be referenced in any subsequent expression. The exception to this is when name is _, in which case expression evaluation will occur but the value will be discarded.

Expressions can take one of three forms:

1. If the expression is the name of a variable, or [], or ends [:], the value of the expression is copied to the named variable, rather than being appended.

2. If the expression contains #, it is interpreted as the left-most element of a list comprehension over the named variable, with occurrences of # being replaced by the iterating variable. The named variable is replaced by the result.

3. Otherwise, the expression is evaluated as a Python expression, and the result appended to the named variable (unless it was _).

The values of attributes of the contextual element can be insterted into the expression as literal strings prior to evaluation by writing $attr where attr is the name of the attribute to be inserted. If the contextual element has no attribute named attr, its ancestors are searched until one is found, or the document root is reached in which case an empty string is inserted. In the same way, literal string versions of the element tag, textual content, and XML representation can be inserted using $_TAG, $_TEXT and $_XML respectively.

The environment in which an expression is evaluated consists of:
 * builtins, including print as a function
 * the sys, os and etree modules
 * any modules previously imported using @import
 * the Spork object running the code as self
 * the contextual element (if present) as _
 * variables assigned by spork as lists

Example:

https://en.wikipedia.org/wiki/XSLT gives examples of XML-to-XML and XML-to-HTML transformations. These could be written in spork as:

person>name {
    users: ($username, $_TEXT)
}

persons {
    root: etree.Element("root");
    users: setattr(etree.SubElement(root[0], "name", username=#[0]), "text", #[1]);
    _: print(etree.tostring(root[0], encoding="UTF-8", pretty_print=True));
}

and:

name, family-name {
    _: $_TEXT
}

persons {
    persons: sorted(zip(family-name, name))[:];
    persons: "      <li>¬n        %s, %s¬n      </li>" % @;
    head: "<html>";
    head: "  <head> <title>Testing XML Example</title> </head>";
    head: "  <body>";
    head: "    <h1>Persons</h1>";
    head: "    <ul>";
    tail: "    </ul>";
    tail: "  </body>";
    tail: "</html>";
    print("¬n".join(head + persons + list))
}