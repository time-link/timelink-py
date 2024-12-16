

# tests/test_utilities.py
# pylint: disable=C0116

from timelink.kleio.utilities import (
    get_extra_info_from_obs,
    quote_long_text,
    kleio_escape,
    render_with_extra_info
)


def test_quote_long_text_with_none():
    assert quote_long_text(None) is None


def test_quote_long_text_with_short_text():
    assert quote_long_text("short text") == "short text"


def test_quote_long_text_with_long_text():
    long_text = "This is a very long text that should be quoted because it exceeds the length limit."
    s = quote_long_text(long_text, width=64)
    assert len(s.splitlines()) > 1


def test_quote_long_text_with_text_containing_quotes():
    text_with_quotes = 'This text "contains" quotes.'
    s = quote_long_text(text_with_quotes)
    assert s == f'"""{text_with_quotes}"""'


def test_quote_long_text_with_text_containing_newlines():
    text_with_newlines = "This text\ncontains\nnewlines."
    s = quote_long_text(text_with_newlines, initial_indent="", indent="", width=80)
    assert s == f'"""{text_with_newlines}\n"""'


def test_quote_long_text_with_text_containing_special_chars():
    text_with_special_chars = "This text contains special chars like /, ;, =, #, $, % but no quotes nor newlines"
    s = quote_long_text(text_with_special_chars, initial_indent="", indent="", width=120)
    assert s == f'"{text_with_special_chars}"'


def test_get_extra_info_with_none():
    result = get_extra_info_from_obs(None)
    assert result == ("", {})


def test_get_extra_info_with_empty_string():
    result = get_extra_info_from_obs("")
    assert result == ("", {})


def test_get_extra_info_with_valid_string():
    extra_info = 'saiu a primeira vez extra_info: {"value": {"comment": "@wikidata:Q45412"}}'
    expected_result = ("saiu a primeira vez", {"value": {"comment": "@wikidata:Q45412"}})
    result = get_extra_info_from_obs(extra_info)
    assert result == expected_result


def test_kleio_escape_with_none():
    assert kleio_escape(None) is None


def test_kleio_escape_with_no_special_chars():
    assert kleio_escape("simpletext") == "simpletext"
    assert kleio_escape("@wikidata:Q45412") == "@wikidata:Q45412"


def test_kleio_escape_with_special_chars():
    assert kleio_escape("text/with/special;chars") == '"text/with/special;chars"'
    assert kleio_escape("text=with=special#chars") == '"text=with=special#chars"'
    assert kleio_escape("text$with%special\nchars") == '"text$with%special\nchars"'


def test_kleio_escape_with_quotes():
    assert kleio_escape('text"with"quotes') == 'text"with"quotes'


def test_kleio_escape_with_mixed_chars():
    assert kleio_escape("text/with=special;chars#and$more%chars\n") == '"text/with=special;chars#and$more%chars\n"'


def test_render_with_extra_info():
    element_name = "value"
    element_value = 'saiu a primeira vez extra_info: {"value": {"comment": "@wikidata:Q45412"}}'
    core, extra_info = get_extra_info_from_obs(element_value)
    expected_result = f'{core}#@wikidata:Q45412'
    assert render_with_extra_info(element_name, core, extra_info) == expected_result
