# GuardLine - Challenges & How They Were Solved

This doc tracks engineering challenges encountered while building GuardLine, how they were resolved, and what's still open. The goal is a record of decisions and tradeoffs.

---

## Solved

### Relearning and conceptual gaps (after a 3 month gap)
- Rebuilt understanding of `@dataclass`, the `ABC`/`@abstractmethod` contract pattern (`BaseScanner`), and why a shared `Finding` shape lets an orchestrator treat different scanners uniformly.
- Rebuilt Shannon entropy from scratch: character counting, frequency, log2, and why entropy measures distribution, not length (`"ab"` and `"abab"` have identical entropy).
- Understood why secrets detection needs regex and entropy together. Regex alone produces false positives on placeholder text shaped like a secret.

### Testing gaps found and closed
- Discovered 3 of 5 scanners (`config`, `dependencies`, `patterns`) had zero automated tests.
- Discovered the `permissions` scanner didn't exist at all and built it from scratch, including learning Unix permission bits, octal notation, and `os.stat()`/`os.chmod()`.
- Learned mocking (`unittest.mock.patch`) for the dependencies scanner test, since it makes a real live call to OSV.dev, and why mocking matters: speed, reliability, and isolating your own code's correctness from an external service.
- Learned why the permissions test needed setup/teardown (creating a real file and chmod-ing it fresh) instead of a checked-in fixture. Git doesn't reliably preserve permission bits across machines.

### Bugs caught before they shipped
- A test accidentally overwrote the real `requirements.txt`, wiping out `pyyaml`/`requests`. Caught via `git diff` before pushing, fixed by using a non-colliding fixture filename.
- `PermissionsScanner` was built and tested but never registered in `orchestrator.py`, meaning it silently never ran in real scans. Found by reading the file.
- README had multiple factual errors: a stale roadmap, the wrong vulnerability database named (NVD instead of the actual OSV.dev), and a broken Quick Start pointing at a nonexistent GitHub org.

### New features built
- Policy gate: build fails on critical findings (`sys.exit(1)`), including correctly reasoning through `>` vs `>=` with real numbers.
- SARIF output: learned the spec shape, built a severity translation dictionary, and wired it through `main.py` to write `results.sarif` to disk.
- SARIF upload to GitHub's Security tab: found and fixed a real, documented GitHub bug where composite actions need an explicit `token:` input for `upload-sarif` to work.
- Configurable policy gate thresholds: built a severity ranking system (`fail-on: warning` means "warning or worse"), then caught and fixed a bug reading `fail-on` from the top level of config instead of correctly nested under `thresholds`.

### Production debugging
- First live GitHub Actions run: scanning worked, but the PR comment failed with a 403 error.
- Diagnosed the actual cause: GitHub Actions resets all unspecified permissions to `none` the moment you declare any single permission, and fixed it by adding `issues: write` and `pull-requests: write`.
- Documented that exact momement in the README for future reference.

### Versioning and release management
- Discovered `v1` and `v1.0.0` tags were frozen at an old commit, completely disconnected from current `main`.
- Learned the difference between git tags (fixed) and branches (moving), and that GitHub Releases snapshot a commit independently of the tag.
- Chose proper semantic versioning going forward, creating `v1.1.0` as a new release rather than repeatedly force-moving old tags, avoiding breaking anyone who might depend on `@v1.0.0` later.

### Demo and validation
- Built a working demo repo with four deliberately planted, realistic issues across all four scanner types.
- Successfully validated the entire pipeline end to end in a real, live PR: scan, comment, SARIF upload, and policy gate blocking the merge, not just local tests.

### GitHub Actions workflow syntax
Getting the CI workflow (`.github/workflows/ci.yml`) right took several iterations: the correct trigger event names (`push` and `pull_request`), the distinction between `uses:` (calling a pre-packaged Action) and `run:` (executing a raw shell command), and verifying current major versions of third party Actions (`actions/checkout@v7`, `actions/setup-python@v5`) rather than assuming stale ones.

### `action.yml` was cloning its own repo, unpinned
The "Run GuardLine" step manually did `git clone https://github.com/toutlawbradley/GuardLine.git`, which always pulled `main`, regardless of what version tag a consumer's `uses: toutlawbradley/GuardLine@vX.X.X` line pinned to. Root cause: not knowing that GitHub Actions already checks out the correct, versioned copy of a composite Action's repo automatically, exposed via `${{ github.action_path }}`. Fix: removed the manual clone entirely and pointed the run step and the SARIF upload path at `github.action_path` instead. Version pinning is now actually meaningful, not cosmetic.

