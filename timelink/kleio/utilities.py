""".. module:: utilities
   :synopsis: Various utilities for handling Kleio groups and elements

.. moduleauthor: Joaquim Ramos de Carvalho

Kleio Groups are the building blocks for transcription of historical sources.
"""

from datetime import datetime
import json
import textwrap
from os import linesep as nl
import warnings
from decimal import Decimal


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
    if v.strip().startswith('"'):
        return v
    s = str(v)

    if any(i in s for i in "/;=$#%\n\""):
        if '"' not in s:
            return '"' + s + '"'
        else:  # double quote in value, need triple quotes
            return '"""' + s + '"""'
    else:
        return s


def quote_long_text(txt, initial_indent=" " * 4, indent=" " * 2, width=2048, **kwargs) -> str:
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

    if type(txt) is not str:
        txt = str(txt)

    # check if text already is triple quoted, starts with """ and end with """
    if txt.strip().startswith('"""'):
        return txt
    if len(txt) > width or len(txt.splitlines()) > 1:
        s = '"""'
        for line in txt.splitlines():
            w = textwrap.fill(line, width=width, initial_indent=initial_indent)
            s = s + textwrap.indent(w, indent) + nl
        s = s + indent + '"""'
    elif '"' in txt:
        s = '"""' + txt + '"""'
    else:
        s = kleio_escape(txt)
    return s


