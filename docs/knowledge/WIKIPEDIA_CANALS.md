# Wikipedia canals (หมวดหมู่:คลองในประเทศไทย)

Founder task (verbatim): th.wikipedia หมวดหมู่:คลองในประเทศไทย -> "สกัดเข้า kggraph อย่างเป็นระบบ" (extract systematically into the knowledge graph). This document + `sources/wikipedia_canals.yaml` are that extraction; the KG-build step itself (`tools/kg/build_kg.py`) is owned by another worker in this run and not touched here.

## Method

- MediaWiki API (`th.wikipedia.org/w/api.php`), generic User-Agent (`FloodConnect canal harvester; non-commercial research`), `maxlag=5`, max 1 request/second, one polite retry (10s) on HTTP 429/503 only, no other retries.
- `list=categorymembers` on `หมวดหมู่:คลองในประเทศไทย`, `cmtype=page|subcat`, followed recursively into subcategories to depth 3, deduped by pageid; each page's subcategory path is recorded.
- Per page: `prop=coordinates|pageprops|revisions` (`rvprop=ids|timestamp|content`, `rvslots=main`), batched 50 pageids/request. Infobox/body wikitext parsed for จังหวัด, ต้นน้ำ/จุดเริ่ม, ปลายน้ำ/จุดสิ้นสุด, ความยาว, ผู้ดูแล/หน่วยงาน where present -- never fabricated when absent.
- No page coordinate -> Wikidata P625 lookup via the page's `pageprops.wikibase_item` (`wbgetclaims`).
- Every raw API response archived append-only to `raw/wikipedia/canals/<UTC ts>/pages.jsonl` + `manifest.json` (gitignored under `raw/`, per this repo's convention).
- Matched against this repo's existing assets registry (`data/observations.sqlite` `assets` table) by exact normalised Thai name only -- recorded as a `matches` NOTE field, never merged, never used to overwrite either source's coordinate.

## Counts (this run)

- Pages found: **190**
- With a coordinate: **33** (page: 33, wikidata: 0, none/OPEN: 157)
- With an upstream and/or downstream field extracted: **93**
- Matched (exact normalised name) to an existing asset in this repo's registry: **16**
- API errors this run: **21**

## API problems

th.wikipedia.org's `categorymembers` endpoint returned HTTP 429 (Too Many Requests) repeatedly during this harvester's development, even at or well under the 1 request/second ceiling it enforces client-side (observed at 1 req/s, then again at 0.5 req/s); only backing off to 0.25 req/s (`MIN_REQUEST_INTERVAL_S = 4.0` in the script) brought the error count down substantially, to 21 for this run. Every 429 gets one polite retry (10s) per this check's spec; a page still 429'd after that retry is simply skipped, never looped further -- so the category tree walked by any single run is not fully deterministic: a subcategory that 429's twice in a row is silently under-explored that run, and the total page count can move run to run as a result (this is the honest reason to re-run this harvester periodically rather than trust any one run as final/complete). Wikidata's `wbgetclaims` endpoint, by contrast, drew zero errors at every pace tried. No non-429/503 error (a genuine network failure or a different HTTP status) occurred in any run made for this check.

## Licence / attribution

Content from th.wikipedia.org, licensed **CC BY-SA 4.0** (Wikipedia's own text licence). Every row here is tagged `RELAYED` -- a community-edited encyclopedia article, not an official agency telemetry feed or dataset; coordinates and prose fields carry whatever accuracy that article's own editors gave them, not independently re-verified by this repo.

## OPEN

- 157 canal page(s) have no coordinate anywhere (neither the page itself nor its Wikidata item) -- left `lat`/`lon`: null, never geocoded.
- Upstream/downstream/length/operator fields depend entirely on whether a given article's infobox actually uses one of the label variants this harvester looks for; an article using a different label, or prose-only with no infobox, yields nulls for those fields even if the information exists in running text.
- `matches` is a name-string heuristic (exact-after-normalisation only) against this repo's own `assets` table snapshot at run time -- it is not re-run automatically when the assets registry itself is rebuilt, and a genuine same-canal pair with different Thai spellings between Wikipedia and the government source will simply not match (recorded as no match, never guessed).
