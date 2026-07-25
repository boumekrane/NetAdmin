import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from repositories.auth_repository import AuthRepository
from services.auth_service import AuthService, AuthenticationError, AccountLockedError
from models.auth_models import User


class AuthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(dir=os.path.dirname(__file__))
        self.db_path = os.path.join(self.temp_dir.name, "test_auth.db")
        self.db = DatabaseManager(self.db_path)
        self.repo = AuthRepository(self.db)
        self.service = AuthService(self.repo, max_failed_attempts=2, session_ttl_minutes=30)
        self.service.initialize_defaults()

    def tearDown(self) -> None:
        try:
            self.temp_dir.cleanup()
        except OSError:
            pass

    def test_login_succeeds_for_valid_credentials(self) -> None:
        user = User(username="alice", email="alice@example.com", is_active=True, role_id=1)
        self.repo.create_user(user, self.service.hash_password("StrongPass123!"))
        session = self.service.login("alice", "StrongPass123!", ip_address="127.0.0.1")
        self.assertEqual(session.username, "alice")
        self.assertTrue(self.service.can(session, "VIEW_INVENTORY"))

    def test_login_fails_for_invalid_password(self) -> None:
        user = User(username="alice", email="alice@example.com", is_active=True, role_id=1)
        self.repo.create_user(user, self.service.hash_password("StrongPass123!"))
        with self.assertRaises(AuthenticationError):
            self.service.login("alice", "WrongPassword!", ip_address="127.0.0.1")

    def test_account_locks_after_repeated_failures(self) -> None:
        user = User(username="alice", email="alice@example.com", is_active=True, role_id=1)
        self.repo.create_user(user, self.service.hash_password("StrongPass123!"))
        with self.assertRaises(AuthenticationError):
            self.service.login("alice", "WrongPassword!", ip_address="127.0.0.1")
        with self.assertRaises(AuthenticationError):
            self.service.login("alice", "WrongPassword!", ip_address="127.0.0.1")
        with self.assertRaises(AccountLockedError):
            self.service.login("alice", "StrongPass123!", ip_address="127.0.0.1")

    def test_password_change_and_verification(self) -> None:
        user = User(username="alice", email="alice@example.com", is_active=True, role_id=1)
        self.repo.create_user(user, self.service.hash_password("StrongPass123!"))
        session = self.service.login("alice", "StrongPass123!", ip_address="127.0.0.1")
        self.service.change_password(session, "StrongPass123!", "NewStrongPass456!")
        updated_user = self.repo.get_user_by_username("alice")
        self.assertTrue(self.service.verify_password("NewStrongPass456!", updated_user.password_hash or ""))


if __name__ == "__main__":
    unittest.main()
