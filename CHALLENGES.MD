# GuardLine - Challenges & How They Were Solved

This doc tracks engineering challenges encountered while building GuardLine, how they were resolved, and what's still open. The goal is a record of actual decisions and tradeoffs, not a highlight reel.

---

## Solved

### Relearning and conceptual gaps (after a 3 month gap)
- Rebuilt understanding of `@dataclass`, the `ABC`/`@abstractmethod` contract pattern (`BaseScanner`), and why a shared `Finding` shape lets an orchestrator treat different scanners uniformly.
- Rebuilt Shannon entropy from scratch: character counting, frequency, log2, and why entropy measures distribution, not length (`"ab"` and `"abab"` have identical entropy).
- Understood why secrets detection needs regex and entropy together. Regex alone produces false positives on placeholder text shaped like a secret.

### Testing gaps found and closed
- Discovered 3 of 5 scanners (`config`, `dependencies`, `patterns`) had code but zero automated tests. Manually confirming something worked once wasn't the same as verified, repeatable proof.
- Discovered the `permissions` scanner didn't exist at all and built it from scratch, including learning Unix permission bits, octal notation, and `os.stat()`/`os.chmod()`.
- Learned mocking (`unittest.mock.patch`) for the dependencies scanner test, since it makes a live call to OSV.dev, and why mocking matters: speed, reliability, and isolating your own code's correctness from an external service.
- Learned why the permissions test needed setup/teardown (creating a file and chmod-ing it fresh) instead of a checked-in fixture. Git doesn't reliably preserve permission bits across machines.

### Bugs caught before they shipped
- A test accidentally overwrote the`requirements.txt`, wiping out `pyyaml`/`requests`. Caught via `git diff` before pushing, fixed by using a non-colliding fixture filename.
- `PermissionsScanner` was built and tested but never registered in `orchestrator.py`, meaning it silently never ran in the scans. Found by reading the actual file, not assuming.
- README had multiple factual errors: a stale roadmap, the wrong vulnerability database named (NVD instead of the actual OSV.dev), a false "no external API calls" claim, and a broken Quick Start pointing at a nonexistent GitHub org.

### New features built
- Policy gate: build fails on critical findings (`sys.exit(1)`), including correctly reasoning through `>` vs `>=` with numbers.
- SARIF output: learned the spec shape, built a severity translation dictionary, and wired it through `main.py` to write `results.sarif` to disk.
- SARIF upload to GitHub's Security tab: found and fixed a documented GitHub bug where composite actions need an explicit `token:` input for `upload-sarif` to work.
- Configurable policy gate thresholds: built a severity ranking system (`fail-on: warning` means "warning or worse"), then caught and fixed a bug reading `fail-on` from the top level of config instead of correctly nested under `thresholds`.

### Production debugging
- First live GitHub Actions run: scanning worked, but the PR comment failed with a 403 error.
- Diagnosed the actual cause: GitHub Actions resets all unspecified permissions to `none` the moment you declare any single permission, and fixed it by adding `issues: write` and `pull-requests: write`.
- Documented that exact gotcha in the README so future users (including future me) don't hit it blind.

### Versioning and release management
- Discovered `v1` and `v1.0.0` tags were frozen at an old commit, completely disconnected from current `main`.
- Learned the difference between git tags (fixed) and branches (moving), and that GitHub Releases snapshot a commit independently of the tag.
- Chose proper semantic versioning going forward, creating `v1.1.0` as a new release rather than repeatedly force-moving old tags, avoiding breaking anyone who might depend on `@v1.0.0` later.

### Demo and validation
- Built a working demo repo with four deliberately planted, realistic issues across all four scanner types.
- Successfully validated the entire pipeline end to end in a live PR: scan, comment, SARIF upload, and policy gate blocking the merge, not just local tests.

