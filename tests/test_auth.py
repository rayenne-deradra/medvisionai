"""Activation-code licensing: format, hashing, expiry, revocation and brute-force lockout."""
from datetime import date

import pytest

from medvision.auth import (MAX_ATTEMPTS, ActivationError, AttemptLimiter, code_hash, generate_code, normalise,
                            verify)

SECRET = "test-secret"


def licences(code, **extra):
    return {"acme": {"hash": code_hash(code, SECRET), "organisation": "Acme Hospital", "plan": "Research", **extra}}


def test_generated_codes_are_unique_and_well_formed():
    codes = {generate_code() for _ in range(200)}
    assert len(codes) == 200
    assert all(normalise(c) == c and len(c) == 24 for c in codes)


def test_code_is_accepted_regardless_of_case_spaces_and_dashes():
    code = generate_code()
    sloppy = code.lower().replace("-", " ")
    lic = verify(sloppy, SECRET, licences(code))
    assert lic.organisation == "Acme Hospital" and lic.licence_id == "acme"


def test_wrong_malformed_expired_and_revoked_codes_are_rejected():
    code = generate_code()
    with pytest.raises(ActivationError, match="not valid"):
        verify(generate_code(), SECRET, licences(code))
    with pytest.raises(ActivationError, match="doesn't look like"):
        verify("hello", SECRET, licences(code))
    with pytest.raises(ActivationError, match="expired"):
        verify(code, SECRET, licences(code, expires="2026-01-31"), today=date(2026, 2, 1))
    assert verify(code, SECRET, licences(code, expires="2026-01-31"), today=date(2026, 1, 31))
    with pytest.raises(ActivationError, match="deactivated"):
        verify(code, SECRET, licences(code, active=False))
    with pytest.raises(ActivationError, match="not valid"):          # a different secret gives other hashes
        verify(code, "other-secret", licences(code))


def test_hash_does_not_contain_the_code():
    code = generate_code()
    assert code.replace("-", "") not in code_hash(code, SECRET).upper()


def test_lockout_after_repeated_failures():
    state = {}
    lim = AttemptLimiter(state)
    for _ in range(MAX_ATTEMPTS - 1):
        lim.failed()
    assert lim.locked_for() == 0
    lim.failed()
    assert lim.locked_for() > 0
    lim.succeeded()
    assert lim.locked_for() == 0


def test_remember_device_token_round_trip_and_tampering():
    from medvision.auth import Licence, make_device_token, read_device_token
    code = generate_code()
    table = licences(code)
    lic = verify(code, SECRET, table)
    token = make_device_token(lic, SECRET)
    assert code.replace("-", "") not in token                      # the code itself is never in the cookie
    assert read_device_token(token, SECRET, table).organisation == "Acme Hospital"
    assert read_device_token(token, "other-secret", table) is None            # forged / wrong secret
    assert read_device_token(token[:-2] + "xx", SECRET, table) is None        # tampered signature
    assert read_device_token("garbage", SECRET, table) is None
    assert read_device_token(token, SECRET, table, now=10**12) is None         # token expired
    assert read_device_token(token, SECRET, licences(code, active=False)) is None   # licence revoked
    assert read_device_token(token, SECRET, {}) is None                       # licence deleted
    short = Licence("acme", "Acme", "", date(2000, 1, 1))
    assert read_device_token(make_device_token(short, SECRET), SECRET, table) is None   # capped by licence expiry


def test_browser_scripts_save_clear_and_restore():
    from medvision.auth import DEVICE_KEY, DEVICE_PARAM, restore_script, storage_script
    assert f'localStorage.setItem("{DEVICE_KEY}", "abc.123.sig")' in storage_script("abc.123.sig")
    assert f'localStorage.removeItem("{DEVICE_KEY}")' in storage_script(None)
    assert f'"{DEVICE_PARAM}"' in restore_script() and "location.replace" in restore_script()
