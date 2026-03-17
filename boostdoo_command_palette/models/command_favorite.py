# Copyright 2026 Boostdoo

from odoo import models, fields


class BoostdooCommandFavorite(models.Model):
    _name = "boostdoo.command.favorite"
    _description = "Boostdoo Command Palette Favorite"
    _order = "sequence, id"

    name = fields.Char(
        string="Command Name",
        required=True,
    )
    command_key = fields.Char(
        string="Command Key",
        required=True,
        help="Unique identifier for the command in the registry.",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        default=lambda self: self.env.user,
        ondelete="cascade",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    _sql_constraints = [
        (
            "unique_command_per_user",
            "UNIQUE(command_key, user_id)",
            "A command can only be favorited once per user.",
        ),
    ]
