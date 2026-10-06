"""tests/test_l0_check.py -- l0_check.py (L0 daily check, TRIGGERS.md section 1/2/6).

Every HTTP call is monkeypatched (`l0_check._get`) against real captured fixtures under
tests/fixtures/l0_check/ (TMD CAP feed + 3 real item XMLs, a real thaiwater rain_24h row
for BKK008, a real Open-Meteo 7-day response, and the real trimmed BMA StationDetail
page for WL.SMK.01/id284 already used elsewhere in this suite) -- no network, no write
under raw/ (`l0_check.RAW_LIVE_DIR` is pointed at a tmp_path for every test, per this
suite's own real-data/no-tracked-mutation rules, see conftest.py)."""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

import l0_check

FIXTURES = Path(__file__).parent / "fixtures" / "l0_check"
BMA_FIXTURES = Path(__file__).parent / "fixtures" / "bma_station_detail"


@pytest.fixture(autouse=True)
def _isolate_raw(tmp_path, monkeypatch):
    """Every test gets its own throwaway raw/live/ dir -- never the real repo tree."""
    monkeypatch.setattr(l0_check, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    l0_check._cap_item_cache.clear()
    l0_check._BMA_DETAIL_HTML_CACHE.clear()
    yield
    l0_check._cap_item_cache.clear()
    l0_check._BMA_DETAIL_HTML_CACHE.clear()


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ---------------------------------------------------------------------------
# CAP matching (section 1A)
# ---------------------------------------------------------------------------

def test_cap_sev_match_drills_not_card(monkeypatch):
    """T01: TMD20261006060902_2, Heavy Rain/Severe, 06:00-18:00 TH-10, user Bangkok,
    now inside the window -> CAP-SEV fires (never CARD on its own), colour_floor
    YELLOW, first evidence line names the event."""
    feed = _read("cap_feed.xml")
    item = _read("cap_item_1.xml")

    def fake_get(url, **kw):
        if url == l0_check.TMD_CAP_FEED_URL:
            return 200, feed
        return 200, item  # every item link in this fixture's feed -> the one real item

    monkeypatch.setattr(l0_check, "_get", fake_get)
    now = datetime.datetime(2026, 10, 6, 9, 20, tzinfo=datetime.timezone.utc)  # 16:20 +07
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)

    point = {"iso": "TH-10", "province_th": "กรุงเทพมหานคร"}
    out = l0_check.evaluate_cap(point)
    assert "CAP-SEV" in out["reasons"]
    assert "CARD" not in out["reasons"]
    assert out["colour_floor"] == "YELLOW"
    # live run, 2026-10-06: the feed's own Thai <item><title>
    # ("ฝนตกหนัก") is used, never the CAP <info><event> field's English text
    # ("Heavy Rain") -- see cap_feed.xml's real <title>.
    assert "ฝนตกหนัก" in out["phrases"]["CAP-SEV"]
    assert "Heavy Rain" not in out["phrases"]["CAP-SEV"]
    assert "กรุงเทพมหานคร" in out["phrases"]["CAP-SEV"]


def test_cap_falls_back_to_english_event_when_feed_title_missing(monkeypatch):
    """live run, 2026-10-06: the Thai feed <item><title> is the normal case and always
    preferred -- but a feed item with NO title at all (never observed live, kept as
    an honest fallback rather than crashing or showing a blank event) must still
    fall back to the CAP <info><event> field (English, per the real feed) rather
    than an empty/blank phrase."""
    item = _read("cap_item_1.xml")
    bare_feed = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<rss><channel><item>'
        b'<link>https://www.tmd.go.th/uploads/CAP/CAPTMD20261006060902_2.xml</link>'
        b'<guid>g1</guid>'
        b'</item></channel></rss>'
    )

    def fake_get(url, **kw):
        if url == l0_check.TMD_CAP_FEED_URL:
            return 200, bare_feed
        return 200, item

    monkeypatch.setattr(l0_check, "_get", fake_get)
    now = datetime.datetime(2026, 10, 6, 9, 20, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)

    point = {"iso": "TH-10", "province_th": "กรุงเทพมหานคร"}
    out = l0_check.evaluate_cap(point)
    assert "CAP-SEV" in out["reasons"]
    assert "Heavy Rain" in out["phrases"]["CAP-SEV"]


