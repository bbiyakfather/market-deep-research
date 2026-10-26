"""Helpers for matching JavaScript's ``Date.parse`` / ``new Date(value)``.

V8's ``Date.parse`` is famously permissive and inconsistent. The pure-Python
``dateutil`` parser disagrees with V8 in two opposite directions:

  * V8 *accepts* free-form prefixes like ``"FY 2018"`` and ``"hello world 2018"``
    by extracting the trailing year — ``dateutil`` rejects them.
  * V8 *rejects* dot/slash/dash-separated numeric dates like ``"15.01.2020"``
    or ``"15/01/2020"`` — ``dateutil`` happily parses them as
    ``DD.MM.YYYY``.

To keep the Python port byte-for-byte compatible with the TypeScript
reference (and to faithfully reproduce the JS behaviour that the gallery
test cases depend on) we layer a small compatibility wrapper on top of
``dateutil``:

  1. Strict ISO-8601 via :func:`datetime.fromisoformat` (with explicit
     timezone handling: ISO date-only → UTC; ISO datetime without zone →
     local time; matches ECMAScript's Date Time String format spec).
  2. Reject obviously-numeric ``DD?D?[./-]MM?[./-]YYYY`` forms that V8
     would not parse.
  3. ``dateutil.parser.parse`` for free-form dates V8 supports (month
     names, RFC 2822, etc.).
  4. V8's "trailing year" heuristic — if every non-whitespace token in
     the string is either a pure-letter word or a single 4-digit year,
     parse as Jan 1 of that year (local time).

These helpers return floats representing JS milliseconds since the Unix
epoch (matching ``+new Date(value)``) or ``None`` when the value cannot
be parsed.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional


_ISO_DATE_ONLY = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")

# V8 numeric-date forms: slash / dash / dot separated.  V8 interprets these
# as US-style MM-DD-YYYY (or YYYY-MM-DD when the first component is a 4-digit
# year), and rejects them if the month component is out of range (1–12) or
# the day is out of range for that month. Our ``dateutil`` fallback would
# instead happily parse "15.01.2020" as 15-Jan-2020, which disagrees with V8.
_V8_NUMERIC_DATE = re.compile(r"^\s*(\d{1,4})\s*([./\-])\s*(\d{1,2})\s*\2\s*(\d{1,4})\s*$")

# A V8-style "all-words-and-one-year" string: zero or more pure-letter words
# and exactly one 4-digit year (1000–9999), in any order.
_WORD_RE = re.compile(r"[A-Za-z]+")
_YEAR_RE = re.compile(r"\b(\d{4})\b")


def _looks_like_word_plus_year(s: str) -> Optional[int]:
    """Return the year if ``s`` is "FY 2018" / "May 2018" / "X 2018" — i.e.
    every non-whitespace token is either a pure-letter word or exactly one
    4-digit year. Otherwise ``None``.
    """
    years = _YEAR_RE.findall(s)
    if len(years) != 1:
        return None
    year = int(years[0])
    if not (1000 <= year <= 9999):
        return None
    # Strip out the year and check the remainder consists only of letters / ws.
    rest = _YEAR_RE.sub("", s).strip()
    if rest and not re.fullmatch(r"[A-Za-z\s]+", rest):
        return None
    return year


def _try_v8_numeric_date(s: str) -> Optional[datetime]:
    """Parse V8-style numeric dates (``MM/DD/YYYY``, ``YYYY-MM-DD``, etc.).

    V8 only accepts these forms when the *month* component is in 1–12. The
    common Python fallback (``dateutil``) is more lenient and would interpret
    ``"15.01.2020"`` as 15-Jan-2020, which V8 rejects. Returns ``None`` to
    signal "let the caller try a different strategy", or a naive ``datetime``
    on success (caller is responsible for assigning the timezone).
    """
    m = _V8_NUMERIC_DATE.match(s)
    if not m:
        return None
    a, _sep, b, c = m.group(1), m.group(2), m.group(3), m.group(4)
    aa, bb, cc = int(a), int(b), int(c)
    if len(a) == 4:
        year, month, day = aa, bb, cc
    elif len(c) == 4:
        # MM/DD/YYYY (V8 prefers month first).
        year, month, day = cc, aa, bb
    else:
        # All 1–3 digit components — V8 generally rejects.
        return None
    if not (1 <= month <= 12):
        return None
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def js_date_parse_ms(value: Any) -> Optional[float]:
    """Mirror V8's ``Date.parse(value)`` returning milliseconds since epoch.

    Returns ``None`` when the value cannot be parsed (matching V8's ``NaN``).
    Numeric and ``datetime`` inputs are passed through (matching
    ``new Date(num)`` and ``new Date(date)`` semantics).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.timestamp() * 1000.0
    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    # 1. Strict ISO 8601 first.
    try:
        iso_input = s[:-1] + "+00:00" if s.endswith("Z") else s
        dt = datetime.fromisoformat(iso_input)
        if dt.tzinfo is None:
            if _ISO_DATE_ONLY.match(s):
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone()
        return dt.timestamp() * 1000.0
    except Exception:
        pass

    # 2. V8 numeric-date forms ("01/15/2020", "01-15-2020", "01.15.2020",
    #    "2020-01-15", etc.). V8 only parses these when the month component
    #    is 1–12; ``dateutil`` is more permissive and would happily parse
    #    "15.01.2020" as 15-Jan, which V8 rejects. Handle them explicitly
    #    here so dateutil never sees these strings.
    if _V8_NUMERIC_DATE.match(s):
        dt = _try_v8_numeric_date(s)
        if dt is None:
            # V8 rejects — fall through to the word-plus-year heuristic only.
            year = _looks_like_word_plus_year(s)
            if year is not None:
                return datetime(year, 1, 1).astimezone().timestamp() * 1000.0
            return None
        # ECMAScript: ISO-8601 date-only forms are UTC; everything else local.
        if _ISO_DATE_ONLY.match(s):
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone()
        return dt.timestamp() * 1000.0

    # 3. dateutil for free-form formats V8 also accepts (month names, RFC 2822).
    try:
        from dateutil.parser import parse as _du_parse  # type: ignore
        dt = _du_parse(s, default=datetime(1970, 1, 1))
        if dt.tzinfo is None:
            # ECMAScript spec: ISO date-only forms ("2020", "2020-03") parse
            # as UTC; everything else is local. ``datetime.fromisoformat`` only
            # accepts full ``YYYY-MM-DD``, so short ISO date-only forms fall
            # through to ``dateutil`` here — keep them UTC for parity.
            if _ISO_DATE_ONLY.match(s):
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone()
        return dt.timestamp() * 1000.0
    except Exception:
        pass

    # 4. V8 trailing-year heuristic ("FY 2018", "hello world 2018").
    year = _looks_like_word_plus_year(s)
    if year is not None:
        return datetime(year, 1, 1).astimezone().timestamp() * 1000.0

    return None


def js_date_parse(value: Any) -> Optional[datetime]:
    """Return a timezone-aware ``datetime`` matching V8's ``new Date(value)``."""
    ms = js_date_parse_ms(value)
    if ms is None:
        return None
    # Avoid floating-point drift in the microsecond field by going through int.
    ms_int = int(ms)
    seconds, ms_remainder = divmod(ms_int, 1000)
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return dt.replace(microsecond=ms_remainder * 1000)


def is_js_parseable(value: Any) -> bool:
    """``True`` if V8's ``Date.parse(value)`` would succeed (i.e. not NaN)."""
    return js_date_parse_ms(value) is not None
