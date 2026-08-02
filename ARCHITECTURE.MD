# GuardLine - Architecture Document

## Overview

GuardLine is a GitHub Action that performs automated security scanning on pull requests. It runs entirely within GitHub Actions infrastructure, requires no external services for core functionality, and produces human-readable security reports as PR comments.

This document describes the system architecture and the real design decisions behind it, including where reality has diverged from the original plan. For a detailed log of specific bugs found and fixed during development, see [`CHALLENGES.MD`](CHALLENGES.MD).

---

## Design Principles

**1. Zero-friction adoption.**
A developer should go from "never heard of this" to "running on my repo" in under two minutes. No API keys, no accounts, no configuration files required for default behavior.

**2. Actionable over comprehensive.**
Every finding must include a specific remediation step. A warning without a fix is noise. GuardLine prioritizes telling you what to do over telling you everything that's wrong.

**3. No data exfiltration.**
Core scanning runs entirely within the GitHub Actions runner. No code or findings are sent to external services.

**4. Fail-safe defaults (partially implemented).**
The intent: if a scanner errors out, it reports the error but does not block the PR. In practice, this is currently only true for one specific, known failure mode, `DependenciesScanner`'s OSV API call is wrapped in a try/except (a network failure or unparseable response skips that one dependency and continues). There is no blanket exception handling around scanner calls in `Orchestrator.run()` itself, so an uncaught exception in any scanner, for any other reason, would still crash the entire scan. This is a known, documented gap, not a silent one, see [`CHALLENGES.MD`](CHALLENGES.MD).

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    GitHub Actions Runner                  │
│                                                          │
│  ┌─────────────┐    ┌──────────────────────────────────┐ │
│  │  Entry Point │───▶│         Core Orchestrator        │ │
│  │  (action.yml)│    │                                  │ │
│  └─────────────┘    │  - Reads config (.guardline.yml) │ │
│                      │  - Dispatches to scanners        │ │
│                      │  - Aggregates results            │ │
│                      │  - Generates report              │ │
│                      └──────────┬───────────────────────┘ │
│                                 │                         │
│              ┌──────────────────┼──────────────────┐      │
│              ▼                  ▼                   ▼      │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│  │    Secrets     │ │  Dependency   │ │    Config     │   │
│  │    Scanner     │ │   Scanner     │ │   Auditor     │   │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘   │
│          │                  │                  │           │
│          │      ┌───────────────┐ ┌───────────────┐       │
│          │      │   Pattern     │ │  Permission   │       │
│          │      │   Analyzer    │ │   Checker     │       │
│          │      └───────┬───────┘ └───────┬───────┘       │
│          │              │                  │               │
│          ▼              ▼                  ▼               │
│  ┌──────────────────────────────────────────────────┐     │
│  │              Results Aggregator                    │     │
│  │  - Sums checks_run and findings across scanners   │     │
│  │  - Assigns severity (critical/warning/info)       │     │
│  │  - Attaches remediation text                      │     │
│  │  - Formats output (Markdown / SARIF)              │     │
│  └──────────────────────┬───────────────────────────┘     │
│                          │                                 │
│                          ▼                                 │
│               ┌────────────────────┐                       │
│               │   PR Comment API   │                       │
│               │  (GitHub REST API) │                       │
│               └────────────────────┘                       │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

---

## Diff-Scoped Findings

By default, findings are scoped to only the lines actually changed in a PR, not the whole file. `src/utils/git.py` parses `git diff -U0` output into a `dict[str, set[int]]` mapping each changed file to its changed line numbers, threaded through `BaseScanner.scan()` and every scanner as a third parameter, `changed_lines`.

This applies to `secrets`, `patterns`, and `config`'s pattern-type rules (line-level checks). It does not apply to `permissions`, `dependencies`, or `config`'s required-type rules, since those check whole-file or whole-repo state with no individual line to scope to.

Fail-safe default: a file absent from `changed_lines` (missing diff data, or outside a PR context) scans in full rather than being skipped, so missing diff data never silently reduces coverage.

---

## Scanner Specifications

### 1. Secrets Scanner

**Purpose:** Detect hardcoded credentials, API keys, tokens, and secrets.

**Approach:** Two-pass detection.
- **Pass 1, pattern matching.** A library of regex patterns targeting known secret formats (AWS keys, GitHub tokens, Stripe keys, generic passwords in config files, private key headers, etc.). Each pattern includes metadata: name, severity, and remediation text.
- **Pass 2, entropy analysis.** For strings that match a pattern, calculate Shannon entropy; only matches scoring above a threshold are reported, filtering out low-entropy placeholder text shaped like a secret.