def test_cap_expired_item_does_not_fire(monkeypatch):
    """T03: CAPTMD20261005175406_2, Severe, 2026-10-05 18:00 -> 2026-10-06 06:00,
    TH-10. At 2026-10-06 16:20 +07 it has expired -- must not fire."""
    feed = _read("cap_feed.xml")
    item = _read("CAPTMD20261005175406_2.xml")
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (
        (200, feed) if url == l0_check.TMD_CAP_FEED_URL else (200, item)))
    now = datetime.datetime(2026, 10, 6, 9, 20, tzinfo=datetime.timezone.utc)  # 16:20 +07
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)

    out = l0_check.evaluate_cap({"iso": "TH-10", "province_th": "กรุงเทพมหานคร"})
    assert "CAP-SEV" not in out["reasons"]


def test_cap_expired_item_fires_when_still_inside_window(monkeypatch):
    """Same item as above, but `now` moved inside its own effective/expires window --
    confirms the fixture/parsing is correct and the expiry check (not a different bug)
    is what suppressed the previous test."""
    feed = _read("cap_feed.xml")
    item = _read("CAPTMD20261005175406_2.xml")
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (
        (200, feed) if url == l0_check.TMD_CAP_FEED_URL else (200, item)))
    now = datetime.datetime(2026, 10, 5, 13, 0, tzinfo=datetime.timezone.utc)  # 20:00 +07
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)

    out = l0_check.evaluate_cap({"iso": "TH-10", "province_th": "กรุงเทพมหานคร"})
    assert "CAP-SEV" in out["reasons"]
    assert out["colour_floor"] == "YELLOW"


def test_cap_substring_trap_thani(monkeypatch):
    """T05: areaDesc token-equality must not let 'ธานี' substrings leak a match --
    a user province 'อุดรธานี' must not match an areaDesc containing 'ปทุมธานี
    อุทัยธานี สุราษฎร์ธานี' (all real tokens in cap_item_1.xml's own areaDesc)."""
    feed = _read("cap_feed.xml")
    item = _read("cap_item_1.xml")
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (
        (200, feed) if url == l0_check.TMD_CAP_FEED_URL else (200, item)))
    now = datetime.datetime(2026, 10, 6, 9, 20, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)

    out = l0_check.evaluate_cap({"iso": "TH-41", "province_th": "อุดรธานี"})
    assert "CAP-SEV" not in out["reasons"]
    assert "CAP-ANY" not in out["reasons"]


def test_cap_feed_fetch_failure_is_fail_not_quiet(monkeypatch):
    def boom(url, **kw):
        raise l0_check.L0FetchError("simulated network failure")
    monkeypatch.setattr(l0_check, "_get", boom)
    out = l0_check.evaluate_cap({"iso": "TH-10", "province_th": "กรุงเทพมหานคร"})
    assert out["reasons"] == ["CAP-FAIL"]


def test_cap_no_province_never_matches():
    """A point with no resolved province/iso (bare coordinate) must never match --
    this function does not guess a province from lat/lon."""
    info = {"geocodes": [("ISO3166-2", "TH-10")], "areaDesc": "กรุงเทพมหานคร"}
    assert l0_check._cap_match(info, None, None) is None


# ---------------------------------------------------------------------------
# Rain (section 1B)
# ---------------------------------------------------------------------------

SAMMAKORN = l0_check.POINTS["sammakorn"]


