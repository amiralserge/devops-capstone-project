"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"

HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_read_an_account(self):
        """it should Read an existing Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type='application/json'
        )
        created_account_id = response.get_json()["id"]

        response = self.client.get(f"{BASE_URL}/{created_account_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        read_data = response.get_json()
        self.assertEqual(account.name, read_data["name"])

    def test_account_not_found(self):
        """It should not Read a non existing account"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_an_account(self):
        """It should update an existing account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type='application/json'
        )
        created_account_id = response.get_json()["id"]

        old_name = account.name
        new_name = "John 117"
        account.name = new_name

        response = self.client.put(
            f"{BASE_URL}/{created_account_id}",
            json=account.serialize(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.get_json()
        self.assertEqual(response_data["name"], new_name)
        self.assertNotEqual(response_data["name"], old_name)

    def test_update_a_non_existing_account(self):
        """It should not update a non existing account"""
        account = AccountFactory()
        response = self.client.put(
            f"{BASE_URL}/0",
            json=account.serialize(),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_an_account(self):
        """It should delete an account"""
        account = self._create_accounts(1)[0]
        response = self.client.delete(
            f"{BASE_URL}/{account.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.text, "")

    def test_delete_non_existing_account(self):
        """delete endpoint should return 204 even for non existing account"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.text, "")

    def test_list_accounts(self):
        """It should list all existing accounts"""
        accounts_list = [a.serialize() for a in self._create_accounts(10)]
        response = self.client.get(BASE_URL)
        accounts_list_from_server = response.get_json()
        self.assertListEqual(accounts_list_from_server, accounts_list)

    def test_list_accounts_should_never_return_404(self):
        """List account endpoint should nerver return 404"""
        response = self.client.get(BASE_URL)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestSecurity(TestCase):
    """Security Tests"""

    def setUp(self):
        self.client = app.test_client()

    def test_security_headers(self):
        """Response should return secured headers"""
        response = self.client.get("/")
        expected_headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'self'; object-src 'none'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for header, expected_value in expected_headers.items():
            self.assertEqual(response.headers.get(header), expected_value)

    def test_cors_policies_headers(self):
        """Response should contain CORS headers"""

        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), "*")

        