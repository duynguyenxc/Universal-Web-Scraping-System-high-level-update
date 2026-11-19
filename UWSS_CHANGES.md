# Six defects found by running the system against a second corpus

These were found while pointing UWSS at a systematic review of emotional awareness and
regulation in learning — roughly 1,900 records across OpenAlex, Crossref, DOAJ, PubMed,
arXiv and Semantic Scholar. Every one is a defect that stopped real work, and every one
was found by running the system rather than by reading it.

---

## 1. `src/uwss/discovery.py` — the module two commands import did not exist

`discover-doaj` and `discover-semanticscholar` both begin
`from src.uwss.discovery import ...`. That module was not in the repository, so **both
commands had always failed on import**:

```
ModuleNotFoundError: No module named 'src.uwss.discovery'
```

The file now supplies `iter_doaj_results` and `iter_semanticscholar_results` in the shape
`cli.py` already expects.

**One decision in it is worth keeping if the file is ever rewritten.** Both iterators
check the response **Content-Type**, not just the status code, and raise
`CatalogueUnavailable` rather than yielding nothing when a service answers with something
that is not JSON. This is not defensive programming for its own sake: NCBI answers a
blocked request with **HTTP 200 and an HTML error page**, so a client that trusts the
status line and catches the JSON parse error reports *zero results*. In a literature
review that number goes into a flow diagram as a fact about the literature.

**A refused request and an empty result must never look the same to the caller.**

---

## 2. `cli.py`, `_cmd_doaj` — the DOI and abstract were thrown away

The command built its `Document` with `doi=None` and `abstract=None` hardcoded, although
DOAJ supplies both in `bibjson`. Two consequences: DOAJ rows could never be deduplicated
against a DOI-keyed corpus, so every one looked new; and they arrived with no abstract,
which is the only field that makes a record screenable without fetching the full text.

Now reads `bibjson.identifier[type=doi]` and `bibjson.abstract`, and deduplicates on DOI
first, title second.

---

## 3. `cli.py`, `_cmd_fetch` — `--limit` governed only the download

`resolve_publisher_links` and `enrich_open_access_with_unpaywall` were called with a
hardcoded `limit=200` while `download_open_links` took `args.limit`. So `fetch --limit
1500` resolved 200 links, enriched 200 DOIs, and then reported a download count — and
because the reported number came from the last stage, **the ceiling was invisible**.

`--limit` now governs every stage.

---

## 4. `crawl/__init__.py`, `enrich_open_access_with_unpaywall` — re-running made no progress

The query was:

```python
q = session.execute(select(Document).where(Document.doi != None))
```

with the loop stopping once `limit` records had been **updated**. Nothing marked a row as
already asked about, so every run started at the same first row and stopped in the same
place. Running it ten times enriched the same 200 records ten times and sent some 1,800
pointless requests to a free service that asks callers to identify themselves.

Now filtered on `Document.oa_status == None`, and a definitive "Unpaywall knows this DOI
and it is not open access" writes `oa_status = 'not_oa'` so that row leaves the queue too.
A transport failure writes nothing, so it is retried next run. **Repeat runs are now
cumulative**, which is what makes a large corpus reachable at all.

---

## 5. `cli.py`, `_cmd_fetch` — landing-page resolution ran first, by default

`resolve_publisher_links` opens publisher landing pages looking for PDF links. Those are
exactly the pages publisher CDNs refuse to scripted clients, at three retries and a
20-second timeout each. Measured: minutes per record, for links that were never going to
yield a file, while Unpaywall answers the same question in one request against an API
that wants to be asked.

Now **off by default**, with `--resolve-limit N` to re-enable it.

---

## 6. A ranking bug I introduced, and then removed

The first version of `iter_doaj_results` requested `sort=created_date:desc`. That returns
the *newest* records matching a phrase rather than the *best-matching* ones, which skews
the sample hard towards the current year: 135 of 370 hits were from that year alone.

Worth recording because the first instinct on seeing a strange result is to explain it,
and the explanation was wrong — removing the sort did not change the overlap figure at
all. The bug was real; the thing it appeared to be causing, it was not causing.

---

## Environment notes (not code changes)

- **`uwss-env/` is a Windows virtualenv** (`Scripts/`, `Lib/`) and cannot run on macOS or
  Linux. A working one was built with Python 3.12 — the code uses `str | None`, so 3.10 is
  the floor. Worth removing from version control: it is platform-specific and large.
- **`web-crawler-scrapy-discover` does not load**: `cannot import name '_safe_chars' from
  'w3lib.url'`. Scrapy 2.11.2 against a newer `w3lib`. Not needed for API-based discovery,
  so it was left alone.
- **`paperscraper` warns about missing biorxiv/medrxiv/chemrxiv dumps** on every command.
  Harmless, but it buries real output.
- **A contact address does not belong in a config file.** `config/config_emotion.yaml`
  deliberately carries none; `scripts/run_emotion_fetch.sh` reads `UWSS_CONTACT_EMAIL`
  from the environment and refuses to run without it, rather than falling back to
  `example@example.com` the way the library does — which makes the tool a rude anonymous
  client wearing someone else's name.

## Files added

| File | What it is |
|---|---|
| `src/uwss/discovery.py` | The missing module, with the content-type guard described above |
| `config/config_emotion.yaml` | A worked configuration: 27 search phrases for one review topic |
| `scripts/run_emotion_fetch.sh` | Unpaywall enrichment and download, reading the contact address from the environment |

## What these changes bought

DOAJ went from *cannot run at all* to **370 records with abstracts and DOIs** — the most
useful of the four catalogues tried, because it indexes only fully open-access
peer-reviewed journals, so its hits are both in scope and obtainable as full text.