def test_rain_below_heavy_band_no_rain_num(monkeypatch):
    """T08: BKK008 real row, 33.6mm < 35.1mm TMD 'heavy rain' lower bound ->
    RAIN-SHOW only, never RAIN-NUM, even though the forecast fixture used here also
    stays under the band."""
    rain_body = _read("rain_24h_trimmed.json")
    fcst_body = _read("openmeteo_7d_sammakorn.json")

    def fake_get(url, **kw):
        if url == l0_check.THAIWATER_RAIN24H_URL:
            return 200, rain_body
        return 200, fcst_body

    monkeypatch.setattr(l0_check, "_get", fake_get)
    payload = json.loads(rain_body)
    today_local = payload["data"][0]["rainfall_datetime"][:10]
    bkk_now = datetime.datetime.fromisoformat(today_local) - datetime.timedelta(hours=7)
    monkeypatch.setattr(l0_check, "_utcnow",
                         lambda: bkk_now.replace(tzinfo=datetime.timezone.utc))

    out = l0_check.evaluate_rain(SAMMAKORN)
    assert out["observed"]["mm_24h"] == 33.6
    assert "RAIN-NUM" not in out["reasons"]
    assert "RAIN-FAIL" not in out["reasons"]


def test_rain_num_fires_from_forecast(monkeypatch):
    """Same observed row (33.6mm, under the band) but a forecast day >= 35.1mm must
    still fire RAIN-NUM -- 'any(precipitation_sum in 7 days >= 35.1)' is a real,
    separate OR-branch, not just the observed-today value."""
    rain_body = _read("rain_24h_trimmed.json")
    fcst = json.loads(_read("openmeteo_7d_sammakorn.json"))
    fcst["daily"]["precipitation_sum"][2] = 40.0  # real fixture's 3rd day, bumped
    fcst_body = json.dumps(fcst).encode("utf-8")

    def fake_get(url, **kw):
        if url == l0_check.THAIWATER_RAIN24H_URL:
            return 200, rain_body
        return 200, fcst_body

    monkeypatch.setattr(l0_check, "_get", fake_get)
    payload = json.loads(rain_body)
    today_local = payload["data"][0]["rainfall_datetime"][:10]
    bkk_now = datetime.datetime.fromisoformat(today_local) - datetime.timedelta(hours=7)
    monkeypatch.setattr(l0_check, "_utcnow",
                         lambda: bkk_now.replace(tzinfo=datetime.timezone.utc))

    out = l0_check.evaluate_rain(SAMMAKORN)
    assert "RAIN-NUM" in out["reasons"]
    assert "40" in out["phrases"]["RAIN-NUM"]


def test_rain_stale_when_observed_date_not_today(monkeypatch):
    rain_body = _read("rain_24h_trimmed.json")
    fcst_body = _read("openmeteo_7d_sammakorn.json")
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (
        (200, rain_body) if url == l0_check.THAIWATER_RAIN24H_URL else (200, fcst_body)))
    # Real observed row is for one fixed date; push "now" two days later.
    payload = json.loads(rain_body)
    today_local = payload["data"][0]["rainfall_datetime"][:10]
    bkk_now = datetime.datetime.fromisoformat(today_local) + datetime.timedelta(days=2)
    monkeypatch.setattr(l0_check, "_utcnow",
                         lambda: (bkk_now - datetime.timedelta(hours=7)).replace(
                             tzinfo=datetime.timezone.utc))

    out = l0_check.evaluate_rain(SAMMAKORN)
    assert "RAIN-STALE" in out["reasons"]


def test_rain_nogauge_for_undeclared_point():
    """ram53 has no declared rain-gauge KG edge -- RAIN-NOGAUGE, never a nearest-pick."""
    out = l0_check.evaluate_rain(l0_check.POINTS["ram53"])
    assert out["reasons"] == ["RAIN-NOGAUGE"]


def test_rain_fetch_failure_is_fail(monkeypatch):
    def boom(url, **kw):
        raise l0_check.L0FetchError("simulated")
    monkeypatch.setattr(l0_check, "_get", boom)
    out = l0_check.evaluate_rain(SAMMAKORN)
    assert out["reasons"] == ["RAIN-FAIL"]


