#!/usr/bin/env python3
"""
Generate index.json for country flag SVG files.
Usage: python generate_index.py <flags_directory> [output_file]
"""

import os
import re
import json
import sys

# ISO-2 → (ISO-3, description) mapping
# Includes standard countries plus special/regional codes found in this flag set
ISO2_MAP = {
    "ad": ("AND", "Andorra"),
    "ae": ("ARE", "United Arab Emirates"),
    "af": ("AFG", "Afghanistan"),
    "ag": ("ATG", "Antigua and Barbuda"),
    "ai": ("AIA", "Anguilla"),
    "al": ("ALB", "Albania"),
    "am": ("ARM", "Armenia"),
    "ao": ("AGO", "Angola"),
    "aq": ("ATA", "Antarctica"),
    "ar": ("ARG", "Argentina"),
    "as": ("ASM", "American Samoa"),
    "at": ("AUT", "Austria"),
    "au": ("AUS", "Australia"),
    "aw": ("ABW", "Aruba"),
    "ax": ("ALA", "Åland Islands"),
    "az": ("AZE", "Azerbaijan"),
    "ba": ("BIH", "Bosnia and Herzegovina"),
    "bb": ("BRB", "Barbados"),
    "bd": ("BGD", "Bangladesh"),
    "be": ("BEL", "Belgium"),
    "bf": ("BFA", "Burkina Faso"),
    "bg": ("BGR", "Bulgaria"),
    "bh": ("BHR", "Bahrain"),
    "bi": ("BDI", "Burundi"),
    "bj": ("BEN", "Benin"),
    "bl": ("BLM", "Saint Barthélemy"),
    "bm": ("BMU", "Bermuda"),
    "bn": ("BRN", "Brunei"),
    "bo": ("BOL", "Bolivia"),
    "bq": ("BES", "Caribbean Netherlands"),
    "br": ("BRA", "Brazil"),
    "bs": ("BHS", "Bahamas"),
    "bt": ("BTN", "Bhutan"),
    "bv": ("BVT", "Bouvet Island"),
    "bw": ("BWA", "Botswana"),
    "by": ("BLR", "Belarus"),
    "bz": ("BLZ", "Belize"),
    "ca": ("CAN", "Canada"),
    "cc": ("CCK", "Cocos (Keeling) Islands"),
    "cd": ("COD", "DR Congo"),
    "cf": ("CAF", "Central African Republic"),
    "cg": ("COG", "Republic of the Congo"),
    "ch": ("CHE", "Switzerland"),
    "ci": ("CIV", "Côte d'Ivoire"),
    "ck": ("COK", "Cook Islands"),
    "cl": ("CHL", "Chile"),
    "cm": ("CMR", "Cameroon"),
    "cn": ("CHN", "China"),
    "co": ("COL", "Colombia"),
    "cp": ("CPT", "Clipperton Island"),
    "cr": ("CRI", "Costa Rica"),
    "cu": ("CUB", "Cuba"),
    "cv": ("CPV", "Cape Verde"),
    "cw": ("CUW", "Curaçao"),
    "cx": ("CXR", "Christmas Island"),
    "cy": ("CYP", "Cyprus"),
    "cz": ("CZE", "Czech Republic"),
    "de": ("DEU", "Germany"),
    "dg": ("DGA", "Diego Garcia"),
    "dj": ("DJI", "Djibouti"),
    "dk": ("DNK", "Denmark"),
    "dm": ("DMA", "Dominica"),
    "do": ("DOM", "Dominican Republic"),
    "dz": ("DZA", "Algeria"),
    "ec": ("ECU", "Ecuador"),
    "ee": ("EST", "Estonia"),
    "eg": ("EGY", "Egypt"),
    "eh": ("ESH", "Western Sahara"),
    "er": ("ERI", "Eritrea"),
    "es": ("ESP", "Spain"),
    "et": ("ETH", "Ethiopia"),
    "fi": ("FIN", "Finland"),
    "fj": ("FJI", "Fiji"),
    "fk": ("FLK", "Falkland Islands"),
    "fm": ("FSM", "Micronesia"),
    "fo": ("FRO", "Faroe Islands"),
    "fr": ("FRA", "France"),
    "ga": ("GAB", "Gabon"),
    "gb": ("GBR", "United Kingdom"),
    "gd": ("GRD", "Grenada"),
    "ge": ("GEO", "Georgia"),
    "gf": ("GUF", "French Guiana"),
    "gg": ("GGY", "Guernsey"),
    "gh": ("GHA", "Ghana"),
    "gi": ("GIB", "Gibraltar"),
    "gl": ("GRL", "Greenland"),
    "gm": ("GMB", "Gambia"),
    "gn": ("GIN", "Guinea"),
    "gp": ("GLP", "Guadeloupe"),
    "gq": ("GNQ", "Equatorial Guinea"),
    "gr": ("GRC", "Greece"),
    "gs": ("SGS", "South Georgia and the South Sandwich Islands"),
    "gt": ("GTM", "Guatemala"),
    "gu": ("GUM", "Guam"),
    "gw": ("GNB", "Guinea-Bissau"),
    "gy": ("GUY", "Guyana"),
    "hk": ("HKG", "Hong Kong"),
    "hm": ("HMD", "Heard Island and McDonald Islands"),
    "hn": ("HND", "Honduras"),
    "hr": ("HRV", "Croatia"),
    "ht": ("HTI", "Haiti"),
    "hu": ("HUN", "Hungary"),
    "ic": ("ICA", "Canary Islands"),
    "id": ("IDN", "Indonesia"),
    "ie": ("IRL", "Ireland"),
    "il": ("ISR", "Israel"),
    "im": ("IMN", "Isle of Man"),
    "in": ("IND", "India"),
    "io": ("IOT", "British Indian Ocean Territory"),
    "iq": ("IRQ", "Iraq"),
    "ir": ("IRN", "Iran"),
    "is": ("ISL", "Iceland"),
    "it": ("ITA", "Italy"),
    "je": ("JEY", "Jersey"),
    "jm": ("JAM", "Jamaica"),
    "jo": ("JOR", "Jordan"),
    "jp": ("JPN", "Japan"),
    "ke": ("KEN", "Kenya"),
    "kg": ("KGZ", "Kyrgyzstan"),
    "kh": ("KHM", "Cambodia"),
    "ki": ("KIR", "Kiribati"),
    "km": ("COM", "Comoros"),
    "kn": ("KNA", "Saint Kitts and Nevis"),
    "kp": ("PRK", "North Korea"),
    "kr": ("KOR", "South Korea"),
    "kw": ("KWT", "Kuwait"),
    "ky": ("CYM", "Cayman Islands"),
    "kz": ("KAZ", "Kazakhstan"),
    "la": ("LAO", "Laos"),
    "lb": ("LBN", "Lebanon"),
    "lc": ("LCA", "Saint Lucia"),
    "li": ("LIE", "Liechtenstein"),
    "lk": ("LKA", "Sri Lanka"),
    "lr": ("LBR", "Liberia"),
    "ls": ("LSO", "Lesotho"),
    "lt": ("LTU", "Lithuania"),
    "lu": ("LUX", "Luxembourg"),
    "lv": ("LVA", "Latvia"),
    "ly": ("LBY", "Libya"),
    "ma": ("MAR", "Morocco"),
    "mc": ("MCO", "Monaco"),
    "md": ("MDA", "Moldova"),
    "me": ("MNE", "Montenegro"),
    "mf": ("MAF", "Saint Martin"),
    "mg": ("MDG", "Madagascar"),
    "mh": ("MHL", "Marshall Islands"),
    "mk": ("MKD", "North Macedonia"),
    "ml": ("MLI", "Mali"),
    "mm": ("MMR", "Myanmar"),
    "mn": ("MNG", "Mongolia"),
    "mo": ("MAC", "Macau"),
    "mp": ("MNP", "Northern Mariana Islands"),
    "mq": ("MTQ", "Martinique"),
    "mr": ("MRT", "Mauritania"),
    "ms": ("MSR", "Montserrat"),
    "mt": ("MLT", "Malta"),
    "mu": ("MUS", "Mauritius"),
    "mv": ("MDV", "Maldives"),
    "mw": ("MWI", "Malawi"),
    "mx": ("MEX", "Mexico"),
    "my": ("MYS", "Malaysia"),
    "mz": ("MOZ", "Mozambique"),
    "na": ("NAM", "Namibia"),
    "nc": ("NCL", "New Caledonia"),
    "ne": ("NER", "Niger"),
    "nf": ("NFK", "Norfolk Island"),
    "ng": ("NGA", "Nigeria"),
    "ni": ("NIC", "Nicaragua"),
    "nl": ("NLD", "Netherlands"),
    "no": ("NOR", "Norway"),
    "np": ("NPL", "Nepal"),
    "nr": ("NRU", "Nauru"),
    "nu": ("NIU", "Niue"),
    "nz": ("NZL", "New Zealand"),
    "om": ("OMN", "Oman"),
    "pa": ("PAN", "Panama"),
    "pc": ("PCN", "Pacific Community"),
    "pe": ("PER", "Peru"),
    "pf": ("PYF", "French Polynesia"),
    "pg": ("PNG", "Papua New Guinea"),
    "ph": ("PHL", "Philippines"),
    "pk": ("PAK", "Pakistan"),
    "pl": ("POL", "Poland"),
    "pm": ("SPM", "Saint Pierre and Miquelon"),
    "pn": ("PCN", "Pitcairn Islands"),
    "pr": ("PRI", "Puerto Rico"),
    "ps": ("PSE", "Palestine"),
    "pt": ("PRT", "Portugal"),
    "pw": ("PLW", "Palau"),
    "py": ("PRY", "Paraguay"),
    "qa": ("QAT", "Qatar"),
    "re": ("REU", "Réunion"),
    "ro": ("ROU", "Romania"),
    "rs": ("SRB", "Serbia"),
    "ru": ("RUS", "Russia"),
    "rw": ("RWA", "Rwanda"),
    "sa": ("SAU", "Saudi Arabia"),
    "sb": ("SLB", "Solomon Islands"),
    "sc": ("SYC", "Seychelles"),
    "sd": ("SDN", "Sudan"),
    "se": ("SWE", "Sweden"),
    "sg": ("SGP", "Singapore"),
    "sh": ("SHN", "Saint Helena"),
    "si": ("SVN", "Slovenia"),
    "sj": ("SJM", "Svalbard and Jan Mayen"),
    "sk": ("SVK", "Slovakia"),
    "sl": ("SLE", "Sierra Leone"),
    "sm": ("SMR", "San Marino"),
    "sn": ("SEN", "Senegal"),
    "so": ("SOM", "Somalia"),
    "sr": ("SUR", "Suriname"),
    "ss": ("SSD", "South Sudan"),
    "st": ("STP", "São Tomé and Príncipe"),
    "sv": ("SLV", "El Salvador"),
    "sx": ("SXM", "Sint Maarten"),
    "sy": ("SYR", "Syria"),
    "sz": ("SWZ", "Eswatini"),
    "tc": ("TCA", "Turks and Caicos Islands"),
    "td": ("TCD", "Chad"),
    "tf": ("ATF", "French Southern Territories"),
    "tg": ("TGO", "Togo"),
    "th": ("THA", "Thailand"),
    "tj": ("TJK", "Tajikistan"),
    "tk": ("TKL", "Tokelau"),
    "tl": ("TLS", "Timor-Leste"),
    "tm": ("TKM", "Turkmenistan"),
    "tn": ("TUN", "Tunisia"),
    "to": ("TON", "Tonga"),
    "tr": ("TUR", "Turkey"),
    "tt": ("TTO", "Trinidad and Tobago"),
    "tv": ("TUV", "Tuvalu"),
    "tw": ("TWN", "Taiwan"),
    "tz": ("TZA", "Tanzania"),
    "ua": ("UKR", "Ukraine"),
    "ug": ("UGA", "Uganda"),
    "um": ("UMI", "United States Minor Outlying Islands"),
    "us": ("USA", "United States"),
    "uy": ("URY", "Uruguay"),
    "uz": ("UZB", "Uzbekistan"),
    "va": ("VAT", "Vatican City"),
    "vc": ("VCT", "Saint Vincent and the Grenadines"),
    "ve": ("VEN", "Venezuela"),
    "vg": ("VGB", "British Virgin Islands"),
    "vi": ("VIR", "United States Virgin Islands"),
    "vn": ("VNM", "Vietnam"),
    "vu": ("VUT", "Vanuatu"),
    "wf": ("WLF", "Wallis and Futuna"),
    "ws": ("WSM", "Samoa"),
    "xk": ("XKX", "Kosovo"),
    "ye": ("YEM", "Yemen"),
    "yt": ("MYT", "Mayotte"),
    "za": ("ZAF", "South Africa"),
    "zm": ("ZMB", "Zambia"),
    "zw": ("ZWE", "Zimbabwe"),
    # Special / regional codes
    "arab":    ("ARAB",   "Arab League"),
    "asean":   ("ASEAN",  "ASEAN"),
    "cefta":   ("CEFTA",  "Central European Free Trade Agreement"),
    "eac":     ("EAC",    "East African Community"),
    "eu":      ("EU",     "European Union"),
    "un":      ("UN",     "United Nations"),
    "xx":      ("XX",     "Unknown"),
    "es-ct":   ("ES-CT",  "Catalonia"),
    "es-ga":   ("ES-GA",  "Galicia"),
    "es-pv":   ("ES-PV",  "Basque Country"),
    "gb-eng":  ("GB-ENG", "England"),
    "gb-nir":  ("GB-NIR", "Northern Ireland"),
    "gb-sct":  ("GB-SCT", "Scotland"),
    "gb-wls":  ("GB-WLS", "Wales"),
    "sh-ac":   ("SH-AC",  "Ascension Island"),
    "sh-hl":   ("SH-HL",  "Saint Helena"),
    "sh-ta":   ("SH-TA",  "Tristan da Cunha"),
}


