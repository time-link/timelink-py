from datetime import datetime
from timelink.kleio.utilities import convert_timelink_date
import warnings


def test_valid_date():
    assert convert_timelink_date("19000101") == datetime(1900, 1, 1)
    assert convert_timelink_date("20241231") == datetime(2024, 12, 31)


def test_incomplete_date():
    assert convert_timelink_date("1900") == datetime(1900, 7, 2)
    assert convert_timelink_date("190001") == datetime(1900, 1, 15)


def test_date_with_dashes():
    assert convert_timelink_date("1900-01-01") == datetime(1900, 1, 1)
    assert convert_timelink_date("1900-01") == datetime(1900, 1, 15)
    assert convert_timelink_date("1900-") == datetime(1900, 7, 2)


def test_date_with_greater_less_than():
    assert convert_timelink_date(">1900-01-01") == datetime(1900, 1, 1)
    assert convert_timelink_date("<1900-01") == datetime(1900, 1, 15)
    assert convert_timelink_date("<1900-") == datetime(1900, 7, 2)


def test_ranges_with_greater_less_than():
    assert convert_timelink_date(">1900-01-01:<2000-01-01") == datetime(1900, 1, 1)


def test_date_with_custom_format():
    assert convert_timelink_date("01/01/1900", format="%d/%m/%Y") == datetime(1900, 1, 1)


def test_invalid_date():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert convert_timelink_date("00000101") is None
        assert len(w) == 0  # Expecting no warning

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert convert_timelink_date("19001301") is None
        assert len(w) == 1  # Expecting one warning
        assert isinstance(w[-1].message, UserWarning)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert convert_timelink_date("19000132") is None
        assert len(w) == 1  # Expecting one warning
        assert isinstance(w[-1].message, UserWarning)


def test_none_date():
    assert convert_timelink_date(None) is None


def test_not_string_date():
    assert convert_timelink_date(19000101) is None