def test_forecast_fetch_failure_is_fcst_fail(monkeypatch):
    rain_body = _read("rain_24h_trimmed.json")

    def fake_get(url, **kw):
        if url == l0_check.THAIWATER_RAIN24H_URL:
            return 200, rain_body
        raise l0_check.L0FetchError("simulated forecast outage")

    monkeypatch.setattr(l0_check, "_get", fake_get)
    payload = json.loads(rain_body)
    today_local = payload["data"][0]["rainfall_datetime"][:10]
    bkk_now = datetime.datetime.fromisoformat(today_local) - datetime.timedelta(hours=7)
    monkeypatch.setattr(l0_check, "_utcnow",
                         lambda: bkk_now.replace(tzinfo=datetime.timezone.utc))

    out = l0_check.evaluate_rain(SAMMAKORN)
    assert "FCST-FAIL" in out["reasons"]


# ---------------------------------------------------------------------------
# Z0 (section 1C)
# ---------------------------------------------------------------------------

def test_z0_real_sparse_fixture_gives_notrend_never_flat(monkeypatch):
    """Real id284/WL.SMK.01 trimmed page (6 real points, 2-day gaps): warning=0.35,
    critical=0.44, last reading h=-0.45 -- below both thresholds, and the real series
    has no point near 1h before the last reading, so trend must be Z0-NOTREND
    (UNKNOWN), never silently FLAT/STABLE."""
    html = (BMA_FIXTURES / "stationdetail_id284_20261005_trimmed.html").read_bytes()
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (200, html))

    out = l0_check.evaluate_z0(SAMMAKORN)
    assert out["h"] == -0.45
    assert "Z0-WARN" not in out["reasons"]
    assert "Z0-CRIT" not in out["reasons"]
    assert "Z0-NOTREND" in out["reasons"]
    assert out["trend"] == "UNKNOWN"


def test_z0_crit_fires_above_critical(monkeypatch):
    html = (BMA_FIXTURES / "stationdetail_id284_20261005_trimmed.html").read_text(encoding="utf-8")
    # Real fixture's last two real points are both -0.45; bump them above the real
    # critical=0.44 threshold to exercise CRIT without inventing a new station.
    html = html.replace("-0.45", "0.50")
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (200, html.encode("utf-8")))

    out = l0_check.evaluate_z0(SAMMAKORN)
    assert out["h"] == 0.50
    assert "Z0-CRIT" in out["reasons"]


def test_z0_rising_carries_a_short_eta_in_its_own_phrase(monkeypatch):
    """Mutation-protecting (short ETA in the l0_check line when Z0 is RISING):
    the real WL.KJK.02 page `tests/test_kb_answer_sandwich.py`'s own short-lag
    regression also replays (series real last point 17:15:00Z, one real 5-min
    step past this fixture's own "now" of 17:10:00Z) is RISING with a published
    warning threshold -- `evaluate_z0`'s own Z0-RISE phrase must carry a real
    ETA range, not only the raw delta/lag, and the WHOLE phrase must stay
    comfortably inside this module's own <=50 o200k-token line budget (see
    `test_quiet_line_is_within_token_budget`/`test_escalate_line_is_within_token_
    budget` below) even with a real reason id, source timestamp and action
    appended around it."""
    tiktoken = pytest.importorskip("tiktoken")
    html = (BMA_FIXTURES / "stationdetail_id199_20261006_series_ahead_of_reading_"
            "trimmed.html").read_bytes()
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (200, html))
    now = datetime.datetime(2026, 10, 6, 17, 10, 0, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)

    out = l0_check.evaluate_z0(SAMMAKORN)
    assert out["trend"] == "RISING"
    assert "Z0-RISE" in out["reasons"]
    phrase = out["phrases"]["Z0-RISE"]
    assert "ETA" in phrase or any(ch.isdigit() for ch in phrase), phrase
    assert out["eta"] is not None
    assert out["eta"]["critical"]["status"] == "OK" or out["eta"]["warning"]["status"] == "OK"

    full_line = f"ขยับ:ใช่|Z0-RISE|{phrase}|{out['observed_at_utc']}|→H1"
    enc = tiktoken.get_encoding("o200k_base")
    n = len(enc.encode(full_line))
    assert n <= 50, f"RISING Z0-RISE line used {n} o200k tokens: {full_line!r}"


