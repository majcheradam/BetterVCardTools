# Refactor To‑Do Checklist

A checkbox tracker derived from `refactor_plan.md` and the Roadmap. Check off as you deliver increments. Use nested items for clarity.

## 0) Global prerequisites

- [ ] Adopt monorepo layout plan and communicate migration path
- [ ] Decide initial feature flags (CLI vs legacy path) and default to legacy until parity
- [ ] Add `/fixtures` directory with a minimal starter set (small, messy, large)

## 1) Repository layout setup

- [ ] Create Rust workspace at repo root (`/crates`, `/cli`)
- [ ] Add placeholder crates: `vcard-ast`, `vcard-normalize`, `vcard-dedupe`, `vcard-validate`, `vcard-write`, `encoding-repair`
- [ ] Keep Python `app/` as adapter layer (to be archived later)
- [ ] Prepare `/docs` and `/web` folders (empty README stubs)

## 2) Iteration 0 — Foundations (Phase 0)

- [ ] Minimal AST for vCard (2.1/3.0/4.0 essential fields)
- [ ] 4.0 writer with proper line folding (≤75 octets) and CRLF
- [ ] Tiny parser to roundtrip simple 4.0 cards
- [ ] Golden snapshot tests for roundtrip and folding/unfolding
- [ ] GitHub Actions: Rust build/test + keep Python tests running
- [ ] Deliverable: `bvt` prints a simple vCard; roundtrip tests pass

## 3) Iteration 1 — MVP conversion

- [ ] Parser for 2.1/3.0/4.0 → AST (incl. basic legacy TYPE mapping)
- [ ] 4.0 writer fully wired with folding/escaping
- [ ] Basic validator: syntax + UTF‑8 + NFC checks
- [ ] Normalizations v1: Unicode NFC; whitespace/control cleanup
- [ ] Python adapter: endpoints shell out to `bvt convert`
- [ ] Deterministic output: golden snapshots updated and stable
- [ ] Acceptance: small inputs convert to strict 4.0, Python tests green

## 4) Iteration 2 — Normalization + Dedupe v1

- [ ] Phones to E.164 (region-aware, `--region` hint)
- [ ] Emails: lowercase domain
- [ ] Dates: normalize to ISO
- [ ] UID generation when missing; refresh REV
- [ ] Dedupe keys: email_ci, phone_e164, uid
- [ ] Merge policy: pick base by completeness; union values; keep all photos
- [ ] Summary report v0 (JSON) with soft/hard error taxonomy
- [ ] Acceptance: deterministic merges on fixtures; zero hard errors on golden set

## 5) Iteration 3 — PWA spike (client-only)

- [ ] Build WASM for core with `wasm-bindgen`
- [ ] Worker pipeline streaming conversion
- [ ] Minimal web UI: drag/drop, progress, download `clean.vcf`
- [ ] Service Worker and offline manifest (PWA)
- [ ] Strict CSP; no external calls; client-only execution
- [ ] Acceptance: offline conversion demo works without server

## 6) Hardening & large-file mode (Phase 2)

- [ ] Incremental parse/write; bounded RAM; chunk pipeline
- [ ] Locale toggles (`--region auto/none`), better address tokenization
- [ ] Encoding-repair heuristics (incl. Polish mojibake), reversible, opt-out flag
- [ ] Broader legacy mapping (iCloud `X-AB*`, Google labels)
- [ ] Acceptance: 50k contacts within resource bounds; <1% soft warnings

## 7) Media policy

- [ ] 1:1 media preservation
- [ ] Rewrap to valid base64 where needed
- [ ] Photos in valid 4.0 form (ENCODING/mediatype or URI)

## 8) CLI maturity

- [ ] `bvt convert --in … --out … --strict --keep-photos`
- [ ] Add `--dry-run` and `--report report.json`
- [ ] ZIP inputs, globs, streaming merge

## 9) Testing & QA

- [ ] Fixture zoo (messy real-world + fuzz)
- [ ] Property-based tests: parse→write→parse idempotence
- [ ] Golden snapshots (deterministic outputs)
- [ ] Performance gates: memory per N contacts; streaming tests
- [ ] Dual-path tests (legacy Python vs Rust CLI) during parity period

## 10) CI/CD

- [ ] GitHub Actions matrix (macOS, Linux) for Rust + Python
- [ ] Cache cargo and pip
- [ ] Lints: clippy, rustfmt, ruff/black (while Python remains)
- [ ] Release pipeline: signed CLI binaries; Homebrew formula (later)

## 11) Security & privacy

- [ ] No telemetry by default
- [ ] Static hosting CSP for PWA; no external connections
- [ ] Threat model document in `/docs`

## 12) Docs & specs

- [ ] Dedupe spec: keys, scoring, merge policy, conflict handling
- [ ] Normalization spec: Unicode, phones, emails, dates, addresses
- [ ] Validation rules: strict 4.0 grammar, escaping, folding
- [ ] Contribution guide and repo overview

## 13) Definition of done (per phase)

- [ ] Phase 0: Rust workspace compiles; minimal roundtrip; CI green
- [ ] Phase 1: CLI `convert` handles small/multi-file; adapter passes tests
- [ ] Phase 2: Normalization + dedupe v1; deterministic outputs; report v0
- [ ] Phase 3: PWA offline demo; no server dependency for standard conversions
- [ ] Phase 4: Packaging + website; docs complete; MIT license confirmed

## 14) Risks and mitigations (tracked as tasks)

- [ ] Add golden tests that exercise both legacy and Rust paths in CI
- [ ] Large-file WASM fallback to CLI; document limits in UI
- [ ] Encoding edge cases: reversible repairs + opt-out flags; targeted tests

## 15) Immediate next steps

- [ ] Scaffold Rust workspace and crates; add CI job for Rust
- [ ] Implement 4.0 writer + minimal parser; add golden tests
- [ ] Create `bvt convert` with basic I/O; integrate with Python adapter (feature-flag)
- [ ] Expand fixtures and baseline golden outputs for normalization and legacy mapping
