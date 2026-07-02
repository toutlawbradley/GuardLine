from src.scanners.config.scanner import ConfigScanner

def test_config_scanner():
    scanner = ConfigScanner()
    findings = scanner.scan(['tests/fixtures/bad_configs/Dockerfile'], {})
    assert len(findings) == 3
    assert findings[0].severity == "warning"
    assert findings[0].title == "Docker image using latest tag"
    assert findings[0].detail == "Using the latest tag means your build is not reproducible and could pull a broken or vulnerable image without warning"
    assert findings[0].remediation == "Pin to a specific version like python:3.13 instead of python:latest"