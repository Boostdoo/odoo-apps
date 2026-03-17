# Copyright 2026 Boostdoo

"""
Security tests for boostdoo_command_palette.
Covers:
  - ACL: regular users vs system users on custom commands
  - Record rules: users can only access their own history and favorites
  - Multi-user isolation
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestFavoriteRecordRules(TransactionCase):
    """Record rule tests: each user sees only their own favorites."""

    def setUp(self):
        super().setUp()
        self.Favorite = self.env["boostdoo.command.favorite"]

        palette_user_group = self.env.ref(
            "boostdoo_command_palette.group_boostdoo_command_palette_user"
        )
        self.user1 = self.env["res.users"].create({
            "name": "BCP Security User 1",
            "login": "bcp_sec_user1@boostdoo.test",
            "groups_id": [(4, palette_user_group.id)],
        })
        self.user2 = self.env["res.users"].create({
            "name": "BCP Security User 2",
            "login": "bcp_sec_user2@boostdoo.test",
            "groups_id": [(4, palette_user_group.id)],
        })

    def test_user_sees_own_favorites_only(self):
        """A user can only read their own favorites, not another user's."""
        fav1 = self.Favorite.with_user(self.user1).create({
            "name": "User1 Favorite",
            "command_key": "key_sec_u1",
        })
        fav2 = self.Favorite.with_user(self.user2).create({
            "name": "User2 Favorite",
            "command_key": "key_sec_u2",
        })
        # User1 should see their own favorite
        user1_favs = self.Favorite.with_user(self.user1).search([
            ("command_key", "in", ["key_sec_u1", "key_sec_u2"])
        ])
        self.assertIn(fav1, user1_favs, "User1 must see their own favorite")
        self.assertNotIn(fav2, user1_favs, "User1 must NOT see User2's favorite")

    def test_user_cannot_write_other_users_favorite(self):
        """A user cannot modify another user's favorite."""
        fav2 = self.Favorite.with_user(self.user2).create({
            "name": "User2 Own Fav",
            "command_key": "key_write_sec",
        })
        with self.assertRaises(AccessError):
            fav2.with_user(self.user1).write({"name": "Hacked"})

    def test_user_cannot_delete_other_users_favorite(self):
        """A user cannot delete another user's favorite."""
        fav2 = self.Favorite.with_user(self.user2).create({
            "name": "User2 Delete Fav",
            "command_key": "key_delete_sec",
        })
        with self.assertRaises(AccessError):
            fav2.with_user(self.user1).unlink()


class TestHistoryRecordRules(TransactionCase):
    """Record rule tests: each user sees only their own history."""

    def setUp(self):
        super().setUp()
        self.History = self.env["boostdoo.command.history"]

        palette_user_group = self.env.ref(
            "boostdoo_command_palette.group_boostdoo_command_palette_user"
        )
        self.user1 = self.env["res.users"].create({
            "name": "BCP History User 1",
            "login": "bcp_hist_user1@boostdoo.test",
            "groups_id": [(4, palette_user_group.id)],
        })
        self.user2 = self.env["res.users"].create({
            "name": "BCP History User 2",
            "login": "bcp_hist_user2@boostdoo.test",
            "groups_id": [(4, palette_user_group.id)],
        })

    def test_user_sees_own_history_only(self):
        """A user can only read their own history entries."""
        hist1 = self.History.with_user(self.user1).create({
            "command_key": "key_hist_sec_u1",
            "command_name": "History U1",
        })
        hist2 = self.History.with_user(self.user2).create({
            "command_key": "key_hist_sec_u2",
            "command_name": "History U2",
        })
        user1_history = self.History.with_user(self.user1).search([
            ("command_key", "in", ["key_hist_sec_u1", "key_hist_sec_u2"])
        ])
        self.assertIn(hist1, user1_history, "User1 must see their own history")
        self.assertNotIn(hist2, user1_history, "User1 must NOT see User2's history")

    def test_user_cannot_write_other_users_history(self):
        """A user cannot modify another user's history."""
        hist2 = self.History.with_user(self.user2).create({
            "command_key": "key_hist_write_sec",
            "command_name": "Hist Write Sec",
        })
        with self.assertRaises(AccessError):
            hist2.with_user(self.user1).write({"command_name": "Hacked History"})

    def test_user_cannot_delete_other_users_history(self):
        """A user cannot delete another user's history."""
        hist2 = self.History.with_user(self.user2).create({
            "command_key": "key_hist_delete_sec",
            "command_name": "Hist Delete Sec",
        })
        with self.assertRaises(AccessError):
            hist2.with_user(self.user1).unlink()


