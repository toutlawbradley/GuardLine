from src.orchestrator import Orchestrator

def test_orchestrator_combines_all_scanners():
    orchestrator = Orchestrator()
    result = orchestrator.run(['tests/fixtures/secrets/fake_config.py'], {}, {})

    assert result.summary.critical == 2   
    assert result.summary.warning == 3    
    assert result.summary.passed > 1      

def test_orchestrator_scan_duration():
    orchestrator = Orchestrator()
    result = orchestrator.run(['tests/fixtures/secrets/fake_config.py'], {}, {})

    assert result.scan_duration > 0

def test_orchestrator_files_scanned():
    orchestrator = Orchestrator()
    result = orchestrator.run(['tests/fixtures/secrets/fake_config.py'], {}, {})

    assert result.files_scanned == 1

def test_orchestrator_with_no_files_has_zero_everything():
    orchestrator = Orchestrator()
    result = orchestrator.run([], {}, {})

    assert result.findings == []
    assert result.summary.passed == 0

def test_orchestrator_with_no_files_has_zero_scan_duration():
    orchestrator = Orchestrator()
    result = orchestrator.run([], {}, {})

    assert result.scan_duration >= 0

def test_orchestrator_with_no_files_has_zero_files_scanned():
    orchestrator = Orchestrator()
    result = orchestrator.run([], {}, {})

    assert result.files_scanned == 0

def test_orchestrator_with_multiple_files_scanned():
    orchestrator = Orchestrator()
    result = orchestrator.run(['tests/fixtures/secrets/fake_config.py', 'tests/fixtures/dangerous_patterns/fake_code.py'], {}, {})

    assert result.files_scanned == 2

def test_orchestrator_with_multiple_files_has_findings():
    orchestrator = Orchestrator()
    result = orchestrator.run(['tests/fixtures/secrets/fake_config.py', 'tests/fixtures/dangerous_patterns/fake_code.py'], {}, {})

    assert len(result.findings) > 0

def test_orchestrator_with_multiple_files_has_correct_summary():
    orchestrator = Orchestrator()
    result = orchestrator.run(['tests/fixtures/secrets/fake_config.py', 'tests/fixtures/dangerous_patterns/fake_code.py'], {}, {})

    assert result.summary.critical >= 2   
    assert result.summary.warning >= 3    
    assert result.summary.passed > 1