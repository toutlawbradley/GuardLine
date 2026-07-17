from src.models import Report, Finding

SEVERITY_TO_SARIF_LEVEL = {
    "critical": "error",
    "warning": "warning",
    "info": "note"
}

class Reporter:
    def generate(self, report: Report) -> str:
        critical_findings = []
        for finding in report.findings:
            if finding.severity == "critical":
                critical_findings.append(finding)

        warning_findings = []
        for finding in report.findings:
            if finding.severity == "warning":
                warning_findings.append(finding)

        info_findings = []
        for finding in report.findings:
            if finding.severity == "info":
                info_findings.append(finding)

        output = ""

        output = output + "🔴 CRITICAL (" + str(report.summary.critical) + ")\n"
        for finding in critical_findings:
            output = output + "  → " + finding.title + " in " + finding.file + ":" + str(finding.line) + "\n"
            output = output + "    Remediation: " + finding.remediation + "\n"

        output = output + "\n"

        output = output + "🟡 WARNING (" + str(report.summary.warning) + ")\n"
        for finding in warning_findings:
            output = output + "  → " + finding.title + " in " + finding.file + ":" + str(finding.line) + "\n"
            output = output + "    Remediation: " + finding.remediation + "\n"

        output = output + "\n"

        output = output + "ℹ️ INFO (" + str(report.summary.info) + ")\n"
        for finding in info_findings:
            output = output + "  → " + finding.title + " in " + finding.file + ":" + str(finding.line) + "\n"

        output = output + "\n"

        output = output + "📊 Summary: " + str(report.summary.critical) + " critical, " + str(report.summary.warning) + " warnings, " + str(report.summary.info) + " info | Scanned " + str(report.files_scanned) + " files in " + str(round(report.scan_duration, 2)) + "s\n"

        return output

    def _finding_to_sarif_result(self, finding):
        level = SEVERITY_TO_SARIF_LEVEL.get(finding.severity, "note")
        line_number = finding.line if finding.line is not None else 1

        return {
            "ruleId": finding.pattern_id,
            "level": level,
            "message": {"text": finding.title},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.file},
                        "region": {"startLine": line_number}
                    }
                }
            ]
        }

    def generate_sarif(self, report: Report) -> dict:
        results = []
        for finding in report.findings:
            results.append(self._finding_to_sarif_result(finding))

        return {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "GuardLine", "rules": []}},
                    "results": results
                }
            ]
        }