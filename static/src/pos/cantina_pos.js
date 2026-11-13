
/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";


/*
 * PEDIDOS DE CANTINA
 *
 * Permite consultar los pedidos pendientes y cargar sus productos
 * directamente en una orden normal del Punto de Venta.
 */

patch(ControlButtons.prototype, {
    async openCantinaOrders() {
        try {
            // Consultar los pedidos pendientes de Cantina.
            const orders = await this.pos.data.call(
                "cantina.order",
                "get_pending_pos_orders",
                [this.pos.session.id]
            );

            if (!orders || !orders.length) {
                this.notification.add(
                    _t("No hay pedidos de Cantina pendientes de pago."),
                    { type: "info" }
                );
                return;
            }

            // Preparar las opciones de selección.
            const list = orders.map((order) => ({
                id: order.id,
                label:
                    `${order.name} | ${order.employee} | ` +
                    `${Number(order.total).toLocaleString("es-PY")} Gs.`,
                item: order,
                isSelected: false,
            }));

            // Mostrar la ventana de selección.
            const selected = await makeAwaitable(
                this.dialog,
                SelectionPopup,
                {
                    title: _t("Seleccionar pedido de Cantina"),
                    list,
                }
            );

            if (!selected) {
                return;
            }

            // Cargar el pedido seleccionado.
            await this.loadCantinaOrderIntoPOS(selected);

        } catch (error) {
            console.error("Error al consultar pedidos de Cantina:", error);

            this.notification.add(
                error.message ||
                    _t("No se pudieron cargar los pedidos de Cantina."),
                { type: "danger" }
            );
        }
    },


    /*
     * CARGAR PEDIDO EN EL POS
     */

    async loadCantinaOrderIntoPOS(cantinaOrder) {
        try {
            const productIds = [
                ...new Set(
                    cantinaOrder.lines.map(
                        (line) => line.pos_product_id
                    )
                ),
            ];

            // Solicitar los productos al servidor.
            await this.pos.data.searchRead(
                "product.product",
                [["id", "in", productIds]]
            );

            // Reutilizar la orden vacía o crear una nueva.
            const currentOrder = this.pos.getOrder();

            const posOrder =
                currentOrder && currentOrder.isEmpty()
                    ? currentOrder
                    : this.pos.addNewOrder();

            // Agregar cada producto con su cantidad y precio.
            for (const line of cantinaOrder.lines) {
                const product = this.pos.models["product.product"].get(
                    line.pos_product_id
                );

                if (!product) {
                    throw new Error(
                        `No se pudo cargar el producto: ${line.product_name}`
                    );
                }

                await this.pos.addLineToOrder(
                    {
                        product_id: product,
                        product_tmpl_id: product.product_tmpl_id,
                        qty: line.quantity,
                        price_unit: line.price_unit,
                    },
                    posOrder,
                    { merge: false },
                    false
                );
            }

            // Guardar la relación temporal entre la orden POS y Cantina.
            this.pos.cantinaOrderByUuid ??= {};

            this.pos.cantinaOrderByUuid[posOrder.uuid] =
                cantinaOrder.id;

            // Mostrar la orden cargada.
            this.pos.navigate("ProductScreen", {
                orderUuid: posOrder.uuid,
            });

            this.notification.add(
                _t(
                    "Pedido %s cargado correctamente.",
                    cantinaOrder.name
                ),
                { type: "success" }
            );

        } catch (error) {
            console.error("Error al cargar el pedido en POS:", error);

            this.notification.add(
                error.message ||
                    _t("No se pudo cargar el pedido en la venta."),
                { type: "danger" }
            );

            throw error;
        }
    },
});


/*
 * CONFIRMACIÓN DEL PAGO
 *
 * El POS realiza el cobro mediante su flujo normal.
 * Después de finalizar correctamente, se vincula la venta
 * con el pedido original de Cantina.
 */

patch(PaymentScreen.prototype, {
    async validateOrder(...args) {
        const order = this.currentOrder;

        const orderUuid = order?.uuid;
        const sessionId = this.pos.session.id;

        const cantinaOrderId =
            this.pos.cantinaOrderByUuid?.[orderUuid];

        // Ejecutar primero el proceso de pago original de Odoo.
        await super.validateOrder(...args);

        // Si no es un pedido procedente de Cantina, no hacer nada.
        if (!cantinaOrderId) {
            return;
        }

        try {
            // Registrar en Cantina que el pedido fue pagado.
            await this.pos.data.call(
                "cantina.order",
                "mark_paid_from_pos",
                [
                    cantinaOrderId,
                    orderUuid,
                    sessionId,
                ]
            );

            // Eliminar la relación temporal una vez vinculada.
            delete this.pos.cantinaOrderByUuid[orderUuid];

            this.notification.add(
                _t(
                    "El pedido de Cantina quedó registrado como pagado."
                ),
                { type: "success" }
            );

        } catch (error) {
            console.error(
                "Error al vincular el pago con Cantina:",
                error
            );

            this.dialog.add(AlertDialog, {
                title: _t(
                    "El cobro POS se realizó, pero falta vincular Cantina"
                ),
                body:
                    error.message ||
                    _t(
                        "Contactá a la administradora para revisar el pedido."
                    ),
            });
        }
    },
});