### GitHub Actions workflow syntax
Getting the CI workflow (`.github/workflows/ci.yml`) right took several iterations: the correct trigger event names (`push` and `pull_request`, not a made up `push_requests`), the distinction between `uses:` (calling a pre-packaged Action) and `run:` (executing a raw shell command), and verifying current major versions of third party Actions (`actions/checkout@v7`, `actions/setup-python@v5`) rather than assuming stale ones.

### `action.yml` was cloning its own repo, unpinned
The "Run GuardLine" step manually did `git clone https://github.com/toutlawbradley/GuardLine.git`, which always pulled `main`, regardless of what version tag a consumer's `uses: toutlawbradley/GuardLine@vX.X.X` line pinned to. Root cause: not knowing that GitHub Actions already checks out the correct, versioned copy of a composite Action's repo automatically, exposed via `${{ github.action_path }}`. Fix: removed the manual clone entirely and pointed the run step and the SARIF upload path at `github.action_path` instead. Version pinning is now actually meaningful, not cosmetic.

### `scan-level` (quick/standard/deep) was fully undocumented vaporware
The README documented three scan tiers with specific claimed behavior (speed, scope, and an "AI-powered deep scan" mode), `action.yml` declared a `scan-level` input, and `models.py`/`orchestrator.py` stored the value, but nothing anywhere actually changed scanner behavior based on it. All three tiers ran identically. Decided to remove the feature entirely rather than build tiering, since the current single scan mode was already fast enough not to need it. Required cleanup across `README.MD`, `ARCHITECTURE.MD` (4 separate spots, including a design philosophy paragraph and a pseudocode reference to a `resolve_scanners()` dispatch function that was never built), `models.py`, `orchestrator.py`, and `action.yml`.

### `scanners: { secrets: true, ... }` enable/disable config also did nothing
Found while cleaning up the `scan-level` gap: the example `.guardline.yml`'s per-scanner enable/disable block is read nowhere in the code. `Orchestrator.__init__` always instantiates all 5 scanners. Decided to document this as a known limitation rather than implement it right now, the same treatment as `max-warnings`.

### Evaluating and rejecting AI integration
Walked through three possible AI features (triage/false positive reduction, an independent contextual scanner, and AI generated fix suggestions) and rejected all three with reasoning:
- Triage: heuristics (path exclusions, entropy tuning, allowlists) already solve false positive reduction without an LLM.
- Independent scanning: genuine cross file contextual reasoning is taint analysis territory (what CodeQL already does deterministically), not a chat model's job.
- Fix suggestions: a bare `Finding` (file, line, generic remediation string) lacks the surrounding codebase context, imports, existing patterns, which libraries are in use, to generate a fix trustworthy enough to auto-suggest.

Also compared this decision against modern tools: Trivy and CodeQL use zero AI; SonarQube's AI features only ever generate fix suggestions for already confirmed, deterministically detected findings. Nobody in the industry uses AI for detection itself.

### `passed` hardcoded to `0`: the `ScanResult` redesign
`Orchestrator.run()` set `passed = 0` unconditionally, contradicting the README's example output showing a passed count. Root cause: `BaseScanner.scan()` only ever returned `list[Finding]`, the problems found, with no way to report how many checks were actually attempted. A simpler sounding fix (counting each scanner's static rule catalog) was ruled out because `DependenciesScanner` has no fixed catalog at all. The check count depends on how many dependency lines exist in a given diff.

Fix: designed a `ScanResult` dataclass (`findings: list[Finding]`, `checks_run: int`) and threaded it through `BaseScanner`'s abstract signature and all 5 scanner implementations. Each scanner defines "one check" differently based on its own loop shape:
- `permissions`: once per eligible file evaluated.
- `secrets` / `patterns`: once per pattern/rule tested against a line.
- `config`: once per rule tested per line (`"pattern"` rules) or once per rule tested per file (`"required"` rules).
- `dependencies`: once per dependency line queried against OSV.

