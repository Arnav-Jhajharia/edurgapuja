"""Signing in with a password instead of a code.

OTP remains the primary route. This is the second door, and the things worth
proving about a second door are that it does not leak who has an account, that
it cannot be brute-forced quietly, and that the shared development password
cannot escape development.
"""

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.accounts.checks import dev_login_password_is_not_live
from apps.accounts.models import AdminMembership, Role, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def member(db):
    """Somebody who has actually set a password."""
    user = User.objects.create(phone="+919812345670", first_name="Ananya")
    user.set_password("a-real-password")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def passwordless(db):
    """The common case: an account created by verifying a phone number."""
    return User.objects.create(phone="+919812345671", first_name="Rohan")


# --------------------------------------------------------------------------
# The ordinary door
# --------------------------------------------------------------------------

def test_a_password_signs_you_in(api, member):
    response = api.post(reverse("password-login"),
                        {"phone": member.phone, "password": "a-real-password"},
                        format="json")

    assert response.status_code == 200
    assert response.json()["user"]["phone"] == member.phone
    assert response.json()["access"]


def test_a_phone_number_is_accepted_however_it_is_typed(api, member):
    response = api.post(reverse("password-login"),
                        {"phone": "98123 45670", "password": "a-real-password"},
                        format="json")

    assert response.status_code == 200


def test_a_wrong_password_is_refused(api, member):
    response = api.post(reverse("password-login"),
                        {"phone": member.phone, "password": "nope"}, format="json")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_every_failure_reads_the_same(api, member, passwordless):
    """Wrong password, no password set, no account at all — one answer.

    Anything else turns this endpoint into a way to ask whether a number holds
    an account, which is exactly what the OTP endpoints refuse to reveal.
    """
    wrong = api.post(reverse("password-login"),
                     {"phone": member.phone, "password": "nope"}, format="json")
    unset = api.post(reverse("password-login"),
                     {"phone": passwordless.phone, "password": "nope"}, format="json")
    absent = api.post(reverse("password-login"),
                      {"phone": "+919999999999", "password": "nope"}, format="json")

    assert wrong.status_code == unset.status_code == absent.status_code == 401
    assert wrong.json() == unset.json() == absent.json()


def test_a_deactivated_account_cannot_sign_in(api, member):
    User.objects.filter(pk=member.pk).update(is_active=False)

    response = api.post(reverse("password-login"),
                        {"phone": member.phone, "password": "a-real-password"},
                        format="json")

    assert response.status_code == 401


# --------------------------------------------------------------------------
# Setting one
# --------------------------------------------------------------------------

def test_setting_a_password_needs_a_session(api, passwordless):
    """A phone number alone must not be able to claim an account by giving it
    a password — proving the number comes first."""
    response = api.post(reverse("password-set"), {"password": "something-long"},
                        format="json")

    assert response.status_code == 401


def test_a_signed_in_visitor_can_set_a_password_and_then_use_it(api, passwordless):
    api.force_authenticate(passwordless)
    assert api.post(reverse("password-set"), {"password": "monsoon-lantern"},
                    format="json").status_code == 204

    api.force_authenticate(None)
    response = api.post(reverse("password-login"),
                        {"phone": passwordless.phone, "password": "monsoon-lantern"},
                        format="json")

    assert response.status_code == 200


def test_a_short_password_is_refused(api, passwordless):
    api.force_authenticate(passwordless)

    response = api.post(reverse("password-set"), {"password": "short"}, format="json")

    assert response.status_code == 422


# --------------------------------------------------------------------------
# The admin door
# --------------------------------------------------------------------------

def test_an_administrator_signs_in_to_the_console_with_a_password(api, member):
    AdminMembership.objects.create(user=member, role=Role.SUPER_ADMIN)

    response = api.post(reverse("admin-password-login"),
                        {"phone": member.phone, "password": "a-real-password"},
                        format="json")

    assert response.status_code == 200
    assert response.json()["roles"] == ["super_admin"]


