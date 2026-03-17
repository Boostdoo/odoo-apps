# Copyright 2026 Boostdoo

"""
Business logic tests for boostdoo_command_palette.
Covers:
  - record_usage() on boostdoo.command.history
  - _cron_cleanup_history() scheduling logic
  - get_commands_for_user() on boostdoo.command.custom
  - Config parameter key correctness
"""

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase


class TestRecordUsage(TransactionCase):
    """Tests for CommandHistory.record_usage()."""

    def setUp(self):
        super().setUp()
        self.History = self.env["boostdoo.command.history"]

    def test_record_usage_creates_new_entry(self):
        """record_usage creates a new history entry if none exists."""
        self.History.record_usage("menu_crm", "CRM")
        entry = self.History.search([
            ("command_key", "=", "menu_crm"),
            ("user_id", "=", self.env.uid),
        ])
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry.command_name, "CRM")
        self.assertEqual(entry.use_count, 1)

    def test_record_usage_updates_existing_entry(self):
        """record_usage increments use_count when called again for the same key."""
        self.History.record_usage("menu_sales", "Sales")
        self.History.record_usage("menu_sales", "Sales")
        self.History.record_usage("menu_sales", "Sales")
        entry = self.History.search([
            ("command_key", "=", "menu_sales"),
            ("user_id", "=", self.env.uid),
        ])
        self.assertEqual(len(entry), 1, "Must not create duplicates")
        self.assertEqual(entry.use_count, 3, "use_count must be incremented on each call")

    def test_record_usage_updates_command_name(self):
        """record_usage updates the command_name on subsequent calls."""
        self.History.record_usage("menu_inv", "Inventory Old")
        self.History.record_usage("menu_inv", "Inventory New")
        entry = self.History.search([
            ("command_key", "=", "menu_inv"),
            ("user_id", "=", self.env.uid),
        ])
        self.assertEqual(entry.command_name, "Inventory New")

    def test_record_usage_updates_last_used(self):
        """record_usage updates last_used on each call."""
        self.History.record_usage("menu_ts", "Timesheet")
        entry = self.History.search([
            ("command_key", "=", "menu_ts"),
            ("user_id", "=", self.env.uid),
        ])
        first_used = entry.last_used
        # Simulate a second call
        self.History.record_usage("menu_ts", "Timesheet")
        entry.invalidate_recordset()
        self.assertGreaterEqual(entry.last_used, first_used)

    def test_record_usage_returns_true(self):
        """record_usage must return True."""
        result = self.History.record_usage("menu_ret", "Return Test")
        self.assertTrue(result)

    def test_record_usage_per_user_isolation(self):
        """record_usage creates separate entries per user."""
        palette_user_group = self.env.ref(
            "boostdoo_command_palette.group_boostdoo_command_palette_user"
        )
        user2 = self.env["res.users"].create({
            "name": "Business Logic User 2",
            "login": "bl_user2@boostdoo.test",
            "groups_id": [(4, palette_user_group.id)],
        })
        self.History.record_usage("menu_shared", "Shared Menu")
        self.History.with_user(user2).record_usage("menu_shared", "Shared Menu")
        entries = self.History.sudo().search([("command_key", "=", "menu_shared")])
        self.assertEqual(len(entries), 2, "Each user must have their own history entry")


