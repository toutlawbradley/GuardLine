import re
import yaml
from src.scanners.base import BaseScanner
from src.models import Finding, ScanResult

class PatternScanner(BaseScanner):

    def __init__(self):
        self.rules = self._load_rules()

    @property
    def name(self) -> str:
        return "pattern"

    @property
    def description(self) -> str:
        return "Detects dangerous code patterns"

    @property
    def supported_file_extensions(self) -> list[str]:
        return [".py", ".js", ".ts", ".go"]

    def _load_rules(self):
        with open("src/scanners/patterns/rules.yml", "r") as f:
            data = yaml.safe_load(f)
        return data["rules"]

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

            for line_number, line in enumerate(lines, start=1):
                for rule in self.rules:
                    checks_run = checks_run + 1
                    if re.search(rule["pattern"], line):
                        findings.append(Finding(
                            scanner=self.name,
                            severity=rule["severity"],
                            confidence=rule["confidence"],
                            file=file_path,
                            line=line_number,
                            title=rule["name"],
                            detail=rule["description"],
                            remediation=rule["remediation"],
                            pattern_id=rule["id"],
                            metadata={"matched_line": line.strip()}
                        ))

        return ScanResult(findings=findings,checks_run=checks_run)