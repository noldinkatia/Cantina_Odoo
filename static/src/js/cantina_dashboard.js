import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useState,
} from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const DAYS = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
];

const MONTHS = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
];

const MONTHS_SHORT = [
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
];

const pad = (n) => String(n).padStart(2, "0");

const toISO = (d) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

const parseISO = (s) => {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d);
};

const weekdayIndex = (d) => (d.getDay() + 6) % 7;

const NAV_SECTIONS = [
    {
        title: "Gestión",
        items: [
            {
                icon: "fa-cube",
                label: "Productos",
                action: "cantina_app.action_cantina_product",
            },
            {
                icon: "fa-cutlery",
                label: "Menú Diario",
                action: "cantina_app.action_cantina_menu",
            },
            {
                icon: "fa-calendar",
                label: "Menú Semanal",
                action: "cantina_app.action_cantina_weekly",
            },
            {
                icon: "fa-cubes",
                label: "Stock",
                action: "cantina_app.action_cantina_stock",
            },
            {
                icon: "fa-file-text-o",
                label: "Reportes",
                action: "cantina_app.action_cantina_report",
            },
            {
                icon: "fa-shopping-cart",
                label: "Pedidos",
                action: "cantina_app.action_cantina_orders",
            },
        ],
    },
];


export class CantinaDashboard extends Component {
    static template = "cantina_app.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            data: null,
            date: toISO(new Date()),
            now: new Date(),
        });

        onWillStart(() => this.load());

        onMounted(() => {
            this.timer = setInterval(() => {
                this.state.now = new Date();
            }, 30000);
        });

        onWillUnmount(() => {
            clearInterval(this.timer);
        });
    }

    async load() {
        this.state.data = await this.orm.call(
            "cantina.dashboard",
            "get_data",
            [],
            {
                date_str: this.state.date,
            }
        );
    }

    get navSections() {
        return NAV_SECTIONS;
    }

    get nowLabel() {
        const d = this.state.now;

        return `${DAYS[weekdayIndex(d)]} ${d.getDate()} de ${
            MONTHS[d.getMonth()]
        }, ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }

    get menuDateLabel() {
        const d = parseISO(this.state.date);

        return `${DAYS[weekdayIndex(d)]} ${d.getDate()} de ${
            MONTHS_SHORT[d.getMonth()]
        }.`;
    }

    formatPrice(value) {
        return (
            "Gs. " +
            Math.round(value)
                .toString()
                .replace(/\B(?=(\d{3})+(?!\d))/g, ".")
        );
    }

    imageUrl(line) {
        return `/web/image/cantina.menu.line/${line.id}/image_256?unique=${line.image_unique}`;
    }

    stateClass(state) {
        return {
            ok: "green",
            low: "orange",
            out: "red",
        }[state] || "gray";
    }

    stateIcon(state) {
        return {
            ok: "fa-check-circle-o",
            low: "fa-exclamation-triangle",
            out: "fa-ban",
        }[state];
    }

    async shiftDay(delta) {
        const d = parseISO(this.state.date);

        d.setDate(d.getDate() + delta);

        this.state.date = toISO(d);

        await this.load();
    }

    async goToday() {
        this.state.date = toISO(new Date());

        await this.load();
    }

    openAction(xmlId) {
        return this.actionService.doAction(xmlId);
    }

    onNav(item) {
        return this.openAction(item.action);
    }

    async updateMenu() {
        const action = await this.orm.call(
            "cantina.menu",
            "action_open_today",
            []
        );

        return this.actionService.doAction(action);
    }

    newProduct() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Registrar producto",
            res_model: "cantina.product",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add(
    "cantina_app.dashboard",
    CantinaDashboard
);


/* ==========================================
   PANEL DEL EMPLEADO
   ========================================== */

export class CantinaEmployeeDashboard extends Component {
    static template = "cantina_app.EmployeeDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            data: null,
            quantities: {},
            sending: false,
            page: "home",
            menuCategory: 0,     // 0 = Todos
            productCategory: 0,  // 0 = Todos
        });

        onWillStart(() => this.load());
    }

    setPage(page) {
        this.state.page = page;
    }

    // ---------- Filtros por categoría ----------
    get categories() {
        return this.state.data ? this.state.data.categories : [];
    }

    setMenuCategory(id) {
        this.state.menuCategory = id;
    }

    setProductCategory(id) {
        this.state.productCategory = id;
    }

    _filterByCategory(items, categoryId) {
        return categoryId
            ? items.filter((item) => item.category_id === categoryId)
            : items;
    }

    get filteredMenu() {
        if (!this.state.data) {
            return [];
        }
        return this._filterByCategory(
            this.state.data.menu,
            this.state.menuCategory
        );
    }

    get filteredProducts() {
        if (!this.state.data) {
            return [];
        }
        return this._filterByCategory(
            this.state.data.products,
            this.state.productCategory
        );
    }

    // Categorías con su cantidad de ítems, según la pestaña
    menuCategoryCount(id) {
        return this._filterByCategory(this.state.data.menu, id).length;
    }

    productCategoryCount(id) {
        return this._filterByCategory(this.state.data.products, id).length;
    }

    get menuCategories() {
        return this.categories.filter((c) => this.menuCategoryCount(c.id) > 0);
    }

    get productCategories() {
        return this.categories.filter((c) => this.productCategoryCount(c.id) > 0);
    }

    async load() {
        this.state.data = await this.orm.call(
            "cantina.dashboard",
            "get_employee_data",
            []
        );

        this.state.quantities = {};

        // Si la categoría elegida ya no tiene ítems, volver a "Todos"
        if (!this.menuCategories.some((c) => c.id === this.state.menuCategory)) {
            this.state.menuCategory = 0;
        }
        if (!this.productCategories.some((c) => c.id === this.state.productCategory)) {
            this.state.productCategory = 0;
        }
    }

    formatPrice(value) {
        return (
            "Gs. " +
            Math.round(value)
                .toString()
                .replace(/\B(?=(\d{3})+(?!\d))/g, ".")
        );
    }

    imageUrl(line) {
        return `/web/image/cantina.menu.line/${line.id}/image_256?unique=${line.image_unique}`;
    }

    productImageUrl(product) {
        return `/web/image/cantina.product/${product.id}/image_256?unique=${product.image_unique}`;
    }

    stateClass(state) {
        return {
            ok: "green",
            low: "orange",
            out: "red",
        }[state] || "gray";
    }

    setQuantity(lineId, value) {
        const quantity = Math.max(
            0,
            Math.min(100, parseInt(value, 10) || 0)
        );

        this.state.quantities[lineId] = quantity;
    }

    get cartItems() {
        if (!this.state.data) {
            return [];
        }

        return this.state.data.menu
            .filter((line) => {
                return (this.state.quantities[line.id] || 0) > 0;
            })
            .map((line) => ({
                ...line,
                quantity: this.state.quantities[line.id],
                subtotal:
                    line.price * this.state.quantities[line.id],
            }));
    }

    get cartTotal() {
        return this.cartItems.reduce(
            (total, item) => total + item.subtotal,
            0
        );
    }

    async confirmOrder() {
        const items = this.cartItems.map((item) => ({
            menu_line_id: item.id,
            quantity: item.quantity,
        }));

        if (!items.length) {
            this.notification.add(
                "Seleccioná al menos un plato.",
                {
                    type: "warning",
                }
            );

            return;
        }

        this.state.sending = true;

        try {
            const result = await this.orm.call(
                "cantina.order",
                "create_order",
                [items]
            );

            this.notification.add(
                `Pedido ${result.name} confirmado correctamente.`,
                {
                    type: "success",
                }
            );

            await this.load();

        } catch (error) {
            const message =
                error?.data?.message ||
                error?.message ||
                "No se pudo confirmar el pedido.";

            this.notification.add(message, {
                type: "danger",
            });

        } finally {
            this.state.sending = false;
        }
    }
}

registry.category("actions").add(
    "cantina_app.employee_dashboard",
    CantinaEmployeeDashboard
);
