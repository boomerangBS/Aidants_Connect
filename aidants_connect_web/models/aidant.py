from __future__ import annotations

import logging
from typing import Collection, Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.dispatch import Signal
from django.utils.functional import cached_property

from aidants_connect_common.utils.constants import JournalActionKeywords

from .mandat import Autorisation, Mandat
from .organisation import Organisation
from .usager import Usager

logger = logging.getLogger()


class AidantManager(UserManager):
    def active(self):
        return self.filter(is_active=True)

    def __normalize_fields(self, extra_fields: dict):
        for field_name in extra_fields.keys():
            field = self.model._meta.get_field(field_name)
            field_value = extra_fields[field_name]

            if field.many_to_many and isinstance(field_value, str):
                extra_fields[field_name] = [pk.strip() for pk in field_value.split(",")]
            if field.many_to_one and not isinstance(
                field_value, field.remote_field.model
            ):
                field_value = (
                    int(field_value)
                    if not isinstance(field_value, int)
                    else field_value
                )
                extra_fields[field_name] = field.remote_field.model(field_value)

    def create_user(self, username, email=None, password=None, **extra_fields):
        self.__normalize_fields(extra_fields)
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        self.__normalize_fields(extra_fields)
        return super().create_superuser(username, email, password, **extra_fields)

    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email).lower()

    def create(self, **kwargs):
        if email := kwargs.get("email"):
            email = email.strip().lower()
            kwargs["email"] = email
            if (
                username := kwargs.get("username")
            ) and username.strip().lower() == email:
                kwargs["username"] = email

        return super().create(**kwargs)


aidants__organisations_changed = Signal()


class AidantType(models.Model):
    name = models.CharField("Nom", max_length=350)

    def __str__(self):
        return f"{self.name}"


