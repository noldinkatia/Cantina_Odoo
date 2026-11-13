from odoo import api, fields, models
from odoo.exceptions import UserError

from .cantina_menu import WEEKDAYS


class CantinaDashboard(models.AbstractModel):
    """Entrega los datos de los paneles de la cantina."""

    _name = "cantina.dashboard"
    _description = "Datos del panel de la cantina"

    @api.model
    def get_data(self, date_str=None):
        """Datos completos del panel administrativo."""

        if not self.env.user.has_group(
            "cantina_app.group_cantina_manager"
        ):
            raise UserError(
                "No tenés permiso para acceder al panel administrativo."
            )

        date = (
            fields.Date.to_date(date_str)
            if date_str
            else fields.Date.context_today(self)
        )

        products = self.env["cantina.product"].search([])

        categories = []

        for cat in self.env["cantina.category"].search([]):
            cat_products = products.filtered(
                lambda p, c=cat: p.category_id == c
            )

            categories.append({
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon or "fa-cutlery",
                "color": cat.color or "purple",
                "products": len(cat_products),
                "stock": sum(cat_products.mapped("stock")),
                "low": len(
                    cat_products.filtered("low_stock")
                ),
            })

        menu = self.env["cantina.menu"].search(
            [("date", "=", date)],
            limit=1,
        )

        state_labels = dict(
            self.env["cantina.product"]._fields[
                "stock_state"
            ].selection
        )

        lines = []

        for line in menu.line_ids:
            product = line.product_id

            lines.append({
                "id": line.id,
                "name": product.name,
                "description": line.description or "",
                "price": line.price,
                "state": line.stock_state,
                "state_label": state_labels.get(
                    line.stock_state,
                    "",
                ),
                "has_image": bool(line.image),
                "product_id": product.id,
                "image_unique": (
                    int(line.write_date.timestamp())
                    if line.write_date
                    else 0
                ),
            })

        weekday_labels = dict(WEEKDAYS)

        weekly = [{
            "id": w.id,
            "day": weekday_labels[w.weekday],
            "description": w.description,
        } for w in self.env["cantina.weekly.menu"].search([])]

        return {
            "kpis": {
                "products": len(products),
                "low_stock": len(
                    products.filtered("low_stock")
                ),
                "menu_count": len(lines),
                "fixed_days": len(weekly),
            },
            "categories": categories,
            "menu": {
                "date": fields.Date.to_string(date),
                "lines": lines,
            },
            "weekly": weekly,
        }

    @api.model
    def get_employee_data(self):
        """Datos limitados para la pantalla del empleado."""

        if not self.env.user.has_group(
            "cantina_app.group_cantina_user"
        ):
            raise UserError(
                "No tenés permiso para consultar el menú."
            )

        today = fields.Date.context_today(self)

        # Datos del empleado
        employee = self.env["hr.employee"].sudo().search(
            [("user_id", "=", self.env.user.id)],
            limit=1,
        )

        # Menú del día
        menu = self.env["cantina.menu"].search(
            [("date", "=", today)],
            limit=1,
        )

        # Etiquetas de los estados de stock
        state_labels = dict(
            self.env["cantina.product"]._fields[
                "stock_state"
            ].selection
        )

        # Preparaciones del menú diario
        dishes = []

        for line in menu.line_ids:
            product = line.product_id

            dishes.append({
                "id": line.id,
                "name": product.name,
                "category_id": product.category_id.id,
                "category": product.category_id.name,
                "description": line.description or "",
                "price": line.price,
                "state": line.stock_state,
                "state_label": state_labels.get(
                    line.stock_state,
                    "",
                ),
                "has_image": bool(line.image),
                "image_unique": (
                    int(line.write_date.timestamp())
                    if line.write_date
                    else 0
                ),
            })

        # Productos activos con stock disponible
        # Incluye productos con pocas unidades.
        # No muestra productos agotados.
        products_records = self.env["cantina.product"].sudo().search(
            [
                ("active", "=", True),
                ("stock", ">", 0),
            ],
            order="category_id, name",
        )

        products = []

        for product in products_records:
            products.append({
                "id": product.id,
                "name": product.name,
                "category_id": product.category_id.id,
                "category": product.category_id.name,
                "description": product.description or "",
                "price": product.price,
                "stock": product.stock,
                "stock_state": product.stock_state,
                "state_label": state_labels.get(
                    product.stock_state,
                    "",
                ),
                "has_image": bool(product.image_256),
                "image_unique": (
                    int(product.write_date.timestamp())
                    if product.write_date
                    else 0
                ),
            })

        # Pedidos del empleado
        orders = self.env["cantina.order"].search(
            [
                ("user_id", "=", self.env.user.id),
            ],
            order="create_date desc",
            limit=20,
        )

        order_data = []

        for order in orders:
            order_data.append({
                "id": order.id,
                "name": order.name,
                "date": fields.Datetime.to_string(
                    order.create_date
                ),
                "total": order.total,
                "state": order.state,
                "paid": order.payment_state == "paid",
                "lines": [{
                    "name": line.product_id.name,
                    "quantity": line.quantity,
                    "price": line.price_unit,
                    "subtotal": line.subtotal,
                } for line in order.line_ids],
            })

        # Categorías para los filtros (solo las que tienen algo para mostrar)
        used_ids = {d["category_id"] for d in dishes} | {
            p["category_id"] for p in products
        }
        categories = [
            {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon or "fa-tag",
                "color": cat.color,
            }
            for cat in self.env["cantina.category"].sudo().search([])
            if cat.id in used_ids
        ]

        return {
            "employee": (
                employee.name
                if employee
                else self.env.user.name
            ),
            "categories": categories,
            "department": (
                employee.department_id.name
                if employee and employee.department_id
                else ""
            ),
            "date": fields.Date.to_string(today),
            "menu": dishes,
            "products": products,
            "orders": order_data,
        }