def test_z0_no_config_is_miss():
    out = l0_check.evaluate_z0(l0_check.POINTS["ram53"])
    assert out["reasons"] == ["Z0-MISS"]


def test_z0_fetch_failure_is_miss(monkeypatch):
    def boom(url, **kw):
        raise l0_check.L0FetchError("simulated")
    monkeypatch.setattr(l0_check, "_get", boom)
    out = l0_check.evaluate_z0(SAMMAKORN)
    assert out["reasons"] == ["Z0-MISS"]


def test_z0_trend_state_pure_math_rising():
    """Pure delta_k/trend_state math (PROP-FLOOD-01), same epsilon this module uses --
    an illustrative synthetic pair (not a live claim), matching docs/EQUATIONS_FOR_AI.md's
    own worked example shape."""
    import floodconnect_model
    out = floodconnect_model.trend_state(0.38, 0.30, epsilon=l0_check.Z0_EPSILON_M)
    assert out["trend"] == "RISING"


# ---------------------------------------------------------------------------
# section 2 (QUIET) + section 6 (one line, token budget) + CA bundle
# ---------------------------------------------------------------------------

def _wire_quiet_sammakorn(monkeypatch):
    feed = _read("cap_feed.xml")
    cap_item = _read("CAPTMD20261005175054_2.xml")  # T04: Kamphaeng Phet/Sukhothai, never matches Bangkok
    rain_body = _read("rain_24h_trimmed.json")
    fcst_body = _read("openmeteo_7d_sammakorn.json")
    z0_html = (BMA_FIXTURES / "stationdetail_id284_20261005_trimmed.html").read_bytes()

    def fake_get(url, **kw):
        if url == l0_check.TMD_CAP_FEED_URL:
            return 200, feed
        if url == l0_check.THAIWATER_RAIN24H_URL:
            return 200, rain_body
        if url.startswith("https://weather.bangkok.go.th"):
            return 200, z0_html
        if url.startswith("https://api.open-meteo.com"):
            return 200, fcst_body
        return 200, cap_item  # every CAP item link

    monkeypatch.setattr(l0_check, "_get", fake_get)
    payload = json.loads(rain_body)
    today_local = payload["data"][0]["rainfall_datetime"][:10]
    now = (datetime.datetime.fromisoformat(today_local) - datetime.timedelta(hours=7)
           ).replace(tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)
    return now


def test_check_escalates_on_real_sparse_z0_even_when_cap_and_rain_are_quiet(monkeypatch):
    """Honest real-data result: CAP and rain are genuinely quiet here, but the real
    captured WL.SMK.01 series (6 points, 2-day gaps -- see
    tests/fixtures/bma_station_detail's own sidecar) has no point near the 1h trend
    lag, so Z0-NOTREND still fires and the overall flag is ESCALATE -- UNKNOWN never
    reads as QUIET, even when it is the only thing firing."""
    _wire_quiet_sammakorn(monkeypatch)
    out = l0_check.check("sammakorn")
    assert out["flag"] == "ESCALATE"
    assert out["reasons"] == ["Z0-NOTREND"]
    assert out["action"] == "H1"
    assert out["experimental"] is False


