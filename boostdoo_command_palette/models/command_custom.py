# Copyright 2026 Boostdoo

from odoo import models, fields, api


class BoostdooCommandCustom(models.Model):
    _name = "boostdoo.command.custom"
    _description = "Boostdoo Custom Command"
    _order = "sequence, name"

    name = fields.Char(
        string="Command Name",
        required=True,
        translate=True,
    )
    description = fields.Char(
        string="Description",
        translate=True,
        help="Short description shown in the command palette.",
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        string="Action",
        required=True,
        ondelete="cascade",
        help="The Odoo action to execute when this command is selected.",
    )
    shortcut = fields.Char(
        string="Keyboard Shortcut",
        help="Optional additional keyboard shortcut (e.g. ctrl+shift+s).",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Allowed Groups",
        help="If set, only users belonging to these groups can see this command.",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        help="If set, this command is only available for the specified company.",
    )

    @api.model
    def get_commands_for_user(self):
        """
        Return custom commands accessible by the current user.
        Applies group and company filtering.
        """
        domain = [("active", "=", True)]

        # Multi-company filter — restrict to the user's currently active company
        domain += [
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.env.company.id),
        ]

        commands = self.search(domain)

        # Filter by group access
        accessible = commands.filtered(
            lambda c: not c.group_ids or bool(c.group_ids & self.env.user.groups_id)
        )

        return accessible.read(["name", "description", "action_id", "shortcut", "sequence"])