Along the way, caught and fixed several bugs in the process of writing this: a counter that reset to `0` every loop iteration instead of incrementing, an increment placed after all loops had already finished (only ever reaching `1`), an increment nested inside an `if match:` block (only counting matches, not attempts), and a few indentation/syntax errors from misplaced code blocks.

### Diff-scoped findings

Built a unified diff parser (`src/utils/git.py`) to scope findings to changed lines instead of whole files. `main.py` now runs `git diff -U0` once, instead of the previous `--name-only` call, producing both the file list and a per-file map of changed line numbers from the same source, rather than maintaining two separate calls for related data.

`changed_lines: dict[str, set[int]]` is threaded through `BaseScanner`, all 5 scanners, and `Orchestrator.run()`. Scoping applies to `secrets`, `patterns`, and `config`'s pattern-type rules (line-level checks). `permissions`, `dependencies`, and `config`'s required-type rules stay unfiltered, since they check whole-file or whole-repo state with no line to scope to.

Fail-safe default: `changed_lines.get(file_path, None)`, and a file absent from the diff data scans in full rather than being skipped. An early draft defaulted to an empty set instead of `None`, which meant missing diff data produced zero findings instead of full coverage, caught and fixed before merging.

Two bugs found while building the parser:
- `parse_diff()` didn't flush the current hunk when transitioning to a new file, so a file's last hunk could be dropped or attributed to the next file. Fixed by flushing on file transition, same as the existing hunk-to-hunk flush.
- An early version of `SecretsScanner`'s filtering had a `return` statement indented one level too deep, causing the scan to stop after the first eligible line of the first file.

Added 17 tests (`test_git.py`) covering the parser, including regression tests for both bugs above. Confirmed one of the multi-file tests wouldn't have caught the file-transition bug on its own, since it only checked file paths, not hunk content, added separate tests asserting on hunk data directly to close that gap.

### Misconceptions cleared up along the way
- Confirmed the OSV dependency vulnerability API needs no API key or account setup. It's a free, public, unauthenticated endpoint.

### `orchestrator.py` never consumed `ScanResult`, so `passed` stayed hardcoded to `0`
Once all 5 scanners returned a `ScanResult`, `Orchestrator.run()` still did `findings.extend(scanner.scan(...))`, treating the return value as a plain list. Fixed by unpacking `scan_result.findings` and `scan_result.checks_run` from each scanner, summing `checks_run` across all 5 into a running total, and computing `passed = checks_run - critical - warning - info` instead of the hardcoded `0`. Verified against a fixture file (`passed=67` on a scan with 5 findings), not just unit tests.

Along the way, 6 existing tests broke, since they were written against the old plain-list interface (`findings[0].scanner` instead of `result.findings[0].scanner`). Fixed all 6 to reach into `.findings` first, all 10 tests passing again.

Also hit a environment issue while applying this locally: edits made in an editor weren't actually landing on disk (confirmed via `cat` showing the old file content even after supposedly saving), traced to a nested nested folder structure (`GuardLine/GuardLine/`) with two separate git repos and two separate virtual environments, one Python 3.13, one Python 3.14. Resolved by identifying which nested folder was the git-tracked repo, collapsing the duplicate structure, and rebuilding the venv fresh from the correct location. Lesson: when a saved fix doesn't behave as expected, `cat` the actual file from the terminal first, before assuming the code is wrong.

### `SEVERITY_RANK.get(fail_on)` crashed with a `TypeError` on an invalid config value
If `.guardline.yml` had a typo'd or invalid `fail_on` value, `.get()` returned `None`, and the comparisons below it (`SEVERITY_RANK["critical"] >= threshold_rank`) crashed comparing an `int` to `None`, after the scan already ran and the PR comment and SARIF file were already written. Decided to fail safe rather than fail closed: validate `threshold_rank` right after the lookup, and if it's `None`, print a clear warning and fall back to `"critical"`'s rank, matching the project's own "fail-safe defaults" design principle. The initial fix was placed *after* the three severity comparisons instead of before them, meaning the crash still happened before the fallback ever ran. Correct placement is validate first, then use the value.

