import math
import re
import yaml
from src.scanners.base import BaseScanner
from src.scanners.secrets.entropy import calculate_entropy
from src.models import Finding, ScanResult

class SecretsScanner(BaseScanner):    

    def __init__(self):
        self.patterns = self._load_patterns()

    @property
    def name(self) -> str:
        return "secrets"

    @property
    def description(self) -> str:
        return "Detects hardcoded credentials, API keys, tokens, and secrets in source code"

    @property
    def supported_file_extensions(self) -> list[str]:
        return [".py", ".js", ".ts", ".json", ".yml", ".yaml", ".env", ".cfg", ".conf", ".toml", ".xml", ".sh"]

    def _load_patterns(self):
        with open("src/scanners/secrets/patterns.yml", "r") as f:
            data = yaml.safe_load(f)
        return data["patterns"]

    def scan(self, changed_files: list[str], config: dict, changed_lines: dict[str, set[int]]) -> ScanResult:
        findings = []

        all_patterns = list(self.patterns)

        if "custom-patterns" in config:
            for custom in config["custom-patterns"]:
                all_patterns.append({
                    "id": "CUSTOM-" + custom.get("name", "unknown"),
                    "name": custom["name"],
                    "pattern": custom["pattern"],
                    "severity": custom.get("severity", "warning"),
                    "confidence": "medium",
                    "description": "Custom rule: " + custom["name"],
                    "remediation": custom.get("remediation", "Review this match and resolve according to your team's security policy")
                })
        
        checks_run = 0

        for file_path in changed_files:
            if not any(file_path.endswith(ext) for ext in self.supported_file_extensions):
                continue

            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()
            except (IOError, UnicodeDecodeError):
                continue

            file_line_numbers = changed_lines.get(file_path, None)                                                         

            for line_number, line in enumerate(lines, start=1):
                if file_line_numbers is not None and line_number not in file_line_numbers:
                    continue
                for pattern in all_patterns:
                    match = re.search(pattern["pattern"], line)
                    checks_run = checks_run + 1
                    if match:
                        matched_text = match.group()
                        score = calculate_entropy(matched_text)
                        if score > 3.0:
                            findings.append(Finding(
                                scanner=self.name,
                                severity=pattern["severity"],
                                confidence=pattern["confidence"],
                                file=file_path,
                                line=line_number,
                                title=pattern["name"],
                                detail=pattern["description"],
                                remediation=pattern["remediation"],
                                pattern_id=pattern["id"],
                                metadata={"matched_line": line.strip(), "entropy_score": score}
                            ))

        return ScanResult(findings=findings, checks_run=checks_run)