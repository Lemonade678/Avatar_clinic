import base64

import httpx
import pytest

from stockcount.cv import CvUnavailable
from stockcount.line_push import LINE_TEXT_LIMIT, LinePushNotifier
from stockcount.roboflow import RoboflowClient

KEY = "rf_secret_key_123"


def roboflow(handler):
    return RoboflowClient("stock-count-packaging/1", KEY, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_roboflow_sends_base64_and_reads_predictions():
    seen = {}

    def handler(request):
        seen["url"] = request.url
        seen["body"] = request.content
        return httpx.Response(200, json={"predictions": [
            {"x": 1, "y": 2, "width": 3, "height": 4, "class": "jar", "confidence": 0.93},
            {"x": 5, "y": 6, "width": 7, "height": 8, "class": "bag", "confidence": 0.41},
        ]})

    preds = roboflow(handler).predict(b"\xff\xd8jpeg")
    assert preds == [{"class": "jar", "confidence": 0.93}, {"class": "bag", "confidence": 0.41}]
    assert seen["url"].path == "/stock-count-packaging/1"
    assert seen["url"].params["api_key"] == KEY
    assert seen["body"] == base64.b64encode(b"\xff\xd8jpeg")


@pytest.mark.parametrize("status", [401, 500])
def test_roboflow_http_errors_become_cv_unavailable(status):
    with pytest.raises(CvUnavailable) as err:
        roboflow(lambda r: httpx.Response(status, text="nope")).predict(b"x")
    assert KEY not in str(err.value)  # never leak the key into logs


def test_roboflow_timeout_becomes_cv_unavailable():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(CvUnavailable) as err:
        roboflow(handler).predict(b"x")
    assert KEY not in str(err.value)


def test_roboflow_odd_response_becomes_cv_unavailable():
    with pytest.raises(CvUnavailable):
        roboflow(lambda r: httpx.Response(200, json={"error": "model not found"})).predict(b"x")


class FakeMessagingApi:
    def __init__(self):
        self.requests = []

    def push_message(self, request):
        self.requests.append(request)


def test_line_push_sends_one_text_message():
    api = FakeMessagingApi()
    LinePushNotifier("token", api=api).push("U-nutt", "สรุป ✅")
    [request] = api.requests
    assert request.to == "U-nutt"
    assert request.messages[0].text == "สรุป ✅"


def test_line_push_trims_to_the_line_limit():
    api = FakeMessagingApi()
    LinePushNotifier("token", api=api).push("U-nutt", "ก" * (LINE_TEXT_LIMIT + 10))
    assert len(api.requests[0].messages[0].text) == LINE_TEXT_LIMIT
