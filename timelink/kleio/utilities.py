""".. module:: utilities
   :synopsis: Various utilities for handling Kleio groups and elements

.. moduleauthor: Joaquim Ramos de Carvalho

Kleio Groups are the building blocks for transcription of historical sources.
"""

import textwrap
from os import linesep as nl


def kleio_escape(v: str) -> str:
    """
    Checks for Kleio special characters and quotes if needed::

         >>> print(kleio_escape('normal string'))
         normal string
         >>> print(kleio_escape('oops we have a / in the middle'))
         "oops we have a / in the middle"

    """
    if v is None:
        return None
    s = str(v)
    if any(i in s for i in "/;=$#%\n"):
        return '"' + s + '"'
    else:
        return s


def quote_long_text(txt, initial_indent=" " * 4, indent=" " * 2, width=2048) -> str:
    """Surround long text with triple quotes,
    wraps and indents lines if needed.
    Some of the parameters are passed on to :py:func:`textwrap.fill`.

    Sphynx style markup

    :param txt: The text to be transformed
    :type txt: str
    :param initial_indent: string to ident the first line of paragraphs.
                        Default is 4 spaces. See :py:func:`textwrap.fill`.
    :type initial_indent: str
    :param indent: string to ident the wrap lines of
                    paragraphs (after the first).
                    Default is 2 spaces. See :py:func:`textwrap.fill`.
    :type indent: str
    :param width: width of line for wrapping. See :py:func:`textwrap.fill`.
    :type width: int
    :rtype: str
    """
    if txt is None:
        return None
    if width is None:
        width = 80
    if len(txt) > 127 or len(txt.splitlines()) > 1:
        s = '"""' + nl
        for line in txt.splitlines():
            w = textwrap.fill(line, width=width, initial_indent=initial_indent)
            s = s + textwrap.indent(w, indent) + nl
        s = s + indent + '"""'
    else:
        s = kleio_escape(txt)
    return s
