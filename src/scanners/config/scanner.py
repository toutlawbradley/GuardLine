import re
import yaml
from src.scanners.base import BaseScanner
from src.models import Finding, ScanResult

class ConfigScanner(BaseScanner):

    def __init__(self):
        self.rules = self._load_rules()

    @property
    def name(self) -> str:
        return "config"

    @property
    def description(self) -> str:
        return "Detects insecure configurations in infrastructure and deployment files"

    @property
    def supported_file_extensions(self) -> list[str]:
        return ["Dockerfile", ".conf", ".tf", ".yml", ".yaml"]

    def _load_rules(self):
        with open("src/scanners/config/rules.yml", "r") as f:
            data = yaml.safe_load(f)
        return data["rules"]

    def scan(self, changed_files: list[str], config: dict) -> ScanResult:
        findings = []

        checks_run = 0

        for file_path in changed_files:
            if not any(file_path.endswith(ext) for ext in self.supported_file_extensions):
                continue

            try:
                with open(file_path, "r") as f:
                    content = f.read()
                    lines = content.splitlines()
            except (IOError, UnicodeDecodeError):
                continue

            for rule in self.rules:

                if rule["type"] == "pattern":
                    for line_number, line in enumerate(lines, start=1):
                        checks_run = checks_run + 1
                        if re.search(rule["pattern"], line):
                            findings.append(Finding(
                                scanner=self.name,
                                severity=rule["severity"],
                                confidence="high",
                                file=file_path,
                                line=line_number,
                                title=rule["name"],
                                detail=rule["description"],
                                remediation=rule["remediation"],
                                pattern_id=rule["id"],
                                metadata={"matched_line": line.strip()}
                            ))

                elif rule["type"] == "required":
                    checks_run = checks_run + 1
                    if rule["required"] not in content:
                        findings.append(Finding(
                            scanner=self.name,
                            severity=rule["severity"],
                            confidence="high",
                            file=file_path,
                            line=None,
                            title=rule["name"],
                            detail=rule["description"],
                            remediation=rule["remediation"],
                            pattern_id=rule["id"],
                            metadata={"missing_keyword": rule["required"]}
                        ))

        return ScanResult(findings=findings, checks_run= checks_run)