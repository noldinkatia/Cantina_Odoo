from odoo import api, fields, models

COLORS = [
    ("purple", "Violeta"),
    ("orange", "Naranja"),
    ("green", "Verde"),
    ("blue", "Azul"),
    ("pink", "Rosa"),
    ("gray", "Gris"),
]


class CantinaCategory(models.Model):
    _name = "cantina.category"
    _description = "Categoría de producto de cantina"
    _order = "sequence, id"

    name = fields.Char("Categoría", required=True)
    sequence = fields.Integer("Secuencia", default=10)
    icon = fields.Char(
        "Ícono", default="fa-cutlery",
        help="Clase de Font Awesome 4, por ejemplo: fa-cutlery, fa-coffee, fa-birthday-cake.",
    )
    color = fields.Selection(COLORS, "Color", default="purple", required=True)
    product_ids = fields.One2many("cantina.product", "category_id", "Productos")
    product_count = fields.Integer("Cantidad de productos", compute="_compute_product_count")

    _name_unique = models.Constraint("UNIQUE(name)", "Ya existe una categoría con ese nombre.")

    @api.depends("product_ids")
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_ids)


class CantinaProduct(models.Model):
    _name = "cantina.product"
    _description = "Producto de cantina"
    _order = "category_id, name"

    def _default_category(self):
        return self.env["cantina.category"].search([], limit=1).id

    def _default_min_stock(self):
        return self.env["cantina.config"].get_config().default_min_stock

    name = fields.Char("Producto", required=True)
    category_id = fields.Many2one(
        "cantina.category", "Categoría", required=True,
        default=_default_category, ondelete="restrict",
    )
    description = fields.Char("Descripción")
    image = fields.Image("Foto", max_width=1024, max_height=1024)
    image_256 = fields.Image("Foto (miniatura)", related="image", max_width=256, max_height=256, store=True)
    price = fields.Float("Precio (Gs.)", digits=(16, 0), required=True)
    stock = fields.Integer("Stock", default=0)
    min_stock = fields.Integer(
        "Stock mínimo", default=_default_min_stock,
        help="Con este valor o menos el producto se marca como 'Pocas unidades'.",
    )
    active = fields.Boolean("Activo", default=True)
    stock_state = fields.Selection(
        [("ok", "Disponible"), ("low", "Pocas unidades"), ("out", "Agotado")],
        "Estado", compute="_compute_stock_state", store=True,
    )
    low_stock = fields.Boolean("Stock bajo", compute="_compute_stock_state", store=True)

    _price_positive = models.Constraint("CHECK(price >= 0)", "El precio no puede ser negativo.")
    _stock_positive = models.Constraint("CHECK(stock >= 0)", "El stock no puede ser negativo.")

    @api.depends("stock", "min_stock")
    def _compute_stock_state(self):
        for rec in self:
            if rec.stock <= 0:
                state = "out"
            elif rec.stock <= rec.min_stock:
                state = "low"
            else:
                state = "ok"
            rec.stock_state = state
            rec.low_stock = state != "ok"
