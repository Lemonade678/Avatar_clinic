"""Push the shift summary into ณัฑฒ์'s LINE chat (one message per round — well inside the free quota)."""
from __future__ import annotations

from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, PushMessageRequest, TextMessage

LINE_TEXT_LIMIT = 5000


class LinePushNotifier:
    def __init__(self, access_token: str, api: MessagingApi | None = None):
        self.api = api or MessagingApi(ApiClient(Configuration(access_token=access_token)))

    def push(self, user_id: str, text: str) -> None:
        self.api.push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text=text[:LINE_TEXT_LIMIT])]))
