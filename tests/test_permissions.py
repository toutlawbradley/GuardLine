import os
from src.scanners.permissions.scanner import PermissionsScanner

def test_permissions_scanner():
    with open("fake_requirements.txt", "w") as f:
        f.write("some content")
    os.chmod("fake_requirements.txt", 0o777)

    scanner = PermissionsScanner()
    findings = scanner.scan(['fake_requirements.txt'], {})

    assert len(findings) == 1
    assert findings[0].severity == "warning"

    os.remove("fake_requirements.txt")