**Files scanned:** Files matching `supported_file_extensions`, filtered by `.guardline.yml`'s `ignore` list, scoped to changed lines when diff data is available.

```
secrets/
├── patterns.yml          # Regex patterns with metadata
└── scanner.py            # Main secrets scanning logic, entropy.py holds the entropy calculator
```

### 2. Dependency Scanner

**Purpose:** Check project dependencies against known vulnerability databases.

**Approach:**
- Parse `requirements.txt`-style `package==version` lines. This is currently the only genuinely supported format.
- Query the OSV (Open Source Vulnerabilities) API for known CVEs per package/version.

**Key design decisions:**
- OSV is used over NVD directly because it provides better package-level mapping and is free with no API key required.
- `supported_file_extensions` originally listed `Pipfile.lock`, `package-lock.json`, `yarn.lock`, and `Cargo.lock` as well, none of these were ever actually parsed correctly (their formats don't match `package==version` text at all; `Pipfile.lock`'s JSON structure produced garbage data through the same line parser). Narrowed to `requirements.txt` only rather than build three additional format-specific parsers, estimated at 8-16 hours, see [`CHALLENGES.MD`](CHALLENGES.MD).
- No response caching exists; every scan re-queries OSV for every `package==version` line found, this was originally planned but never implemented.
- The OSV network call and JSON parsing are wrapped in a try/except; a failure skips that one dependency and prints a warning rather than crashing the scan. This scanner-specific protection was added after a real crash during external validation against `psf/requests`.

```
dependencies/
└── scanner.py            # Parsing, OSV querying, and finding construction all in one file
```

### 3. Config Auditor

**Purpose:** Identify insecure configurations in infrastructure and deployment files.

**Approach:** Rule-based analysis, rules loaded from `rules.yml`, with two rule types:
- `"pattern"` rules test each line via regex, scoped to changed lines when diff data is available.
- `"required"` rules test whether a keyword exists anywhere in the file's content; never scoped to changed lines, since there's no single line to scope to.

**Key design decision:** each rule declares a `file_pattern` (e.g. `"Dockerfile"`) describing which files it's meant for. Originally this field was defined in `rules.yml` but never actually read by `scan()`, every rule applied to every file matching the scanner's broad extension list (`Dockerfile`, `.conf`, `.tf`, `.yml`, `.yaml`), regardless of intent. This produced a real false positive during external validation (a Docker-specific rule firing on unrelated `.yaml` config files). Fixed by skipping a rule if its `file_pattern` doesn't match the current file's path; rules with no `file_pattern` still apply broadly.

```
config/
├── rules.yml
└── scanner.py
```

### 4. Code Pattern Analyzer

**Purpose:** Detect dangerous code patterns that commonly lead to vulnerabilities (SQL injection, unsafe `eval()`, etc.).

**Approach:** Regex-based, rules loaded from `rules.yml`. Scoped to changed lines when diff data is available.

```
patterns/
├── rules.yml
└── scanner.py
```

### 5. Permission Checker

**Purpose:** Detect overly permissive file permissions on sensitive files.

**Approach:** Checks each eligible file's Unix permission bits via `os.stat()`; flags world-writable files. File-level, never scoped to changed lines, since a permission issue isn't tied to a specific line.

```
permissions/
└── scanner.py
```

---

## Core Orchestrator

```python
# Actual current shape, not aspirational pseudocode

def run(self, changed_files: list[str], config: dict, changed_lines: dict[str, set[int]]) -> Report:
    findings = []
    checks_run = 0

    for scanner in self.scanners:
        scan_result = scanner.scan(changed_files, config, changed_lines)
        findings.extend(scan_result.findings)
        checks_run += scan_result.checks_run
        # No exception handling here. See Design Principles #4.

    # Tally severity counts, compute passed = checks_run - critical - warning - info
    # Return a Report
```

---

## Data Model

### Finding

```python
@dataclass
class Finding:
    scanner: str
    severity: str          # "critical", "warning", "info"
    confidence: str        # "high", "medium", "low"
    file: str
    line: int | None
    title: str
    detail: str
    remediation: str
    pattern_id: str
    metadata: dict
```

### ScanResult

Returned by every scanner's `scan()` method, bundling findings with how many checks were actually performed (not just how many produced a finding), which is what makes an accurate `passed` count possible.

```python
@dataclass
class ScanResult:
    findings: list[Finding]
    checks_run: int
```

"One check" means something different per scanner, based on its own loop shape: once per eligible file for `permissions`, once per pattern/rule tested against a line for `secrets`/`patterns`, once per rule tested per line or per file for `config`'s pattern/required rule types respectively, once per dependency line queried for `dependencies`.

