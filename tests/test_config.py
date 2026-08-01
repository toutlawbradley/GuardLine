from src.scanners.config.scanner import ConfigScanner

def test_config_scanner():
    scanner = ConfigScanner()
    result = scanner.scan(['tests/fixtures/bad_configs/Dockerfile'], {})
    assert len(result.findings) == 3
    assert result.findings[0].severity == "warning"
    assert result.findings[0].title == "Docker image using latest tag"
    assert result.findings[0].detail == "Using the latest tag means your build is not reproducible and could pull a broken or vulnerable image without warning"
    assert result.findings[0].remediation == "Pin to a specific version like python:3.13 instead of python:latest"