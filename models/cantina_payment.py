
"""Integración de Cantina con el Punto de Venta de Odoo 19.

Los pedidos se crean en Cantina. La cajera los recupera desde el POS,
los carga en una orden normal y los cobra con los medios de pago del POS.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


PAYMENT_STATES = [
    ("unpaid", "Pendiente de pago"),
    ("paid", "Pagado"),
]


def _only_existing(model, vals):
    """Conserva únicamente los campos existentes en el modelo."""
    return {key: value for key, value in vals.items() if key in model._fields}


class CantinaConfig(models.Model):
    _inherit = "cantina.config"

    pos_config_id = fields.Many2one(
        "pos.config",
        string="Caja de la cantina (Punto de Venta)",
        help="Punto de venta donde se cobran los pedidos.",
    )

    def get_pos_config(self):
        self.ensure_one()
        return self.pos_config_id or self.env["pos.config"].sudo().search([], limit=1)

    @api.model
    def get_open_pos_session(self):
        config = self.get_config().get_pos_config()
        if not config:
            raise UserError(_(
                "No hay ningún Punto de Venta configurado. "
                "Creá una caja y seleccionala en los parámetros de Cantina."
            ))

        session = config.current_session_id
        if not session or session.state != "opened":
            raise UserError(_(
                "La caja '%s' no está abierta. Abrila antes de cobrar.",
                config.display_name,
            ))
        return session

    def action_open_pos(self):
        self.ensure_one()
        config = self.get_pos_config()
        if not config:
            raise UserError(_("Primero configurá un Punto de Venta para la cantina."))
        return config.open_ui()

    @api.model
    def action_open_pos_ui(self):
        return self.get_config().action_open_pos()


class CantinaProduct(models.Model):
    _inherit = "cantina.product"

    pos_product_id = fields.Many2one(
        "product.product",
        string="Producto en Punto de Venta",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    def _get_pos_product(self):
        """Obtiene o crea el producto equivalente que utiliza el POS."""
        self.ensure_one()

        if not self.pos_product_id:
            Product = self.env["product.product"].sudo()
            vals = _only_existing(Product, {
                "name": self.name,
                "list_price": self.price,
                "type": "consu",
                "available_in_pos": True,
                "sale_ok": True,
                "purchase_ok": False,
                "taxes_id": [(6, 0, [])],
            })
            product = Product.create(vals)
            self.sudo().write({"pos_product_id": product.id})

        return self.pos_product_id


class CantinaOrder(models.Model):
    _inherit = "cantina.order"

    payment_state = fields.Selection(
        PAYMENT_STATES,
        string="Pago",
        default="unpaid",
        required=True,
        readonly=True,
        copy=False,
        index=True,
    )

    payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Medio de pago",
        readonly=True,
        copy=False,
    )

    amount_received = fields.Float(
        "Monto recibido (Gs.)",
        digits=(16, 0),
        readonly=True,
        copy=False,
    )

    change_amount = fields.Float(
        "Vuelto (Gs.)",
        digits=(16, 0),
        readonly=True,
        copy=False,
    )

    paid_date = fields.Datetime(
        "Fecha de pago",
        readonly=True,
        copy=False,
    )

    paid_by_id = fields.Many2one(
        "res.users",
        string="Cobrado por",
        readonly=True,
        copy=False,
    )

    pos_order_id = fields.Many2one(
        "pos.order",
        string="Venta en Punto de Venta",
        readonly=True,
        copy=False,
    )

    def _check_pos_manager(self):
        if not self.env.user.has_group("cantina_app.group_cantina_manager"):
            raise UserError(_("Solo la administradora de Cantina puede realizar esta operación."))

    def action_pay(self):
        """Abre el POS. El pedido se selecciona desde el botón Pedidos Cantina."""
        self.ensure_one()
        self._check_pos_manager()

        if self.state != "confirmed":
            raise UserError(_("Solamente se pueden cobrar pedidos confirmados."))

        if self.payment_state == "paid":
            raise UserError(_("Este pedido ya fue cobrado."))

        return self.env["cantina.config"].get_config().action_open_pos()

    def action_view_pos_order(self):
        self.ensure_one()

        if not self.pos_order_id:
            raise UserError(_("Este pedido todavía no tiene una venta en Punto de Venta."))

        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.order",
            "res_id": self.pos_order_id.id,
            "view_mode": "form",
            "views": [[False, "form"]],
        }

    @api.model
    def get_pending_pos_orders(self, session_id):
        """Devuelve los pedidos pendientes para la caja POS que está abierta."""
        self._check_pos_manager()

        session = self.env["pos.session"].browse(session_id).exists()
        if not session or session.state != "opened":
            raise UserError(_("La sesión de Punto de Venta no está abierta."))

        config = self.env["cantina.config"].get_config().get_pos_config()
        if not config or session.config_id != config:
            raise UserError(_(
                "Esta sesión no corresponde a la caja configurada para Cantina."
            ))

        orders = self.search([
            ("state", "=", "confirmed"),
            ("payment_state", "=", "unpaid"),
        ], order="create_date asc, id asc")

        result = []

        for order in orders:
            lines = []

            for line in order.line_ids:
                pos_product = line.product_id._get_pos_product()

                if not pos_product or not pos_product.available_in_pos:
                    raise UserError(_(
                        "El producto '%s' no está disponible en el Punto de Venta.",
                        line.product_id.display_name,
                    ))

                lines.append({
                    "pos_product_id": pos_product.id,
                    "product_name": line.product_id.name,
                    "quantity": line.quantity,
                    "price_unit": line.price_unit,
                })

            result.append({
                "id": order.id,
                "name": order.name,
                "employee": order.employee_id.name,
                "department": order.department_id.name or "",
                "total": order.total,
                "lines": lines,
            })

        return result

    @api.model
    def mark_paid_from_pos(self, order_id, pos_order_uuid, session_id):
        """Vincula el pedido de Cantina con una venta ya cobrada en el POS."""
        self._check_pos_manager()

        order = self.browse(order_id).exists()
        if not order:
            raise UserError(_("El pedido de Cantina ya no existe."))

        session = self.env["pos.session"].browse(session_id).exists()
        if not session or session.state != "opened":
            raise UserError(_("La sesión de caja ya no está abierta."))

        config = self.env["cantina.config"].get_config().get_pos_config()
        if not config or session.config_id != config:
            raise UserError(_("La sesión no corresponde a la caja de Cantina."))

        pos_order = self.env["pos.order"].sudo().search([
            ("uuid", "=", pos_order_uuid),
            ("session_id", "=", session.id),
        ], limit=1)

        if not pos_order:
            raise UserError(_("No se encontró la venta correspondiente en el Punto de Venta."))

        if pos_order.state not in ("paid", "done", "invoiced"):
            raise UserError(_("La venta del Punto de Venta todavía no está pagada."))

        if not pos_order.payment_ids:
            raise UserError(_("La venta no tiene pagos registrados."))

        if order.payment_state == "paid":
            if order.pos_order_id == pos_order:
                return True
            raise UserError(_("Este pedido ya fue vinculado con otra venta."))

        if order.state != "confirmed":
            raise UserError(_("El pedido de Cantina ya no está confirmado."))

        currency = pos_order.currency_id
        if float_compare(
            pos_order.amount_total,
            order.total,
            precision_rounding=currency.rounding,
        ) != 0:
            raise UserError(_(
                "El total de la venta POS no coincide con el total del pedido de Cantina. "
                "Pedido: %(cantina)s. Venta POS: %(pos)s.",
                cantina=order.total,
                pos=pos_order.amount_total,
            ))

        if float_compare(
            pos_order.amount_paid,
            order.total,
            precision_rounding=currency.rounding,
        ) < 0:
            raise UserError(_("El pedido todavía tiene un importe pendiente de pago."))

        methods = pos_order.payment_ids.mapped("payment_method_id")

        order.sudo().write({
            "payment_state": "paid",
            "payment_method_id": methods.id if len(methods) == 1 else False,
            "amount_received": pos_order.amount_paid,
            "change_amount": pos_order.amount_return,
            "paid_date": pos_order.date_order or fields.Datetime.now(),
            "paid_by_id": pos_order.user_id.id or self.env.user.id,
            "pos_order_id": pos_order.id,
        })

        return True

    def _register_payment(self, payment_method, amount_received):
        """Se bloquea el cobro antiguo por ORM para evitar ventas duplicadas."""
        raise UserError(_(
            "El cobro ahora debe realizarse desde el Punto de Venta. "
            "Abrí la caja y seleccioná el pedido en 'Pedidos Cantina'."
        ))


class CantinaOrderPayWizard(models.TransientModel):
    _name = "cantina.order.pay.wizard"
    _description = "Cobrar pedido de cantina"

    order_id = fields.Many2one("cantina.order", required=True, readonly=True)
    employee_id = fields.Many2one(related="order_id.employee_id")
    department_id = fields.Many2one(related="order_id.department_id")
    total = fields.Float(
        "Total (Gs.)",
        related="order_id.total",
        digits=(16, 0),
    )
    allowed_method_ids = fields.Many2many(
        "pos.payment.method",
        compute="_compute_allowed_method_ids",
    )
    payment_method_id = fields.Many2one("pos.payment.method", string="Medio de pago")
    is_cash = fields.Boolean(compute="_compute_is_cash")
    amount_received = fields.Float("Monto recibido (Gs.)", digits=(16, 0))
    change_amount = fields.Float(
        "Vuelto (Gs.)",
        digits=(16, 0),
        compute="_compute_change_amount",
    )

    @api.depends("order_id")
    def _compute_allowed_method_ids(self):
        config = self.env["cantina.config"].get_config().get_pos_config()
        for wizard in self:
            wizard.allowed_method_ids = config.payment_method_ids if config else False

    @api.depends("payment_method_id")
    def _compute_is_cash(self):
        for wizard in self:
            wizard.is_cash = bool(
                wizard.payment_method_id
                and wizard.payment_method_id.type == "cash"
            )

    @api.depends("is_cash", "amount_received", "total")
    def _compute_change_amount(self):
        for wizard in self:
            wizard.change_amount = (
                max(wizard.amount_received - wizard.total, 0.0)
                if wizard.is_cash else 0.0
            )

    def action_confirm(self):
        raise UserError(_(
            "Utilizá el Punto de Venta para cobrar. "
            "Los cobros directos desde esta ventana están deshabilitados."
        ))
