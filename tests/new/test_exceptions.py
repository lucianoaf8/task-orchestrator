from orchestrator.core.exceptions import OrchestratorError

def test_exception_str():
    e = OrchestratorError('msg', error_code='E1')
    assert str(e) == 'E1: msg'
