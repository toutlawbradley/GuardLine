import os
from src.scanners.base import BaseScanner
from src.models import Finding


class PermissionsScanner(BaseScanner):

    @property
    def name(self) -> str:
        return "permissions"

    @property
    def description(self) -> str:
        return "Detects overly permissive file permissions"

    @property
    def supported_file_extensions(self) -> list[str]:
        return [".env", ".pem", ".key", "requirements.txt", "Dockerfile"]

    def scan(self, changed_files: list[str], config: dict) -> list[Finding]:
        findings = []

        for file_path in changed_files:
            if not any(file_path.endswith(ext) for ext in self.supported_file_extensions):
                continue

            if not os.path.exists(file_path):
                continue

            file_stats = os.stat(file_path)
            permissions = oct(file_stats.st_mode)[-3:]

            other_bits = int(permissions[-1])

            # bit 2 = write, bit 4 = read (octal). If "other" can write OR read+write, flag it.
            if other_bits & 0o2:
                findings.append(Finding(
                    scanner=self.name,
                    severity="warning",
                    confidence="high",
                    file=file_path,
                    line=None,
                    title="Overly permissive file permissions",
                    detail=f"{file_path} has permissions {permissions}, which allows unauthorized users to modify or read this file",
                    remediation="Restrict permissions, e.g. chmod 600 for sensitive files",
                    pattern_id="PERM-001",
                    metadata={"permissions": permissions}
                ))

        return findings