from dataclasses import dataclass


@dataclass
class Finding:
    scanner: str          # Which scanner produced this ("secrets", "dependencies", etc.)
    severity: str         # "critical", "warning", "info"
    confidence: str       # "high", "medium", "low"
    file: str             # File path relative to repo root
    line: int | None      # Line number (if applicable)
    title: str            # Short description ("Hardcoded AWS Secret Key")
    detail: str           # Longer explanation of why this is a problem
    remediation: str      # Specific fix ("Move to environment variable AWS_SECRET_ACCESS_KEY")
    pattern_id: str       # Unique ID for this rule (for suppressions)
    metadata: dict        # Scanner-specific data (CVE ID, entropy score, etc.)

@dataclass
class ReportSummary:        # Summary of the scan
    critical: int           # Number of critical findings
    warning: int            # Number of warning findings
    info: int               # Number of info findings
    passed: int             # Number of passed findings

@dataclass
class Report:
    findings: list[Finding]  # List of findings from the scan
    summary: ReportSummary   # Summary of the scan
    scan_duration: float     # Duration of the scan
    files_scanned: int       # Number of files scanned
    guardline_version: str   # Version of GuardLine

@dataclass                 
class ScanResult:
    findings: list[Finding]  
    checks_run: int
