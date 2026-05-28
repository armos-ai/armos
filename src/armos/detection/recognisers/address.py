# SPDX-License-Identifier: MIT
from presidio_analyzer import Pattern, PatternRecognizer


class PhysicalAddressRecogniser(PatternRecognizer):
    """
    Detects physical / postal addresses.

    Patterns (in descending confidence):
      - Full US address: street + city + 2-letter state + ZIP
      - Street address: house number + street keyword
      - Indian address: Flat / House / Plot / Apartment + identifier
      - P.O. Box

    False-positive risk is mitigated by keeping street-only patterns at 0.65
    and letting Presidio's context boost push them above 0.85 when surrounded
    by address-related vocabulary.
    """

    # Major Indian cities — anchors the named-location pattern to reduce false positives
    _IN_CITIES = (
        r"Bangalore|Bengaluru|Mumbai|Bombay|Delhi|New Delhi|Chennai|Madras|"
        r"Kolkata|Calcutta|Hyderabad|Pune|Ahmedabad|Jaipur|Surat|Lucknow|"
        r"Kanpur|Nagpur|Indore|Thane|Bhopal|Visakhapatnam|Vizag|Noida|"
        r"Gurgaon|Gurugram|Ghaziabad|Faridabad|Patna|Vadodara|Ludhiana|"
        r"Agra|Nashik|Rajkot|Meerut|Varanasi|Kochi|Cochin|Coimbatore|"
        r"Madurai|Bhubaneswar|Chandigarh|Mysore|Mysuru|Srinagar|Ranchi|"
        r"Aurangabad|Jodhpur|Raipur|Guwahati|Amritsar|Allahabad|Prayagraj|"
        r"Vijayawada|Guntur|Warangal|Tiruchirappalli|Salem|Hubli|Hubballi"
    )

    # Common English non-address words that happen to start with a capital letter
    # after a number (document refs, quantities) — excluded from locality matching.
    # Presidio compiles patterns with re.IGNORECASE, so (?-i:...) is needed to
    # restore case-sensitivity for the locality portion.
    _NOT_LOCALITY = (
        r"Summary|Analysis|Overview|Review|Report|Section|Chapter|Version|"
        r"Phase|Stage|Step|Part|Plan|Orders?|Points?|Cases?|Files?|Tasks?|"
        r"Issues?|Tests?|Bugs?|Items?|Lines?|Batches?|Units?|Groups?|Sets?|"
        r"Modules?|Features?|Results?|Examples?|Notes?|Updates?|Details?"
    )

    PATTERNS = [
        # Full US address — most specific, high confidence
        Pattern(
            "us_full_address",
            r"\b\d{1,5}[A-Za-z]?\s+(?:[A-Za-z0-9]+\s+){1,5}"
            r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|"
            r"Lane|Ln|Court|Ct|Place|Pl|Way|Circle|Cir|Highway|Hwy|"
            r"Terrace|Ter|Trail|Trl|Parkway|Pkwy)\.?"
            r"[,\s]+[A-Za-z][A-Za-z\s]{1,24}[,\s]+[A-Z]{2}[\s,]+\d{5}(?:-\d{4})?\b",
            score=0.9,
        ),
        # Street address: house/apt number + any word(s) + recognised street suffix
        # Score raised to 0.82 so it beats spaCy NER PERSON (~0.8) on overlap resolution
        Pattern(
            "street_address",
            r"\b\d{1,5}[A-Za-z]?\s+(?:[A-Za-z0-9]+\s+){0,4}"
            r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|"
            r"Drive|Dr\.?|Lane|Ln\.?|Court|Ct\.?|Place|Pl\.?|Way|"
            r"Circle|Cir\.?|Highway|Hwy\.?|Terrace|Ter\.?|Trail|Trl\.?|"
            r"Parkway|Pkwy\.?)\b",
            score=0.82,
        ),
        # Indian address: Flat / House / Plot / Apartment + alphanumeric identifier
        Pattern(
            "indian_address",
            r"\b(?:Flat|House|Door|H\.?\s*No\.?|Plot\s*(?:No\.?)?|Villa|"
            r"Apt\.?|Apartment|Block)\s*[#\-–]?\s*[A-Za-z0-9][A-Za-z0-9\-]*\b",
            score=0.55,
        ),
        # Indian named location: bare house number + locality + major city (no street suffix)
        # e.g. "180 Powai, Kolkata" / "42 Sector 12, Jaipur" / "7 HSR Layout, Bangalore"
        # (?-i:...) restores case-sensitivity inside Presidio's IGNORECASE compilation so
        # only genuinely capitalised locality names match (not lowercase "orders", "points").
        # Negative lookahead blocks common English document/quantity words (Summary, Phase…)
        # that happen to be capitalised after a number.
        # Score 0.88 beats spaCy NER PERSON (~0.85) on Indian city/locality names.
        Pattern(
            "indian_named_location",
            r"\b\d{1,3}\s+(?-i:(?!" + _NOT_LOCALITY + r"\b)[A-Z][a-zA-Z0-9]*)"
            r"(?:\s+(?-i:[A-Za-z0-9]+)){0,2}"
            r",\s*(?:" + _IN_CITIES + r")\b",
            score=0.88,
        ),
        # P.O. Box — very specific
        Pattern(
            "po_box",
            r"\bP\.?\s*O\.?\s*Box\s+\d+\b",
            score=0.9,
        ),
    ]

    CONTEXT = [
        "address", "residence", "home", "office", "located at", "lives at",
        "resides at", "shipping", "ship", "delivery", "billing", "mailing",
        "parcel", "house", "flat", "apartment", "door no", "plot", "village",
        "district", "pincode", "zip", "postal", "locality", "area",
        "street", "avenue", "road", "lane", "building",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="PHYSICAL_ADDRESS",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )
