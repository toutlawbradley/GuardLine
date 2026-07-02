import time
from src.scanners.config.scanner import ConfigScanner
from src.scanners.dependencies.scanner import DependenciesScanner
from src.scanners.patterns.scanner import PatternScanner
from src.scanners.secrets.scanner import SecretsScanner
from src.scanners.permissions.scanner import PermissionsScanner
from src.models import Finding, Report, ReportSummary

class Orchestrator:
    def __init__(self):
        self.scanners = [SecretsScanner(),DependenciesScanner(),ConfigScanner(), PatternScanner(), PermissionsScanner()]

    def run(self, changed_files: list[str], config: dict) -> Report:
        start_time = time.time()
        findings = []
        for scanner in self.scanners:
            findings.extend(scanner.scan(changed_files, config))

        critical = 0
        for finding in findings:
            if finding.severity == "critical":
                critical = critical + 1

        warning = 0
        for finding in findings:
            if finding.severity == "warning":
                warning = warning + 1

        info = 0
        for finding in findings:
            if finding.severity == "info":
                info = info + 1

        passed = 0

        end_time = time.time()
        scan_duration = end_time - start_time

        return Report(
            findings=findings,
            summary=ReportSummary(
                critical=critical,
                warning=warning,
                info=info,
                passed=passed
            ),
            scan_duration=scan_duration,
            scan_level=config.get("scan_level", "standard"),
            files_scanned=len(changed_files),
            guardline_version="0.1.0"
        )

