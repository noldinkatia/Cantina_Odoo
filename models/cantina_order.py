from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CantinaOrder(models.Model):
    _name = "cantina.order"
    _description = "Pedido de empleado"
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Número de pedido",
        required=True,
        readonly=True,
        default="Nuevo",
        copy=False,
    )

    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        required=True,
        readonly=True,
        index=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        required=True,
        readonly=True,
        index=True,
    )

    department_id = fields.Many2one(
        "hr.department",
        string="Departamento",
        related="employee_id.department_id",
        store=True,
        readonly=True,
    )

    line_ids = fields.One2many(
        "cantina.order.line",
        "order_id",
        string="Platos pedidos",
    )

    total = fields.Float(
        string="Total (Gs.)",
        compute="_compute_total",
        store=True,
        digits=(16, 0),
    )

    state = fields.Selection(
        [
            ("confirmed", "Confirmado"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado",
        default="confirmed",
        required=True,
        readonly=True,
    )

    @api.depends("line_ids.subtotal")
    def _compute_total(self):
        for order in self:
            order.total = sum(order.line_ids.mapped("subtotal"))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group(
            "cantina_app.group_cantina_user"
        ) and not self.env.user.has_group(
            "cantina_app.group_cantina_manager"
        ):
            raise UserError(_("No tenés permiso para crear pedidos."))

        employee = self.env["hr.employee"].sudo().search(
            [("user_id", "=", self.env.user.id)],
            limit=1,
        )

        if not employee:
            raise UserError(_(
                "Tu usuario no está vinculado a una ficha de empleado. "
                "Solicitá a la administradora que vincule tu usuario."
            ))

        for vals in vals_list:
            # El usuario y el empleado siempre se determinan en el servidor.
            vals["user_id"] = self.env.user.id
            vals["employee_id"] = employee.id

            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("cantina.order")
                    or "Pedido"
                )

        return super().create(vals_list)

    @api.model
    def create_order(self, items):
        """Crea un pedido con varios platos y cantidades."""

        if not self.env.user.has_group(
            "cantina_app.group_cantina_user"
        ):
            raise UserError(_("No tenés permiso para realizar pedidos."))

        if not isinstance(items, list) or not items:
            raise UserError(_("Agregá al menos un plato al pedido."))

        today = fields.Date.context_today(self)
        menu_lines = self.env["cantina.menu.line"]

        # Combinar productos repetidos.
        quantities = {}

        for item in items:
            if not isinstance(item, dict):
                raise UserError(_("Los datos del pedido no son válidos."))

            try:
                line_id = int(item.get("menu_line_id"))
                quantity = int(item.get("quantity"))
            except (TypeError, ValueError):
                raise UserError(_("Los datos del pedido no son válidos."))

            if quantity < 1 or quantity > 100:
                raise UserError(
                    _("La cantidad debe estar entre 1 y 100.")
                )

            quantities[line_id] = quantities.get(line_id, 0) + quantity

            if quantities[line_id] > 100:
                raise UserError(
                    _("No podés pedir más de 100 unidades del mismo plato.")
                )

        order_lines = []

        for line_id, quantity in quantities.items():
            menu_line = menu_lines.search(
                [
                    ("id", "=", line_id),
                    ("menu_id.date", "=", today),
                ],
                limit=1,
            )

            if not menu_line:
                raise UserError(_(
                    "Uno de los platos ya no pertenece al menú de hoy."
                ))

            if menu_line.product_id.stock_state == "out":
                raise UserError(_(
                    "El plato '%s' está agotado."
                ) % menu_line.product_id.name)

            order_lines.append({
                "menu_line_id": menu_line.id,
                "quantity": quantity,
            })

        order = self.create({
            "line_ids": [
                (0, 0, line_vals)
                for line_vals in order_lines
            ],
        })

        return {
            "id": order.id,
            "name": order.name,
            "total": order.total,
            "state": order.state,
        }


class CantinaOrderLine(models.Model):
    _name = "cantina.order.line"
    _description = "Detalle del pedido"
    _order = "id"

    order_id = fields.Many2one(
        "cantina.order",
        string="Pedido",
        required=True,
        ondelete="cascade",
        index=True,
    )

    menu_line_id = fields.Many2one(
        "cantina.menu.line",
        string="Plato del menú",
        required=True,
        ondelete="restrict",
    )

    product_id = fields.Many2one(
        "cantina.product",
        string="Producto",
        related="menu_line_id.product_id",
        store=True,
        readonly=True,
    )

    quantity = fields.Integer(
        string="Cantidad",
        required=True,
        default=1,
    )

    price_unit = fields.Float(
        string="Precio unitario (Gs.)",
        required=True,
        digits=(16, 0),
        readonly=True,
    )

    subtotal = fields.Float(
        string="Subtotal (Gs.)",
        compute="_compute_subtotal",
        store=True,
        digits=(16, 0),
    )

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group(
            "cantina_app.group_cantina_user"
        ) and not self.env.user.has_group(
            "cantina_app.group_cantina_manager"
        ):
            raise UserError(_("No tenés permiso para agregar platos."))

        for vals in vals_list:
            order = self.env["cantina.order"].browse(
                vals.get("order_id")
            ).exists()

            if not order:
                raise UserError(_("El pedido indicado no existe."))

            if order.user_id != self.env.user:
                raise UserError(
                    _("No podés agregar platos a otro pedido.")
                )

            menu_line = self.env["cantina.menu.line"].browse(
                vals.get("menu_line_id")
            ).exists()

            if not menu_line:
                raise UserError(_("El plato indicado no existe."))

            if menu_line.menu_id.date != fields.Date.context_today(self):
                raise UserError(
                    _("Solo podés pedir platos del menú de hoy.")
                )

            try:
                quantity = int(vals.get("quantity", 0))
            except (TypeError, ValueError):
                raise ValidationError(_("La cantidad no es válida."))

            if quantity < 1 or quantity > 100:
                raise ValidationError(
                    _("La cantidad debe estar entre 1 y 100.")
                )

            if menu_line.product_id.stock_state == "out":
                raise UserError(_("Ese producto está agotado."))

            # El precio se obtiene del menú en el servidor.
            vals["price_unit"] = menu_line.price

        return super().create(vals_list)
