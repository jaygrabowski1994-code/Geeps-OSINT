"""
Phone Investigation module.

Core checks run entirely offline via Google's libphonenumber (the
`phonenumbers` package): validity, number type (mobile/landline/VoIP),
region, timezone(s), and the carrier at time of number assignment.
This is all public, static metadata baked into the library -- no
lookups against a live person, no spoofed caller ID, no SMS pinging.

Optional live carrier/line-type verification via numverify.com runs
only if the user has configured an API key.
"""

from __future__ import annotations

from core.config import get as config_get
from core.logger import get_logger
from core.netutils import get
from core.ui import banner, clear, err, info, ok, pause, prompt, section, warn

log = get_logger("phone")


def _offline_lookup(raw_number: str) -> None:
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone

    try:
        parsed = phonenumbers.parse(raw_number, None)
    except phonenumbers.NumberParseException as exc:
        err(f"Could not parse number: {exc}. Try including the country code, e.g. +1..., +44...")
        return None

    valid = phonenumbers.is_valid_number(parsed)
    possible = phonenumbers.is_possible_number(parsed)

    if valid:
        ok("Number is valid.")
    elif possible:
        warn("Number has a plausible format but failed full validation.")
    else:
        err("Number does not look possible for its region.")

    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    intl = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    info(f"E.164 format: {e164}")
    info(f"International format: {intl}")

    region = geocoder.description_for_number(parsed, "en") or "unknown"
    info(f"Region: {region}")

    carrier_name = carrier.name_for_number(parsed, "en") or "unknown / not carrier-mappable"
    info(f"Carrier (at assignment): {carrier_name}")

    zones = timezone.time_zones_for_number(parsed)
    info(f"Possible timezone(s): {', '.join(zones) if zones else 'unknown'}")

    number_type = phonenumbers.number_type(parsed)
    type_names = {
        0: "FIXED_LINE", 1: "MOBILE", 2: "FIXED_LINE_OR_MOBILE",
        3: "TOLL_FREE", 4: "PREMIUM_RATE", 5: "SHARED_COST",
        6: "VOIP", 7: "PERSONAL_NUMBER", 8: "PAGER",
        9: "UAN", 10: "VOICEMAIL", 27: "UNKNOWN",
    }
    info(f"Line type: {type_names.get(number_type, 'UNKNOWN')}")

    return e164


def _numverify_lookup(e164_number: str) -> None:
    api_key = config_get("api_keys.numverify_api_key", "")
    if not api_key:
        info("Live carrier/line verification skipped (no numverify API key configured).")
        return

    result = get(
        "http://apilayer.net/api/validate",
        params={"access_key": api_key, "number": e164_number},
        expect_json=True,
    )
    if not result.ok or not result.json_data:
        warn(f"Live verification lookup failed ({result.error or 'no data'}).")
        return

    data = result.json_data
    if not data.get("valid"):
        warn("Live verification service reports this number as invalid.")
        return

    ok("Live verification (numverify):")
    info(f"  Line type: {data.get('line_type', 'unknown')}")
    info(f"  Carrier: {data.get('carrier', 'unknown')}")
    info(f"  Location: {data.get('location', 'unknown')}, {data.get('country_name', '')}")


def run() -> None:
    clear()
    banner("PHONE INVESTIGATION")
    print("Validates a phone number and reports publicly known, static\n"
          "metadata: region, timezone, and carrier at time of assignment.\n"
          "Include the country code, e.g. +14155552671\n")

    raw_number = prompt("Enter phone number to investigate")
    if not raw_number:
        warn("No number entered. Returning to menu.")
        pause()
        return

    log.info("Phone investigation started")

    section("Offline validation (libphonenumber)")
    try:
        e164 = _offline_lookup(raw_number)
    except ImportError:
        err("The 'phonenumbers' package is not installed. Run Health Check to install dependencies.")
        pause()
        return
    except Exception:
        log.exception("Unexpected error during offline phone lookup")
        err("Unexpected error during validation.")
        pause()
        return

    if e164:
        section("Live carrier/line verification (optional)")
        try:
            _numverify_lookup(e164)
        except Exception:
            log.exception("Unexpected error during numverify lookup")
            err("Unexpected error during live verification -- skipping.")

    log.info("Phone investigation complete")
    pause()