def parse_filename(filename):
    """Parse 'NNN_cc.svg' or 'NNN-cc.svg' → (id, code)."""
    name = os.path.splitext(filename)[0]          # strip .svg
    match = re.match(r'^(\d{3})[-_](.+)$', name)
    if not match:
        return None, None
    return match.group(1), match.group(2).lower()


def generate_index(flags_dir, output_file=None):
    svgs = sorted(
        f for f in os.listdir(flags_dir) if f.endswith('.svg')
    )

    entries = []
    unknown = []

    for filename in svgs:
        file_id, code = parse_filename(filename)
        if file_id is None:
            print(f"  [SKIP] Could not parse: {filename}")
            continue

        if code in ISO2_MAP:
            iso3, description = ISO2_MAP[code]
        else:
            iso3 = code.upper()
            description = f"Unknown ({code})"
            unknown.append(filename)

        entries.append({
            "id": file_id,
            "name": iso3,
            "file": filename,
            "description": description,
        })

    if unknown:
        print(f"  [WARN] {len(unknown)} unrecognised code(s): {unknown}")

    result = json.dumps(entries, indent=2, ensure_ascii=False)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Written {len(entries)} entries → {output_file}")
    else:
        print(result)

    return entries


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <flags_directory> [output.json]")
        sys.exit(1)

    flags_dir  = sys.argv[1]
    output     = sys.argv[2] if len(sys.argv) > 2 else None
    generate_index(flags_dir, output)
