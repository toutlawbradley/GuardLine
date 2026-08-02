from src.reporter import Reporter
from src.models import Report, ReportSummary, Finding

def test_generate_produces_expected_text():
    finding = Finding(
        scanner="secrets",
        severity="critical",
        confidence="high",
        file="fake.py",
        line=10,
        title="Hardcoded Secret",
        detail="A secret was found",
        remediation="Move it to an environment variable",
        pattern_id="SEC-001",
        metadata={}
    )

    report = Report(
        findings=[finding],
        summary=ReportSummary(critical=1, warning=0, info=0, passed=0),
        scan_duration=1.23,
        files_scanned=1,
        guardline_version="1.0.0"
    )

    reporter = Reporter()
    output = reporter.generate(report)

    assert "Hardcoded Secret" in output

def test_generate_sarif_produces_expected_structure():
    finding = Finding(
        scanner="secrets",
        severity="critical",
        confidence="high",
        file="fake.py",
        line=10,
        title="Hardcoded Secret",
        detail="A secret was found",
        remediation="Move it to an environment variable",
        pattern_id="SEC-001",
        metadata={}
    )

    report = Report(
        findings=[finding],
        summary=ReportSummary(critical=1, warning=0, info=0, passed=0),
        scan_duration=1.23,
        files_scanned=1,
        guardline_version="1.0.0"
    )

    reporter = Reporter()
    output = reporter.generate_sarif(report)

    result = output["runs"][0]["results"][0]

    assert result["message"]["text"] == "Hardcoded Secret"
    assert result["level"] == "error"