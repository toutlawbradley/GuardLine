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

def test_generate_produces_expected_text_with_multiple_findings():
    finding1 = Finding(
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
    finding2 = Finding(
        scanner="secrets",
        severity="warning",
        confidence="medium",
        file="fake.py",
        line=20,
        title="Potential Secret",
        detail="A potential secret was found",
        remediation="Review this line for sensitive information",
        pattern_id="SEC-002",
        metadata={}
    )
    report = Report(
        findings=[finding1, finding2],
        summary=ReportSummary(critical=1, warning=1, info=0, passed=0),
        scan_duration=2.34,
        files_scanned=1,
        guardline_version="1.0.0"
    )
    reporter = Reporter()
    output = reporter.generate(report)
    assert "Hardcoded Secret" in output
    assert "Potential Secret" in output

def test_generate_sarif_with_no_findings():
    report = Report(
        findings=[],
        summary=ReportSummary(critical=0, warning=0, info=0, passed=1),
        scan_duration=0.56,
        files_scanned=1,
        guardline_version="1.0.0"
    )
    reporter = Reporter()
    output = reporter.generate_sarif(report)
    assert output["runs"][0]["results"] == []