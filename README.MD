# GuardLine

**Automated security scanning for pull requests.**

GuardLine is an open-source GitHub Action I built to learn how security scanning tools work under the hood — secrets detection, dependency vulnerability checks, config auditing, and more, wired into a real CI/CD pipeline. It scans a pull request and posts a report of what it finds, with an option to block the merge if something critical turns up.

---

## What It Does

GuardLine scans a codebase for common security issues and posts a report on the pull request. Findings are also published in SARIF format to GitHub's Security tab, and critical findings can automatically block a PR from merging.

### Scan Categories

- **Secrets Detection** — Finds hardcoded API keys, tokens, passwords, private keys, and credentials that should be in environment variables
- **Dependency Vulnerabilities** — Checks your dependencies against [OSV.dev](https://osv.dev) (Google's Open Source Vulnerabilities database) for known CVEs
- **Configuration Risks** — Identifies insecure defaults in common config files (Dockerfiles, nginx configs, CI/CD pipelines, cloud provider configs)
- **Code Patterns** — Flags dangerous code patterns like SQL injection vectors and unsafe use of `eval()`
- **Permission Issues** — Detects overly permissive file permissions on sensitive files (secrets, keys, configs)

### Example Output

```
🔴 CRITICAL (1)
  → Hardcoded AWS secret key found in src/config.py:47
    Remediation: Move to environment variable AWS_SECRET_ACCESS_KEY

🟡 WARNING (3)
  → Dockerfile runs as root (Dockerfile:1)
    Remediation: Add USER directive with non-root user
  → Dependency 'lodash@4.17.20' has known CVE-2021-23337 (HIGH)
    Remediation: Upgrade to lodash@4.17.21 or later
  → requirements.txt has permissions 777, allowing unauthorized read/write access
    Remediation: Restrict permissions, e.g. chmod 600 for sensitive files

🟢 PASSED (12 checks)
  → No hardcoded credentials in environment files
  → All file permissions within acceptable range
  → No SQL injection patterns detected
  ...

📊 Summary: 1 critical, 3 warnings, 12 passed | Scanned 847 files in 14s

❌ Build failed: 1 critical finding must be resolved before merging.
```

Findings are also uploaded as a SARIF file, so they show up natively in GitHub's **Security** tab alongside tools like CodeQL — not just as a PR comment.

---

## Quick Start

Add this to `.github/workflows/guardline.yml` in your repo:

```yaml
name: GuardLine Security Scan
on:
  pull_request:
    branches: [main, develop]

permissions:
  security-events: write  # required so GuardLine can publish results to the Security tab
  issues: write            # required so GuardLine can post the PR comment
  pull-requests: write     # required so GuardLine can post the PR comment

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: toutlawbradley/GuardLine@v1.1.0
        with:
          scan-level: standard  # Options: quick, standard, deep
```

Every pull request to your main branches gets a security review, and a critical finding will fail the check, blocking the merge until it's resolved.

> **Note:** GitHub Actions resets *all* unspecified permissions to `none` the moment you declare any single permission in your workflow — so all three permissions above are required together, not individually optional. `security-events: write` is needed for SARIF results to appear in the Security tab; `issues: write` and `pull-requests: write` are needed for GuardLine to post its PR comment at all. Missing the latter two will cause the comment step to fail with a 403 error, even though scanning and the policy gate still work correctly.

---

## Scan Levels

| Level | What It Covers | Speed | Best For |
|-------|---------------|-------|----------|
| `quick` | Secrets + critical config issues | ~5s | Fast feedback on every commit |
| `standard` | All scan categories | ~15-30s | Default for most repos |
| `deep` | Standard + AI-powered contextual analysis | ~60s | Pre-release or sensitive repos |

---

## Policy Gates

GuardLine doesn't just report findings — it can block a merge. By default, **any critical finding fails the build** (the GitHub Action exits with a non-zero status). If you mark this check as required in your repo's branch protection settings, PRs with unresolved findings at or above the threshold can't be merged.

The threshold is configurable via `.guardline.yml`'s `thresholds.fail-on` setting (`critical`, `warning`, or `info`). Setting a looser threshold like `fail-on: info` also fails on anything worse than info (warning or critical) — it's a minimum severity to tolerate, not an exact match. `max-warnings` (capping the number of allowed warnings regardless of severity) is not yet implemented.

---

## Configuration (Optional)

No config file is required — GuardLine runs with sensible defaults out of the box. To customize behavior, create a `.guardline.yml` in your repo root:

```yaml
# .guardline.yml
scan-level: standard

# Ignore specific paths
ignore:
  - "test/**"
  - "docs/**"
  - "*.test.js"

# Customize severity thresholds
thresholds:
  fail-on: critical          # Options: critical, warning, info
  max-warnings: 10           # Fail if warnings exceed this count

# Enable or disable specific scanners
scanners:
  secrets: true
  dependencies: true
  config: true
  code-patterns: true
  permissions: true

# Custom secret patterns (regex)
custom-patterns:
  - name: "Internal API Token"
    pattern: "INTERNAL_[A-Z]+_TOKEN=['\"][^'\"]+['\"]"
    severity: critical
```

> **Note:** `thresholds.fail-on` is respected by the policy gate — see [Policy Gates](#policy-gates). `thresholds.max-warnings` is not yet implemented; setting it currently has no effect. `custom-patterns` is only supported by the secrets scanner today, and isn't yet covered by an automated test.

---

## Supported Languages & Frameworks

GuardLine scans any text-based file for secrets and configuration issues. Language-specific code pattern analysis currently supports:

- **Python** — Django, Flask, FastAPI
- **JavaScript / TypeScript** — Node.js, Express, React, Next.js
- **Go** — Standard library, Gin, Echo
- **Docker** — Dockerfile best practices
- **Infrastructure** — Terraform, CloudFormation, nginx, Apache
- **CI/CD** — GitHub Actions, GitLab CI, Jenkins

More languages and frameworks are added with each release.

---

## How It Works

```
Pull Request Opened
        │
        ▼
┌─────────────────┐
│   File Scanner   │ ─── Identifies changed files, filters by .guardline.yml
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Secrets Engine  │ ─── Regex + entropy analysis for credentials
├─────────────────┤
│   Dep Checker    │ ─── Cross-references lockfiles against OSV.dev
├─────────────────┤
│  Config Auditor  │ ─── Rule-based checks on infrastructure configs
├─────────────────┤
│ Pattern Analyzer │ ─── Regex-based scanning for dangerous code patterns
├─────────────────┤
│ Permission Check │ ─── File permission review for sensitive files
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Report Generator │ ─── Formats findings as a PR comment AND as SARIF
└────────┬────────┘
         │
    ┌────┴─────┐
    ▼          ▼
PR Comment   SARIF Upload → GitHub Security tab
    │
    ▼
Critical finding? ─── Yes ──▶ Build fails (policy gate)
    │
    No
    ▼
Build passes
```

---

## About This Project

GuardLine is a personal project built to understand how real security scanning tools work. Enterprise security tools do this at a much larger scale with far more sophisticated detection; this is a learning exercise in building something similar from scratch.

A few things it does aim to get right:

- **Actionable output** — findings include a specific remediation step, not just a warning
- **Enforceable** — critical findings can block a merge via a policy gate, not just get commented on
- **Native GitHub integration** — results appear in the Security tab via SARIF, the same format tools like CodeQL use
- **Mostly local** — secrets, config, pattern, and permission scanning all run inside GitHub Actions with no external calls. The dependency scanner is the exception: it queries the public OSV.dev API to check for known CVEs.

Current limitations are documented honestly in the [Roadmap](#roadmap) below rather than glossed over.

---

## Roadmap

- [x] **v0.1** — Secrets detection (regex + entropy)
- [x] **v0.2** — Dependency vulnerability scanning (OSV.dev integration)
- [x] **v0.3** — Configuration file auditing
- [x] **v0.4** — Dangerous code pattern detection
- [x] **v0.4.5** — File permission scanning
- [x] **v0.6** — Policy gates (fail build on critical findings)
- [x] **v0.7** — SARIF output for GitHub Security tab integration
- [ ] **v0.5** — Custom rule definitions (secrets scanner supports `custom-patterns` today, but it's untested and not yet extended to the other four scanners)
- [x] **v0.8** — Configurable policy gate thresholds (respect `.guardline.yml`'s `thresholds` section)
- [ ] **v1.0** — Stable release with full documentation
- [ ] **v2.0** — AI-powered contextual analysis (deep scan mode)

---

---

## License

MIT License. Use it, fork it, build on it.

---

**Built by [Tyler Outlaw-Bradley](https://github.com/toutlawbradley)**