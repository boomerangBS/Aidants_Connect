from datetime import datetime

from django.test import TestCase

import pytz

from aidants_connect_habilitation.tasks import update_pix_and_create_aidant
from aidants_connect_web.models import Aidant, HabilitationRequest
from aidants_connect_web.tests.factories import (
    HabilitationRequestFactory,
    OrganisationFactory,
)


class ImportPixTests(TestCase):
    def test_import_pix_results_and_create_new_aidant(self):
        aidant_a_former = HabilitationRequestFactory(
            email="marina.botteau@aisne.gouv.fr",
            formation_done=True,
            date_formation=datetime(2022, 1, 1, tzinfo=pytz.UTC),
        )
        self.assertEqual(aidant_a_former.test_pix_passed, False)
        self.assertEqual(aidant_a_former.date_test_pix, None)
        self.assertEqual(aidant_a_former.status, HabilitationRequest.STATUS_NEW)
        self.assertEqual(0, Aidant.objects.filter(email=aidant_a_former.email).count())

        data = [
            {
                "date d'envoi": "2022-01-01",
                "email saisi": "marina.botteau@aisne.gouv.fr",
            }
        ]
        update_pix_and_create_aidant(data)

        aidant_a_former = HabilitationRequest.objects.filter(
            email=aidant_a_former.email
        )[0]
        self.assertTrue(aidant_a_former.test_pix_passed)
        self.assertEqual(aidant_a_former.status, HabilitationRequest.STATUS_VALIDATED)

        self.assertEqual(1, Aidant.objects.filter(email=aidant_a_former.email).count())

    def test_import_pix_results_and_do_not_create_new_aidant(self):
        aidant_a_former = HabilitationRequestFactory(
            email="marina.botteau@aisne.gouv.fr"
        )
        self.assertEqual(aidant_a_former.formation_done, False)
        self.assertEqual(aidant_a_former.date_formation, None)
        self.assertEqual(aidant_a_former.test_pix_passed, False)
        self.assertEqual(aidant_a_former.date_test_pix, None)
        self.assertEqual(aidant_a_former.status, HabilitationRequest.STATUS_NEW)
        self.assertEqual(0, Aidant.objects.filter(email=aidant_a_former.email).count())

        data = [
            {
                "date d'envoi": "2022-01-01",
                "email saisi": "marina.botteau@aisne.gouv.fr",
            }
        ]
        update_pix_and_create_aidant(data)

        aidant_a_former = HabilitationRequest.objects.filter(
            email=aidant_a_former.email
        )[0]
        self.assertTrue(aidant_a_former.test_pix_passed)
        self.assertEqual(aidant_a_former.status, HabilitationRequest.STATUS_NEW)

        self.assertEqual(0, Aidant.objects.filter(email=aidant_a_former.email).count())

    def test_import_pix_results_aidant_has_two_orgas(self):
        organisation_1 = OrganisationFactory(name="MAIRIE", siret="121212122")
        aidant_a_former_1 = HabilitationRequestFactory(
            email="marina.botteau@aisne.gouv.fr",
            formation_done=True,
            date_formation=datetime(2022, 1, 1, tzinfo=pytz.UTC),
            organisation=organisation_1,
        )
        organisation_2 = OrganisationFactory(name="MAIRIE2", siret="121212123")
        aidant_a_former_2 = HabilitationRequestFactory(
            email="marina.botteau@aisne.gouv.fr",
            formation_done=True,
            date_formation=datetime(2022, 1, 1, tzinfo=pytz.UTC),
            organisation=organisation_2,
        )
        self.assertEqual(aidant_a_former_1.test_pix_passed, False)
        self.assertEqual(aidant_a_former_1.date_test_pix, None)
        self.assertEqual(aidant_a_former_2.test_pix_passed, False)
        self.assertEqual(aidant_a_former_2.date_test_pix, None)
        self.assertEqual(aidant_a_former_1.status, HabilitationRequest.STATUS_NEW)
        self.assertEqual(aidant_a_former_2.status, HabilitationRequest.STATUS_NEW)
        self.assertEqual(
            0, Aidant.objects.filter(email=aidant_a_former_1.email).count()
        )

        data = [
            {
                "date d'envoi": "2022-01-01",
                "email saisi": "marina.botteau@aisne.gouv.fr",
            }
        ]
        update_pix_and_create_aidant(data)

        aidant_a_former_1 = HabilitationRequest.objects.filter(
            email=aidant_a_former_1.email
        )[0]
        self.assertTrue(aidant_a_former_1.test_pix_passed)
        self.assertEqual(aidant_a_former_1.status, HabilitationRequest.STATUS_VALIDATED)

        aidant_a_former_2 = HabilitationRequest.objects.filter(
            email=aidant_a_former_1.email
        )[1]
        self.assertTrue(aidant_a_former_2.test_pix_passed)
        self.assertEqual(aidant_a_former_2.status, HabilitationRequest.STATUS_VALIDATED)

        self.assertEqual(
            1, Aidant.objects.filter(email=aidant_a_former_1.email).count()
        )
        aidant = Aidant.objects.filter(email=aidant_a_former_1.email)[0]
        self.assertIn(organisation_1, aidant.organisations.all())
        self.assertIn(organisation_2, aidant.organisations.all())