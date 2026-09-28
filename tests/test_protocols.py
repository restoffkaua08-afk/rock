from rock.core.contracts import CouncilProtocol
from rock.core.protocols import (
    CritiqueSynthesisProtocol,
    ParallelProtocol,
    RedTeamProtocol,
    VoteProtocol,
    get_protocol,
)

def test_protocol_registry_returns_expected_runner() -> None:
    assert isinstance(get_protocol(CouncilProtocol.PARALLEL), ParallelProtocol)
    assert isinstance(get_protocol(CouncilProtocol.CRITIQUE_SYNTHESIS), CritiqueSynthesisProtocol)


def test_protocol_registry_returns_red_team_runner() -> None:
    assert isinstance(get_protocol(CouncilProtocol.RED_TEAM), RedTeamProtocol)


def test_protocol_registry_returns_vote_runner() -> None:
    assert isinstance(get_protocol(CouncilProtocol.VOTE), VoteProtocol)
