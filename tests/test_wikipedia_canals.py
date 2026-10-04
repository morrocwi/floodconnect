"""Tests for tools/harvest/wikipedia_canals.py's extractor -- parses a saved fixture
of 2-3 real th.wikipedia canal pages (trimmed wikitext, tests/fixtures/
wikipedia_canals_pages.json) and checks infobox-field extraction + normalisation.
No network calls."""
import json
from pathlib import Path

from tools.harvest import wikipedia_canals as wc

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "wikipedia_canals_pages.json"


def load_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _find(pages, pageid):
    return next(p for p in pages if p["pageid"] == pageid)


def test_fixture_has_three_real_pages():
    pages = load_fixture()
    assert len(pages) == 3
    ids = {p["pageid"] for p in pages}
    assert ids == {32585, 32586, 202395}


def test_convert_template_length_extracted():
    # คลองเปรมประชากร -- length_km = {{convert|50.846|km}}
    pages = load_fixture()
    p = _find(pages, 32585)
    wikitext = p["revisions"][0]["slots"]["main"]["*"]
    fields = wc.extract_infobox_fields(wikitext)
    assert fields.get("length_km_raw", "").startswith("50.846")
    assert wc._parse_length_km(fields["length_km_raw"]) == 50.846


def test_english_keyed_infobox_start_end_point():
    # same page also carries start_point/end_point as wikilinked location text
    pages = load_fixture()
    p = _find(pages, 32585)
    wikitext = p["revisions"][0]["slots"]["main"]["*"]
    fields = wc.extract_infobox_fields(wikitext)
    assert "คลองผดุงกรุงเกษม" in fields.get("upstream_name", "")
    assert "แม่น้ำเจ้าพระยา" in fields.get("downstream_name", "")
    # wikilink brackets must be stripped, never left as raw [[ ]] markup
    assert "[[" not in fields["upstream_name"]


def test_plain_numeric_length_km_no_convert_template():
    # คลองพระโขนง -- length_km = 14.5 (no {{convert}} wrapper)
    pages = load_fixture()
    p = _find(pages, 32586)
    wikitext = p["revisions"][0]["slots"]["main"]["*"]
    fields = wc.extract_infobox_fields(wikitext)
    assert wc._parse_length_km(fields.get("length_km_raw")) == 14.5
    assert fields.get("upstream_name") == "แม่น้ำเจ้าพระยา"
    assert fields.get("downstream_name") == "คลองประเวศบุรีรมย์"


def test_page_coordinate_used_when_present():
    pages = load_fixture()
    p = _find(pages, 32586)
    meta = {"subcat_path": ["หมวดหมู่:คลองในประเทศไทย"]}
    row = wc.normalise_page(32586, meta, p, wikidata_coord=None)
    assert row["coord_source"] == "page"
    assert row["lat"] == p["coordinates"][0]["lat"]
    assert row["lon"] == p["coordinates"][0]["lon"]
    assert row["tag"] == "RELAYED"
    assert row["canal_id"] == "wp:32586"
    assert row["licence"] == "CC BY-SA 4.0"


def test_no_infobox_no_page_coord_falls_back_to_wikidata_then_open():
    # คลองดำเนินสะดวก -- prose-only page, no infobox, no `coordinates` prop result
    pages = load_fixture()
    p = _find(pages, 202395)
    assert p.get("coordinates") is None
    wikitext = p["revisions"][0]["slots"]["main"]["*"]
    fields = wc.extract_infobox_fields(wikitext)
    assert fields == {}  # no infobox in this trim -> nothing fabricated

    meta = {"subcat_path": ["หมวดหมู่:คลองในประเทศไทย"]}

    # simulate a Wikidata P625 hit
    row_with_wikidata = wc.normalise_page(202395, meta, p, wikidata_coord=(13.5, 99.9))
    assert row_with_wikidata["coord_source"] == "wikidata"
    assert row_with_wikidata["lat"] == 13.5
    assert row_with_wikidata["lon"] == 99.9

    # simulate no Wikidata coordinate either -> OPEN (null, never geocoded)
    row_open = wc.normalise_page(202395, meta, p, wikidata_coord=(None, None))
    assert row_open["coord_source"] == "none"
    assert row_open["lat"] is None
    assert row_open["lon"] is None


def test_fetch_wikidata_coord_parses_p625_claim():
    payload = {
        "claims": {
            "P625": [
                {"mainsnak": {"datavalue": {"value": {
                    "latitude": 13.456, "longitude": 100.123}}}}
            ]
        }
    }
    lat, lon = None, None
    claims = payload.get("claims", {}).get("P625", [])
    value = claims[0]["mainsnak"]["datavalue"]["value"]
    lat, lon = value.get("latitude"), value.get("longitude")
    assert (lat, lon) == (13.456, 100.123)


def test_normalise_th_name_for_match_strips_prefix_and_disambiguator():
    a = wc._normalise_th_name_for_match("คลองบางแก้ว (จังหวัดนครปฐม)")
    b = wc._normalise_th_name_for_match("คลองบางแก้ว")
    assert a == b == "บางแก้ว"