class TestCronCleanup(TransactionCase):
    """Tests for CommandHistory._cron_cleanup_history()."""

    def setUp(self):
        super().setUp()
        self.History = self.env["boostdoo.command.history"]

    def _create_old_entry(self, days_ago, key, name):
        """Helper: create a history entry with last_used set to N days ago."""
        entry = self.History.create({
            "command_key": key,
            "command_name": name,
            "user_id": self.env.uid,
        })
        old_date = fields.Datetime.now() - timedelta(days=days_ago)
        entry.write({"last_used": old_date})
        return entry

    def test_cron_cleanup_removes_old_entries(self):
        """Entries older than retention_days are removed."""
        # Set retention to 30 days
        self.env["ir.config_parameter"].sudo().set_param(
            "boostdoo_command_palette.history_retention_days", "30"
        )
        old_entry = self._create_old_entry(40, "key_old_40", "Old Entry 40d")
        recent_entry = self._create_old_entry(10, "key_recent_10", "Recent Entry 10d")

        self.History._cron_cleanup_history()

        self.assertFalse(
            self.History.search([("id", "=", old_entry.id)]),
            "Entry older than 30 days must be deleted"
        )
        self.assertTrue(
            self.History.search([("id", "=", recent_entry.id)]),
            "Recent entry (10 days) must be kept"
        )

    def test_cron_cleanup_config_key_name(self):
        """
        REGRESSION TEST: Verifies that _cron_cleanup_history reads the correct
        config parameter key 'boostdoo_command_palette.history_retention_days'
        and NOT the wrong 'boostdoo_command_palette.history_retention'.

        BUG: command_history.py line 72 reads 'history_retention' but the config
        parameter in ir_config_parameter.xml is 'history_retention_days'.
        This test WILL FAIL until the bug is fixed.
        """
        # Set the correct key (as defined in ir_config_parameter.xml)
        self.env["ir.config_parameter"].sudo().set_param(
            "boostdoo_command_palette.history_retention_days", "5"
        )
        # Ensure the WRONG key returns nothing / default
        self.env["ir.config_parameter"].sudo().set_param(
            "boostdoo_command_palette.history_retention", False
        )

        old_entry = self._create_old_entry(10, "key_config_bug", "Config Bug Test")

        # If the bug is present, the code reads the WRONG key and gets default=30,
        # so the 10-day old entry will NOT be deleted.
        # If the bug is fixed, the code reads the correct key (5 days),
        # so the 10-day old entry WILL be deleted.
        self.History._cron_cleanup_history()

        self.assertFalse(
            self.History.search([("id", "=", old_entry.id)]),
            "BUG: _cron_cleanup_history reads wrong config key 'history_retention' "
            "instead of 'history_retention_days'. Entry should have been deleted "
            "with 5-day retention but was not."
        )

    def test_cron_cleanup_default_retention(self):
        """With no config parameter set, default of 30 days is used."""
        # Remove any existing param
        param = self.env["ir.config_parameter"].sudo().search([
            ("key", "=", "boostdoo_command_palette.history_retention_days")
        ])
        param.unlink()

        # 40 days old should be deleted with default 30
        old_entry = self._create_old_entry(40, "key_default_ret", "Default Retention")
        # 20 days old should be kept
        recent_entry = self._create_old_entry(20, "key_default_keep", "Default Keep")

        self.History._cron_cleanup_history()

        self.assertFalse(self.History.search([("id", "=", old_entry.id)]))
        self.assertTrue(self.History.search([("id", "=", recent_entry.id)]))


class TestGetCommandsForUser(TransactionCase):
    """Tests for CommandCustom.get_commands_for_user()."""

    def setUp(self):
        super().setUp()
        self.Custom = self.env["boostdoo.command.custom"]
        self.action = self.env["ir.actions.actions"].search([], limit=1)

    def test_get_commands_returns_active_only(self):
        """Only active commands are returned."""
        active_cmd = self.Custom.create({
            "name": "Active Command",
            "action_id": self.action.id,
            "active": True,
        })
        archived_cmd = self.Custom.create({
            "name": "Archived Command",
            "action_id": self.action.id,
            "active": False,
        })
        results = self.Custom.get_commands_for_user()
        result_names = [r["name"] for r in results]
        self.assertIn("Active Command", result_names)
        self.assertNotIn("Archived Command", result_names)

    def test_get_commands_returns_dict_list(self):
        """get_commands_for_user returns a list of dicts with expected keys."""
        self.Custom.create({
            "name": "Dict Test Command",
            "action_id": self.action.id,
        })
        results = self.Custom.get_commands_for_user()
        self.assertIsInstance(results, list)
        if results:
            expected_keys = {"name", "description", "action_id", "shortcut", "sequence"}
            self.assertTrue(
                expected_keys.issubset(set(results[0].keys())),
                f"Result dict missing keys. Got: {results[0].keys()}"
            )

    def test_get_commands_company_filter(self):
        """Commands for a different company are not returned."""
        other_company = self.env["res.company"].create({
            "name": "Other Company Test",
        })
        cmd_other = self.Custom.create({
            "name": "Other Company Cmd",
            "action_id": self.action.id,
            "company_id": other_company.id,
        })
        results = self.Custom.get_commands_for_user()
        result_names = [r["name"] for r in results]
        self.assertNotIn("Other Company Cmd", result_names)

    def test_get_commands_no_company_visible_to_all(self):
        """Commands without a company are visible to everyone."""
        cmd_global = self.Custom.create({
            "name": "Global Command No Company",
            "action_id": self.action.id,
            "company_id": False,
        })
        results = self.Custom.get_commands_for_user()
        result_names = [r["name"] for r in results]
        self.assertIn("Global Command No Company", result_names)

    def test_get_commands_group_filter(self):
        """Commands restricted to a group not belonging to the user are hidden."""
        # Create a group the user does NOT belong to
        restricted_group = self.env["res.groups"].create({
            "name": "Restricted Group BCP Test",
        })
        cmd_restricted = self.Custom.create({
            "name": "Restricted Command",
            "action_id": self.action.id,
            "group_ids": [(4, restricted_group.id)],
        })
        results = self.Custom.get_commands_for_user()
        result_names = [r["name"] for r in results]
        self.assertNotIn("Restricted Command", result_names)

    def test_get_commands_no_group_visible_to_all(self):
        """Commands without group restriction are visible to all users."""
        self.Custom.create({
            "name": "Open Command",
            "action_id": self.action.id,
            "group_ids": [],
        })
        results = self.Custom.get_commands_for_user()
        result_names = [r["name"] for r in results]
        self.assertIn("Open Command", result_names)
