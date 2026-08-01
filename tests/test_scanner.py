from src.scanners.secrets.scanner import SecretsScanner


def test_finds_secrets_in_fake_config():
    scanner = SecretsScanner()
    result = scanner.scan(['tests/fixtures/secrets/fake_config.py'], {})
    assert len(result.findings) == 5

def test_finds_scanner_name():
    scanner = SecretsScanner()
    result = scanner.scan(['tests/fixtures/secrets/fake_config.py'], {})
    assert result.findings[0].scanner == "secrets"