class TestCustomCommandACL(TransactionCase):
    """ACL tests for boostdoo.command.custom."""

    def setUp(self):
        super().setUp()
        self.Custom = self.env["boostdoo.command.custom"]
        self.action = self.env["ir.actions.actions"].search([], limit=1)

        # A regular palette user: can READ custom commands but not write/create/delete
        palette_user_group = self.env.ref(
            "boostdoo_command_palette.group_boostdoo_command_palette_user"
        )
        self.regular_user = self.env["res.users"].create({
            "name": "BCP Regular User",
            "login": "bcp_regular@boostdoo.test",
            "groups_id": [(4, palette_user_group.id)],
        })

    def test_regular_user_can_read_custom_commands(self):
        """Regular users have read access on custom commands."""
        cmd = self.Custom.create({
            "name": "Readable Command",
            "action_id": self.action.id,
        })
        result = self.Custom.with_user(self.regular_user).search([("id", "=", cmd.id)])
        self.assertTrue(result, "Regular user must be able to read custom commands")

    def test_regular_user_cannot_create_custom_command(self):
        """Regular users (non-admin) cannot create custom commands."""
        with self.assertRaises(AccessError):
            self.Custom.with_user(self.regular_user).create({
                "name": "Illegal Command",
                "action_id": self.action.id,
            })

    def test_regular_user_cannot_write_custom_command(self):
        """Regular users cannot modify custom commands."""
        cmd = self.Custom.create({
            "name": "Write Protected Cmd",
            "action_id": self.action.id,
        })
        with self.assertRaises(AccessError):
            cmd.with_user(self.regular_user).write({"name": "Hacked"})

    def test_regular_user_cannot_delete_custom_command(self):
        """Regular users cannot delete custom commands."""
        cmd = self.Custom.create({
            "name": "Delete Protected Cmd",
            "action_id": self.action.id,
        })
        with self.assertRaises(AccessError):
            cmd.with_user(self.regular_user).unlink()

    def test_admin_can_create_custom_command(self):
        """System admin (base.group_system) can create custom commands."""
        cmd = self.Custom.create({
            "name": "Admin Created Cmd",
            "action_id": self.action.id,
        })
        self.assertTrue(cmd.id, "Admin must be able to create custom commands")

    def test_admin_can_update_custom_command(self):
        """System admin can update custom commands."""
        cmd = self.Custom.create({
            "name": "Admin Update Cmd",
            "action_id": self.action.id,
        })
        cmd.write({"name": "Admin Updated"})
        self.assertEqual(cmd.name, "Admin Updated")

    def test_admin_can_delete_custom_command(self):
        """System admin can delete custom commands."""
        cmd = self.Custom.create({
            "name": "Admin Delete Cmd",
            "action_id": self.action.id,
        })
        cmd_id = cmd.id
        cmd.unlink()
        self.assertFalse(self.Custom.search([("id", "=", cmd_id)]))


class TestManagerRoleACL(TransactionCase):
    """ACL tests: group_boostdoo_command_palette_manager has full CRUD on custom commands."""

    def setUp(self):
        super().setUp()
        self.Custom = self.env["boostdoo.command.custom"]
        self.action = self.env["ir.actions.actions"].search([], limit=1)

        manager_group = self.env.ref(
            "boostdoo_command_palette.group_boostdoo_command_palette_manager"
        )
        palette_user_group = self.env.ref(
            "boostdoo_command_palette.group_boostdoo_command_palette_user"
        )

        self.manager_user = self.env["res.users"].create({
            "name": "BCP Manager User",
            "login": "bcp_manager@boostdoo.test",
            "groups_id": [(4, manager_group.id)],
        })
        self.regular_user = self.env["res.users"].create({
            "name": "BCP Palette User",
            "login": "bcp_palette_user@boostdoo.test",
            "groups_id": [(4, palette_user_group.id)],
        })

    def test_manager_can_create_custom_command(self):
        """A user with manager role can create custom commands."""
        cmd = self.Custom.with_user(self.manager_user).create({
            "name": "Manager Created Cmd",
            "action_id": self.action.id,
        })
        self.assertTrue(cmd.id, "Manager must be able to create custom commands")

    def test_manager_can_write_custom_command(self):
        """A user with manager role can modify custom commands."""
        cmd = self.Custom.create({
            "name": "Manager Write Cmd",
            "action_id": self.action.id,
        })
        cmd.with_user(self.manager_user).write({"name": "Manager Updated"})
        self.assertEqual(cmd.name, "Manager Updated")

    def test_manager_can_delete_custom_command(self):
        """A user with manager role can delete custom commands."""
        cmd = self.Custom.create({
            "name": "Manager Delete Cmd",
            "action_id": self.action.id,
        })
        cmd_id = cmd.id
        cmd.with_user(self.manager_user).unlink()
        self.assertFalse(self.Custom.search([("id", "=", cmd_id)]))

    def test_manager_inherits_user_group(self):
        """Manager group implies palette user group — manager can also manage favorites."""
        Favorite = self.env["boostdoo.command.favorite"]
        fav = Favorite.with_user(self.manager_user).create({
            "name": "Manager Fav",
            "command_key": "key_mgr_fav",
        })
        self.assertTrue(fav.id, "Manager (implying user group) must create favorites")

    def test_regular_user_cannot_create_custom_command(self):
        """Palette user (non-manager) cannot create custom commands."""
        with self.assertRaises(AccessError):
            self.Custom.with_user(self.regular_user).create({
                "name": "Unauthorized Cmd",
                "action_id": self.action.id,
            })

    def test_regular_user_cannot_write_custom_command(self):
        """Palette user cannot modify custom commands."""
        cmd = self.Custom.create({
            "name": "Protected Cmd",
            "action_id": self.action.id,
        })
        with self.assertRaises(AccessError):
            cmd.with_user(self.regular_user).write({"name": "Hijacked"})

    def test_regular_user_cannot_delete_custom_command(self):
        """Palette user cannot delete custom commands."""
        cmd = self.Custom.create({
            "name": "Protected Delete Cmd",
            "action_id": self.action.id,
        })
        with self.assertRaises(AccessError):
            cmd.with_user(self.regular_user).unlink()

    def test_regular_user_can_read_custom_command(self):
        """Palette user can always read (list) custom commands."""
        cmd = self.Custom.create({
            "name": "Readable By All",
            "action_id": self.action.id,
        })
        result = self.Custom.with_user(self.regular_user).search([("id", "=", cmd.id)])
        self.assertTrue(result, "Palette user must be able to read custom commands")
