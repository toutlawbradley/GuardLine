from unittest.mock import patch
from src.scanners.dependencies.scanner import DependenciesScanner

@patch("src.scanners.dependencies.scanner.requests.post")
def test_dependencies_scanner(mock_post):
    mock_post.return_value.json.return_value = {
        "vulns": [
            {"id": "CVE-2021-12345", "summary": "Some flask vulnerability"}
        ]
    }

    scanner = DependenciesScanner()
    result = scanner.scan(['tests/fixtures/vulnerable_deps/requirements.txt'], {}, {})

    assert len(result.findings) == 3
    assert result.findings[0].severity == "critical"
    assert result.findings[0].title == "CVE-2021-12345"
    assert result.findings[0].detail == "Some flask vulnerability"