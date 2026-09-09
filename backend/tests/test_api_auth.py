import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.otp.senders import MemorySender

pytestmark = pytest.mark.django_db

LOCAL = "9876543210"
E164 = "+919876543210"


def request_code(api, phone=LOCAL, purpose="login"):
    response = api.post(reverse("otp-request"), {"phone": phone, "purpose": purpose},
                        format="json")
    assert response.status_code == 200
    return MemorySender.last_code(E164)


def test_signing_up_creates_the_account_on_first_verification(api):
    code = request_code(api)

    response = api.post(reverse("otp-verify"), {"phone": LOCAL, "code": code}, format="json")

    body = response.json()
    assert response.status_code == 200
    assert body["is_new_user"] is True
    assert body["access"] and body["refresh"]
    assert User.objects.get(phone=E164).phone_verified_at is not None


def test_signing_in_again_does_not_duplicate_the_account(api, visitor):
    code = request_code(api)

    response = api.post(reverse("otp-verify"), {"phone": LOCAL, "code": code}, format="json")

    assert response.json()["is_new_user"] is False
    assert User.objects.filter(phone=E164).count() == 1


def test_any_format_of_the_same_number_reaches_one_account(api, visitor):
    code = request_code(api, phone="+91 98765 43210")

    response = api.post(reverse("otp-verify"), {"phone": LOCAL, "code": code}, format="json")

    assert response.status_code == 200
    assert User.objects.count() == 1


def test_a_nonsense_number_is_refused_in_the_error_envelope(api):
    response = api.post(reverse("otp-request"), {"phone": "12"}, format="json")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_a_wrong_code_says_how_many_attempts_remain(api):
    request_code(api)

    response = api.post(reverse("otp-verify"), {"phone": LOCAL, "code": "000000"}, format="json")

    body = response.json()["error"]
    assert response.status_code == 400
    assert body["code"] == "otp_invalid"
    assert body["attempts_left"] == 4
    assert not User.objects.filter(phone=E164).exists()


def test_asking_twice_in_a_row_is_rate_limited_with_a_wait(api):
    request_code(api)

    response = api.post(reverse("otp-request"), {"phone": LOCAL}, format="json")

    assert response.status_code == 429
    assert response.json()["error"]["retry_after"] > 0


def test_a_web_checkout_code_does_not_open_a_session(api):
    """Purpose is part of a challenge's identity."""
    checkout_code = request_code(api, purpose="web_checkout")

    response = api.post(reverse("otp-verify"),
                        {"phone": LOCAL, "code": checkout_code, "purpose": "login"},
                        format="json")

    assert response.status_code == 400


def test_the_profile_is_read_and_updated_by_its_owner(api, visitor, city, profile_types):
    api.force_authenticate(visitor)

    assert api.get(reverse("me")).json()["phone"] == visitor.phone

    response = api.patch(reverse("me"), {
        "first_name": "Ananya", "last_name": "Sen", "email": "a@example.com",
        "date_of_birth": "1994-03-02", "gender": "female",
        "city": str(city.id), "state": str(city.state_id),
        "profile_types": [str(profile_types[0].id)],
    }, format="json")

    assert response.status_code == 200
    assert response.json()["profile_completeness"] == 100
    assert response.json()["full_name"] == "Ananya Sen"


def test_the_profile_needs_an_account(api):
    assert api.get(reverse("me")).status_code == 401
