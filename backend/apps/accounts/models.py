import hashlib
import hmac

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class ProfileType(BaseModel):
    """Senior Citizens, Families with Young Children, Specially Abled, Press,
    Social Media Influencer (FR-010). Master data, not a hard-coded list."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self) -> str:
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone: str, password: str | None = None, **extra):
        if not phone:
            raise ValueError("A phone number is required.")
        extra["email"] = self.normalize_email(extra.get("email", "")) or ""
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """One table for visitors and administrators.

    The mobile number is the identity (D10). Email and date of birth are profile
    data captured after sign-up, never credentials.
    """

    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        OTHER = "other", "Other"
        UNDISCLOSED = "undisclosed", "Prefer not to say"

    phone = models.CharField(max_length=20, unique=True, help_text="E.164, e.g. +919876543210")

    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)
    email = models.EmailField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=12, choices=Gender.choices, blank=True)

    state = models.ForeignKey("geo.State", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    city = models.ForeignKey("geo.City", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="+")
    pin_code = models.CharField(max_length=10, blank=True)
    profile_types = models.ManyToManyField(ProfileType, blank=True, related_name="users")

    preferred_language = models.CharField(max_length=5, choices=settings.LANGUAGES, default="en")
    phone_verified_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["email"], condition=~models.Q(email=""),
                name="uniq_user_email_when_present",
            )
        ]

    def __str__(self) -> str:
        return self.full_name or self.phone

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def profile_completeness(self) -> int:
        """Drives the app's 'Profile 30% complete' card (FR-011)."""
        filled = sum(bool(v) for v in (
            self.first_name, self.last_name, self.email,
            self.date_of_birth, self.gender, self.city_id,
        ))
        return round(filled / 6 * 100)


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    PANDAL_ADMIN = "pandal_admin", "Pandal Admin"
    SPONSOR_ADMIN = "sponsor_admin", "Sponsor Admin"
    SUB_SPONSOR_ADMIN = "sub_sponsor_admin", "Sub-Sponsor Admin"


class AdminMembership(BaseModel):
    """Grants a role, optionally scoped to one pandal.

    The role tab at sign-in only chooses which portal renders; authority comes
    from this row and is checked server-side (FR-231).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=24, choices=Role.choices)
    # Exactly one of these is set, and which one depends on the role: a pandal
    # admin is scoped to a pandal, a sponsor admin to an organisation, and a
    # super admin to neither.
    pandal = models.ForeignKey("pandals.Pandal", null=True, blank=True,
                               on_delete=models.CASCADE, related_name="memberships")
    organisation = models.ForeignKey("sponsorship.Organisation", null=True, blank=True,
                                     on_delete=models.CASCADE, related_name="memberships")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "role", "pandal", "organisation"],
                                    name="uniq_membership_scope")
        ]

    def __str__(self) -> str:
        scope = self.pandal or self.organisation or "platform"
        return f"{self.user} — {self.get_role_display()} @ {scope}"


class StaffInvitation(BaseModel):
    """How administrator accounts are created (FR-237).

    A single-use link; the invitee sets their own secret. No screen, export or
    log ever shows a credential.
    """

    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=24, choices=Role.choices)
    pandal = models.ForeignKey("pandals.Pandal", null=True, blank=True,
                               on_delete=models.CASCADE, related_name="+")
    invited_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                   related_name="invitations_sent")
    token_hash = models.CharField(max_length=64, db_index=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_user = models.ForeignKey(User, null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name="+")

    @staticmethod
    def hash_token(raw: str) -> str:
        return hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()

    @property
    def is_usable(self) -> bool:
        return self.accepted_at is None and self.expires_at > timezone.now()

    def __str__(self) -> str:
        return f"invite {self.phone} as {self.role}"


class OtpChallenge(BaseModel):
    """Channel-agnostic on purpose. Serves visitors, web checkout and admins."""

    class Channel(models.TextChoices):
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"

    class Purpose(models.TextChoices):
        LOGIN = "login", "Login or sign-up"
        WEB_CHECKOUT = "web_checkout", "Web checkout"
        ADMIN_LOGIN = "admin_login", "Admin login"

    channel = models.CharField(max_length=8, choices=Channel.choices, default=Channel.SMS)
    destination = models.CharField(max_length=254, db_index=True)
    purpose = models.CharField(max_length=16, choices=Purpose.choices, default=Purpose.LOGIN)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    consumed_at = models.DateTimeField(null=True, blank=True)
    request_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["destination", "-created_at"])]

    @staticmethod
    def hash_code(code: str, destination: str) -> str:
        return hmac.new(settings.SECRET_KEY.encode(),
                        f"{destination}:{code}".encode(), hashlib.sha256).hexdigest()

    @property
    def is_live(self) -> bool:
        return (self.consumed_at is None
                and self.attempts < self.max_attempts
                and self.expires_at > timezone.now())

    def verify(self, code: str) -> bool:
        return hmac.compare_digest(self.code_hash, self.hash_code(code, self.destination))

    def __str__(self) -> str:
        return f"otp {self.destination} ({self.purpose})"
