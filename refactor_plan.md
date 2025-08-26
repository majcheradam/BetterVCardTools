# Refactor Plan

This plan translates the roadmap into discrete engineering steps to evolve the current proof-of-concept into a robust, privacy‑first vCard conversion tool. Tasks are grouped by phase and roughly ordered.

## Phase 0 – Foundations
- Establish a Rust workspace with crates for AST, normalization, deduplication, validation and writing.
- Produce a minimal parser supporting vCard 2.1/3.0/4.0 and a writer that emits folded, strictly valid vCard 4.0.
- Provide a basic validator checking UTF‑8, NFC and syntax.
- Set up continuous integration and round‑trip tests for simple cards.

## Phase 1 – MVP
- Deliver a WASM powered web UI that runs fully offline and a CLI with `bvt convert` entry point.
- Implement core normalizations (Unicode NFC, casing, E.164 phones, email domain lowercasing, ISO dates).
- Introduce deterministic deduplication using email, phone and UID keys with a union merge strategy.
- Preserve media 1:1, re‑encoding only when necessary, and support streaming merge for multiple files or ZIP archives.

## Phase 2 – Global Hardening
- Add locale aware options such as `--region` and improved address tokenization.
- Expand encoding repair heuristics and legacy label mappings (e.g. iCloud `X-AB*`, Google labels).
- Support large data sets through incremental parsing/writing and bounded memory usage.
- Maintain responsiveness in the web UI and aim for less than 1% soft warnings on messy corpora.

## Phase 3 – UX Polish & Reports
- Produce human readable summary reports and CSV/JSON exports in both web and CLI (`--report`).
- Offer a dry‑run mode that performs all analysis without writing output.
- Allow users to verify merges without opening the resulting VCF.

## Phase 4 – Ecosystem & Releases
- Ship signed binaries and wrappers (Homebrew, Scoop, NPM) with reproducible builds.
- Host a static website/PWA that executes entirely on the client and documents normalization, dedupe and the threat model.
- Maintain MIT licensing and provide contribution guidelines.

## Testing & QA
- Build a fixture zoo of real‑world and fuzzed vCards.
- Use property‑based tests for parse→write→parse fidelity and golden snapshots for deterministic output.
- Add performance gates covering memory use and streaming behavior.

## Success Metrics
- Zero hard schema errors and ≤1% soft warnings across diverse corpora.
- Deterministic output for identical inputs.
- Smooth handling of large contact sets in both CLI and web environments.
- User feedback indicates imports succeed without manual fixes.

