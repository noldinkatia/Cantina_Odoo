# DOCUMENTACIÓN TÉCNICA
## Sistema de Gestión de Cantina – Odoo 19

### 1. Descripción general

El módulo `cantina_app` es una aplicación desarrollada para Odoo 19, destinada a la gestión de productos, categorías, inventario, menús, pedidos y pagos de una cantina empresarial.

El módulo incorpora interfaces administrativas, una interfaz de consulta para empleados y una integración con el Punto de Venta de Odoo.

### 2. Tecnologías utilizadas

- **Odoo 19:** plataforma principal del sistema.
- **Python:** desarrollo de modelos y lógica de negocio.
- **PostgreSQL:** sistema de gestión de base de datos.
- **XML:** definición de vistas, menús, acciones, seguridad y plantillas.
- **JavaScript:** lógica de interacción de las interfaces.
- **OWL:** desarrollo de componentes interactivos.
- **CSS:** diseño y personalización visual.


### 3. Estructura del módulo

cantina_app/
│
├── models/
│   ├── __init__.py
│   ├── cantina_config.py
│   ├── cantina_product.py
│   ├── cantina_menu.py
│   ├── cantina_dashboard.py
│   ├── cantina_order.py
│   └── cantina_payment.py
│
├── security/
│   ├── security.xml
│   └── ir.model.access.csv
│
├── data/
│   ├── cantina_data.xml
│   ├── cantina_demo.xml
│   └── cantina_order_sequence.xml
│
├── views/
│   ├── cantina_product_views.xml
│   ├── cantina_menu_views.xml
│   ├── cantina_config_views.xml
│   ├── cantina_dashboard.xml
│   ├── cantina_order_views.xml
│   ├── cantina_payment_views.xml
│   └── cantina_menus.xml
│
├── static/
│   └── src/
│       ├── css/
│       │   └── cantina.css
│       │
│       ├── js/
│       │   └── cantina_dashboard.js
│       │
│       ├── xml/
│       │   └── cantina_dashboard.xml
│       │
│       └── pos/
│           ├── cantina_pos.css
│           ├── cantina_pos.js
│           └── cantina_pos.xml
│
├── docs/
│   ├── imagenes/
│   ├── cliente.md
│   ├── Administrador.md
│   └── tecnica.md
│
├── __init__.py
└── __manifest__.py


### 4. Modelos del sistema

Los modelos principales implementados son:

| Modelo | Descripción |
|---|---|
| `cantina.product` | Gestión de productos y stock. |
| `cantina.category` | Clasificación de productos. |
| `cantina.menu` | Gestión del menú diario. |
| `cantina.menu.line` | Líneas y productos de los menús. |
| `cantina.weekly.menu` | Configuración del menú semanal. |
| `cantina.order` | Registro y gestión de pedidos. |
| `cantina.order.line` | Detalle de los productos de cada pedido. |
| `cantina.config` | Parámetros de configuración de la cantina. |
| `cantina.shift` | Gestión de turnos. |
| `cantina.payment` | Gestión de pagos. |
| `cantina.order.pay.wizard` | Asistente para operaciones de pago. |

### 5. Seguridad y control de acceso

El módulo implementa dos grupos principales:

**5.1. Empleado**

Identificador técnico: `group_cantina_user`

Permisos:
- Consultar productos y categorías.
- Consultar menús.
- Registrar sus propios pedidos.
- Consultar sus propios pedidos.
- No modificar productos, categorías ni menús.

**5.2. Administradora de Cantina**

Identificador técnico: `group_cantina_manager`

Permisos:
- Crear, consultar, modificar y eliminar productos.
- Administrar categorías.
- Gestionar menús diarios y semanales.
- Administrar pedidos.
- Gestionar pagos y configuración.
- Consultar los pedidos de todos los empleados.

**5.3. Archivos de seguridad**

- `security/security.xml`: definición de grupos y reglas de acceso a registros.
- `security/ir.model.access.csv`: permisos de lectura, escritura, creación y eliminación para cada modelo.

También se implementan reglas de registro para limitar la visualización de pedidos de los empleados a sus propios registros.

### 6. Interfaces del sistema

El módulo contiene dos interfaces principales:

**6.1. Panel administrativo**

Desarrollado mediante JavaScript, OWL, XML y CSS.

Archivos:
- `static/src/js/cantina_dashboard.js`
- `static/src/xml/cantina_dashboard.xml`
- `static/src/css/cantina.css`

Permite visualizar y administrar la información general de la cantina.

**6.2. Interfaz del empleado**

Permite consultar productos, menús y acceder a las funcionalidades habilitadas para su perfil.

La interfaz utiliza las plantillas y componentes del módulo.

**6.3. Integración con el Punto de Venta**

Archivos:
- `static/src/pos/cantina_pos.js`
- `static/src/pos/cantina_pos.xml`
- `static/src/pos/cantina_pos.css`

Permiten extender la interfaz del Punto de Venta de Odoo e incorporar funcionalidades relacionadas con los pedidos de la cantina.

### 7. Dependencias

El módulo declara las siguientes dependencias en `__manifest__.py`:

- `base`
- `web`
- `hr`
- `point_of_sale`

Estas dependencias permiten utilizar las funcionalidades generales de Odoo, las interfaces web, la gestión de empleados y el Punto de Venta.

### 8. Instalación y actualización

**8.1. Ubicación del proyecto**

```text
/home/pasante2/odoo/odoo_addons/cantina_app
```

**8.2. Base de datos**

```text
cantina_db
```

**8.3. Actualización del módulo**

Desde la terminal:

```bash
cd /home/pasante2/odoo

source venv/bin/activate

python odoo-bin -c odoo.conf \
-d cantina_db \
-u cantina_app \
--stop-after-init
```

**8.4. Inicio de Odoo**

```bash
cd /home/pasante2/odoo

source venv/bin/activate

python odoo-bin -c odoo.conf -d cantina_db
```

**8.5. Acceso al sistema**

```text
http://localhost:8069
```

### 9. Configuración de recursos

El archivo `__manifest__.py` declara los recursos del módulo.

Los archivos administrativos se cargan mediante el bundle:

`web.assets_backend`

Los archivos del Punto de Venta se cargan mediante:

`point_of_sale._assets_pos`

### 10. Conclusión

El módulo `cantina_app` integra las principales operaciones de una cantina empresarial en Odoo 19.

Su arquitectura modular permite separar la lógica de negocio, las interfaces, la seguridad y los recursos visuales, facilitando su mantenimiento y futuras ampliaciones.

**Fin de la documentación técnica.**