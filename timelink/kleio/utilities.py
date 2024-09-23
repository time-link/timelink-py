""".. module:: utilities
   :synopsis: Various utilities for handling Kleio groups and elements

.. moduleauthor: Joaquim Ramos de Carvalho

Kleio Groups are the building blocks for transcription of historical sources.
"""
import json
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
    # test if v is already quoted
    if v.startswith('"') and v.endswith('"'):
        return v
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

    # check if text already is triple quoted, starts with """ and end with """
    if txt.startswith('"""') and txt.endswith('"""'):
        return txt
    if len(txt) > width or len(txt.splitlines()) > 1:
        s = '"""' + nl
        for line in txt.splitlines():
            w = textwrap.fill(line, width=width, initial_indent=initial_indent)
            s = s + textwrap.indent(w, indent) + nl
        s = s + indent + '"""'
    elif '"' in txt:
        s = '"""' + txt + '"""'
    else:
        s = kleio_escape(txt)
    return s


def get_extra_info(obs_text: str) -> tuple[str, dict]:
    """
    Extracts the extra information from the extra_info string
    and returns a tuple with the cleaned string and a dictionary

    :param obs_text: The string with extra information (can have other text before)
    :type obs_text: str
    :rtype: tuple[str,dict]
    """
    if obs_text is None:
        return "", {}

    if "extra_info:" in obs_text:
        extra_info = obs_text.split("extra_info:")[1].strip()
        s = obs_text.split("extra_info:")[0].strip()
        if len(extra_info) > 0:
            extra_info_dict = json.loads(extra_info)
        else:
            extra_info_dict = {}
    else:
        s = obs_text
        extra_info_dict = {}

    return s, extra_info_dict


def render_with_extra_info(element_name, element_value, extra_info, **kwargs) -> str:
    """
    Renders a Kleio element with extra information

    :param element_name: The name of the element
    :type element_name: str
    :param element_value: The value of the element from the db
    :type element_value: str
    :param extra_info: The extra information dictionary
    :type extra_info: dict
    :param kwargs: Additional parameters for :py:func:`quote_long_text`
    :rtype: str
    """
    element_value = quote_long_text(element_value, **kwargs)
    extras = extra_info.get(element_name, {})
    element_comment = extras.get("comment", None)
    element_original = extras.get("original", None)

    if element_comment is not None:
        element_value = f"{element_value}#{quote_long_text(element_comment, **kwargs)}"
    if element_original is not None:
        element_value = f"{element_value}%{quote_long_text(element_original, **kwargs)}"
    return element_value
