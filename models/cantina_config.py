from odoo import api, fields, models


class CantinaConfig(models.Model):
    """Parámetros generales de la cantina (un único registro)."""
    _name = "cantina.config"
    _description = "Parámetros de la cantina"

    name = fields.Char("Nombre de la cantina", required=True, default="Cantina Central")
    subtitle = fields.Char(
        "Mensaje de bienvenida",
        default="Gestioná los productos, el stock y el menú de tu cantina.",
    )
    default_min_stock = fields.Integer("Stock mínimo por defecto", default=5)

    @api.model
    def get_config(self):
        config = self.sudo().search([], limit=1)
        return config or self.sudo().create({})

    @api.model
    def action_open(self):
        config = self.get_config()
        return {
            "type": "ir.actions.act_window",
            "name": "Parámetros",
            "res_model": "cantina.config",
            "res_id": config.id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "current",
        }


class CantinaShift(models.Model):
    _name = "cantina.shift"
    _description = "Turno de la cantina"
    _order = "hour_from, id"

    name = fields.Char("Turno", required=True)
    hour_from = fields.Float("Desde")
    hour_to = fields.Float("Hasta")
    active = fields.Boolean("Activo", default=True)
