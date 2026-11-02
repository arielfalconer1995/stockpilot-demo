import json
from html import escape
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st


ARCHIVO_PRODUCTOS = Path(__file__).with_name("productos.json")
ARCHIVO_PEDIDOS = Path(__file__).with_name("pedidos.json")
ARCHIVO_HISTORIAL = Path(__file__).with_name("historial.json")
ARCHIVO_CLIENTES = Path(__file__).with_name("clientes.json")


st.set_page_config(
    page_title="StockPilot",
    page_icon="📦",
    layout="wide"
)

# Unificar el color de todas las advertencias de la aplicación en amarillo.
st.markdown(
    """
    <style>
    div[data-testid="stAlert"][kind="warning"] {
        background-color: #fff3cd;
        border: 1px solid #e0b400;
        color: #664d03;
    }
    div[data-testid="stAlert"][kind="warning"] p,
    div[data-testid="stAlert"][kind="warning"] div {
        color: #664d03;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def cargar_json(ruta, tipo_esperado, valor_inicial):
    """Lee un archivo JSON y comprueba el tipo de dato esperado."""
    if not ruta.exists():
        return valor_inicial

    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            contenido = archivo.read().strip()
            if not contenido:
                return valor_inicial
            datos = json.loads(contenido)

        if not isinstance(datos, tipo_esperado):
            st.error(f"El archivo {ruta.name} tiene un formato incorrecto.")
            return None

        return datos

    except (json.JSONDecodeError, OSError) as error:
        st.error(f"No se pudo leer {ruta.name}: {error}")
        return None


def guardar_json(ruta, datos):
    """Guarda datos en un archivo JSON."""
    try:
        with ruta.open("w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, indent=4, ensure_ascii=False)
        return True

    except (OSError, TypeError, ValueError) as error:
        st.error(f"No se pudieron guardar los datos en {ruta.name}: {error}")
        return False


def estado_normalizado(estado):
    """Unifica los estados actuales y los registros antiguos."""
    estado = str(estado or "").strip().upper()
    if estado == "VALIDADO":
        return "CONFIRMADO"
    return estado


def pedido_compromete_stock(pedido):
    """Indica si un pedido mantiene unidades reservadas."""
    return estado_normalizado(pedido.get("estado")) in {
        "CONFIRMADO", "PREPARADO"
    }


def siguiente_id_cliente(clientes):
    """Genera códigos CLI-0001, CLI-0002, etc."""
    numeros = []
    for codigo in clientes.keys():
        codigo = str(codigo)
        if codigo.startswith("CLI-"):
            try:
                numeros.append(int(codigo[4:]))
            except ValueError:
                pass
    return f"CLI-{max(numeros, default=0) + 1:04d}"


def siguiente_id_pedido(pedidos):
    """Genera el siguiente identificador PED-0001, PED-0002, etc."""
    numeros = []
    for pedido in pedidos:
        identificador = str(pedido.get("id", ""))
        if identificador.startswith("PED-"):
            try:
                numeros.append(int(identificador[4:]))
            except ValueError:
                pass
    return f"PED-{max(numeros, default=0) + 1:04d}"


def formatear_fecha_hora(valor):
    """Muestra fecha como día/mes/año - hora:minuto."""
    if not valor:
        return ""
    try:
        fecha = datetime.fromisoformat(str(valor))
        return fecha.strftime("%d/%m/%Y - %H:%M")
    except (ValueError, TypeError):
        return str(valor)


def fecha_hora_actual():
    """Devuelve fecha y hora actual de Argentina en formato ISO."""
    return datetime.now(
        ZoneInfo("America/Argentina/Buenos_Aires")
    ).isoformat(timespec="seconds")


def registrar_evento(tipo, codigo, nombre, detalle=""):
    """Añade un evento al historial con fecha y hora de Argentina."""
    historial = cargar_json(ARCHIVO_HISTORIAL, list, [])

    if historial is None:
        return False

    evento = {
        "fecha_hora": fecha_hora_actual(),
        "tipo": tipo,
        "codigo_producto": codigo,
        "nombre_producto": nombre,
        "detalle": detalle
    }

    historial.append(evento)
    return guardar_json(ARCHIVO_HISTORIAL, historial)


productos = cargar_json(ARCHIVO_PRODUCTOS, dict, {})
pedidos = cargar_json(ARCHIVO_PEDIDOS, list, [])
historial = cargar_json(ARCHIVO_HISTORIAL, list, [])
clientes = cargar_json(ARCHIVO_CLIENTES, dict, {})

if productos is None or pedidos is None or historial is None or clientes is None:
    st.error(
        "StockPilot no puede continuar porque hay un problema "
        "con uno o más archivos de datos. Revisalos antes de continuar."
    )
    st.stop()

# Calcula las unidades reservadas por pedidos confirmados o en preparación.
# Se calcula al cargar los datos para que esté disponible en todos los módulos.
comprometidos = {}
for pedido in pedidos:
    if pedido_compromete_stock(pedido):
        codigo_comprometido = str(pedido.get("codigo_producto", ""))
        try:
            cantidad_comprometida = int(pedido.get("cantidad", 0))
        except (TypeError, ValueError):
            cantidad_comprometida = 0
        if codigo_comprometido:
            comprometidos[codigo_comprometido] = (
                comprometidos.get(codigo_comprometido, 0) + cantidad_comprometida
            )

# Navegación lateral de StockPilot
opciones_validas = {
    "Inicio",
    "Alta de Producto", "Editar producto", "Eliminar producto", "Ver inventario",
    "Crear pedido", "Gestionar pedidos", "Ver pedidos",
    "Historial de movimientos", "Clientes", "Finanzas"
}
if st.session_state.get("opcion_stockpilot") not in opciones_validas:
    st.session_state["opcion_stockpilot"] = "Inicio"

opcion = st.session_state["opcion_stockpilot"]

st.sidebar.title("📦 StockPilot")
st.sidebar.caption("Sistema de gestión")
st.sidebar.divider()

def boton_navegacion(etiqueta, destino, icono=None, contenedor=None):
    """Botón de navegación dentro del contenedor que corresponda."""
    texto = f"{icono}  {etiqueta}" if icono else etiqueta
    contenedor = contenedor or st.sidebar
    if contenedor.button(
        texto,
        key=f"nav_{destino}",
        type="primary" if opcion == destino else "secondary",
        width="stretch",
    ):
        st.session_state["opcion_stockpilot"] = destino
        st.rerun()

boton_navegacion("Inicio", "Inicio", "🏠", st.sidebar)

with st.sidebar.expander("📦 Productos", expanded=opcion in {
    "Alta de Producto", "Editar producto", "Eliminar producto", "Ver inventario"
}):
    boton_navegacion("Alta de producto", "Alta de Producto", "➕", st)
    boton_navegacion("Editar producto", "Editar producto", "✏️", st)
    boton_navegacion("Eliminar producto", "Eliminar producto", "🗑️", st)
    boton_navegacion("Ver inventario", "Ver inventario", "📋", st)

with st.sidebar.expander("🧾 Pedidos", expanded=opcion in {
    "Crear pedido", "Gestionar pedidos", "Ver pedidos"
}):
    boton_navegacion("Crear pedido", "Crear pedido", "📝", st)
    boton_navegacion("Gestionar pedidos", "Gestionar pedidos", "🔄", st)
    boton_navegacion("Ver pedidos", "Ver pedidos", "🔎", st)

with st.sidebar.expander("👥 Clientes", expanded=opcion == "Clientes"):
    boton_navegacion("Clientes", "Clientes", "👤", st)

with st.sidebar.expander("💰 Finanzas", expanded=opcion == "Finanzas"):
    boton_navegacion("Resumen financiero", "Finanzas", "💹", st)

with st.sidebar.expander("📊 Informes", expanded=opcion == "Historial de movimientos"):
    boton_navegacion("Historial de movimientos", "Historial de movimientos", "🕘", st)

st.sidebar.divider()
st.sidebar.caption("StockPilot · Versión local")

if opcion == "Inicio":
    st.title("📦 StockPilot")
    st.subheader("Resumen general")
    st.write(
        "Controlá tus productos, el stock disponible y los pedidos de tu negocio "
        "desde un solo lugar. Elegí un módulo en el panel izquierdo para empezar."
    )

    # Indicadores generales existentes
    comprometidos_inicio = {}
    for pedido_inicio in pedidos if "pedidos" in globals() and pedidos is not None else []:
        if pedido_compromete_stock(pedido_inicio):
            codigo_inicio = pedido_inicio.get("codigo_producto")
            cantidad_inicio = pedido_inicio.get("cantidad", 0)
            if (
                codigo_inicio is not None
                and isinstance(cantidad_inicio, int)
                and not isinstance(cantidad_inicio, bool)
                and cantidad_inicio > 0
            ):
                comprometidos_inicio[codigo_inicio] = (
                    comprometidos_inicio.get(codigo_inicio, 0) + cantidad_inicio
                )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Productos registrados", len(productos) if productos is not None else 0)
    with col2:
        st.metric("Pedidos registrados", len(pedidos) if pedidos is not None else 0)
    with col3:
        st.metric("Unidades comprometidas", sum(comprometidos_inicio.values()))

    st.divider()
    st.markdown("### Accesos rápidos")
    acceso1, acceso2, acceso3 = st.columns(3)
    with acceso1:
        if st.button("＋ Crear pedido", width="stretch"):
            st.session_state["opcion_stockpilot"] = "Crear pedido"
            st.rerun()
    with acceso2:
        if st.button("＋ Alta de producto", width="stretch"):
            st.session_state["opcion_stockpilot"] = "Alta de Producto"
            st.rerun()
    with acceso3:
        if st.button("▤ Ver inventario", width="stretch"):
            st.session_state["opcion_stockpilot"] = "Ver inventario"
            st.rerun()

# REGISTRAR PRODUCTO
if opcion == "Alta de Producto":
    st.subheader("➕ Alta de Producto")

    if "mensaje_registro" in st.session_state:
        st.success(st.session_state.pop("mensaje_registro"))

    with st.form("formulario_producto"):
        codigo = st.text_input(
            "Código del producto",
            placeholder="Ej.: PROD004"
        ).strip().upper()

        nombre = st.text_input(
            "Nombre del producto",
            placeholder="Ej.: Mouse inalámbrico"
        ).strip()

        precio = st.number_input(
            "Precio en pesos argentinos ($)",
            min_value=0,
            value=0,
            step=100
        )

        stock = st.number_input(
            "Cantidad inicial en stock",
            min_value=0,
            value=0,
            step=1
        )

        enviar = st.form_submit_button(
            "Guardar producto",
            type="primary",
            width="stretch"
        )

    if enviar:
        if not codigo:
            st.error("Ingresá un código para el producto.")
        elif not nombre:
            st.error("Ingresá el nombre del producto.")
        elif codigo in productos:
            st.error(f"El código {codigo} ya existe. Elegí otro código.")
        elif precio <= 0:
            st.error("El precio debe ser mayor que cero.")
        else:
            productos_actualizados = dict(productos)
            productos_actualizados[codigo] = {
                "nombre": nombre,
                "precio": int(precio),
                "stock": int(stock)
            }

            if guardar_json(ARCHIVO_PRODUCTOS, productos_actualizados):
                if registrar_evento(
                    "PRODUCTO_AGREGADO",
                    codigo,
                    nombre,
                    f"Precio inicial: ${int(precio)}; stock inicial: {int(stock)}"
                ):
                    st.session_state["mensaje_registro"] = (
                        f"¡Producto '{nombre}' registrado correctamente!"
                    )
                else:
                    st.session_state["mensaje_registro"] = (
                        f"Producto '{nombre}' guardado, pero no se pudo "
                        "registrar su evento en el historial."
                    )
                st.rerun()

# EDITAR PRODUCTO
elif opcion == "Editar producto":
    st.subheader("✏️ Editar producto")

    if not productos:
        st.info("Todavía no hay productos para editar.")
    else:
        codigo_seleccionado = st.selectbox(
            "Seleccioná el producto",
            list(productos.keys()),
            format_func=lambda codigo: (
                f"{codigo} - {productos[codigo].get('nombre', 'Sin nombre')}"
            ),
            key="producto_a_editar"
        )

        producto_actual = productos[codigo_seleccionado]

        with st.form("formulario_editar_producto"):
            nombre_nuevo = st.text_input(
                "Nombre del producto",
                value=producto_actual.get("nombre", "")
            ).strip()

            precio_nuevo = st.number_input(
                "Precio en pesos argentinos ($)",
                min_value=1,
                value=max(1, int(producto_actual.get("precio", 1))),
                step=100
            )

            stock_nuevo = st.number_input(
                "Stock físico",
                min_value=0,
                value=max(0, int(producto_actual.get("stock", 0))),
                step=1
            )

            guardar_cambios = st.form_submit_button(
                "Guardar cambios",
                type="primary",
                width="stretch"
            )

        if guardar_cambios:
            if not nombre_nuevo:
                st.error("El nombre del producto no puede estar vacío.")
            else:
                productos_actualizados = dict(productos)
                productos_actualizados[codigo_seleccionado] = {
                    "nombre": nombre_nuevo,
                    "precio": int(precio_nuevo),
                    "stock": int(stock_nuevo)
                }

                if guardar_json(ARCHIVO_PRODUCTOS, productos_actualizados):
                    detalle = (
                        f"Antes: nombre={producto_actual.get('nombre', '')}, "
                        f"precio=${producto_actual.get('precio', 0)}, "
                        f"stock={producto_actual.get('stock', 0)}. "
                        f"Después: nombre={nombre_nuevo}, "
                        f"precio=${int(precio_nuevo)}, stock={int(stock_nuevo)}."
                    )

                    if registrar_evento(
                        "PRODUCTO_EDITADO",
                        codigo_seleccionado,
                        nombre_nuevo,
                        detalle
                    ):
                        st.success(
                            f"Producto '{nombre_nuevo}' actualizado correctamente."
                        )
                    else:
                        st.warning(
                            "El producto se actualizó, pero no se pudo "
                            "guardar el evento en el historial."
                        )

# ELIMINAR PRODUCTO
elif opcion == "Eliminar producto":
    st.subheader("🗑️ Eliminar producto")

    if "mensaje_eliminacion" in st.session_state:
        st.success(st.session_state.pop("mensaje_eliminacion"))

    if not productos:
        st.info("No hay productos para eliminar.")
    else:
        codigo_seleccionado = st.selectbox(
            "Seleccioná el producto que querés eliminar",
            list(productos.keys()),
            format_func=lambda codigo: (
                f"{codigo} - {productos[codigo].get('nombre', 'Sin nombre')}"
            ),
            key="producto_a_eliminar"
        )

        producto = productos[codigo_seleccionado]
        st.write(f"**Producto:** {producto.get('nombre', 'Sin nombre')}")
        st.write(f"**Código:** {codigo_seleccionado}")

        tiene_pedidos_activos = any(
            pedido.get("codigo_producto") == codigo_seleccionado
            and estado_normalizado(pedido.get("estado")) != "CANCELADO"
            for pedido in pedidos
        )

        if tiene_pedidos_activos:
            st.warning(
                "No se puede eliminar este producto porque tiene pedidos "
                "no cancelados asociados. Cancelá esos pedidos primero."
            )
        else:
            if st.button("Eliminar producto", type="primary", key="iniciar_eliminacion"):
                st.session_state["producto_pendiente_de_eliminar"] = codigo_seleccionado
                st.rerun()

            if st.session_state.get("producto_pendiente_de_eliminar") == codigo_seleccionado:
                st.warning(
                    f"¿Estás seguro de que querés eliminar '{producto.get('nombre', 'Sin nombre')}'? "
                    "Esta acción no se puede deshacer."
                )
                col_confirmar, col_volver = st.columns(2)
                with col_confirmar:
                    confirmar_eliminacion = st.button(
                        "Sí, eliminar definitivamente",
                        type="primary",
                        key="confirmar_eliminacion_final"
                    )
                with col_volver:
                    cancelar_eliminacion = st.button(
                        "No, volver",
                        key="cancelar_eliminacion_final"
                    )

                if cancelar_eliminacion:
                    st.session_state.pop("producto_pendiente_de_eliminar", None)
                    st.rerun()

                if confirmar_eliminacion:
                    nombre_eliminado = producto.get("nombre", "")
                    productos_actualizados = dict(productos)
                    del productos_actualizados[codigo_seleccionado]

                    if guardar_json(ARCHIVO_PRODUCTOS, productos_actualizados):
                        if registrar_evento(
                            "PRODUCTO_ELIMINADO",
                            codigo_seleccionado,
                            nombre_eliminado
                        ):
                            st.session_state["mensaje_eliminacion"] = (
                                f"Producto '{nombre_eliminado}' eliminado correctamente."
                            )
                        else:
                            st.session_state["mensaje_eliminacion"] = (
                                f"Producto '{nombre_eliminado}' eliminado, pero "
                                "no se pudo guardar el evento en el historial."
                            )
                        st.session_state.pop("producto_pendiente_de_eliminar", None)
                        st.rerun()


# CREAR PEDIDO
elif opcion == "Crear pedido":
    st.subheader("🧾 Crear pedido")

    if "mensaje_pedido" in st.session_state:
        st.success(st.session_state.pop("mensaje_pedido"))

    if not productos:
        st.info("Primero tenés que registrar al menos un producto.")
    else:
        # Este selector debe estar fuera del formulario: los widgets dentro de
        # st.form no actualizan la interfaz hasta que se envía el formulario.
        codigos_clientes_activos = [
            codigo for codigo, datos in clientes.items()
            if datos.get("activo", True)
        ]

        if codigos_clientes_activos:
            modo_cliente = st.radio(
                "Cliente del pedido",
                ["Cliente registrado", "Ingresar cliente manualmente"],
                horizontal=True,
                key="modo_cliente_pedido"
            )
        else:
            modo_cliente = "Ingresar cliente manualmente"

        with st.form("formulario_crear_pedido"):
            if modo_cliente == "Cliente registrado" and codigos_clientes_activos:
                cliente_id_seleccionado = st.selectbox(
                    "Seleccioná el cliente",
                    codigos_clientes_activos,
                    format_func=lambda codigo: (
                        f"{codigo} - "
                        f"{clientes[codigo].get('nombre', '')} "
                        f"{clientes[codigo].get('apellido', '')}".strip()
                    )
                )
                cliente_manual = ""
            else:
                cliente_id_seleccionado = ""
                cliente_manual = st.text_input(
                    "Nombre del cliente",
                    placeholder="Ej.: Juan Pérez"
                ).strip()

            codigo_producto = st.selectbox(
                "Producto",
                list(productos.keys()),
                format_func=lambda codigo: (
                    f"{codigo} - {productos[codigo].get('nombre', 'Sin nombre')}"
                )
            )

            producto_elegido = productos[codigo_producto]
            stock_fisico = int(producto_elegido.get("stock", 0))
            stock_reservado = comprometidos.get(codigo_producto, 0)
            stock_disponible = stock_fisico - stock_reservado

            st.caption(
                f"Stock físico: {stock_fisico} · "
                f"Comprometido: {stock_reservado} · "
                f"Disponible para confirmar: {stock_disponible}"
            )

            cantidad = st.number_input(
                "Cantidad solicitada",
                min_value=1,
                value=1,
                step=1
            )

            crear_pedido = st.form_submit_button(
                "Registrar pedido pendiente",
                type="primary",
                width="stretch"
            )

        if crear_pedido:
            if modo_cliente == "Cliente registrado" and cliente_id_seleccionado:
                datos_cliente = clientes[cliente_id_seleccionado]
                cliente = (
                    f"{datos_cliente.get('nombre', '')} "
                    f"{datos_cliente.get('apellido', '')}"
                ).strip()
                cliente_id_pedido = cliente_id_seleccionado
            else:
                cliente = cliente_manual.strip()
                cliente_id_pedido = ""

            if not cliente:
                st.error("Seleccioná un cliente registrado o ingresá el nombre del cliente.")
            else:
                nuevo_pedido = {
                    "id": siguiente_id_pedido(pedidos),
                    "cliente": cliente,
                    "cliente_id": cliente_id_pedido,
                    "codigo_producto": codigo_producto,
                    "nombre_producto": producto_elegido.get("nombre", "Sin nombre"),
                    "cantidad": int(cantidad),
                    "estado": "PENDIENTE",
                    "fecha_creacion": fecha_hora_actual()
                }

                pedidos_actualizados = pedidos + [nuevo_pedido]
                if guardar_json(ARCHIVO_PEDIDOS, pedidos_actualizados):
                    if registrar_evento(
                        "PEDIDO_CREADO",
                        codigo_producto,
                        producto_elegido.get("nombre", "Sin nombre"),
                        (
                            f"Pedido {nuevo_pedido['id']} creado para {cliente}. "
                            f"Cantidad solicitada: {int(cantidad)}. "
                            "Estado: PENDIENTE."
                        )
                    ):
                        st.session_state["mensaje_pedido"] = (
                            f"Pedido {nuevo_pedido['id']} registrado como PENDIENTE."
                        )
                    else:
                        st.session_state["mensaje_pedido"] = (
                            f"Pedido {nuevo_pedido['id']} guardado, pero no se "
                            "pudo registrar el evento en el historial."
                        )
                    st.rerun()

# GESTIONAR PEDIDOS
elif opcion == "Gestionar pedidos":
    st.subheader("🔄 Gestionar pedidos")

    if "mensaje_gestion_pedido" in st.session_state:
        st.success(st.session_state.pop("mensaje_gestion_pedido"))

    if not pedidos:
        st.info("Todavía no hay pedidos. Creá uno desde «Crear pedido».")
    else:
        st.markdown("### Buscar y filtrar pedidos")
        col_busqueda, col_filtro = st.columns([2, 1])
        with col_busqueda:
            busqueda_pedido = st.text_input(
                "Buscar por número de pedido, cliente, producto o código",
                placeholder="Ej.: PED-0007, Juan Pérez o PROD004",
                key="busqueda_pedido"
            ).strip().casefold()
        with col_filtro:
            filtro_estado = st.selectbox(
                "Mostrar pedidos",
                ["Activos", "Todos", "Pendiente", "Confirmado", "Preparado", "Enviado", "Entregado", "Cancelado"],
                index=0,
                key="filtro_estado_pedido"
            )

        estados_filtro = {
            "Pendiente": {"PENDIENTE"},
            "Confirmado": {"CONFIRMADO"},
            "Preparado": {"PREPARADO"},
            "Enviado": {"ENVIADO"},
            "Entregado": {"ENTREGADO"},
            "Cancelado": {"CANCELADO"},
        }
        pedidos_filtrados = []
        for pedido in pedidos:
            estado = estado_normalizado(pedido.get("estado"))
            if filtro_estado == "Activos" and estado in {"CANCELADO", "ENTREGADO"}:
                continue
            if filtro_estado in estados_filtro and estado not in estados_filtro[filtro_estado]:
                continue
            texto_busqueda = " ".join([
                str(pedido.get("id", "")),
                str(pedido.get("cliente", "")),
                str(pedido.get("nombre_producto", "")),
                str(pedido.get("codigo_producto", "")),
                estado,
            ]).casefold()
            if busqueda_pedido and busqueda_pedido not in texto_busqueda:
                continue
            pedidos_filtrados.append(pedido)

        def etiqueta_estado(estado):
            estilos = {
                "PENDIENTE": ("#FFF0BF", "#805800"),
                "CONFIRMADO": ("#DCEBFA", "#174A8B"),
                "PREPARADO": ("#E9DDFB", "#5B2C83"),
                "ENVIADO": ("#DCEBFA", "#175A9C"),
                "ENTREGADO": ("#DDF3E4", "#176B36"),
                "CANCELADO": ("#FBE0E0", "#A61B1B"),
            }
            estado_seguro = escape(str(estado))
            fondo, texto = estilos.get(str(estado).upper(), ("#E5E7EB", "#374151"))
            return (
                f'<span style="display:inline-block; padding:4px 10px; '
                f'border-radius:999px; background-color:{fondo}; color:{texto}; '
                f'font-weight:600; font-size:12px; white-space:nowrap;">'
                f'{estado_seguro}</span>'
            )

        if pedidos_filtrados:
            # Tabla con casilla explícita para abrir/cerrar la ficha del pedido.
            filas_tabla = []
            ids_filas = []
            id_actual = st.session_state.get("pedido_seleccionado_id")
            for pedido in pedidos_filtrados:
                identificador = str(pedido.get("id", "Pedido sin ID"))
                ids_filas.append(identificador)
                filas_tabla.append({
                    "Seleccionar": identificador == id_actual,
                    "Pedido": identificador,
                    "Cliente": pedido.get("cliente", "No especificado"),
                    "Producto": pedido.get("nombre_producto", "Sin nombre"),
                    "Código": pedido.get("codigo_producto", ""),
                    "Cantidad": pedido.get("cantidad", 0),
                    "Estado": estado_normalizado(pedido.get("estado", "Sin estado")),
                })
            df_pedidos = pd.DataFrame(filas_tabla)

            colores_estado = {
                "PENDIENTE": ("#FFF0BF", "#805800"),
                "CONFIRMADO": ("#DCEBFA", "#174A8B"),
                "PREPARADO": ("#E9DDFB", "#5B2C83"),
                "ENVIADO": ("#DCEBFA", "#175A9C"),
                "ENTREGADO": ("#DDF3E4", "#176B36"),
                "CANCELADO": ("#FBE0E0", "#A61B1B"),
            }

            def estilo_estado(valor):
                fondo, texto = colores_estado.get(str(valor).upper(), ("#E5E7EB", "#374151"))
                return f"background-color: {fondo}; color: {texto}; font-weight: 600;"

            tabla_editada = st.data_editor(
                df_pedidos.style.map(estilo_estado, subset=["Estado"]),
                hide_index=True,
                width="stretch",
                key="tabla_pedidos_con_casillas",
                disabled=["Pedido", "Cliente", "Producto", "Código", "Cantidad", "Estado"],
                column_config={
                    "Seleccionar": st.column_config.CheckboxColumn(
                        "Seleccionar",
                        help="Marcá la casilla para abrir la ficha; destildala para cerrarla.",
                        default=False,
                    )
                },
            )

            marcados = [
                str(tabla_editada.iloc[i]["Pedido"])
                for i in range(len(tabla_editada))
                if bool(tabla_editada.iloc[i]["Seleccionar"])
            ]
            # La ficha es única: se permite seleccionar un pedido por vez.
            # Si se desmarca la casilla, se limpia la selección y desaparece la ficha.
            if not marcados:
                st.session_state.pop("pedido_seleccionado_id", None)
            else:
                nuevo_seleccionado = marcados[-1]
                st.session_state["pedido_seleccionado_id"] = nuevo_seleccionado
                if len(marcados) > 1:
                    st.info("La ficha muestra un pedido a la vez. Dejá marcada solo la casilla del pedido que querés consultar.")
            st.caption("Marcá la casilla de un pedido para abrir su ficha. Destildala para ocultarla.")

        st.caption(f"Mostrando {len(pedidos_filtrados)} de {len(pedidos)} pedidos. Los cancelados y entregados se ocultan inicialmente; elegí ‘Todos’ para verlos.")

        if not pedidos_filtrados:
            st.session_state.pop("pedido_seleccionado_id", None)
            st.info("No hay pedidos que coincidan con la búsqueda y los filtros.")
        else:
            pedido_por_id = {
                str(pedido.get("id", f"Pedido {i + 1}")): pedido
                for i, pedido in enumerate(pedidos_filtrados)
            }
            id_seleccionado = st.session_state.get("pedido_seleccionado_id")

            # Si el pedido seleccionado ya no está entre los resultados visibles,
            # limpiar la selección para evitar mostrar una ficha que no corresponde.
            if id_seleccionado not in pedido_por_id:
                st.session_state.pop("pedido_seleccionado_id", None)
                id_seleccionado = None

            if id_seleccionado is None:
                st.info("Seleccioná una fila de la tabla para abrir la ficha, consultar su historial y gestionar el pedido.")
            else:
                pedido_seleccionado = pedido_por_id[id_seleccionado]
                st.markdown("### Ficha del pedido seleccionado")
                st.caption(f"Pedido seleccionado: {id_seleccionado}")
                estado_actual = estado_normalizado(pedido_seleccionado.get("estado"))
                codigo_pedido = pedido_seleccionado.get("codigo_producto", "")
                producto_pedido = productos.get(codigo_pedido, {})
                cantidad_pedido = pedido_seleccionado.get("cantidad", 0)

                st.write(f"**Cliente:** {pedido_seleccionado.get('cliente', 'No especificado')}")
                st.write(f"**Producto:** {pedido_seleccionado.get('nombre_producto', 'Sin nombre')}")
                st.write(f"**Cantidad:** {cantidad_pedido}")
                st.write(f"**Estado actual:** {estado_actual}")

                st.markdown("#### Fechas del pedido")
                fechas_pedido = [
                    ("Creado", "fecha_creacion"),
                    ("Confirmado", "fecha_confirmacion"),
                    ("Preparado", "fecha_preparacion"),
                    ("Enviado / despachado", "fecha_envio"),
                    ("Entregado", "fecha_entrega"),
                    ("Cancelado", "fecha_cancelacion"),
                ]
                columnas_fechas = st.columns(3)
                for indice, (etiqueta_fecha, campo_fecha) in enumerate(fechas_pedido):
                    valor_fecha = formatear_fecha_hora(pedido_seleccionado.get(campo_fecha))
                    with columnas_fechas[indice % 3]:
                        st.caption(etiqueta_fecha)
                        st.write(valor_fecha if valor_fecha else "—")

                # Trazabilidad del pedido: muestra los eventos del historial que mencionan su ID.
                st.markdown("#### Historial de este pedido")
                eventos_pedido = []
                for evento in historial:
                    detalle_evento = str(evento.get("detalle", ""))
                    # Los eventos recientes incluyen el ID del pedido en el detalle.
                    if id_seleccionado and id_seleccionado in detalle_evento:
                        eventos_pedido.append(evento)

                if eventos_pedido:
                    eventos_pedido.sort(
                        key=lambda evento: str(evento.get("fecha_hora", "")),
                        reverse=True
                    )
                    for evento in eventos_pedido:
                        fecha_evento = formatear_fecha_hora(evento.get("fecha_hora", ""))
                        tipo_evento = str(evento.get("tipo", "Movimiento")).replace("_", " ").title()
                        detalle_evento = str(evento.get("detalle", ""))
                        with st.container(border=True):
                            st.caption(fecha_evento or "Fecha no disponible")
                            st.write(f"**{tipo_evento}**")
                            st.write(detalle_evento)
                else:
                    st.info(
                        "Todavía no hay eventos vinculados a este pedido. "
                        "Los cambios nuevos de estado se registrarán en el historial."
                    )

                def guardar_estado_pedido(nuevo_estado, tipo_evento, detalle_extra=""):
                    pedidos_actualizados = [dict(p) for p in pedidos]
                    for pedido_actualizado in pedidos_actualizados:
                        if str(pedido_actualizado.get("id", "")) == id_seleccionado:
                            momento = fecha_hora_actual()
                            campo_fecha = {
                                "CONFIRMADO": "fecha_confirmacion",
                                "PREPARADO": "fecha_preparacion",
                                "ENTREGADO": "fecha_entrega",
                                "CANCELADO": "fecha_cancelacion",
                            }.get(nuevo_estado)
                            pedido_actualizado["estado"] = nuevo_estado
                            if campo_fecha:
                                pedido_actualizado[campo_fecha] = momento
                            break
                    if guardar_json(ARCHIVO_PEDIDOS, pedidos_actualizados):
                        detalle = (
                            f"Pedido {id_seleccionado}: {estado_actual} → {nuevo_estado}. "
                            f"Cliente: {pedido_seleccionado.get('cliente', 'cliente sin nombre')}. "
                            f"Cantidad: {cantidad_pedido}. {detalle_extra}"
                        )
                        registrar_evento(
                            tipo_evento, codigo_pedido,
                            pedido_seleccionado.get("nombre_producto", "Sin nombre"), detalle
                        )
                        st.session_state["mensaje_gestion_pedido"] = (
                            f"Pedido {id_seleccionado}: estado actualizado a {nuevo_estado}."
                        )
                        st.rerun()

                if estado_actual == "PENDIENTE":
                    stock_fisico = int(producto_pedido.get("stock", 0))
                    stock_reservado = comprometidos.get(codigo_pedido, 0)
                    disponible = stock_fisico - stock_reservado
                    st.caption(f"Stock disponible para confirmar este pedido: {disponible}")
                    col_confirmar, col_cancelar = st.columns(2)
                    with col_confirmar:
                        confirmar_pedido = st.button("Confirmar pedido", type="primary", width="stretch")
                    with col_cancelar:
                        cancelar_pedido = st.button("Cancelar pedido", width="stretch")

                    if confirmar_pedido:
                        if codigo_pedido not in productos:
                            st.error("No se puede confirmar: el producto ya no existe en el inventario.")
                        elif not isinstance(cantidad_pedido, int) or isinstance(cantidad_pedido, bool) or cantidad_pedido <= 0:
                            st.error("La cantidad del pedido no es válida.")
                        elif cantidad_pedido > disponible:
                            st.error(f"No hay stock suficiente. Disponible: {disponible}; solicitado: {cantidad_pedido}.")
                        else:
                            guardar_estado_pedido("CONFIRMADO", "PEDIDO_CONFIRMADO", "Las unidades quedaron reservadas.")
                    if cancelar_pedido:
                        st.session_state["pedido_pendiente_de_cancelar"] = id_seleccionado
                        st.rerun()

                elif estado_actual == "CONFIRMADO":
                    st.info("El pedido reserva stock. Preparalo antes de despacharlo; el stock físico todavía no se descuenta.")
                    col_preparar, col_cancelar = st.columns(2)
                    with col_preparar:
                        preparar_pedido = st.button("Marcar como preparado", type="primary", width="stretch")
                    with col_cancelar:
                        cancelar_pedido = st.button("Cancelar pedido confirmado", width="stretch")
                    if preparar_pedido:
                        guardar_estado_pedido("PREPARADO", "PEDIDO_PREPARADO", "Pedido listo para despacho; stock sigue reservado.")
                    if cancelar_pedido:
                        st.session_state["pedido_pendiente_de_cancelar"] = id_seleccionado
                        st.rerun()

                elif estado_actual == "PREPARADO":
                    st.info("Pedido listo para despacho. El stock físico se descontará cuando confirmes el despacho.")
                    if st.button("Preparar despacho", type="primary", width="stretch"):
                        st.session_state["pedido_pendiente_de_despacho"] = id_seleccionado
                        st.rerun()
                    if st.button("Cancelar pedido preparado", width="stretch"):
                        st.session_state["pedido_pendiente_de_cancelar"] = id_seleccionado
                        st.rerun()

                elif estado_actual == "ENVIADO":
                    st.success("Pedido despachado. El stock ya fue descontado; solo falta registrar la entrega.")
                    if st.button("Marcar como entregado", type="primary", width="stretch"):
                        guardar_estado_pedido("ENTREGADO", "PEDIDO_ENTREGADO", "Entrega confirmada; no se vuelve a descontar stock.")

                elif estado_actual == "ENTREGADO":
                    st.success("Pedido entregado. Es un estado final.")

                elif estado_actual == "CANCELADO":
                    st.info("Este pedido está cancelado. No reserva unidades de stock.")
                else:
                    st.warning(f"El estado «{estado_actual}» no se reconoce. No lo modifiques hasta revisarlo.")

                if st.session_state.get("pedido_pendiente_de_despacho") == id_seleccionado:
                    st.warning(
                        f"¿Confirmás el despacho de {id_seleccionado}? Se descontarán {cantidad_pedido} unidades del stock físico. "
                        "Esta acción no debe repetirse para el mismo pedido."
                    )
                    col_si, col_no = st.columns(2)
                    with col_si:
                        confirmar_despacho = st.button("Sí, despachar pedido", type="primary", key="confirmar_despacho")
                    with col_no:
                        cancelar_despacho = st.button("No, volver", key="cancelar_despacho")
                    if cancelar_despacho:
                        st.session_state.pop("pedido_pendiente_de_despacho", None)
                        st.rerun()
                    if confirmar_despacho:
                        if codigo_pedido not in productos:
                            st.error("No se puede despachar: el producto ya no existe en el inventario.")
                        elif not isinstance(cantidad_pedido, int) or isinstance(cantidad_pedido, bool) or cantidad_pedido <= 0:
                            st.error("La cantidad del pedido no es válida.")
                        elif int(productos[codigo_pedido].get("stock", 0)) < cantidad_pedido:
                            st.error("No hay suficiente stock físico para despachar este pedido. Revisá el inventario antes de continuar.")
                        else:
                            # Guardar la baja de stock antes de marcar ENVIADO evita repetir la baja
                            # si el estado ya quedó actualizado. Los archivos JSON siguen siendo separados.
                            productos_actualizados = {k: dict(v) for k, v in productos.items()}
                            productos_actualizados[codigo_pedido]["stock"] = int(productos_actualizados[codigo_pedido].get("stock", 0)) - cantidad_pedido
                            if guardar_json(ARCHIVO_PRODUCTOS, productos_actualizados):
                                pedidos_actualizados = [dict(p) for p in pedidos]
                                for pedido_actualizado in pedidos_actualizados:
                                    if str(pedido_actualizado.get("id", "")) == id_seleccionado:
                                        pedido_actualizado["estado"] = "ENVIADO"
                                        pedido_actualizado["fecha_envio"] = fecha_hora_actual()
                                        break
                                if guardar_json(ARCHIVO_PEDIDOS, pedidos_actualizados):
                                    registrar_evento(
                                        "PEDIDO_ENVIADO", codigo_pedido,
                                        pedido_seleccionado.get("nombre_producto", "Sin nombre"),
                                        f"Pedido {id_seleccionado} despachado. Se descontaron {cantidad_pedido} unidades del stock físico."
                                    )
                                    st.session_state["mensaje_gestion_pedido"] = (
                                        f"Pedido {id_seleccionado} despachado. Stock descontado: {cantidad_pedido} unidades."
                                    )
                                    st.session_state.pop("pedido_pendiente_de_despacho", None)
                                    st.rerun()
                                else:
                                    st.error("No se pudo actualizar el pedido después de guardar el stock. No vuelvas a intentar el despacho; revisá los archivos JSON y el respaldo primero.")

                if st.session_state.get("pedido_pendiente_de_cancelar") == id_seleccionado:
                    st.warning(
                        f"¿Estás seguro de cancelar el pedido {id_seleccionado}? Se liberará la reserva si la tenía. "
                        "Los pedidos ya despachados no se pueden cancelar desde aquí."
                    )
                    col_si, col_no = st.columns(2)
                    with col_si:
                        confirmar_cancelacion = st.button("Sí, cancelar pedido", type="primary", key="confirmar_cancelacion_pedido")
                    with col_no:
                        desistir_cancelacion = st.button("No, volver", key="desistir_cancelacion_pedido")
                    if desistir_cancelacion:
                        st.session_state.pop("pedido_pendiente_de_cancelar", None)
                        st.rerun()
                    if confirmar_cancelacion:
                        if estado_actual not in {"PENDIENTE", "CONFIRMADO", "PREPARADO"}:
                            st.error("Solo se pueden cancelar pedidos antes del despacho.")
                        else:
                            guardar_estado_pedido(
                                "CANCELADO", "PEDIDO_CANCELADO",
                                "Se liberó la reserva de stock si existía."
                            )
                            st.session_state.pop("pedido_pendiente_de_cancelar", None)


    # VER INVENTARIO
elif opcion == "Ver inventario":
    st.subheader("📋 Inventario de productos")

    if not productos:
        st.info("Todavía no hay productos registrados.")
    else:
        filas = []

        for codigo, producto in productos.items():
            stock_producto = producto.get("stock", 0)
            stock_comprometido = comprometidos.get(codigo, 0)

            filas.append({
                "Código": codigo,
                "Producto": producto.get("nombre", "Sin nombre"),
                "Precio ($)": producto.get("precio", 0),
                "Stock físico": stock_producto,
                "Comprometido": stock_comprometido,
                "Disponible": stock_producto - stock_comprometido
            })

        st.dataframe(
            pd.DataFrame(filas),
            width="stretch",
            hide_index=True
        )

# VER PEDIDOS
elif opcion == "Ver pedidos":
    st.subheader("🧾 Pedidos registrados")

    if not pedidos:
        st.info("Todavía no hay pedidos registrados.")
    else:
        filas = []

        for pedido in pedidos:
            filas.append({
                "ID": str(pedido.get("id", "")),
                "Cliente": pedido.get("cliente", "No especificado"),
                "Código": pedido.get("codigo_producto", ""),
                "Producto": pedido.get("nombre_producto", "Sin nombre"),
                "Cantidad": pedido.get("cantidad", 0),
                "Estado": estado_normalizado(pedido.get("estado", "Sin estado"))
            })

        st.dataframe(
            pd.DataFrame(filas),
            width="stretch",
            hide_index=True
        )

# HISTORIAL DE MOVIMIENTOS
elif opcion == "Historial de movimientos":
    st.subheader("🕘 Historial de movimientos")

    if not historial:
        st.info(
            "Todavía no hay movimientos registrados. "
            "Las nuevas altas, ediciones y eliminaciones aparecerán acá."
        )
    else:
        filas = []

        for evento in reversed(historial):
            filas.append({
                "Fecha y hora": formatear_fecha_hora(evento.get("fecha_hora", "")),
                "Movimiento": evento.get("tipo", ""),
                "Código": evento.get("codigo_producto", ""),
                "Producto": evento.get("nombre_producto", ""),
                "Detalle": evento.get("detalle", "")
            })

        st.dataframe(
            pd.DataFrame(filas),
            width="stretch",
            hide_index=True
        )

elif opcion == "Clientes":
    st.title("👥 Gestión de clientes")

    if "mensaje_eliminacion_cliente" in st.session_state:
        st.success(st.session_state.pop("mensaje_eliminacion_cliente"))

    st.write(
        "Registrá clientes una sola vez y vinculalos con nuevos pedidos. "
        "Los pedidos anteriores se conservan aunque no tengan un cliente asociado."
    )

    pesta_alta, pesta_busqueda, pesta_edicion, pesta_eliminar = st.tabs(
        [
            "➕ Registrar cliente",
            "🔎 Buscar y consultar",
            "✏️ Editar cliente",
            "🗑️ Eliminar cliente"
        ]
    )

    with pesta_alta:
        with st.form("formulario_alta_cliente", clear_on_submit=True):
            nombre_cliente = st.text_input(
                "Nombre *", placeholder="Ej.: Juan"
            ).strip()
            apellido_cliente = st.text_input(
                "Apellido *", placeholder="Ej.: Pérez"
            ).strip()
            telefono_cliente = st.text_input(
                "Teléfono", placeholder="Ej.: 11 1234-5678"
            ).strip()
            email_cliente = st.text_input(
                "Correo electrónico", placeholder="Ej.: cliente@correo.com"
            ).strip()
            guardar_cliente = st.form_submit_button(
                "Guardar cliente", type="primary", width="stretch"
            )

        if guardar_cliente:
            if not nombre_cliente or not apellido_cliente:
                st.error("Completá el nombre y el apellido del cliente.")
            else:
                duplicado = any(
                    str(datos.get("nombre", "")).strip().casefold() == nombre_cliente.casefold()
                    and str(datos.get("apellido", "")).strip().casefold() == apellido_cliente.casefold()
                    and str(datos.get("telefono", "")).strip() == telefono_cliente
                    for datos in clientes.values()
                )
                if duplicado:
                    st.warning(
                        "Ya existe un cliente con el mismo nombre, apellido y teléfono. "
                        "Revisá el registro antes de crear un duplicado."
                    )
                else:
                    codigo_cliente = siguiente_id_cliente(clientes)
                    clientes_actualizados = dict(clientes)
                    clientes_actualizados[codigo_cliente] = {
                        "nombre": nombre_cliente,
                        "apellido": apellido_cliente,
                        "telefono": telefono_cliente,
                        "email": email_cliente,
                        "activo": True,
                        "fecha_alta": fecha_hora_actual()
                    }
                    if guardar_json(ARCHIVO_CLIENTES, clientes_actualizados):
                        registrar_evento(
                            "CLIENTE_AGREGADO", "", "",
                            f"Cliente {codigo_cliente} registrado: "
                            f"{nombre_cliente} {apellido_cliente}."
                        )
                        st.success(
                            f"Cliente {nombre_cliente} {apellido_cliente} registrado "
                            f"con el código {codigo_cliente}."
                        )
                        st.rerun()

    with pesta_busqueda:
        busqueda_cliente = st.text_input(
            "Buscar por código, nombre, apellido, teléfono o correo",
            placeholder="Ej.: CLI-0001, Juan o 11 1234-5678",
            key="busqueda_cliente"
        ).strip().casefold()

        clientes_encontrados = []
        for codigo_cliente, datos in clientes.items():
            texto_cliente = " ".join([
                str(codigo_cliente),
                str(datos.get("nombre", "")),
                str(datos.get("apellido", "")),
                str(datos.get("telefono", "")),
                str(datos.get("email", ""))
            ]).casefold()
            if not busqueda_cliente or busqueda_cliente in texto_cliente:
                clientes_encontrados.append((codigo_cliente, datos))

        st.caption(f"Clientes registrados: {len(clientes)}")
        if clientes_encontrados:
            filas_clientes = []
            for codigo_cliente, datos in clientes_encontrados:
                pedidos_cliente = [
                    pedido for pedido in pedidos
                    if str(pedido.get("cliente_id", "")) == str(codigo_cliente)
                ]
                filas_clientes.append({
                    "Código": str(codigo_cliente),
                    "Nombre": str(datos.get("nombre", "")),
                    "Apellido": str(datos.get("apellido", "")),
                    "Teléfono": str(datos.get("telefono", "")),
                    "Correo": str(datos.get("email", "")),
                    "Pedidos asociados": len(pedidos_cliente),
                    "Estado": "Activo" if datos.get("activo", True) else "Inactivo"
                })
            st.dataframe(
                pd.DataFrame(filas_clientes),
                width="stretch",
                hide_index=True
            )

            opciones_ficha = [codigo for codigo, _ in clientes_encontrados]
            codigo_ficha = st.selectbox(
                "Ver historial de un cliente",
                opciones_ficha,
                format_func=lambda codigo: (
                    f"{codigo} - {clientes[codigo].get('nombre', '')} "
                    f"{clientes[codigo].get('apellido', '')}".strip()
                ),
                key="cliente_ficha"
            )
            pedidos_de_cliente = [
                pedido for pedido in pedidos
                if str(pedido.get("cliente_id", "")) == str(codigo_ficha)
            ]
            st.markdown("#### Historial de pedidos")
            if pedidos_de_cliente:
                filas_historial_cliente = []
                for pedido in sorted(
                    pedidos_de_cliente,
                    key=lambda p: str(p.get("fecha_creacion", "")),
                    reverse=True
                ):
                    filas_historial_cliente.append({
                        "Pedido": str(pedido.get("id", "")),
                        "Fecha": formatear_fecha_hora(pedido.get("fecha_creacion", "")) or "—",
                        "Producto": str(pedido.get("nombre_producto", "Sin nombre")),
                        "Cantidad": pedido.get("cantidad", 0),
                        "Estado": estado_normalizado(pedido.get("estado", "Sin estado"))
                    })
                st.dataframe(
                    pd.DataFrame(filas_historial_cliente),
                    width="stretch",
                    hide_index=True
                )
            else:
                st.info("Este cliente todavía no tiene pedidos asociados.")
        else:
            st.info("No hay clientes que coincidan con la búsqueda." if clientes else "Todavía no hay clientes registrados.")

    with pesta_edicion:
        if not clientes:
            st.info("Todavía no hay clientes para editar. Registrá el primero en la pestaña correspondiente.")
        else:
            codigo_editar_cliente = st.selectbox(
                "Seleccioná el cliente que querés editar",
                list(clientes.keys()),
                format_func=lambda codigo: (
                    f"{codigo} - {clientes[codigo].get('nombre', '')} "
                    f"{clientes[codigo].get('apellido', '')}".strip()
                ),
                key="cliente_a_editar"
            )
            datos_cliente_editar = clientes[codigo_editar_cliente]
            with st.form("formulario_editar_cliente"):
                nombre_editar_cliente = st.text_input(
                    "Nombre *", value=str(datos_cliente_editar.get("nombre", ""))
                ).strip()
                apellido_editar_cliente = st.text_input(
                    "Apellido *", value=str(datos_cliente_editar.get("apellido", ""))
                ).strip()
                telefono_editar_cliente = st.text_input(
                    "Teléfono", value=str(datos_cliente_editar.get("telefono", ""))
                ).strip()
                email_editar_cliente = st.text_input(
                    "Correo electrónico", value=str(datos_cliente_editar.get("email", ""))
                ).strip()
                activo_editar_cliente = st.checkbox(
                    "Cliente activo", value=datos_cliente_editar.get("activo", True)
                )
                guardar_edicion_cliente = st.form_submit_button(
                    "Guardar cambios", type="primary", width="stretch"
                )

            if guardar_edicion_cliente:
                if not nombre_editar_cliente or not apellido_editar_cliente:
                    st.error("El nombre y el apellido no pueden quedar vacíos.")
                else:
                    clientes_actualizados = {k: dict(v) for k, v in clientes.items()}
                    clientes_actualizados[codigo_editar_cliente] = {
                        **clientes_actualizados[codigo_editar_cliente],
                        "nombre": nombre_editar_cliente,
                        "apellido": apellido_editar_cliente,
                        "telefono": telefono_editar_cliente,
                        "email": email_editar_cliente,
                        "activo": activo_editar_cliente
                    }
                    if guardar_json(ARCHIVO_CLIENTES, clientes_actualizados):
                        registrar_evento(
                            "CLIENTE_EDITADO", "", "",
                            f"Cliente {codigo_editar_cliente} actualizado."
                        )
                        st.success("Datos del cliente actualizados correctamente.")
                        st.rerun()

    with pesta_eliminar:
        if not clientes:
            st.info("Todavía no hay clientes registrados para eliminar.")
        else:
            codigo_eliminar_cliente = st.selectbox(
                "Seleccioná el cliente que querés eliminar",
                list(clientes.keys()),
                format_func=lambda codigo: (
                    f"{codigo} - {clientes[codigo].get('nombre', '')} "
                    f"{clientes[codigo].get('apellido', '')}".strip()
                ),
                key="cliente_a_eliminar"
            )
            datos_cliente_eliminar = clientes[codigo_eliminar_cliente]
            pedidos_asociados_eliminar = [
                pedido for pedido in pedidos
                if str(pedido.get("cliente_id", "")) == str(codigo_eliminar_cliente)
            ]

            st.markdown(
                f"**Cliente:** {datos_cliente_eliminar.get('nombre', '')} "
                f"{datos_cliente_eliminar.get('apellido', '')}"
            )
            st.caption(f"Código: {codigo_eliminar_cliente}")

            if pedidos_asociados_eliminar:
                st.warning(
                    f"Este cliente tiene {len(pedidos_asociados_eliminar)} pedido(s) asociado(s). "
                    "Para proteger el historial y evitar perder la relación con esos pedidos, "
                    "no se puede eliminar mientras tenga pedidos asociados. "
                    "Podés desactivarlo desde «Editar cliente»."
                )
            else:
                st.info(
                    "Esta acción elimina el registro del cliente. No se puede deshacer. "
                    "Los archivos de pedidos y productos no se borrarán."
                )
                confirmar_eliminacion = st.checkbox(
                    "Confirmo que quiero eliminar este cliente.",
                    key="confirmar_eliminacion_cliente"
                )
                if st.button(
                    "Eliminar cliente",
                    type="primary",
                    disabled=not confirmar_eliminacion,
                    key="boton_eliminar_cliente"
                ):
                    clientes_actualizados = {
                        codigo: datos
                        for codigo, datos in clientes.items()
                        if codigo != codigo_eliminar_cliente
                    }
                    if guardar_json(ARCHIVO_CLIENTES, clientes_actualizados):
                        registrar_evento(
                            "CLIENTE_ELIMINADO", "", "",
                            f"Cliente {codigo_eliminar_cliente} eliminado: "
                            f"{datos_cliente_eliminar.get('nombre', '')} "
                            f"{datos_cliente_eliminar.get('apellido', '')}."
                        )
                        st.session_state["mensaje_eliminacion_cliente"] = (
                            f"Cliente {codigo_eliminar_cliente} "
                            f"({datos_cliente_eliminar.get('nombre', '')} "
                            f"{datos_cliente_eliminar.get('apellido', '')}) "
                            "eliminado correctamente."
                        )
                        st.rerun()

elif opcion == "Finanzas":
    st.title("💰 Finanzas")
    st.info(
        "Este módulo se incorporará más adelante para ventas, cobros, pagos y cuentas pendientes."
    )

elif opcion == "Inicio":
    pass

st.divider()
st.caption("StockPilot · Inventario local y gestión de pedidos")