def get_extra_info_from_obs(obs_text: str) -> tuple[str, dict]:
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
    :type extra_info: dict, or str (wiil be handled by :py:func:`get_extra_info`)
    :param kwargs: Additional parameters for :py:func:`quote_long_text`
    :rtype: str
    """

    if type(extra_info) is not dict:
        if type(extra_info) is str:
            _notused, extra_info = get_extra_info_from_obs(extra_info)
        else:
            extra_info = {}
    if type(element_value) is not str:
        element_value = quote_long_text(element_value, **kwargs)
    extras = extra_info.get(element_name, {})
    element_comment = extras.get("comment", None)
    element_original = extras.get("original", None)

    if element_comment is not None:
        element_value = f"{element_value}#{quote_long_text(element_comment, **kwargs)}"
    if element_original is not None:
        element_value = f"{element_value}%{quote_long_text(element_original, **kwargs)}"
    return element_value


def convert_timelink_date(tl_date: str, format="%Y%m%d") -> datetime:
    """Convert a Timelink date in the format YYYYMMDD to a Python datetime
    If the date is incomplete or correspond to a rage it will return a
    value that represents a sortable aproximation of the date.

    Args:
    tl_date: a string representing a date in the format YYYYMMDD
    format: the format used to scan the date string
    Dates can be incomplete: 1586 or 1586-03 or 158603

    Zeros can be used to register unknown values: 15860000 or 15860300

    Missing information is handled in the following way:
    * If the year is missing returns None
    * If the month is missing, returns the 2nd of July of that year (middle day of the year)
    * If the day is missing, returns the 15th of the month (middle day of the month)
    """
    # return None if tl_date is None
    if tl_date is None:
        return None
    # if tl_date is not a string, return None
    if not isinstance(tl_date, str):
        return None

    # remove dashes
    range = tl_date.split(':')
    tl_date_clean = range[0]
    tl_date_clean = tl_date_clean.replace("-", "").replace(">", "").replace("<", "")
    # pad tl_date with zeros up to length 8
    tl_date_clean = tl_date_clean.ljust(8, "0")
    year, month, day = tl_date_clean[:4], tl_date_clean[4:6], tl_date_clean[6:]
    # handle the case where month is zero by setting the month to 07 and day to 02 (middle day of year)
    if year == "0000":
        return None
    elif month == "00":
        month = "07"
        day = "02"
    elif day == "00":
        day = "15"

    new_date = year + month + day
    try:
        result = datetime.strptime(new_date, format)
    except ValueError as BadDate:
        warnings.warn(f"Invalid date: {tl_date_clean} -> {BadDate}", UserWarning, stacklevel=4)
        result = None
    return result


def format_timelink_date(tl_datet) -> str:
    """Format a timelink date YYYYMMDD and variants to nice string

    Note that we also can get dates as floating point numbers
    as a result of kleio server processing:

    -- from Kleio server issue #1
    value is a sortable representation of the date as a number.

        in single dates is a 8 digit number with 00 in the missing month or day if any.
        15600000
        15600215

        for relative dates (>1580) is a 8 digit number with 0.3 added for "after" dates
        and 0.3 subtracted for before dates.

        >1580 has value: "15800000.3"
        <1640 has value: "16399999.7"

        for ranges is a 8 digit number equal to the "from" date and decimal part equal to the "to" date.
        "1580:1640" has value "15800000.16400000"

        for open ranges where only "from" date or "to" date is available values is an 8
        digit number with 0.1 added for open ended ranges and 0.1 subtracted for open
        start ranges.

        * "1580:" has value "15800000.1"
        * ":1640" has value "16399999.9"

        note that it is possible to infer the date type by computing type=value-round(value)
        * type = 0 -> single date round(value)
        * type = 0.3 -> after date round(value)
        * type = -0.3 -> date before round(value)
        * type = 0.1 -> open ended range starting at round(value)
        * type = -0.1 > open start rand ending at round(value)
        * other = range from round(value) to value-round(value)

    """
    # return empty string if tl_datet is None
    original = tl_datet
    if tl_datet is None or tl_datet == "":
        return ""
    # return empty string if tl_datet is not a string
    if not isinstance(tl_datet, str):
        return ""
    #  check if tl_datet is a string with a decimal point
    if "." in tl_datet:
        # this dates have special semantics
        tl_datet = _reverse_date_value(tl_datet)
    dates = tl_datet.split(':')
    if len(dates) == 2:
        py_date1 = format_timelink_date(dates[0])
        py_date2 = format_timelink_date(dates[1])
        return py_date1 + ":" + py_date2

    if tl_datet[0] == ">":
        return ">" + format_timelink_date(tl_datet[1:])
    if tl_datet[0] == "<":
        return "<" + format_timelink_date(tl_datet[1:])

    # fill with zeros
    tl_datet = tl_datet.ljust(8, "0")
    # if tl_datet is '00000000' return empty string
    if tl_datet == "00000000":
        return ""
    # if date ends in '0000' return just the first 4 characters
    if tl_datet.endswith("0000"):
        return tl_datet[:-4]
    # if date ends in '00' return the first 6 characters with an hifen between 4th and 5th characters
    if tl_datet.endswith("00"):
        return tl_datet[:4] + "-" + tl_datet[4:6]
    # Otherwise convert the date
    py_date = convert_timelink_date(tl_datet)
    # if py_date is None return empty string
    if py_date is None:
        return "E" + original
    else:
        return py_date.strftime("%Y-%m-%d")


def _reverse_date_value(data_str: str):
    """ reverses the sort value of a date:
         note that it is possible to infer the date type by computing type=value-round(value)
        type = 0 -> single date round(value)
        type = 0.3 -> after date round(value)
        type = -0.3 -> date before round(value)
        type = 0.1 -> open ended range starting at round(value)
        type = -0.1 > open start rand ending at round(value)
        other = range from round(value) to value-round(value)
    """
    value = Decimal(data_str)
    round_value = round(value)
    type = value - round_value
    if type == Decimal("0"):
        return data_str
    elif type == Decimal("0.3"):
        return ">" + str(round_value)
    elif type == Decimal("-0.3"):
        return "<" + str(round_value)
    elif type == Decimal("0.1"):
        return str(round_value) + ":"
    elif type == Decimal("-0.1"):
        return ":" + str(round_value)
    else:
        # range
        dates = data_str.split('.')
        return dates[0] + ":" + dates[1]


def calc_age_at(date_birth, today):
    """Compute the number of years between two dates"""
    # return None if either argument is None
    if date_birth is None or today is None:
        return None
    # Ensure the dates are datetime objects
    if not isinstance(date_birth, datetime):
        date_birth = convert_timelink_date(date_birth)
    if not isinstance(today, datetime):
        today = convert_timelink_date(today)

    if date_birth is None or today is None:
        return None

    # Compute the difference in years
    difference_in_years = (today - date_birth).days / 365.25
    return int(difference_in_years)