class Aidant(AbstractUser):
    profession = models.TextField(blank=False)
    phone = models.TextField("Téléphone", blank=True)

    aidant_type = models.ForeignKey(
        AidantType,
        on_delete=models.SET_NULL,
        verbose_name="Type d'aidant",
        null=True,
        blank=True,
    )

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        verbose_name="Organisation courante",
        related_name="current_aidants",
    )
    organisations = models.ManyToManyField(
        Organisation,
        verbose_name="Membre des organisations",
        related_name="aidants",
    )
    responsable_de = models.ManyToManyField(
        Organisation, related_name="responsables", blank=True
    )
    can_create_mandats = models.BooleanField(
        default=True,
        verbose_name="Aidant - Peut créer des mandats",
        help_text=(
            "Précise si l’utilisateur peut accéder à l’espace aidant "
            "pour créer des mandats."
        ),
    )
    validated_cgu_version = models.TextField(null=True)

    created_at = models.DateTimeField("Date de création", auto_now_add=True, null=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True, null=True)

    objects = AidantManager()

    REQUIRED_FIELDS = AbstractUser.REQUIRED_FIELDS + ["organisation"]

    class Meta:
        verbose_name = "aidant"

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.organisations.add(self.organisation)

    def get_full_name(self):
        return str(self)

    def get_valid_autorisation(self, demarche, usager):
        """
        :param demarche:
        :param usager:
        :return: Autorisation object if this aidant may perform the specified `demarche`
        for the specified `usager`, `None` otherwise.`
        """
        try:
            return (
                Autorisation.objects.active()
                .for_demarche(demarche)
                .for_usager(usager)
                .visible_by(self)
                .get()
            )
        except Autorisation.DoesNotExist:
            return None

    def get_usagers(self):
        """
        :return: a queryset of usagers who have at least one autorisation
        (active or expired) with the aidant's organisation.
        """
        return Usager.objects.visible_by(self).distinct()

    def get_usager(self, usager_id):
        """
        :return: an usager or `None` if the aidant isn't allowed
        by an autorisation to access this usager.
        """
        try:
            return self.get_usagers().get(pk=usager_id)
        except Usager.DoesNotExist:
            return None

    def get_usagers_with_active_autorisation(self):
        """
        :return: a queryset of usagers who have an active autorisation
        with the aidant's organisation.
        """
        active_mandats = Mandat.objects.filter(organisation=self.organisation).active()
        user_list = active_mandats.values_list("usager", flat=True)
        return Usager.objects.filter(pk__in=user_list)

    def get_autorisations(self):
        """
        :return: a queryset of autorisations visible by this aidant.
        """
        return Autorisation.objects.visible_by(self).distinct()

    def get_autorisations_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's autorisations.
        """
        return self.get_autorisations().for_usager(usager)

    def get_active_autorisations_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's active autorisations
        that are visible by this aidant.
        """
        return self.get_autorisations_for_usager(usager).active()

    def get_inactive_autorisations_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's inactive (expired or revoked)
        autorisations that are visible by this aidant.
        """
        return self.get_autorisations_for_usager(usager).inactive()

    def get_active_demarches_for_usager(self, usager):
        """
        :param usager:
        :return: a list of demarches the usager has active autorisations for
        in this aidant's organisation.
        """
        return self.get_active_autorisations_for_usager(usager).values_list(
            "demarche", flat=True
        )

    def get_last_action_timestamp(self):
        """
        :return: the timestamp of this aidant's last logged action or `None`.
        """
        try:
            return self.journal_entries.last().creation_date
        except AttributeError:
            return None

    def get_journal_create_attestation(self, access_token):
        """
        :return: the corresponding 'create_attestation' Journal entry initiated
        by the aidant
        """
        journal_create_attestation = self.journal_entries.filter(
            action=JournalActionKeywords.CREATE_ATTESTATION,
            access_token=access_token,
        ).last()
        return journal_create_attestation

    def is_in_organisation(self, organisation: Organisation):
        return self.organisations.filter(pk=organisation.id).exists()

    def is_responsable_structure(self):
        """
        :return: True if the Aidant is responsable of at least one organisation
        """
        return self.responsable_de.count() >= 1

    def can_see_aidant(self, aidant):
        """
        :return: True if the current object is responsible for at least one of aidant's
        organisations
        """
        respo_orgas = self.responsable_de.all()
        aidant_orgas = aidant.organisations.all()
        return any(org in respo_orgas for org in aidant_orgas)

    def must_validate_cgu(self):
        return self.validated_cgu_version != settings.CGU_CURRENT_VERSION

    @cached_property
    def has_a_totp_device(self):
        return self.totpdevice_set.filter(confirmed=True).exists()

    @cached_property
    def has_a_carte_totp(self) -> bool:
        return hasattr(self, "carte_totp")

    @cached_property
    def number_totp_card(self) -> str:
        if self.has_a_carte_totp:
            return self.carte_totp.serial_number
        return "Pas de Carte"

    def remove_from_organisation(self, organisation: Organisation) -> Optional[bool]:
        if not self.is_in_organisation(organisation):
            return None

        if self.organisations.count() == 1:
            self.is_active = False
            self.save()

            return self.is_active

        self.organisations.remove(organisation)
        if not self.is_in_organisation(self.organisation):
            self.organisation = self.organisations.order_by("id").first()
            self.save()

        aidants__organisations_changed.send(
            sender=self.__class__,
            instance=self,
            diff={"removed": [organisation], "added": []},
        )

        return self.is_active

    def set_organisations(self, organisations: Collection[Organisation]):
        if len(organisations) == 0:
            # Request to remove all organisation and add none
            raise ValueError("Can't remove all the organisations from aidant")

        current = set(self.organisations.all())
        future = set(organisations)
        to_remove = current - future
        to_add = future - current

        if len(to_add) == 0 and len(to_remove) == 0:
            # Nothing to do!
            return self.is_active

        if len(to_add) > 0:
            self.organisations.add(*to_add)
        if len(to_remove) > 0:
            self.organisations.remove(*to_remove)

        if not self.is_in_organisation(self.organisation):
            self.organisation = self.organisations.order_by("id").first()
            self.save()

        aidants__organisations_changed.send(
            sender=self.__class__,
            instance=self,
            diff={
                "removed": sorted(to_remove, key=lambda org: org.pk),
                "added": sorted(to_add, key=lambda org: org.pk),
            },
        )

        return self.is_active