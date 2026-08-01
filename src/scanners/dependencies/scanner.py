import requests
from src.scanners.base import BaseScanner
from src.models import Finding, ScanResult

class DependenciesScanner(BaseScanner):

    @property
    def name(self) -> str:
        return "dependencies"
    
    @property
    def description(self) -> str:
        return "Detects security vulnerabilites within codebase packages"

    @property
    def supported_file_extensions(self) -> list[str]:
        return ["requirements.txt", "Pipfile.lock", "package-lock.json", "yarn.lock", "Cargo.lock"]

    def scan(self, changed_files: list[str], config: dict, changed_lines: dict[str, set[int]]) -> ScanResult:
        findings = []

        checks_run = 0

        for file_path in changed_files:
            if not any(file_path.endswith(ext) for ext in self.supported_file_extensions):
                continue

            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()
            except (IOError, UnicodeDecodeError):
                continue

            for line in lines:
                if "==" not in line:
                    continue

                parts = line.strip().split("==")
                name = parts[0]
                version = parts[1]

                checks_run = checks_run + 1

                response = requests.post("https://api.osv.dev/v1/query", json={
                    "package": {"name": name, "ecosystem": "PyPI"},
                    "version": version
                })

                data = response.json()
                if "vulns" in data:
                    for vuln in data["vulns"]:
                        findings.append(Finding(
                            scanner=self.name,
                            severity="critical",
                            confidence="high",
                            file=file_path,
                            line=None,
                            title=vuln.get("id", "Unknown CVE"),
                            detail=vuln.get("summary", "Known vulnerability found"),
                            remediation="Upgrade " + name + " to a patched version",
                            pattern_id=vuln.get("id", "DEP-001"),
                            metadata={"package": name, "version": version}
                        ))

        return ScanResult(findings=findings, checks_run=checks_run)