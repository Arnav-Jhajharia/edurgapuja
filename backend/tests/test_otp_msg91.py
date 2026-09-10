"""Delivering a one-time code over MSG91.

The code is generated, hashed and verified here — MSG91 only carries it. That is
the decision worth protecting: MSG91 sells an OTP product that would generate
and check the code itself, and adopting it would throw away the attempt limits,
the supersede-on-reissue rule and the constant-time comparison already written.

So these tests are about the transport: the right number format, the right
template variable, and what happens when the network will not take the message.
"""

import pytest
from django.test import override_settings

from apps.accounts.models import OtpChallenge
from apps.accounts.otp import service
from apps.accounts.otp.senders import (
    ConsoleSender,
    Msg91Sender,
    OtpDeliveryError,
    default_sender,
    msg91_mobile,
)

pytestmark = pytest.mark.django_db

LIVE = {
    "MSG_91_AUTH_KEY": "an-auth-key",
    "MSG91_TEMPLATE_ID": "a-template-id",
    "MSG_91_SENDER": "EDURGA",
    "OTP_SENDER_BACKEND": "apps.accounts.otp.senders.default_sender",
}


class Recorder:
    """Stands in for httpx.post and remembers what it was handed."""

    def __init__(self, status_code=200, body=None, raises=None):
        self.status_code, self.body, self.raises = status_code, body or {}, raises
        self.calls = []

    def __call__(self, url, **kwargs):
        if self.raises:
            raise self.raises
        self.calls.append({"url": url, **kwargs})
        return self

    # The bits of httpx.Response the sender touches.
    @property
    def content(self):
        return b"{}"

    @property
    def text(self):
        return str(self.body)

    def json(self):
        return self.body


# --------------------------------------------------------------------------
# The number
# --------------------------------------------------------------------------

def test_a_number_reaches_msg91_as_digits_with_a_country_code():
    """We store E.164; MSG91 wants no plus."""
    assert msg91_mobile("+919876543210") == "919876543210"


def test_a_bare_ten_digit_number_is_assumed_indian():
    """The alternative is silently failing to deliver."""
    assert msg91_mobile("9876543210") == "919876543210"


def test_punctuation_a_person_typed_is_stripped():
    assert msg91_mobile("+91 98765-43210") == "919876543210"


# --------------------------------------------------------------------------
# The request
# --------------------------------------------------------------------------

@override_settings(**LIVE)
def test_the_code_is_sent_under_the_templates_variable_name(monkeypatch):
    """The key has to match the DLT-approved template, or MSG91 sends a message
    with an empty placeholder where the code should be."""
    post = Recorder()
    monkeypatch.setattr("apps.accounts.otp.senders.httpx.post", post)

    Msg91Sender().send("+919876543210", "482913", channel="sms")

    body = post.calls[0]["json"]
    assert body["template_id"] == "a-template-id"
    assert body["sender"] == "EDURGA"
    assert body["recipients"] == [{"mobiles": "919876543210", "OTP": "482913"}]
    assert post.calls[0]["headers"]["authkey"] == "an-auth-key"


@override_settings(**LIVE, MSG91_CODE_VARIABLE="var1")
def test_the_variable_name_is_configurable(monkeypatch):
    """Templates in the wild use ##OTP##, ##var1## and worse."""
    post = Recorder()
    monkeypatch.setattr("apps.accounts.otp.senders.httpx.post", post)

    Msg91Sender().send("+919876543210", "482913", channel="sms")

    assert post.calls[0]["json"]["recipients"][0]["var1"] == "482913"


@override_settings(**{**LIVE, "MSG_91_SENDER": "", "MSG_91_SENDER_ID": "EDPUJA"})
def test_either_sender_variable_supplies_the_dlt_header(monkeypatch):
    """MSG91 calls the same six characters both 'sender' and 'sender ID'."""
    post = Recorder()
    monkeypatch.setattr("apps.accounts.otp.senders.httpx.post", post)

    Msg91Sender().send("+919876543210", "482913", channel="sms")

    assert post.calls[0]["json"]["sender"] == "EDPUJA"


# --------------------------------------------------------------------------
# When it does not work
# --------------------------------------------------------------------------

@override_settings(**LIVE)
def test_an_http_error_is_a_delivery_failure(monkeypatch):
    monkeypatch.setattr("apps.accounts.otp.senders.httpx.post",
                        Recorder(status_code=401, body={"message": "bad authkey"}))

    with pytest.raises(OtpDeliveryError):
        Msg91Sender().send("+919876543210", "482913", channel="sms")


@override_settings(**LIVE)
def test_a_200_that_says_error_is_still_a_failure(monkeypatch):
    """MSG91 answers 200 with type=error for a rejected template."""
    monkeypatch.setattr("apps.accounts.otp.senders.httpx.post",
                        Recorder(body={"type": "error", "message": "template not approved"}))

    with pytest.raises(OtpDeliveryError):
        Msg91Sender().send("+919876543210", "482913", channel="sms")


@override_settings(**LIVE)
def test_a_failed_send_leaves_no_live_code_behind(monkeypatch):
    """Nobody received it, so it must not sit there waiting to be answered."""
    monkeypatch.setattr("apps.accounts.otp.senders.httpx.post", Recorder(status_code=500))

    with pytest.raises(service.OtpUndeliverableError):
        service.issue("+919876543210")

    challenge = OtpChallenge.objects.get(destination="+919876543210")
    assert not challenge.is_live


@override_settings(**LIVE)
def test_a_failed_send_does_not_spend_the_persons_quota(monkeypatch):
    """The cooldown limits the person, not the outage — they should be able to
    try again at once."""
    monkeypatch.setattr("apps.accounts.otp.senders.httpx.post", Recorder(status_code=500))

    with pytest.raises(service.OtpUndeliverableError):
        service.issue("+919876543210")

    # Immediately again: a rate limit here would be punishing them for our fault.
    with pytest.raises(service.OtpUndeliverableError):
        service.issue("+919876543210")


# --------------------------------------------------------------------------
# Which transport is live
# --------------------------------------------------------------------------

@override_settings(MSG_91_AUTH_KEY="", MSG91_TEMPLATE_ID="")
def test_with_no_credentials_the_code_goes_to_the_log():
    assert isinstance(default_sender(), ConsoleSender)


@override_settings(MSG_91_AUTH_KEY="k", MSG91_TEMPLATE_ID="t")
def test_credentials_alone_decide_that_real_messages_are_sent():
    """Not DEBUG: a staging box with real credentials should send real messages,
    and a box without them must not quietly pretend to."""
    assert isinstance(default_sender(), Msg91Sender)


@override_settings(MSG_91_AUTH_KEY="k", MSG91_TEMPLATE_ID="")
def test_half_configured_is_treated_as_not_configured():
    """A template id nobody set means every send fails at MSG91; better to log."""
    assert isinstance(default_sender(), ConsoleSender)