def test_a_visitors_password_does_not_open_the_console(api, member):
    """And it is refused in words indistinguishable from a wrong password, so
    the console cannot be used to discover who the administrators are."""
    right = api.post(reverse("admin-password-login"),
                     {"phone": member.phone, "password": "a-real-password"}, format="json")
    wrong = api.post(reverse("admin-password-login"),
                     {"phone": member.phone, "password": "nope"}, format="json")

    assert right.status_code == 401
    assert right.json() == wrong.json()


# --------------------------------------------------------------------------
# The shared development password, and its fence
# --------------------------------------------------------------------------

@override_settings(DEBUG=True, DEV_LOGIN_PASSWORD="password")
def test_the_shared_password_opens_an_account_that_has_none(api, passwordless):
    response = api.post(reverse("password-login"),
                        {"phone": passwordless.phone, "password": "password"},
                        format="json")

    assert response.status_code == 200


@override_settings(DEBUG=False, DEV_LOGIN_PASSWORD="password")
def test_the_shared_password_does_nothing_when_debug_is_off(api, passwordless):
    """Belt as well as braces: even if the check were somehow bypassed, the
    authenticator itself will not honour it outside DEBUG."""
    response = api.post(reverse("password-login"),
                        {"phone": passwordless.phone, "password": "password"},
                        format="json")

    assert response.status_code == 401


@override_settings(DEBUG=False, DEV_LOGIN_PASSWORD="password")
def test_the_server_refuses_to_start_with_a_shared_password_in_production():
    """The braces. One forgotten environment variable would otherwise be every
    account on the platform."""
    problems = dev_login_password_is_not_live(None)

    assert [p.id for p in problems] == ["accounts.E001"]


@override_settings(DEBUG=False, DEV_LOGIN_PASSWORD="")
def test_production_with_no_shared_password_starts_normally():
    assert dev_login_password_is_not_live(None) == []


@override_settings(DEBUG=True, DEV_LOGIN_PASSWORD="password")
def test_the_client_is_told_when_it_is_talking_to_a_demo(api):
    body = api.get(reverse("auth-methods")).json()

    assert body["otp"] is True
    assert body["password"] is True
    assert body["shared_dev_password"] is True


@override_settings(DEBUG=False, DEV_LOGIN_PASSWORD="")
def test_a_real_deployment_says_so(api):
    assert api.get(reverse("auth-methods")).json()["shared_dev_password"] is False


# --------------------------------------------------------------------------
# The first administrator
# --------------------------------------------------------------------------

def test_bootstrapping_creates_the_first_super_admin(db):
    """Every other admin is granted by one who already exists. The first has
    nowhere to come from, so it comes from configuration."""
    from django.core.management import call_command

    call_command("bootstrap_admin", phone="+919812349999", password="a-long-first-password")

    user = User.objects.get(phone="+919812349999")
    assert user.memberships.get().role == Role.SUPER_ADMIN
    assert user.check_password("a-long-first-password")


def test_bootstrapping_twice_changes_nothing(db):
    """It runs on every deploy, so it has to be safe to run on every deploy."""
    from django.core.management import call_command

    call_command("bootstrap_admin", phone="+919812349998", password="first-password-here")
    call_command("bootstrap_admin", phone="+919812349998", password="first-password-here")

    assert AdminMembership.objects.filter(user__phone="+919812349998").count() == 1
    assert User.objects.filter(phone="+919812349998").count() == 1


def test_bootstrapping_rotates_the_password(db):
    """Rotating the platform's first password should be a variable change and a
    redeploy, not a shell session."""
    from django.core.management import call_command

    call_command("bootstrap_admin", phone="+919812349997", password="the-old-password")
    call_command("bootstrap_admin", phone="+919812349997", password="the-new-password")

    user = User.objects.get(phone="+919812349997")
    assert user.check_password("the-new-password")


def test_bootstrapping_with_nothing_configured_does_nothing(db):
    from django.core.management import call_command

    call_command("bootstrap_admin")

    assert not AdminMembership.objects.filter(role=Role.SUPER_ADMIN).exists()

