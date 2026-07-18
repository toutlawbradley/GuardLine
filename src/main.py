import os
import subprocess
import sys
import json
from src.orchestrator import Orchestrator
from src.reporter import Reporter
from src.config import load_config
from src.github_api import post_pr_comment


def get_changed_files():
    scan_target = os.environ.get("SCAN_TARGET", ".")
    base_ref = os.environ.get("BASE_REF", "")

    try:
        if base_ref:
            subprocess.run(
                ["git", "fetch", "origin", base_ref],
                capture_output=True, text=True, cwd=scan_target
            )
            result = subprocess.run(
                ["git", "diff", "--name-only", f"origin/{base_ref}"],
                capture_output=True, text=True, cwd=scan_target
            )
        else:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                capture_output=True, text=True, cwd=scan_target
            )

        files = []
        for f in result.stdout.splitlines():
            f = f.strip()
            if f:
                files.append(os.path.join(scan_target, f))
        return files
    except Exception:
        return []

def main():
    scan_target = os.environ.get("SCAN_TARGET", ".")
    config = load_config(scan_target)

    changed_files = get_changed_files()

    if not changed_files:
        print("No changed files found.")
        return

    orchestrator = Orchestrator()
    reporter = Reporter()

    report = orchestrator.run(changed_files, config)
    output = reporter.generate(report)

    post_pr_comment(output)

    sarif_data = reporter.generate_sarif(report)
    with open("results.sarif", "w") as f:
        f.write(json.dumps(sarif_data))

    SEVERITY_RANK = {
        "critical": 3,
        "warning": 2,
        "info": 1
    }

    thresholds = config.get("thresholds",{})
    fail_on = thresholds.get("fail_on", "critical")
    threshold_rank = SEVERITY_RANK.get(fail_on)

    should_fail = False
    if report.summary.critical > 0 and SEVERITY_RANK["critical"] >= threshold_rank:
        should_fail = True
    if report.summary.warning > 0 and SEVERITY_RANK["warning"] >= threshold_rank:
        should_fail = True
    if report.summary.info > 0 and SEVERITY_RANK["info"] >= threshold_rank:
        should_fail = True

    if should_fail:
         print(f"Findings at or above '{fail_on}' threshold found. Failing build.")
         sys.exit(1)
    


if __name__ == "__main__":
    main()

