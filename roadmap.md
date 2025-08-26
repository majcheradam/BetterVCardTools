# BetterVCardTools Roadmap

Practical, opinionated plan to convert any vCard (2.1/3.0/4.0) to deduplicated, clean, normalized, strict vCard 4.0 in UTF‑8 — with a simple web page + CLI, 100% automatic, global-friendly defaults, photos kept 1:1, download-only, MIT.

## 0) Product pillars (non-negotiables)

- [ ] Local-first & private (browser/CLI, optional static hosting)
- [ ] Strict vCard 4.0 UTF‑8 output (validator, folding, escaping, NFC)
- [ ] Deterministic auto-merge
- [ ] 1:1 media preservation
- [ ] Global normalization (E.164, Unicode, casing, locale-aware)

## 1) Architecture (offline by design)

- [ ] Core engine (Rust): crates for AST/normalize/dedupe/validate/write; compile to CLI + WASM
- [ ] Web app (WASM + Service Worker): pure client-side PWA
- [ ] CLI: `bvt convert --in … --out … --region PL --keep-photos --strict`
- [ ] Internal canonical model → normalization → dedupe → validation → writer

## 2) Data rules (defaults that choose best for users)

- [ ] Parsing & upgrades: charset decode, QP/base64, CRLF fold, legacy TYPE→4.0
- [ ] Preserve proprietary fields as X-*, strip known garbage only
- [ ] UID generation when missing (stable hash of identity)
- [ ] Unicode NFC; whitespace/controls clean-up; mojibake repair (opt-in default ON)
- [ ] Names/title-case; phones E.164; emails domain lower; addresses consistent; dates ISO
- [ ] Dedup: blocking keys, scoring, merge policy, safety rails
- [ ] Output & validation: strict 4.0 grammar; hard/soft errors; summary report

## 3) Phased delivery

### Phase 0 — Foundations (tech spikes, repo, CI)

- [ ] Rust workspace + WASM build (wasm-bindgen); CLI scaffold (clap)
- [ ] Minimal parser 2.1/3.0/4.0 → AST; 4.0 writer with folding
- [ ] Basic validator (syntax + UTF‑8 + NFC)
- [ ] Acceptance: roundtrip simple cards; spec fixtures; folding/unfolding tests

### Phase 1 — MVP (single & multi-file → clean 4.0)

- [ ] Web UI: drag-drop, progress, download; PWA offline
- [ ] CLI: glob inputs, ZIP support, streaming merge
- [ ] Normalizations: Unicode, casing, phones(E.164), emails, dates
- [ ] Dedupe v1: email/phone/uid keys; base-record; union strategy
- [ ] Media policy: keep 1:1; rewrap to valid base64 where needed
- [ ] Acceptance: 10k contacts ok; deterministic output; zero hard errors

### Phase 2 — Global hardening

- [ ] Locale toggles (`--region` auto/none), better address tokenization
- [ ] Encoding-repair heuristics (incl. Polish mojibake) reversible
- [ ] Broader legacy mapping (iCloud `X-AB*`, Google labels)
- [ ] Large-file mode: incremental parse/write; bounded RAM; worker chunk pipeline
- [ ] Acceptance: 50k contacts; responsive UI; <1% soft warnings

### Phase 3 — UX polish & reports

- [ ] Web: summary report + CSV/JSON changes export
- [ ] CLI: `--report report.json` with merge rationale
- [ ] Dry run mode (no write) still shows report
- [ ] Acceptance: verify merges without reading VCF

### Phase 4 — Ecosystem & releases

- [ ] Homebrew/Scoop/NPM wrapper; signed binaries; reproducible builds
- [ ] Website: client-only execution (GitHub Pages/Cloudflare Pages)
- [ ] Docs: dedupe spec, normalization spec, threat model, contribution guide
- [ ] License: MIT

## 4) Interfaces

### CLI examples

```bash
# Basic
bvt convert --in ./contacts/*.vcf --out ./clean.vcf --strict --keep-photos

# Region hint for phones, dry run + report
bvt convert --in in/ --out clean.vcf --region PL --dry-run --report report.json

# Safer merge (no mojibake repair)
bvt convert --in dump.zip --out clean.vcf --no-encoding-repair
```

### Web flow

1. Open PWA → drop files/zip → choose region (optional) → Convert
2. Worker streams results; show report; Download clean.vcf
3. All offline; nothing uploaded

## 5) Security & privacy (local-first + optional static host)

- [ ] No telemetry by default
- [ ] Static hosting CSP; no external connections
- [ ] WASM Worker; PWA offline
- [ ] Threat model document

## 6) Testing & QA strategy

- [ ] Fixture zoo (messy real-world + fuzz)
- [ ] Property-based tests (parse→write→parse)
- [ ] Golden snapshots (deterministic)
- [ ] Performance gates (memory per N contacts; streaming)

## 7) Dedup details (deterministic & explainable)

- [ ] Cluster keys: email_ci, phone_e164, uid, name+org fingerprint
- [ ] Scoring: email > phone > org+name > address > photo hash
- [ ] Merge policy: base by completeness; union values; prefer richer labels; keep all photos
- [ ] Conflicts: keep base; attach alternates; contradictory singletons → NOTE X-ORIGINAL-*

## 8) “Strict 4.0” checklist

- [ ] UTF-8 + NFC; CRLF; folded lines ≤75 octets
- [ ] Escape `\, ; \n`; valid PARAM syntax; legacy TYPE mapping
- [ ] Drop only known invalid empties; keep unknown as X-*
- [ ] Generate UID if missing; refresh REV
- [ ] Photos valid 4.0 form (ENCODING/mediatype or URI)

## 9) Repo layout (future)

```
/bettervcardtools
  /crates
    /vcard-ast
    /vcard-normalize
    /vcard-dedupe
    /vcard-validate
    /vcard-write
    /encoding-repair
  /cli
  /web (WASM + PWA + Worker)
  /fixtures
  /docs
```

## 10) Config (defaults sensible, overrideable)

`bvt.config.toml`

```toml
[normalization]
unicode_nfc = true
encoding_repair = "safe-defaults"   # "off" | "aggressive"
phone_region_default = "auto"       # or "PL", etc.
email_lowercase_domain = true

[dedupe]
strategy = "email_phone_uid_fallback"
keep_all_values = true
conflict_policy = "prefer-most-complete"

[media]
keep_photos = true
```

## 11) Success metrics

- [ ] 0 schema errors in validator; ≤1% soft warnings on messy corpora
- [ ] Deterministic output for identical inputs
- [ ] Handles large sets smoothly in web & CLI
- [ ] Users report “imports succeed with no manual fixes”
