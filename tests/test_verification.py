import pytest

from rock.core.contracts import Verification
from rock.core.verification import VerificationLoop


@pytest.mark.asyncio
async def test_verification_loop_corrects_until_pass() -> None:
    loop = VerificationLoop(max_attempts=3)
    state = {"value": 0}

    async def verify(item):
        return Verification(
            target="demo",
            verifier="test",
            checks=["value"],
            passed=item["value"] >= 2,
            findings=[] if item["value"] >= 2 else ["value too low"],
        )

    async def correct(item, _verification, _attempt):
        return {"value": item["value"] + 1}

    result, verification, attempts = await loop.run(
        state,
        verify=verify,
        correct=correct,
    )

    assert result["value"] == 2
    assert verification.passed
    assert len(attempts) == 3


@pytest.mark.asyncio
async def test_verification_loop_stops_at_three_attempts() -> None:
    loop = VerificationLoop(max_attempts=9)

    async def verify(_):
        return Verification(
            target="demo",
            verifier="test",
            checks=["always_fail"],
            passed=False,
            findings=["still failing"],
        )

    async def correct(item, _verification, _attempt):
        return item

    _, verification, attempts = await loop.run(
        {},
        verify=verify,
        correct=correct,
    )

    assert not verification.passed
    assert len(attempts) == 3
