from uuid import uuid4

from django.db import models
from django.db.models import Q, SET_NULL
from phonenumber_field.modelfields import PhoneNumberField

from aidants_connect.common.constants import (
    RequestStatusConstants,
    MessageStakeholders,
    RequestOriginConstants,
)
from aidants_connect_web.models import OrganisationType

__all__ = [
    "PersonWithResponsibilities",
    "Issuer",
    "DataPrivacyOfficer",
    "Manager",
    "OrganisationRequest",
    "AidantRequest",
    "RequestMessage",
]


def _new_uuid():
    return uuid4()


class Person(models.Model):
    first_name = models.CharField("Prénom", max_length=150)
    last_name = models.CharField("Nom", max_length=150)
    email = models.EmailField("Email", max_length=150)
    profession = models.CharField("Profession", blank=False, max_length=150)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        abstract = True


class PersonWithResponsibilities(Person):
    phone = PhoneNumberField("Téléphone", blank=True)

    class Meta:
        abstract = True


class Issuer(PersonWithResponsibilities):
    """Model describing the issuer of a habilitation request. The French term is
    'demandeur'."""

    issuer_id = models.UUIDField(
        "Identifiant de demandeur", default=_new_uuid, unique=True
    )

    class Meta:
        verbose_name = "Demandeur"


class DataPrivacyOfficer(PersonWithResponsibilities):
    pass


class Manager(PersonWithResponsibilities):
    address = models.TextField("Adresse")
    zipcode = models.CharField("Code Postal", max_length=10)
    city = models.CharField("Ville", max_length=255)

    is_aidant = models.BooleanField("C'est aussi un aidant", default=False)


class OrganisationRequest(models.Model):
    issuer = models.ForeignKey(
        Issuer,
        on_delete=models.CASCADE,
        related_name="organisation_requests",
        verbose_name="Demandeur",
    )

    manager = models.OneToOneField(
        Manager,
        on_delete=models.CASCADE,
        related_name="organisation",
        verbose_name="Responsable",
        default=None,
        null=True,
    )

    data_privacy_officer = models.OneToOneField(
        DataPrivacyOfficer,
        on_delete=models.CASCADE,
        related_name="organisation",
        verbose_name="Délégué à la protection des données",
        default=None,
        null=True,
    )

    draft_id = models.UUIDField(
        "Identifiant de brouillon",
        null=True,
        default=_new_uuid,
        unique=True,
    )

    status = models.CharField(
        "État",
        max_length=150,
        default=RequestStatusConstants.NEW.name,
        choices=RequestStatusConstants.choices(),
    )

    type = models.ForeignKey(OrganisationType, null=True, on_delete=SET_NULL)

    type_other = models.CharField(
        "Type de structure si autre",
        blank=True,
        default="",
        max_length=200,
    )

    # Organisation
    name = models.TextField("Nom de la structure")
    siret = models.BigIntegerField("N° SIRET", default=1)
    address = models.TextField("Adresse")
    zipcode = models.CharField("Code Postal", max_length=10)
    city = models.CharField("Ville", max_length=255, blank=True)

    partner_administration = models.CharField(
        "Administration partenaire",
        blank=True,
        default="",
        max_length=200,
    )

    public_service_delegation_attestation = models.FileField(
        "Attestation de délégation de service public",
        blank=True,
        default="",
    )

    france_services_label = models.BooleanField(
        "Labellisation France Services", default=False
    )

    web_site = models.URLField("Site web", blank=True, default="")

    mission_description = models.TextField("Description des missions de la structure")

    avg_nb_demarches = models.IntegerField(
        "Nombre moyen de démarches ou de dossiers traités par semaine"
    )

    # Checkboxes
    cgu = models.BooleanField("J'accepte les CGU")
    dpo = models.BooleanField("Le DPO est informé")
    professionals_only = models.BooleanField(
        "La structure ne contient que des aidants professionnels"
    )
    without_elected = models.BooleanField("Aucun élu n'est impliqué dans la structure")

    @property
    def is_draft(self):
        return self.draft_id is not None

    def confirm_request(self):
        self.draft_id = None
        self.save()

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (
                        ~Q(type_id=RequestOriginConstants.OTHER.value)
                        & Q(type_other__isnull_or_blank=True)
                    )
                    | (
                        Q(type_id=RequestOriginConstants.OTHER.value)
                        & Q(type_other__isnull_or_blank=False)
                    )
                ),
                name="type_other_correctly_set",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(cgu=True)),
                name="cgu_checked",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(dpo=True)),
                name="dpo_checked",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(professionals_only=True)),
                name="professionals_only_checked",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(without_elected=True)),
                name="without_elected_checked",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(manager__isnull=False)),
                name="manager_set",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(data_privacy_officer__isnull=False)),
                name="data_privacy_officer_set",
            ),
        ]
        verbose_name = "Demande d’habilitation"
        verbose_name_plural = "Demandes d’habilitation"


class AidantRequest(Person):
    organisation = models.ForeignKey(
        OrganisationRequest,
        on_delete=models.CASCADE,
        related_name="aidant_requests",
    )

    @property
    def is_draft(self):
        return self.organisation.is_draft

    @property
    def draft_id(self):
        return self.organisation.draft_id

    class Meta:
        verbose_name = "aidant à habiliter"
        verbose_name_plural = "aidants à habiliter"


class RequestMessage(models.Model):
    organisation = models.ForeignKey(
        OrganisationRequest,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.CharField(
        "Expéditeur", max_length=20, choices=MessageStakeholders.choices()
    )
    content = models.TextField("Message")

    def __str__(self):
        return f"Message {self.id}"

    class Meta:
        verbose_name = "message"