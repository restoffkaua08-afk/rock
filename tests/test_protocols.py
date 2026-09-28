from rock.core.contracts import CouncilProtocol
from rock.core.protocols import CritiqueSynthesisProtocol, ParallelProtocol, get_protocol

def test_protocol_registry_returns_expected_runner() -> None:
    assert isinstance(get_protocol(CouncilProtocol.PARALLEL), ParallelProtocol)
    assert isinstance(get_protocol(CouncilProtocol.CRITIQUE_SYNTHESIS), CritiqueSynthesisProtocol)
