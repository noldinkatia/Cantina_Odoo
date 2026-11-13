from odoo import api, fields, models

WEEKDAYS = [
    ("0", "Lunes"),
    ("1", "Martes"),
    ("2", "Miércoles"),
    ("3", "Jueves"),
    ("4", "Viernes"),
    ("5", "Sábado"),
    ("6", "Domingo"),
]


class CantinaMenu(models.Model):
    _name = "cantina.menu"
    _description = "Menú del día"
    _order = "date desc"
    _rec_name = "date"

    date = fields.Date("Fecha", required=True, default=fields.Date.context_today)
    line_ids = fields.One2many("cantina.menu.line", "menu_id", "Platos")
    line_count = fields.Integer("Cantidad de platos", compute="_compute_line_count")

    _date_unique = models.Constraint("UNIQUE(date)", "Ya existe un menú para esa fecha.")

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.model
    def action_open_today(self):
        """Abre (o crea) el menú de hoy."""
        today = fields.Date.context_today(self)
        menu = self.search([("date", "=", today)], limit=1) or self.create({"date": today})
        return {
            "type": "ir.actions.act_window",
            "name": "Menú diario",
            "res_model": "cantina.menu",
            "res_id": menu.id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "current",
        }

    def action_load_weekly(self):
        """Agrega los productos del menú semanal fijo correspondiente al día."""
        Line = self.env["cantina.menu.line"]
        for menu in self:
            weekly = self.env["cantina.weekly.menu"].search(
                [("weekday", "=", str(menu.date.weekday()))], limit=1)
            for product in weekly.product_ids - menu.line_ids.product_id:
                Line.create({"menu_id": menu.id, "product_id": product.id})
        return True


class CantinaMenuLine(models.Model):
    _name = "cantina.menu.line"
    _description = "Plato del menú del día"
    _order = "sequence, id"

    menu_id = fields.Many2one("cantina.menu", "Menú", required=True, ondelete="cascade")
    sequence = fields.Integer("Secuencia", default=10)
    product_id = fields.Many2one("cantina.product", "Producto", required=True, ondelete="restrict")
    description = fields.Char(
        "Descripción", compute="_compute_from_product",
        store=True, readonly=False, precompute=True)
    price = fields.Float(
        "Precio (Gs.)", digits=(16, 0), compute="_compute_from_product",
        store=True, readonly=False, precompute=True)
    image = fields.Image(
        "Foto del plato", max_width=1024, max_height=1024,
        compute="_compute_image", store=True, readonly=False, precompute=True,
        help="Por defecto es la foto del producto; podés subir otra solo para este menú.")
    image_256 = fields.Image("Foto (miniatura)", related="image", max_width=256, max_height=256, store=True)
    stock_state = fields.Selection(related="product_id.stock_state", string="Estado")

    _menu_product_unique = models.Constraint(
        "UNIQUE(menu_id, product_id)", "Ese producto ya está en el menú de ese día.")

    @api.depends("product_id")
    def _compute_from_product(self):
        for rec in self:
            rec.description = rec.product_id.description
            rec.price = rec.product_id.price

    @api.depends("product_id", "product_id.image")
    def _compute_image(self):
        for rec in self:
            rec.image = rec.product_id.image


class CantinaWeeklyMenu(models.Model):
    _name = "cantina.weekly.menu"
    _description = "Menú semanal fijo"
    _order = "weekday"
    _rec_name = "description"

    weekday = fields.Selection(WEEKDAYS, "Día", required=True)
    description = fields.Char("Menú", required=True, help="Ej: Guiso, poroto, locro")
    product_ids = fields.Many2many("cantina.product", string="Productos")
    active = fields.Boolean("Activo", default=True)

    _weekday_unique = models.Constraint("UNIQUE(weekday)", "Ya hay un menú fijo para ese día.")
