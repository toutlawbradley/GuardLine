from src.scanners.patterns.scanner import PatternScanner


def test_finds_patterns_in_fake_code():
    scanner = PatternScanner()
    result = scanner.scan(['tests/fixtures/dangerous_patterns/fake_code.py'], {})
    assert len(result.findings) == 2

def test_finds_scanner_name():
    scanner = PatternScanner()
    result = scanner.scan(['tests/fixtures/dangerous_patterns/fake_code.py'], {})
    assert result.findings[0].scanner == "pattern"