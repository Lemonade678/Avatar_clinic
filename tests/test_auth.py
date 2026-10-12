import httpx
import pytest

from stockcount.auth import LINE_VERIFY_URL, AuthError, LineTokenVerifier


def verifier(handler):
    return LineTokenVerifier("1234567890", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_valid_token_returns_the_user_id():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"sub": "U-nutt", "aud": "1234567890"})

    assert verifier(handler).verify("tok") == "U-nutt"
    assert seen["url"] == LINE_VERIFY_URL
    assert "client_id=1234567890" in seen["body"] and "id_token=tok" in seen["body"]


def test_rejected_token():
    with pytest.raises(AuthError, match="400"):
        verifier(lambda r: httpx.Response(400, json={"error": "invalid_request"})).verify("tok")


def test_line_unreachable():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(AuthError, match="reach"):
        verifier(handler).verify("tok")


def test_empty_token_is_not_sent():
    with pytest.raises(AuthError, match="missing"):
        verifier(lambda r: httpx.Response(200, json={"sub": "x"})).verify("")
