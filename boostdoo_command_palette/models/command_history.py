# Copyright 2026 Boostdoo

from odoo import models, fields, api
from datetime import timedelta


class BoostdooCommandHistory(models.Model):
    _name = "boostdoo.command.history"
    _description = "Boostdoo Command Palette History"
    _order = "last_used desc"

    command_key = fields.Char(
        string="Command Key",
        required=True,
        help="Unique identifier for the command in the registry.",
    )
    command_name = fields.Char(
        string="Command Name",
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        default=lambda self: self.env.user,
        ondelete="cascade",
    )
    last_used = fields.Datetime(
        string="Last Used",
        required=True,
        default=fields.Datetime.now,
    )
    use_count = fields.Integer(
        string="Use Count",
        default=1,
    )

    _sql_constraints = [
        (
            "unique_command_per_user",
            "UNIQUE(command_key, user_id)",
            "Command history entry must be unique per user.",
        ),
    ]

    @api.model
    def record_usage(self, command_key, command_name):
        """Record or update usage of a command for the current user."""
        existing = self.search([
            ("command_key", "=", command_key),
            ("user_id", "=", self.env.uid),
        ], limit=1)
        if existing:
            existing.write({
                "last_used": fields.Datetime.now(),
                "use_count": existing.use_count + 1,
                "command_name": command_name,
            })
        else:
            self.create({
                "command_key": command_key,
                "command_name": command_name,
                "user_id": self.env.uid,
            })
        return True

    @api.model
    def _cron_cleanup_history(self):
        """Remove history entries older than the configured retention period."""
        retention_days = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "boostdoo_command_palette.history_retention_days", default=30
            )
        )
        cutoff_date = fields.Datetime.now() - timedelta(days=retention_days)
        old_records = self.search([("last_used", "<", cutoff_date)])
        old_records.unlink()