### `scan-level` (quick/standard/deep) was fully undocumented vaporware
The README documented three scan tiers with specific claimed behavior (speed, scope, and an "AI-powered deep scan" mode), `action.yml` declared a `scan-level` input, and `models.py`/`orchestrator.py` stored the value, but nothing anywhere actually changed scanner behavior based on it. All three tiers ran identically. Decided to remove the feature entirely rather than build real tiering, since the current single scan mode was already fast enough not to need it. Required cleanup across `README.MD`, `ARCHITECTURE.MD` (4 separate spots, including a design philosophy paragraph and a pseudocode reference to a `resolve_scanners()` dispatch function that was never built), `models.py`, `orchestrator.py`, and `action.yml`.

### `scanners: { secrets: true, ... }` enable/disable config also did nothing
Found while cleaning up the `scan-level` gap: the example `.guardline.yml`'s per-scanner enable/disable block is read nowhere in the code. `Orchestrator.__init__` always instantiates all 5 scanners. Decided to document this as a known limitation rather than implement it right now, the same treatment as `max-warnings`.

### Evaluating and rejecting AI integration
Walked through three possible AI features (triage/false positive reduction, an independent contextual scanner, and AI generated fix suggestions) and rejected all three with reasoning:
- Triage: heuristics (path exclusions, entropy tuning, allowlists) already solve false positive reduction without an LLM.
- Independent scanning: genuine cross file contextual reasoning is taint analysis territory (what CodeQL already does deterministically), not a chat model's job.
- Fix suggestions: a bare `Finding` (file, line, generic remediation string) lacks the surrounding codebase context, imports, existing patterns, which libraries are in use, to generate a fix trustworthy enough to auto-suggest.

Also compared this decision against real tools: Trivy and CodeQL use zero AI; SonarQube's AI features only ever generate fix suggestions for already confirmed, deterministically detected findings.

### `passed` hardcoded to `0`: the `ScanResult` redesign
`Orchestrator.run()` set `passed = 0` unconditionally, contradicting the README's example output showing a real passed count. Root cause: `BaseScanner.scan()` only ever returned `list[Finding]`, the problems found, with no way to report how many checks were actually attempted. A simpler sounding fix (counting each scanner's static rule catalog) was ruled out because `DependenciesScanner` has no fixed catalog at all. The check count depends on how many dependency lines exist in a given diff.

Fix: designed a `ScanResult` dataclass (`findings: list[Finding]`, `checks_run: int`) and threaded it through `BaseScanner`'s abstract signature and all 5 scanner implementations. Each scanner defines "one check" differently based on its own loop shape:
- `permissions`: once per eligible file evaluated.
- `secrets` / `patterns`: once per pattern/rule tested against a line.
- `config`: once per rule tested per line (`"pattern"` rules) or once per rule tested per file (`"required"` rules).
- `dependencies`: once per dependency line queried against OSV.

Along the way, caught and fixed several real bugs in the process of writing this: a counter that reset to `0` every loop iteration instead of incrementing, an increment placed after all loops had already finished (only ever reaching `1`), an increment nested inside an `if match:` block (only counting matches, not attempts), and a few indentation/syntax errors from misplaced code blocks.

### Misconceptions cleared up along the way
- Confirmed the OSV dependency vulnerability API needs no API key or account setup. It's a free, public, unauthenticated endpoint.

---

## Currently Open

1. **`orchestrator.py` doesn't yet consume `ScanResult`.** All 5 scanners now return it, but `Orchestrator.run()` still does `findings.extend(scanner.scan(...))`, which expects a plain list. Needs updating to unpack `findings` and `checks_run` from each scanner's result, sum `checks_run` across all 5, and use that to compute a real `passed` value instead of `0`.
2. **`SEVERITY_RANK.get(fail_on)` crashes with a `TypeError`** if `.guardline.yml` has a typo'd or invalid `fail_on` value. `.get()` returns `None`, and the next comparison fails at runtime instead of failing gracefully with a clear error message.
3. **`DependenciesScanner` claims broader lockfile support than it delivers.** `supported_file_extensions` lists `package-lock.json`, `yarn.lock`, and `Cargo.lock`, but the scanner only actually parses `==`-pinned PyPI style lines. The other three formats are silently skipped with no findings and no warning.
4. **No error handling around the OSV API call.** A network failure or rate limit would likely crash the whole scan with an unhandled exception, directly contradicting the documented "fail-safe defaults" design principle (a broken scanner should report an error, not block the PR).
5. **GuardLine doesn't dogfood itself yet.** Phase 0 added CI that runs the `pytest` suite on every push/PR, but GuardLine doesn't yet run its own scanner against its own repository.
6. **No dedicated tests for `orchestrator.py` or `reporter.py`.** This is part of why the `passed=0` bug went unnoticed as long as it did. The piece of code responsible for building the `Report` object was never directly under test.