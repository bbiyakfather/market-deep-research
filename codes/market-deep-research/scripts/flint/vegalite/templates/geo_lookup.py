"""Geographic gazetteer for choropleth maps.

Crosswalks user-facing region forms (names, USPS/ISO codes) to the numeric ids
that match Vega's ``us-10m.json`` (states) and ``world-110m.json`` (countries)
feature ids. Port of vegalite/templates/geo-lookup.ts.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

_COMBINING = re.compile(r"[\u0300-\u036f]")
_NON_ALNUM = re.compile(r"[^a-z0-9]")
_DIGITS = re.compile(r"^\d+$")


def _norm(s: str) -> str:
    """Accent-fold, lowercase, alphanumerics only (mirrors JS ``norm``)."""
    s = unicodedata.normalize("NFD", s)
    s = _COMBINING.sub("", s)
    s = s.lower()
    s = _NON_ALNUM.sub("", s)
    return s


# US states — [FIPS, name, USPS code]
_US_STATES = [
    (1, "Alabama", "AL"), (2, "Alaska", "AK"), (4, "Arizona", "AZ"), (5, "Arkansas", "AR"),
    (6, "California", "CA"), (8, "Colorado", "CO"), (9, "Connecticut", "CT"), (10, "Delaware", "DE"),
    (11, "District of Columbia", "DC"), (12, "Florida", "FL"), (13, "Georgia", "GA"), (15, "Hawaii", "HI"),
    (16, "Idaho", "ID"), (17, "Illinois", "IL"), (18, "Indiana", "IN"), (19, "Iowa", "IA"),
    (20, "Kansas", "KS"), (21, "Kentucky", "KY"), (22, "Louisiana", "LA"), (23, "Maine", "ME"),
    (24, "Maryland", "MD"), (25, "Massachusetts", "MA"), (26, "Michigan", "MI"), (27, "Minnesota", "MN"),
    (28, "Mississippi", "MS"), (29, "Missouri", "MO"), (30, "Montana", "MT"), (31, "Nebraska", "NE"),
    (32, "Nevada", "NV"), (33, "New Hampshire", "NH"), (34, "New Jersey", "NJ"), (35, "New Mexico", "NM"),
    (36, "New York", "NY"), (37, "North Carolina", "NC"), (38, "North Dakota", "ND"), (39, "Ohio", "OH"),
    (40, "Oklahoma", "OK"), (41, "Oregon", "OR"), (42, "Pennsylvania", "PA"), (44, "Rhode Island", "RI"),
    (45, "South Carolina", "SC"), (46, "South Dakota", "SD"), (47, "Tennessee", "TN"), (48, "Texas", "TX"),
    (49, "Utah", "UT"), (50, "Vermont", "VT"), (51, "Virginia", "VA"), (53, "Washington", "WA"),
    (54, "West Virginia", "WV"), (55, "Wisconsin", "WI"), (56, "Wyoming", "WY"),
]

_US_STATE_ALIASES = {
    # AP-style abbreviations
    "ala": 1, "ariz": 4, "ark": 5, "calif": 6, "colo": 8, "conn": 9, "del": 10, "fla": 12,
    "ill": 17, "ind": 18, "kan": 20, "kans": 20, "mass": 25, "mich": 26, "minn": 27,
    "miss": 28, "mont": 30, "neb": 31, "nebr": 31, "nev": 32, "okla": 40, "ore": 41,
    "oreg": 41, "penn": 42, "penna": 42, "tenn": 47, "tex": 48, "wash": 53, "wis": 55,
    "wisc": 55, "wyo": 56,
    # Directional shorthand
    "ncarolina": 37, "scarolina": 45, "ndakota": 38, "sdakota": 46, "wvirginia": 54,
    "nhampshire": 33, "njersey": 34, "nmexico": 35, "nyork": 36,
    # District of Columbia variants
    "washingtondc": 11, "dcusa": 11,
}

# Countries — [ISO numeric, name, alpha-2, alpha-3]
_COUNTRIES = [
    (156, "China", "CN", "CHN"), (356, "India", "IN", "IND"), (840, "United States", "US", "USA"),
    (360, "Indonesia", "ID", "IDN"), (586, "Pakistan", "PK", "PAK"), (566, "Nigeria", "NG", "NGA"),
    (76, "Brazil", "BR", "BRA"), (50, "Bangladesh", "BD", "BGD"), (643, "Russia", "RU", "RUS"),
    (484, "Mexico", "MX", "MEX"), (231, "Ethiopia", "ET", "ETH"), (392, "Japan", "JP", "JPN"),
    (608, "Philippines", "PH", "PHL"), (818, "Egypt", "EG", "EGY"), (180, "DR Congo", "CD", "COD"),
    (704, "Vietnam", "VN", "VNM"), (364, "Iran", "IR", "IRN"), (792, "Turkey", "TR", "TUR"),
    (276, "Germany", "DE", "DEU"), (764, "Thailand", "TH", "THA"), (826, "United Kingdom", "GB", "GBR"),
    (250, "France", "FR", "FRA"), (710, "South Africa", "ZA", "ZAF"), (380, "Italy", "IT", "ITA"),
    (404, "Kenya", "KE", "KEN"), (170, "Colombia", "CO", "COL"), (724, "Spain", "ES", "ESP"),
    (32, "Argentina", "AR", "ARG"), (12, "Algeria", "DZ", "DZA"), (124, "Canada", "CA", "CAN"),
    (616, "Poland", "PL", "POL"), (804, "Ukraine", "UA", "UKR"), (682, "Saudi Arabia", "SA", "SAU"),
    (504, "Morocco", "MA", "MAR"), (604, "Peru", "PE", "PER"), (36, "Australia", "AU", "AUS"),
    (398, "Kazakhstan", "KZ", "KAZ"), (152, "Chile", "CL", "CHL"), (752, "Sweden", "SE", "SWE"),
    (578, "Norway", "NO", "NOR"), (528, "Netherlands", "NL", "NLD"), (56, "Belgium", "BE", "BEL"),
    (756, "Switzerland", "CH", "CHE"), (40, "Austria", "AT", "AUT"), (620, "Portugal", "PT", "PRT"),
    (300, "Greece", "GR", "GRC"), (372, "Ireland", "IE", "IRL"), (246, "Finland", "FI", "FIN"),
    (208, "Denmark", "DK", "DNK"), (554, "New Zealand", "NZ", "NZL"), (410, "South Korea", "KR", "KOR"),
    (458, "Malaysia", "MY", "MYS"), (862, "Venezuela", "VE", "VEN"), (218, "Ecuador", "EC", "ECU"),
    (4, "Afghanistan", "AF", "AFG"), (368, "Iraq", "IQ", "IRQ"), (887, "Yemen", "YE", "YEM"),
    (144, "Sri Lanka", "LK", "LKA"), (104, "Myanmar", "MM", "MMR"), (116, "Cambodia", "KH", "KHM"),
    (24, "Angola", "AO", "AGO"), (834, "Tanzania", "TZ", "TZA"), (800, "Uganda", "UG", "UGA"),
    (716, "Zimbabwe", "ZW", "ZWE"), (288, "Ghana", "GH", "GHA"), (384, "Ivory Coast", "CI", "CIV"),
    (686, "Senegal", "SN", "SEN"),
    # Additional countries — numeric ids verified present in world-110m.json.
    (268, "Georgia", "GE", "GEO"), (524, "Nepal", "NP", "NPL"), (192, "Cuba", "CU", "CUB"),
    (634, "Qatar", "QA", "QAT"), (400, "Jordan", "JO", "JOR"), (422, "Lebanon", "LB", "LBN"),
    (376, "Israel", "IL", "ISR"), (414, "Kuwait", "KW", "KWT"), (512, "Oman", "OM", "OMN"),
    (784, "United Arab Emirates", "AE", "ARE"), (788, "Tunisia", "TN", "TUN"), (434, "Libya", "LY", "LBY"),
    (729, "Sudan", "SD", "SDN"), (120, "Cameroon", "CM", "CMR"), (508, "Mozambique", "MZ", "MOZ"),
    (450, "Madagascar", "MG", "MDG"), (894, "Zambia", "ZM", "ZMB"), (466, "Mali", "ML", "MLI"),
    (854, "Burkina Faso", "BF", "BFA"), (562, "Niger", "NE", "NER"), (148, "Chad", "TD", "TCD"),
    (706, "Somalia", "SO", "SOM"), (68, "Bolivia", "BO", "BOL"), (600, "Paraguay", "PY", "PRY"),
    (858, "Uruguay", "UY", "URY"), (320, "Guatemala", "GT", "GTM"), (340, "Honduras", "HN", "HND"),
    (214, "Dominican Republic", "DO", "DOM"), (591, "Panama", "PA", "PAN"), (188, "Costa Rica", "CR", "CRI"),
    (191, "Croatia", "HR", "HRV"), (688, "Serbia", "RS", "SRB"), (703, "Slovakia", "SK", "SVK"),
    (705, "Slovenia", "SI", "SVN"), (100, "Bulgaria", "BG", "BGR"), (642, "Romania", "RO", "ROU"),
    (348, "Hungary", "HU", "HUN"), (112, "Belarus", "BY", "BLR"), (440, "Lithuania", "LT", "LTU"),
    (428, "Latvia", "LV", "LVA"), (233, "Estonia", "EE", "EST"), (352, "Iceland", "IS", "ISL"),
    (418, "Laos", "LA", "LAO"), (496, "Mongolia", "MN", "MNG"), (408, "North Korea", "KP", "PRK"),
    (158, "Taiwan", "TW", "TWN"), (64, "Bhutan", "BT", "BTN"), (760, "Syria", "SY", "SYR"),
    (203, "Czechia", "CZ", "CZE"), (795, "Turkmenistan", "TM", "TKM"), (860, "Uzbekistan", "UZ", "UZB"),
    (31, "Azerbaijan", "AZ", "AZE"), (51, "Armenia", "AM", "ARM"), (558, "Nicaragua", "NI", "NIC"),
]

_COUNTRY_ALIASES = {
    "usa": 840, "us": 840, "unitedstatesofamerica": 840, "america": 840,
    "uk": 826, "greatbritain": 826, "britain": 826, "england": 826,
    "russianfederation": 643, "southkorea": 410, "korea": 410, "republicofkorea": 410,
    "skorea": 410, "korearep": 410, "koreasouth": 410, "koreasouthrepublicof": 410,
    "nkorea": 408, "koreanorth": 408, "koreademrep": 408, "dprk": 408,
    "democraticpeoplesrepublicofkorea": 408,
    "democraticrepublicofthecongo": 180, "congokinshasa": 180, "drc": 180,
    "vietnam": 704, "vietnamsocialistrepublic": 704, "ivorycoast": 384, "cotedivoire": 384,
    "iranislamicrepublicof": 364, "syrianarabrepublic": 760, "tanzaniaunitedrepublicof": 834,
    "burma": 104, "czechrepublic": 203, "czechia": 203, "uae": 784, "unitedarabemirates": 784,
    "holland": 528, "thenetherlands": 528, "turkiye": 792,
    "laopdr": 418, "laopeoplesdemocraticrepublic": 418,
}


def _build_map(entries):
    m = {}
    for id_, keys in entries:
        for k in keys:
            nk = _norm(k)
            if nk and nk not in m:
                m[nk] = id_
    return m


def _build_us_lookup():
    m = _build_map([(id_, [name, usps]) for id_, name, usps in _US_STATES])
    for alias, id_ in _US_STATE_ALIASES.items():
        if alias not in m:
            m[alias] = id_
    return m


def _build_country_lookup():
    m = _build_map([(id_, [name, a2, a3]) for id_, name, a2, a3 in _COUNTRIES])
    for alias, id_ in _COUNTRY_ALIASES.items():
        if alias not in m:
            m[alias] = id_
    return m


_US_STATE_LOOKUP = _build_us_lookup()
_COUNTRY_LOOKUP = _build_country_lookup()


def _resolve_with(lookup, value: Any) -> Optional[int]:
    if value is None:
        return None
    # Already a numeric feature id (or a numeric string like "6" / "06").
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == value and value not in (float("inf"), float("-inf")):
            return value
        return None
    s = str(value).strip()
    if _DIGITS.match(s):
        return int(s)
    nk = _norm(s)
    if not nk:
        return None
    direct = lookup.get(nk)
    if direct is not None:
        return direct
    # Fallback: strip common qualifiers and retry.
    r = nk
    if r.startswith("stateof"):
        r = r[7:]
    if r.endswith("usa"):
        r = r[:-3]
    elif r.endswith("state"):
        r = r[:-5]
    if r != nk and r:
        return lookup.get(r)
    return None


def resolve_us_state(value: Any) -> Optional[int]:
    """Resolve a US state name / USPS code / FIPS id to its FIPS numeric id."""
    return _resolve_with(_US_STATE_LOOKUP, value)


def resolve_country(value: Any) -> Optional[int]:
    """Resolve a country name / ISO alpha-2 / alpha-3 / numeric to its ISO numeric id."""
    return _resolve_with(_COUNTRY_LOOKUP, value)