def test_check_quiet_when_z0_trend_is_resolved(monkeypatch):
    """Same CAP/rain wiring, but with a Z0 reading whose trend IS resolvable (a
    synthetic, densely-spaced series within pure trend math -- `evaluate_z0` is
    monkeypatched directly here rather than fabricating a fake live HTML page) --
    confirms `check()` reaches a real QUIET only when every one of the 3 sources is
    actually clean, not just 2 of them."""
    _wire_quiet_sammakorn(monkeypatch)
    monkeypatch.setattr(l0_check, "evaluate_z0", lambda point: {
        "reasons": [], "signals": ["Z0@2026-10-06T04:00:00Z"], "phrases": {},
        "h": 0.10, "trend": "STABLE", "observed_at_utc": "2026-10-06T04:00:00Z",
        "_display_hhmm": "11:00",
    })
    out = l0_check.check("sammakorn")
    assert out["flag"] == "QUIET"
    assert out["reasons"] == []
    assert out["line"].startswith("ปกติ|")
    assert out["experimental"] is False


def test_check_escalate_on_cap_sev(monkeypatch):
    feed = _read("cap_feed.xml")
    sev_item = _read("cap_item_1.xml")
    rain_body = _read("rain_24h_trimmed.json")
    fcst_body = _read("openmeteo_7d_sammakorn.json")
    z0_html = (BMA_FIXTURES / "stationdetail_id284_20261005_trimmed.html").read_bytes()

    def fake_get(url, **kw):
        if url == l0_check.TMD_CAP_FEED_URL:
            return 200, feed
        if url == l0_check.THAIWATER_RAIN24H_URL:
            return 200, rain_body
        if url.startswith("https://weather.bangkok.go.th"):
            return 200, z0_html
        if url.startswith("https://api.open-meteo.com"):
            return 200, fcst_body
        return 200, sev_item

    monkeypatch.setattr(l0_check, "_get", fake_get)
    now = datetime.datetime(2026, 10, 6, 9, 20, tzinfo=datetime.timezone.utc)  # 16:20 +07
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)

    out = l0_check.check("sammakorn")
    assert out["flag"] == "ESCALATE"
    assert "CAP-SEV" in out["reasons"]
    assert out["action"] == "DRILL+H2"
    assert out["line"].startswith("ขยับ:ใช่|")
    assert out["colour_floor"] == "YELLOW"


def test_check_ram53_is_experimental_and_escalates_on_gaps(monkeypatch):
    feed = _read("cap_feed.xml")
    cap_item = _read("CAPTMD20261005175054_2.xml")
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (
        (200, feed) if url == l0_check.TMD_CAP_FEED_URL else (200, cap_item)))
    out = l0_check.check("ram53")
    assert out["experimental"] is True
    assert out["flag"] == "ESCALATE"  # RAIN-NOGAUGE + Z0-MISS always fire for ram53 today
    assert "RAIN-NOGAUGE" in out["reasons"]
    assert "Z0-MISS" in out["reasons"]
    # the token-budget cap: the full `reasons` list above is never shortened -- only the
    # one printed LINE is, to a bare "+N" count past the top id, to stay <=50
    # tokens even with 3+ reasons firing at once.
    assert "+" in out["line"].split("|")[1]


def test_quiet_line_is_within_token_budget(monkeypatch):
    tiktoken = pytest.importorskip("tiktoken")
    _wire_quiet_sammakorn(monkeypatch)
    monkeypatch.setattr(l0_check, "evaluate_z0", lambda point: {
        "reasons": [], "signals": ["Z0@2026-10-06T04:00:00Z"], "phrases": {},
        "h": 0.10, "trend": "STABLE", "observed_at_utc": "2026-10-06T04:00:00Z",
        "_display_hhmm": "11:00",
    })
    out = l0_check.check("sammakorn")
    enc = tiktoken.get_encoding("o200k_base")
    n = len(enc.encode(out["line"]))
    # founder ruling 2026-10-06: the default (non --json) CLI output
    # is ONLY this one line and must stay <=50 tokens, a hard cap, not a worked
    # example's neighbourhood.
    assert n <= 50, f"quiet line used {n} o200k tokens: {out['line']!r}"


