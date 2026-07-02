# GuardLine

**Automated security scanning for every pull request.**

GuardLine is a free, open-source GitHub Action that scans for common security issues and posts a clear, actionable report directly on your pull request.

---

## What It Does

GuardLine scans your codebase and reports findings by severity, with a specific remediation step for each one. It runs entirely inside GitHub Actions with no external services, no sign-up, and no cost. The one exception is dependency scanning, which queries the public [OSV.dev](https://osv.dev) API to check for known CVEs.

### Scan Categories

- **Secrets Detection:** Finds hardcoded API keys, tokens, passwords, private keys, and credentials that should be in environment variables
- **Dependency Vulnerabilities:** Checks your dependencies against OSV.dev (Google's Open Source Vulnerabilities database) for known CVEs
- **Configuration Risks:** Identifies insecure defaults in common config files (Dockerfiles, nginx configs, CI/CD pipelines, cloud provider configs)
- **Code Patterns:** Flags dangerous code patterns like SQL injection vectors and unsafe use of `eval()`
- **Permission Issues:** Detects overly permissive file permissions on sensitive files (secrets, keys, configs)

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
```

---

## Quick Start

Add this to `.github/workflows/guardline.yml` in your repo:

```yaml
name: GuardLine Security Scan
on:
  pull_request:
    branches: [main, develop]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: outlawmetrics/guardline@v1
        with:
          scan-level: standard  # Options: quick, standard, deep
```

Every pull request to your main branches now gets a security scan with findings posted as a PR comment.

---

## Scan Levels

| Level | What It Covers | Speed | Best For |
|-------|---------------|-------|----------|
| `quick` | Secrets + critical config issues | ~5s | Fast feedback on every commit |
| `standard` | All scan categories | ~15-30s | Default for most repos |
| `deep` | Standard + AI-powered contextual analysis | ~60s | Pre-release or sensitive repos |

---

## Configuration (Optional)

GuardLine works out of the box with zero config. To customize, create a `.guardline.yml` in your repo root:

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

---

## Supported Languages & Frameworks

GuardLine scans any text-based file for secrets and configuration issues. Language-specific code pattern analysis currently supports:

- **Python:** Django, Flask, FastAPI
- **JavaScript / TypeScript:** Node.js, Express, React, Next.js
- **Go:** Standard library, Gin, Echo
- **Docker:** Dockerfile best practices
- **Infrastructure:** Terraform, CloudFormation, nginx, Apache
- **CI/CD:** GitHub Actions, GitLab CI, Jenkins

More languages and frameworks are added with each release.

---

## How It Works

```
Pull Request Opened
        │
        ▼
┌─────────────────┐
│   File Scanner   │  Identifies changed files, filters by .guardline.yml
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Secrets Engine  │  Regex + entropy analysis for credentials
├─────────────────┤
│   Dep Checker    │  Cross-references lockfiles against OSV.dev
├─────────────────┤
│  Config Auditor  │  Rule-based checks on infrastructure configs
├─────────────────┤
│ Pattern Analyzer │  Regex-based scanning for dangerous code patterns
├─────────────────┤
│ Permission Check │  File permission review for sensitive files
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Report Generator │  Formats findings with severity + remediation
└────────┬────────┘
         │
         ▼
  PR Comment Posted
```

---

## Why GuardLine?

I built this to learn how security scanning actually works under the hood, and to share what I built along the way.

Security is something I wanted to understand by doing, not just reading about. GuardLine started as a way to practice: how do you detect secrets in code? How do you check dependencies for known vulnerabilities? How do you turn that into something useful inside a CI/CD pipeline?

If you're learning security or just want automatic scanning on your PRs without signing up for anything, feel free to use it, fork it, or open an issue if you find something it should be catching.

---

## Roadmap

- [x] **v0.1** - Secrets detection (regex + entropy)
- [x] **v0.2** - Dependency vulnerability scanning (OSV.dev integration)
- [x] **v0.3** - Configuration file auditing
- [x] **v0.4** - Dangerous code pattern detection
- [x] **v0.4.5** - File permission scanning
- [ ] **v0.5** - Custom rule definitions
- [ ] **v1.0** - Stable release with full documentation
- [ ] **v1.1** - AI-powered contextual analysis (deep scan mode)
- [ ] **v1.2** - SARIF output for GitHub Security tab integration

---

## Contributing

GuardLine is open source and contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

If you find a false positive or a security pattern we should be catching, open an issue.

---

## License

MIT License. Use it, fork it, build on it.

---

**Built by [Tyler Outlaw-Bradley](https://github.com/toutlawbradley)**