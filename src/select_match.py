US_STATE_NAMES: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}


def fill_candidates(key: str, value: str) -> list[str]:
    """Return profile value plus common variants for dropdown matching."""
    candidates = [value]
    seen = {value.casefold()}

    def add(*items: str) -> None:
        for item in items:
            if item and item.casefold() not in seen:
                seen.add(item.casefold())
                candidates.append(item)

    if key == "country" or key == "phone_country_code":
        if value.casefold() in {"united states", "us", "usa", "u.s.", "u.s.a."}:
            add("United States", "United States of America", "US", "USA", "U.S.", "U.S.A.", "+1", "1")
        elif key == "phone_country_code":
            add(value, "+1", "1", "US", "USA")
    elif key == "phone_type":
        add(value, value.title(), value.casefold())
    elif key == "county":
        add(f"{value} County", value)
    elif key == "state":
        code = value.upper()
        if len(code) == 2 and code in US_STATE_NAMES:
            add(code, US_STATE_NAMES[code])
    elif key == "degree":
        v = value.casefold()
        if "m.s" in v or "master" in v:
            add("M.S.", "MS", "M.S. in Computer Science", "Master of Science", "Master's", "Masters", "Master")
        if "b.s" in v or "bachelor" in v:
            add("B.S.", "BS", "B.S. in Computer Science", "Bachelor of Science", "Bachelor's", "Bachelors", "Bachelor")
        if "ph.d" in v or "doctor" in v:
            add("Ph.D.", "PhD", "Doctorate", "Doctoral")
        # Do not add bare "Computer Science" for degree — it partial-matches Master's options.
    elif key in {"specialization", "field_of_study"}:
        for part in value.replace("/", ",").split(","):
            add(part.strip())
        if "artificial intelligence" in value.casefold():
            add("Artificial Intelligence", "AI", "Machine Learning")
        if "data science" in value.casefold():
            add("Data Science", "Analytics")
        add("Computer Science", "CS")
    elif key == "source":
        v = value.casefold()
        if "linkedin" in v:
            add("LinkedIn", "LinkedIn.com", "Social Media", "Social Networking", "Internet")
        if "indeed" in v:
            add("Indeed", "Job Board", "Internet")
        if "glassdoor" in v:
            add("Glassdoor", "Job Board", "Internet")
        if "referr" in v:
            add("Referral", "Employee Referral", "Referred by Employee")

    return candidates


def pick_option(options: list[tuple[str, str]], candidates: list[str]) -> tuple[str, str] | None:
    """Pick best (value, label) option for a select. options = [(value, text), ...]."""
    normalized_opts = [(v, t, v.casefold(), t.casefold()) for v, t in options if t.strip() or v.strip()]

    for candidate in candidates:
        c = candidate.casefold()
        for value, text, value_cf, text_cf in normalized_opts:
            if c == value_cf or c == text_cf:
                return value, text

    for candidate in candidates:
        c = candidate.casefold()
        for value, text, value_cf, text_cf in normalized_opts:
            if c in text_cf or c in value_cf or text_cf in c:
                return value, text

    return None


def pick_option_for_degree(
    options: list[tuple[str, str]],
    candidates: list[str],
    profile_value: str,
) -> tuple[str, str] | None:
    """Match degree dropdown without confusing Bachelor vs Master."""
    value_cf = profile_value.casefold()
    is_bachelor = "bachelor" in value_cf or "b.s" in value_cf
    is_master = "master" in value_cf or "m.s" in value_cf

    if is_bachelor:
        bachelor_opts = [(v, t) for v, t in options if "bachelor" in t.casefold()]
        if bachelor_opts:
            match = pick_option(bachelor_opts, candidates)
            if match:
                return match

    if is_master:
        master_opts = [(v, t) for v, t in options if "master" in t.casefold()]
        if master_opts:
            match = pick_option(master_opts, candidates)
            if match:
                return match

    return pick_option(options, candidates)


def text_matches_any(text: str, candidates: list[str]) -> bool:
    normalized = text.casefold().strip()
    if not normalized:
        return False

    for candidate in candidates:
        c = candidate.casefold().strip()
        if not c:
            continue
        if normalized == c or c in normalized or normalized in c:
            return True
    return False


def yes_no_candidates(value: str) -> list[str]:
    if value.casefold() in {"yes", "y", "true"}:
        return ["Yes", "yes", "Y", "True"]
    if value.casefold() in {"no", "n", "false"}:
        return ["No", "no", "N", "False"]
    return [value]