While fixing this, also found and fixed a related but separate discrepancy: `main.py` read the config key as `fail_on` (underscore), but the README documented and every other config key used `fail-on` (hyphen), matching the rest of the project's hyphenated convention (`max-warnings`, `custom-patterns`). Resolved by updating the docs to match the code, the simpler and more appropriate fix given the code was otherwise internally consistent.

### The three severity if-statements were simplified to a loop
`should_fail` was computed with three nearly identical `if` blocks, one per severity level, differing only in which key they checked. Replaced with a single loop over `SEVERITY_RANK.items()`, using `getattr(report.summary, severity)` to fetch each count dynamically instead of hardcoding three attribute accesses. Verified behaviorally identical to the original by exhaustively testing every combination of severity counts against every threshold level, zero mismatches.

### Diff-scoped findings

Built a unified diff parser (`src/utils/git.py`) to scope findings to changed lines instead of whole files. `main.py` now runs `git diff -U0` once, instead of the previous `--name-only` call, producing both the file list and a per-file map of changed line numbers from the same source, rather than maintaining two separate calls for related data.

`changed_lines: dict[str, set[int]]` is threaded through `BaseScanner`, all 5 scanners, and `Orchestrator.run()`. Scoping applies to `secrets`, `patterns`, and `config`'s pattern-type rules (line-level checks). `permissions`, `dependencies`, and `config`'s required-type rules stay unfiltered, since they check whole-file or whole-repo state with no line to scope to.

Fail-safe default: `changed_lines.get(file_path, None)`, and a file absent from the diff data scans in full rather than being skipped. An early draft defaulted to an empty set instead of `None`, which meant missing diff data produced zero findings instead of full coverage, caught and fixed before merging.

Two bugs found while building the parser:
- `parse_diff()` didn't flush the current hunk when transitioning to a new file, so a file's last hunk could be dropped or attributed to the next file. Fixed by flushing on file transition, same as the existing hunk-to-hunk flush.
- An early version of `SecretsScanner`'s filtering had a `return` statement indented one level too deep, causing the scan to stop after the first eligible line of the first file.

Added 17 tests (`test_git.py`) covering the parser, including regression tests for both bugs above. Confirmed one of the multi-file tests wouldn't have caught the file-transition bug on its own, since it only checked file paths, not hunk content, added separate tests asserting on hunk data directly to close that gap.
### GuardLine now dogfoods itself
Added `.github/workflows/guardline-selfscan.yml`, which runs the packaged GuardLine Action against GuardLine's own repository on every push and PR to `main`, separate from `ci.yml` (which only runs the `pytest` suite). Also renamed the repo root's config file from `guardline.yml` to `.guardline.yml`, the leading dot was missing, so `config.py`'s `load_config()` (which specifically looks for `.guardline.yml`) had never actually been reading it, the file was dead weight. Added an `ignore: tests/fixtures/**` rule to it, since those files are deliberately vulnerable test fixtures, not real findings.

First self-scan run failed with a missing `results.sarif` file. Traced the cause: `actions/checkout` defaults to a shallow, single-commit clone (`fetch-depth: 1`). On a plain push (not a PR), `main.py` falls back to `git diff -U0 HEAD~1` to determine changed files, but `HEAD~1` doesn't exist in a depth-1 checkout. The `git diff` subprocess call has no `check=True`, so it failed silently rather than raising, producing empty output, which correctly parsed to zero changed files, which triggered `main()`'s early return before `results.sarif` ever got written. Fixed by adding `fetch-depth: 0` to the self-scan workflow's checkout step, and applied the same fix to the README's own Quick Start example, since anyone following that documented setup exactly and pushing directly to `main` would hit the identical bug.