def test_escalate_line_is_within_token_budget(monkeypatch):
    tiktoken = pytest.importorskip("tiktoken")
    feed = _read("cap_feed.xml")
    sev_item = _read("cap_item_1.xml")
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (
        (200, feed) if url == l0_check.TMD_CAP_FEED_URL else (200, sev_item)))
    now = datetime.datetime(2026, 10, 6, 9, 20, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)
    cap = l0_check.evaluate_cap({"iso": "TH-10", "province_th": "กรุงเทพมหานคร"})
    reasons = cap["reasons"]
    top_id = max(reasons, key=lambda r: l0_check._ID_RANK.get(r, 0))
    line = f"ขยับ:ใช่|{top_id}|{cap['phrases'][top_id]}|{cap['signals'][0].split('@',1)[-1]}|→{l0_check._action_for(top_id)}"
    enc = tiktoken.get_encoding("o200k_base")
    n = len(enc.encode(line))
    assert n <= 50, f"escalate line used {n} o200k tokens: {line!r}"


def test_cmd_check_json_is_within_token_budget(monkeypatch, capsys):
    """the token-budget cap: `kb.py check --at ... --json` (this module's own `cmd_check`)
    MEASURED 603 o200k tokens on a live ESCALATE run, dumping `check()`'s full
    per-source `cap`/`rain`/`z0` sub-blocks and every `phrases` entry -- the CLI
    printer must stay a compact line/flag/colour_floor/reasons/times subset,
    <=150 tokens, on a real multi-reason ESCALATE result (never just a QUIET
    best case)."""
    tiktoken = pytest.importorskip("tiktoken")
    feed = _read("cap_feed.xml")
    sev_item = _read("cap_item_1.xml")
    monkeypatch.setattr(l0_check, "_get", lambda url, **kw: (
        (200, feed) if url == l0_check.TMD_CAP_FEED_URL else (200, sev_item)))
    now = datetime.datetime(2026, 10, 6, 9, 20, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)

    class Args:
        at = "ram53"  # RAIN-NOGAUGE + Z0-MISS + CAP-SEV -- the multi-reason case
        json = True

    rc = l0_check.cmd_check(Args())
    assert rc == 0
    printed = capsys.readouterr().out.strip()
    parsed = json.loads(printed)
    assert set(parsed) == {"flag", "colour_floor", "reasons", "times", "line"}
    enc = tiktoken.get_encoding("o200k_base")
    n = len(enc.encode(printed))
    assert n <= 150, f"--json output used {n} o200k tokens: {printed!r}"


def test_tls_bundle_file_is_a_real_pem_and_verifies_live_tmd():
    """The bundled TMD intermediate must exist, parse as a real PEM, and (best-effort,
    skipped if this sandbox has no outbound network -- never `verify=False`) actually
    let a real HTTPS GET to tmd.go.th verify. This never disables verification to pass."""
    assert l0_check.CA_BUNDLE_PATH.exists()
    text = l0_check.CA_BUNDLE_PATH.read_text()
    assert text.startswith("-----BEGIN CERTIFICATE-----")
    ctx = l0_check._tmd_ssl_context()
    assert ctx.verify_mode.name == "CERT_REQUIRED"
    try:
        status, body = l0_check._get(l0_check.TMD_CAP_FEED_URL, context=ctx, timeout=10)
    except l0_check.L0FetchError:
        pytest.skip("no outbound network in this sandbox")
    assert status == 200
    assert b"<rss" in body


def test_rain_gauge_for_kg_edge_declares_bkk008():
    import yaml
    doc = yaml.safe_load((Path(__file__).parent.parent
                           / "typology" / "edges" / "rain_gauge_for.yaml").read_text())
    rows = doc["rows"]
    row = next(r for r in rows if r["point_id"] == "sammakorn")
    assert row["from"] == "gauge:bma_watermap:WL.SMK.01"
    assert row["to_thaiwater_station_id"] == 2
    assert "BKK008" in row["to"]
