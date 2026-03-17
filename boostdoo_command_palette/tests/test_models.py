# Copyright 2026 Boostdoo

"""
Tests for boostdoo_command_palette models.
Covers CRUD operations and SQL constraints on:
  - boostdoo.command.favorite
  - boostdoo.command.history
  - boostdoo.command.custom
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError
from odoo.tools import mute_logger


class TestCommandFavorite(TransactionCase):
    """Tests for the boostdoo.command.favorite model."""

    def setUp(self):
        super().setUp()
        self.Favorite = self.env["boostdoo.command.favorite"]
        self.user = self.env.user

    def test_create_favorite(self):
        """A favorite can be created with valid data."""
        fav = self.Favorite.create({
            "name": "Sales Dashboard",
            "command_key": "menu_123",
            "user_id": self.user.id,
        })
        self.assertTrue(fav.id, "Favorite should be created with a valid ID")
        self.assertEqual(fav.name, "Sales Dashboard")
        self.assertEqual(fav.command_key, "menu_123")
        self.assertEqual(fav.user_id, self.user)

    def test_favorite_default_sequence(self):
        """Sequence defaults to 10."""
        fav = self.Favorite.create({
            "name": "Test Fav",
            "command_key": "key_test_default_seq",
            "user_id": self.user.id,
        })
        self.assertEqual(fav.sequence, 10, "Default sequence must be 10")

    def test_favorite_default_user(self):
        """user_id defaults to the current user when not provided."""
        fav = self.Favorite.create({
            "name": "Default User Fav",
            "command_key": "key_default_user",
        })
        self.assertEqual(fav.user_id, self.env.user, "Default user must be the current user")

    def test_favorite_read(self):
        """Created favorite can be searched."""
        self.Favorite.create({
            "name": "Read Test",
            "command_key": "key_read_test",
            "user_id": self.user.id,
        })
        result = self.Favorite.search([("command_key", "=", "key_read_test")])
        self.assertEqual(len(result), 1)

    def test_favorite_unlink(self):
        """A favorite can be deleted."""
        fav = self.Favorite.create({
            "name": "Delete Me",
            "command_key": "key_delete_test",
            "user_id": self.user.id,
        })
        fav_id = fav.id
        fav.unlink()
        remaining = self.Favorite.search([("id", "=", fav_id)])
        self.assertFalse(remaining, "Favorite should be deleted")

    @mute_logger("odoo.sql_db")
    def test_favorite_unique_constraint(self):
        """Two favorites with the same command_key for the same user raise IntegrityError."""
        self.Favorite.create({
            "name": "Unique Test 1",
            "command_key": "key_unique",
            "user_id": self.user.id,
        })
        with self.assertRaises(IntegrityError):
            self.Favorite.create({
                "name": "Unique Test 2",
                "command_key": "key_unique",
                "user_id": self.user.id,
            })

    def test_favorite_same_key_different_user(self):
        """Two users can favorite the same command_key independently."""
        palette_user_group = self.env.ref(
            "boostdoo_command_palette.group_boostdoo_command_palette_user"
        )
        user2 = self.env["res.users"].create({
            "name": "Test User 2",
            "login": "testuser2_fav@boostdoo.test",
            "groups_id": [(4, palette_user_group.id)],
        })
        self.Favorite.create({
            "name": "Shared Key U1",
            "command_key": "key_shared",
            "user_id": self.user.id,
        })
        fav2 = self.Favorite.create({
            "name": "Shared Key U2",
            "command_key": "key_shared",
            "user_id": user2.id,
        })
        self.assertTrue(fav2.id, "Different users can favorite the same command_key")


class TestCommandHistory(TransactionCase):
    """Tests for the boostdoo.command.history model."""

    def setUp(self):
        super().setUp()
        self.History = self.env["boostdoo.command.history"]
        self.user = self.env.user

    def test_create_history(self):
        """A history entry can be created with valid data."""
        entry = self.History.create({
            "command_key": "menu_sales",
            "command_name": "Sales",
            "user_id": self.user.id,
        })
        self.assertTrue(entry.id)
        self.assertEqual(entry.use_count, 1)

    def test_history_default_use_count(self):
        """use_count defaults to 1."""
        entry = self.History.create({
            "command_key": "key_count_default",
            "command_name": "Count Test",
            "user_id": self.user.id,
        })
        self.assertEqual(entry.use_count, 1)

    def test_history_default_user(self):
        """user_id defaults to current user."""
        entry = self.History.create({
            "command_key": "key_default_user_h",
            "command_name": "User Default Test",
        })
        self.assertEqual(entry.user_id, self.env.user)

    def test_history_last_used_set(self):
        """last_used is populated on creation."""
        entry = self.History.create({
            "command_key": "key_last_used",
            "command_name": "Last Used Test",
            "user_id": self.user.id,
        })
        self.assertIsNotNone(entry.last_used, "last_used must be set on creation")

    def test_history_update(self):
        """History entry can be updated."""
        entry = self.History.create({
            "command_key": "key_update_test",
            "command_name": "Old Name",
            "user_id": self.user.id,
        })
        entry.write({"command_name": "New Name", "use_count": 5})
        self.assertEqual(entry.command_name, "New Name")
        self.assertEqual(entry.use_count, 5)

    @mute_logger("odoo.sql_db")
    def test_history_unique_constraint(self):
        """Two entries with the same command_key for the same user raise IntegrityError."""
        self.History.create({
            "command_key": "key_h_unique",
            "command_name": "History Unique 1",
            "user_id": self.user.id,
        })
        with self.assertRaises(IntegrityError):
            self.History.create({
                "command_key": "key_h_unique",
                "command_name": "History Unique 2",
                "user_id": self.user.id,
            })

    def test_history_same_key_different_user(self):
        """Two different users can have history for the same command_key."""
        palette_user_group = self.env.ref(
            "boostdoo_command_palette.group_boostdoo_command_palette_user"
        )
        user2 = self.env["res.users"].create({
            "name": "Test User History 2",
            "login": "testuser2_hist@boostdoo.test",
            "groups_id": [(4, palette_user_group.id)],
        })
        self.History.create({
            "command_key": "key_h_shared",
            "command_name": "Shared History",
            "user_id": self.user.id,
        })
        entry2 = self.History.create({
            "command_key": "key_h_shared",
            "command_name": "Shared History",
            "user_id": user2.id,
        })
        self.assertTrue(entry2.id)

    def test_history_unlink(self):
        """History entry can be deleted."""
        entry = self.History.create({
            "command_key": "key_h_unlink",
            "command_name": "Delete History",
            "user_id": self.user.id,
        })
        entry_id = entry.id
        entry.unlink()
        self.assertFalse(self.History.search([("id", "=", entry_id)]))


class TestCommandCustom(TransactionCase):
    """Tests for the boostdoo.command.custom model."""

    def setUp(self):
        super().setUp()
        self.Custom = self.env["boostdoo.command.custom"]
        # Get or create a valid action for testing
        self.action = self.env["ir.actions.actions"].search([], limit=1)

    def test_create_custom_command(self):
        """A custom command can be created by admin."""
        cmd = self.Custom.create({
            "name": "Open Sales",
            "action_id": self.action.id,
        })
        self.assertTrue(cmd.id)
        self.assertEqual(cmd.name, "Open Sales")
        self.assertTrue(cmd.active, "Default active must be True")
        self.assertEqual(cmd.sequence, 10, "Default sequence must be 10")

    def test_custom_command_defaults(self):
        """Default values are correctly set."""
        cmd = self.Custom.create({
            "name": "Default Test",
            "action_id": self.action.id,
        })
        self.assertTrue(cmd.active)
        self.assertEqual(cmd.sequence, 10)
        self.assertEqual(cmd.company_id, self.env.company)

    def test_custom_command_shortcut(self):
        """Shortcut field is stored and retrieved correctly."""
        cmd = self.Custom.create({
            "name": "Shortcut Test",
            "action_id": self.action.id,
            "shortcut": "ctrl+shift+s",
        })
        self.assertEqual(cmd.shortcut, "ctrl+shift+s")

    def test_custom_command_update(self):
        """Custom command can be updated."""
        cmd = self.Custom.create({
            "name": "Update Test",
            "action_id": self.action.id,
        })
        cmd.write({"name": "Updated Name", "sequence": 5})
        self.assertEqual(cmd.name, "Updated Name")
        self.assertEqual(cmd.sequence, 5)

    def test_custom_command_archive(self):
        """Custom command can be archived (active=False)."""
        cmd = self.Custom.create({
            "name": "Archive Test",
            "action_id": self.action.id,
        })
        cmd.write({"active": False})
        self.assertFalse(cmd.active)
        # Archived commands should not appear in default search
        results = self.Custom.search([("name", "=", "Archive Test")])
        self.assertFalse(results, "Archived command must not appear in default search")

    def test_custom_command_unlink(self):
        """Custom command can be deleted."""
        cmd = self.Custom.create({
            "name": "Delete Custom",
            "action_id": self.action.id,
        })
        cmd_id = cmd.id
        cmd.unlink()
        self.assertFalse(self.Custom.search([("id", "=", cmd_id)]))

    def test_custom_command_group_filter(self):
        """Group filter stored and read correctly."""
        group = self.env.ref("base.group_user")
        cmd = self.Custom.create({
            "name": "Group Test",
            "action_id": self.action.id,
            "group_ids": [(4, group.id)],
        })
        self.assertIn(group, cmd.group_ids)
