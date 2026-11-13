
{
    "name": "Cantina",
    "version": "19.0.1.1.0",
    "category": "Services",
    "summary": "Gestión de productos, stock, menú y pedidos de cantina",
    "description": "Sistema de administración de cantina con integración de pedidos y cobros mediante Punto de Venta.",
    "author": "Katia",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "hr",
        "point_of_sale",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/cantina_data.xml",
        "data/cantina_demo.xml",
        "data/cantina_order_sequence.xml",
        "views/cantina_product_views.xml",
        "views/cantina_menu_views.xml",
        "views/cantina_config_views.xml",
        "views/cantina_dashboard.xml",
        "views/cantina_order_views.xml",
        "views/cantina_payment_views.xml",
        "views/cantina_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "cantina_app/static/src/css/cantina.css",
            "cantina_app/static/src/xml/cantina_dashboard.xml",
            "cantina_app/static/src/js/cantina_dashboard.js",
        ],
        "point_of_sale._assets_pos": [
    "cantina_app/static/src/pos/cantina_pos.css",
    "cantina_app/static/src/pos/cantina_pos.js",
    "cantina_app/static/src/pos/cantina_pos.xml",
],
    },
    "application": True,
    "installable": True,
}