### Report

```python
@dataclass
class Report:
    findings: list[Finding]
    summary: ReportSummary
    scan_duration: float
    files_scanned: int
    guardline_version: str

@dataclass
class ReportSummary:
    critical: int
    warning: int
    info: int
    passed: int
```

---

## Directory Structure

```
guardline/
├── action.yml                    # GitHub Action definition
├── Dockerfile
├── .guardline.yml                # Default configuration (leading dot required, config.py looks for this exact name)
├── README.MD
├── CHALLENGES.MD                 # Detailed log of bugs found and fixed during development
├── LICENSE
│
├── src/
│   ├── main.py                   # Entry point; get_changed_files_and_lines(), main()
│   ├── orchestrator.py
│   ├── config.py
│   ├── models.py                 # Finding, ScanResult, Report, ReportSummary
│   ├── reporter.py                # generate() and generate_sarif()
│   ├── github_api.py
│   │
│   ├── scanners/
│   │   ├── base.py                # Abstract BaseScanner
│   │   ├── secrets/
│   │   ├── dependencies/
│   │   ├── config/
│   │   ├── patterns/
│   │   └── permissions/
│   │
│   └── utils/
│       └── git.py                # Unified diff parsing for diff-scoped findings
│
├── tests/
│   ├── fixtures/
│   ├── test_scanner.py           # secrets
│   ├── test_dependencies.py
│   ├── test_config.py
│   ├── test_patterns.py
│   ├── test_permissions.py
│   ├── test_entropy.py
│   ├── test_git.py               # diff parser
│   ├── test_orchestrator.py
│   └── test_reporter.py
│
└── .github/workflows/
    ├── ci.yml                    # Runs the pytest suite on every push/PR
    └── guardline-selfscan.yml    # Runs GuardLine itself against its own repo (dogfooding)
```

---

## Technology Stack

- **Language:** Python 3.13
- **Execution:** GitHub Actions (composite action, no Docker container at runtime; `action.yml` uses `github.action_path` to reference its own checked-out code at the pinned version tag, rather than manually cloning)
- **External APIs:** OSV (dependency vulnerabilities), GitHub REST API (PR comments), CodeQL Action (SARIF upload to the Security tab)
- **Testing:** pytest
- **CI:** GitHub Actions runs the test suite (`ci.yml`) and a real self-scan (`guardline-selfscan.yml`) on every push/PR

---

## Design Decisions Log

| Decision | Rationale |
|----------|-----------|
| Python over Go/Rust | Faster development, sufficient performance for CI-scale scanning |
| Composite Action, no Docker at runtime | Faster cold start than a container action; code is fetched automatically by GitHub Actions via `github.action_path` when a consumer pins a version tag |
| Modular scanner architecture | Each scanner is independent, testable, and (in principle, not yet implemented) individually toggleable |
| Findings include remediation | A warning without a fix is noise |
| OSV over NVD | Better package-level mapping, no API key required |
| PR comments + SARIF, not just status checks | Visible in both the PR itself and GitHub's native Security tab |
| Diff-scoped findings by default | A one-line change to a large file shouldn't surface every pre-existing issue elsewhere in that file |
| `checks_run` tracked per-scanner, not from a static rule catalog | `DependenciesScanner` has no fixed rule catalog, its check count depends on how many dependency lines exist in a given diff; a static catalog approach couldn't represent that |
| `DependenciesScanner` scoped to `requirements.txt` only | Multi-format lockfile support (npm, Cargo, Yarn) was estimated at 8-16 hours of real parser work per format; narrowing the documented claim to match actual capability was the higher-priority fix |
| No blanket exception handling in `Orchestrator.run()` | Known, deliberate gap, not yet fixed. Currently only `DependenciesScanner`'s OSV call has scanner-specific error handling |

---

## Security Considerations

GuardLine itself must be secure. It runs inside CI pipelines with access to source code.

- **No outbound data for core scans.** Only the dependency scanner makes external API calls (to OSV), and only sends package names and versions, never source code.
- **No secrets stored.** GuardLine uses the GitHub Actions token provided by the runner, no additional credentials required.
- **Finding content is not currently redacted.** Detected secrets appear in full in PR comments and SARIF output; this was originally planned but never implemented.
- **Action is pinned.** Users pin to a specific version tag, not a branch. `action.yml` references its own code via `github.action_path`, which resolves to the pinned tag's checkout, not a live clone of `main`, so pinning is actually meaningful.
- **The tool scans itself.** `guardline-selfscan.yml` runs GuardLine against its own repository on every push and PR to `main`.