### Added tests for Orchestrator.run() and Reporter's two methods
9 tests for `Orchestrator.run()` covering aggregation across all 5 scanners, the passed-count arithmetic, and empty-input edge cases. 4 tests for `Reporter` covering `generate()` and `generate_sarif()` against manually constructed `Report` objects, not scanned output. First drafts of both test files assumed methods and behavior that don't exist: an `Orchestrator.run_scanners()` method, a `Reporter.generate_report()` method, a `format="json"` parameter on `generate()`, and "No issues found" text on empty scans. None of these are real. Rewrote both files against the actual method signatures and actual output, `generate_sarif()` in particular returns a `dict`, not a JSON string, so its tests needed real dict indexing, not string-membership checks.

Writing the empty-input orchestrator tests surfaced a real regression: `SecretsScanner`'s `return` statement had drifted back inside the `for file_path` loop (the exact bug fixed earlier the same night), causing `scan()` to return `None` on an empty file list instead of a `ScanResult`, which crashed `Orchestrator.run()` with an `AttributeError`. Fixed by re-indenting the `return` to sit after the loop, not inside it.

### No error handling around the OSV API call
This stopped being theoretical the moment it was tested against a real external repo (`psf/requests`): one dependency's OSV lookup returned a response `.json()` couldn't parse, and since `requests.post()` and `response.json()` had no error handling at all, it crashed the entire scan, not just that one dependency check. Fixed by wrapping both calls in a `try`/`except`, printing a visible warning (matching `ARCHITECTURE.MD`'s "reports the error but does not block the PR" principle, silent failure isn't the same as fail-safe) and skipping to the next dependency rather than crashing.

### `ConfigScanner` ignored its own rules' `file_pattern` field
Found while running GuardLine against `psf/requests` for external validation: `ConfigScanner` flagged `.pre-commit-config.yaml` and `.readthedocs.yaml`, neither a Dockerfile, with `"Docker container running as root"`. Root cause: `rules.yml` declares `file_pattern: "Dockerfile"` on each Docker-specific rule, but `scan()` never read that field at all, every rule in the file was applied to every eligible file (`Dockerfile`, `.conf`, `.tf`, `.yml`, `.yaml`), regardless of what that rule was actually meant for. Fixed by skipping a rule entirely if it declares a `file_pattern` that doesn't appear in the current file's path. Rules with no `file_pattern` at all are unaffected, they still apply broadly, as before. Re-ran the same external scan after the fix: the false positive was gone, 0 findings against `psf/requests`, confirming the fix without introducing new gaps.

### `DependenciesScanner` claimed broader lockfile support than it delivered
`supported_file_extensions` listed `Pipfile.lock`, `package-lock.json`, `yarn.lock`, and `Cargo.lock` alongside `requirements.txt`, but the scanner only ever parsed plain-text `package==version` lines. `Pipfile.lock` is JSON, checking it against `"==" in line` and splitting on `==` produced garbage data (`name='"version": "'`, `version='1.2.3",'`, stray quotes and commas included), sent to OSV, and silently failed to match anything real once the OSV error-handling fix was in place. `package-lock.json`, `yarn.lock`, and `Cargo.lock` are structurally nothing like `requirements.txt` at all, none of them would ever match. Building real parsers for all three formats was estimated at 8-16 hours, npm's JSON is the most tractable, Cargo's TOML is moderate, Yarn's lockfile has no standard format to parse against at all. Given the time cost relative to the actual, current dependency footprint of this project, decided to narrow `supported_file_extensions` to just `requirements.txt`, the one format that's genuinely correct, and updated the README to state the real, current scope instead of an aspirational one. Multi-format lockfile support remains a reasonable future feature, just not built now.

---

## Currently Open

Nothing tracked here right now, every item logged during development has been resolved (either fixed, or deliberately scoped down and documented, see the entries above). New gaps will be added here as they're found.