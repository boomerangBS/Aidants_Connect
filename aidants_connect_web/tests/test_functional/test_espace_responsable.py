from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


@tag("functional")
class RemoveAidantFromOrganisationTests(FunctionalTestCase):
    def setUp(self):
        self.organisation = OrganisationFactory()
        self.aidant_responsable: Aidant = AidantFactory(
            organisation=self.organisation,
            post__with_otp_device=True,
            post__is_organisation_manager=True,
        )

        self.aidant_coresponsable: Aidant = AidantFactory(
            organisation=self.organisation,
            post__is_organisation_manager=True,
        )

        self.aidant_active_with_card = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=False,
        )

        self.aidant_active_with_card_confirmed = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
        )

        self.aidant_active_without_card = AidantFactory(organisation=self.organisation)

        self.aidant_inactive_with_card = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=False,
            is_active=False,
        )

        self.aidant_inactive_with_card_confirmed = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
            is_active=False,
        )

        self.aidant_inactive_without_card = AidantFactory(
            organisation=self.organisation,
            is_active=False,
        )

        self.aidant_with_multiple_orgs = AidantFactory(organisation=self.organisation)
        self.aidant_with_multiple_orgs.organisations.add(
            OrganisationFactory(),
            OrganisationFactory(),
        )

    def __get_live_url(self, organisation_id: int):
        return reverse(
            "espace_responsable_organisation",
            kwargs={"organisation_id": organisation_id},
        )

    def test_aidants_actions(self):
        root_path = self.__get_live_url(self.organisation.pk)

        self.open_live_url(root_path)

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(url_matches(f"^.+{root_path}$"))

        # Can't link card to inactive aidants
        self.assertElementNotFound(
            By.ID, f"add-totp-card-to-aidant-{self.aidant_inactive_with_card.pk}"
        )
        self.assertElementNotFound(
            By.ID, f"add-totp-card-to-aidant-{self.aidant_inactive_without_card.pk}"
        )
        self.assertElementNotFound(
            By.ID,
            f"add-totp-card-to-aidant-{self.aidant_inactive_with_card_confirmed.pk}",
        )

        # Can't validate card for inactive aidants
        self.assertElementNotFound(
            By.ID, f"validate-totp-card-for-aidant-{self.aidant_inactive_with_card.pk}"
        )
        self.assertElementNotFound(
            By.ID,
            "validate-totp-card-for-aidant-" f"{self.aidant_inactive_without_card.pk}",
        )
        self.assertElementNotFound(
            By.ID,
            "validate-totp-card-for-aidant-"
            f"{self.aidant_inactive_with_card_confirmed.pk}",
        )

        # Can unlink card from inactive aidant
        self.selenium.find_element(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_inactive_with_card.pk}"
        )
        self.selenium.find_element(
            By.ID,
            "remove-totp-card-from-aidant-"
            f"{self.aidant_inactive_with_card_confirmed.pk}",
        )

        # Can't unlink card from aidants without card
        self.assertElementNotFound(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_active_without_card.pk}"
        )
        self.assertElementNotFound(
            By.ID,
            f"remove-totp-card-from-aidant-{self.aidant_inactive_without_card.pk}",
        )

        # Can add card to active aidant without card
        self.selenium.find_element(
            By.ID, f"add-totp-card-to-aidant-{self.aidant_active_without_card.pk}"
        )
        self.assertElementNotFound(
            By.ID, f"add-totp-card-to-aidant-{self.aidant_active_with_card.pk}"
        )
        self.assertElementNotFound(
            By.ID,
            f"add-totp-card-to-aidant-{self.aidant_active_with_card_confirmed.pk}",
        )

        # Can verify card for active aidant with card
        self.selenium.find_element(
            By.ID, f"validate-totp-card-for-aidant-{self.aidant_active_with_card.pk}"
        )
        self.assertElementNotFound(
            By.ID, f"validate-totp-card-for-aidant-{self.aidant_active_without_card.pk}"
        )
        self.assertElementNotFound(
            By.ID,
            "validate-totp-card-for-aidant-"
            f"{self.aidant_active_with_card_confirmed.pk}",
        )

    def test_grouped_autorisations(self):
        root_path = self.__get_live_url(self.organisation.pk)

        self.open_live_url(root_path)

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(url_matches(f"^.+{root_path}$"))

        # Check button text
        button = self.selenium.find_element(
            By.ID,
            f"remove-aidant-{self.aidant_with_multiple_orgs.pk}-from-organisation",
        )
        self.assertEqual(
            "Retirer l’aidant de l’organisation",
            button.text,
        )

        button = self.selenium.find_element(
            By.ID, f"remove-aidant-{self.aidant_active_with_card.pk}-from-organisation"
        )
        self.assertEqual("Désactiver l’aidant", button.text)

        self.assertElementNotFound(
            By.ID, f"remove-aidant-{self.aidant_responsable.pk}-from-organisation"
        )

        # Let's try those btns shall we?
        button.click()
        path = reverse(
            "espace_responsable_remove_aidant_from_organisation",
            kwargs={
                "organisation_id": self.organisation.pk,
                "aidant_id": self.aidant_active_with_card.pk,
            },
        )
        self.wait.until(url_matches(f"^.+{path}$"))

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Confirmer']"
        ).click()

        self.wait.until(url_matches(f"^.+{root_path}$"))

        self.assertElementNotFound(
            By.ID, f"remove-aidant-{self.aidant_active_with_card.pk}-from-organisation"
        )

        self.selenium.find_element(
            By.ID,
            f"remove-aidant-{self.aidant_with_multiple_orgs.pk}-from-organisation",
        ).click()
        path = reverse(
            "espace_responsable_remove_aidant_from_organisation",
            kwargs={
                "organisation_id": self.organisation.pk,
                "aidant_id": self.aidant_with_multiple_orgs.pk,
            },
        )
        self.wait.until(url_matches(f"^.+{path}$"))

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Confirmer']"
        ).click()

        self.wait.until(url_matches(f"^.+{root_path}$"))

        self.assertElementNotFound(
            By.ID,
            f"remove-aidant-{self.aidant_with_multiple_orgs.pk}-from-organisation",
        )

    def test_remove_card_from_aidant(self):
        root_path = self.__get_live_url(self.organisation.pk)

        self.open_live_url(root_path)

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(url_matches(f"^.+{root_path}$"))

        # First aidant: disabled
        self.assertIsNotNone(self.aidant_inactive_with_card.carte_totp)
        button1 = self.selenium.find_element(
            By.ID,
            f"remove-totp-card-from-aidant-{ self.aidant_inactive_with_card.pk }",
        )
        self.assertEqual("Délier la carte", button1.text)

        button1.click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_aidant_remove_card",
                kwargs={"aidant_id": self.aidant_inactive_with_card.pk},
            )
        )

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Dissocier']"
        ).click()

        self.wait.until(
            self.path_matches(
                "espace_responsable_organisation",
                kwargs={"organisation_id": self.aidant_responsable.organisation.pk},
            )
        )

        self.assertElementNotFound(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_inactive_with_card.pk}"
        )

        self.aidant_inactive_with_card.refresh_from_db()
        with self.assertRaises(Aidant.carte_totp.RelatedObjectDoesNotExist):
            self.aidant_inactive_with_card.carte_totp

        self.assertIsNotNone(self.aidant_active_with_card.carte_totp)
        button2 = self.selenium.find_element(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_active_with_card.pk}"
        )
        self.assertEqual("Délier la carte", button2.text)

        # First aidant: active
        button2.click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_aidant_remove_card",
                kwargs={"aidant_id": self.aidant_active_with_card.pk},
            )
        )

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Dissocier']"
        ).click()

        self.wait.until(
            self.path_matches(
                "espace_responsable_organisation",
                kwargs={"organisation_id": self.aidant_responsable.organisation.pk},
            )
        )

        self.assertElementNotFound(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_active_with_card.pk}"
        )

        self.aidant_active_with_card.refresh_from_db()
        with self.assertRaises(Aidant.carte_totp.RelatedObjectDoesNotExist):
            self.aidant_active_with_card.carte_totp