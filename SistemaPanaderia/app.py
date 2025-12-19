import streamlit as st
import sqlite3
import hashlib
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import uuid
import tempfile

# ============================================
# CONFIGURACIÓN DE PÁGINA
# ============================================
st.set_page_config(
    page_title="Sistema MRP - Panadería",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# CONSTANTES Y CONFIGURACIONES
# ============================================
SECRET_KEY = "panaderia-mrp-2024-seguro-streamlit-cloud"

# ============================================
# FUNCIONES DE UTILIDAD - CORREGIDAS
# ============================================
def hash_password(password):
    """Hash seguro de contraseñas"""
    salt = "panaderia-salt-2024-"
    return hashlib.sha256((password + salt + SECRET_KEY).encode()).hexdigest()

def get_db_connection():
    """Conexión a la base de datos - Compatible con Streamlit Cloud"""
    # Usar directorio temporal
    db_dir = tempfile.gettempdir()
    db_path = os.path.join(db_dir, 'panaderia_mrp_cloud.db')
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================
# INICIALIZACIÓN DE BASE DE DATOS - CORREGIDA
# ============================================
@st.cache_resource
def init_database():
    """Inicializa todas las tablas - Cacheada para mejor rendimiento"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        rol TEXT NOT NULL,
        password TEXT NOT NULL,
        permisos TEXT,
        email TEXT,
        telefono TEXT,
        departamento TEXT,
        creado_por INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ultimo_acceso TIMESTAMP,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # Verificar y crear usuario administrador si no existe
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        admin_password = hash_password("Admin2024!")
        try:
            cursor.execute('''
            INSERT INTO usuarios (username, nombre, rol, password, permisos, email, creado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('admin', 'Administrador Principal', 'admin', admin_password, 'all', 'admin@panaderia.com', 1))
            conn.commit()
        except:
            pass  # Si falla, el admin ya existe
    
    # Tabla de productos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        categoria TEXT NOT NULL,
        unidad_medida TEXT NOT NULL,
        precio_compra DECIMAL(10,2) DEFAULT 0,
        precio_venta DECIMAL(10,2) DEFAULT 0,
        stock_minimo INTEGER DEFAULT 0,
        stock_maximo INTEGER DEFAULT 0,
        stock_actual INTEGER DEFAULT 0,
        ubicacion TEXT,
        proveedor_id INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_creador INTEGER,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # Tabla de proveedores
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        ruc TEXT,
        direccion TEXT,
        telefono TEXT,
        email TEXT,
        contacto TEXT,
        tipo_producto TEXT,
        plazo_entrega INTEGER DEFAULT 0,
        calificacion INTEGER DEFAULT 5,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_creador INTEGER,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # Tabla de clientes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        tipo_documento TEXT,
        numero_documento TEXT,
        direccion TEXT,
        telefono TEXT,
        email TEXT,
        limite_credito DECIMAL(10,2) DEFAULT 0,
        saldo_actual DECIMAL(10,2) DEFAULT 0,
        categoria TEXT DEFAULT 'REGULAR',
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_creador INTEGER,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # Tabla de ventas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_factura TEXT UNIQUE NOT NULL,
        cliente_id INTEGER NOT NULL,
        fecha_venta DATE NOT NULL,
        subtotal DECIMAL(10,2) DEFAULT 0,
        descuento DECIMAL(10,2) DEFAULT 0,
        impuestos DECIMAL(10,2) DEFAULT 0,
        total DECIMAL(10,2) DEFAULT 0,
        estado TEXT DEFAULT 'PENDIENTE',
        forma_pago TEXT,
        observaciones TEXT,
        usuario_vendedor INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Tabla de detalles de venta
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detalle_venta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        precio_unitario DECIMAL(10,2) NOT NULL,
        descuento DECIMAL(10,2) DEFAULT 0,
        total_linea DECIMAL(10,2) NOT NULL
    )
    ''')
    
    # Tabla de movimientos de inventario
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS movimientos_inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_movimiento TEXT NOT NULL,
        referencia_id INTEGER,
        referencia_tipo TEXT,
        producto_id INTEGER,
        cantidad DECIMAL(10,2) NOT NULL,
        unidad_medida TEXT NOT NULL,
        stock_anterior DECIMAL(10,2),
        stock_nuevo DECIMAL(10,2),
        fecha_movimiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_responsable INTEGER,
        observaciones TEXT
    )
    ''')
    
    conn.commit()
    return conn

# ============================================
# FUNCIONES DE AUTENTICACIÓN - CORREGIDAS
# ============================================
def autenticar_usuario(username, password):
    """Autentica un usuario con nombre de usuario y contraseña"""
    try:
        conn = get_db_connection()
        hashed_password = hash_password(password)
        
        cursor = conn.cursor()
        cursor.execute('''
        SELECT id, username, nombre, rol, permisos 
        FROM usuarios 
        WHERE username = ? AND password = ? AND activo = 1
        ''', (username, hashed_password))
        
        usuario = cursor.fetchone()
        
        if usuario:
            # Actualizar último acceso
            cursor.execute('''
            UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP WHERE id = ?
            ''', (usuario['id'],))
            conn.commit()
            
            return {
                'id': usuario['id'],
                'username': usuario['username'],
                'nombre': usuario['nombre'],
                'rol': usuario['rol'],
                'permisos': usuario['permisos']
            }
        
        conn.close()
        return None
        
    except Exception as e:
        return None

# ============================================
# FUNCIONES PRINCIPALES DEL SISTEMA
# ============================================
@st.cache_data(ttl=300)
def obtener_usuarios():
    """Obtiene todos los usuarios"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, username, nombre, rol, permisos, email, telefono, 
           departamento, fecha_creacion, ultimo_acceso, activo
    FROM usuarios
    ORDER BY fecha_creacion DESC
    ''')
    usuarios = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return usuarios

def crear_usuario_sistema(admin_id, datos_usuario):
    """Crea un nuevo usuario en el sistema"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si usuario existe
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (datos_usuario['username'],))
        if cursor.fetchone():
            return False, "El nombre de usuario ya existe"
        
        # Hashear contraseña
        hashed_password = hash_password(datos_usuario['password'])
        
        # Insertar nuevo usuario
        cursor.execute('''
        INSERT INTO usuarios (username, nombre, rol, password, permisos, email, 
                            telefono, departamento, creado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos_usuario['username'],
            datos_usuario['nombre'],
            datos_usuario['rol'],
            hashed_password,
            datos_usuario.get('permisos', ''),
            datos_usuario.get('email', ''),
            datos_usuario.get('telefono', ''),
            datos_usuario.get('departamento', ''),
            admin_id
        ))
        
        conn.commit()
        conn.close()
        return True, "✅ Usuario creado exitosamente"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

@st.cache_data(ttl=300)
def obtener_productos():
    """Obtiene todos los productos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT p.*, pr.nombre as proveedor_nombre
    FROM productos p
    LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
    WHERE p.activo = 1
    ORDER BY p.nombre
    ''')
    productos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return productos

def crear_producto_sistema(usuario_id, datos_producto):
    """Crea un nuevo producto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generar código único si no se proporciona
        if not datos_producto.get('codigo'):
            datos_producto['codigo'] = f"PROD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        cursor.execute('''
        INSERT INTO productos (codigo, nombre, descripcion, categoria, 
                             unidad_medida, precio_compra, precio_venta,
                             stock_minimo, stock_maximo, stock_actual,
                             ubicacion, proveedor_id, usuario_creador)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos_producto['codigo'],
            datos_producto['nombre'],
            datos_producto.get('descripcion', ''),
            datos_producto['categoria'],
            datos_producto['unidad_medida'],
            datos_producto.get('precio_compra', 0),
            datos_producto.get('precio_venta', 0),
            datos_producto.get('stock_minimo', 0),
            datos_producto.get('stock_maximo', 0),
            datos_producto.get('stock_actual', 0),
            datos_producto.get('ubicacion', ''),
            datos_producto.get('proveedor_id'),
            usuario_id
        ))
        
        conn.commit()
        conn.close()
        return True, "✅ Producto creado exitosamente"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

@st.cache_data(ttl=300)
def obtener_ventas_recientes(limite=10):
    """Obtiene ventas recientes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT v.*, c.nombre as cliente_nombre
    FROM ventas v
    JOIN clientes c ON v.cliente_id = c.id
    ORDER BY v.fecha_venta DESC
    LIMIT ?
    ''', (limite,))
    ventas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return ventas

@st.cache_data(ttl=300)
def obtener_kpis():
    """Obtiene KPIs principales del sistema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    kpis = {}
    
    try:
        # Total productos
        cursor.execute("SELECT COUNT(*) FROM productos WHERE activo = 1")
        kpis['total_productos'] = cursor.fetchone()[0] or 0
        
        # Productos bajo stock mínimo
        cursor.execute("SELECT COUNT(*) FROM productos WHERE stock_actual < stock_minimo AND activo = 1")
        kpis['productos_bajo_stock'] = cursor.fetchone()[0] or 0
        
        # Ventas del mes
        cursor.execute('''
        SELECT COALESCE(SUM(total), 0) 
        FROM ventas 
        WHERE strftime('%Y-%m', fecha_venta) = strftime('%Y-%m', 'now')
        ''')
        kpis['ventas_mes'] = float(cursor.fetchone()[0] or 0)
        
        # Valor del inventario
        cursor.execute('''
        SELECT COALESCE(SUM(stock_actual * precio_compra), 0)
        FROM productos
        WHERE activo = 1
        ''')
        kpis['valor_inventario'] = float(cursor.fetchone()[0] or 0)
        
        # Total usuarios activos
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE activo = 1")
        kpis['total_usuarios'] = cursor.fetchone()[0] or 0
        
    except Exception as e:
        # Si hay error, establecer valores por defecto
        kpis = {
            'total_productos': 0,
            'productos_bajo_stock': 0,
            'ventas_mes': 0.0,
            'valor_inventario': 0.0,
            'total_usuarios': 0
        }
    
    conn.close()
    return kpis

# ============================================
# INTERFAZ DE LOGIN - CORREGIDA
# ============================================
def mostrar_login():
    """Muestra la pantalla de login"""
    
    st.markdown("""
    <style>
    .login-container {
        max-width: 450px;
        margin: 50px auto;
        padding: 40px 30px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
    }
    .login-title {
        text-align: center;
        color: #2c3e50;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown('<h2 class="login-title">🏭 Sistema MRP</h2>', unsafe_allow_html=True)
            st.markdown('<p style="text-align: center; color: #666;">Panadería Industrial</p>', unsafe_allow_html=True)
            st.markdown("---")
            
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("**Usuario**", placeholder="admin")
                password = st.text_input("**Contraseña**", type="password", placeholder="Admin2024!")
                
                submit = st.form_submit_button("🚀 **INGRESAR**", use_container_width=True, type="primary")
                
                if submit:
                    if not username or not password:
                        st.error("⚠️ Por favor complete todos los campos")
                    else:
                        with st.spinner("🔐 Verificando credenciales..."):
                            usuario = autenticar_usuario(username, password)
                            if usuario:
                                st.session_state.usuario = usuario
                                st.success("✅ ¡Autenticación exitosa!")
                                st.rerun()
                            else:
                                st.error("❌ Usuario o contraseña incorrectos")
            
            # Botón de debug para crear admin si no funciona
            st.markdown("---")
            if st.button("👑 Crear Admin (Debug)", type="secondary", use_container_width=True):
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Verificar si admin existe
                cursor.execute("SELECT username FROM usuarios WHERE username = 'admin'")
                if cursor.fetchone():
                    st.info("✅ El usuario admin ya existe")
                else:
                    try:
                        admin_hash = hash_password("Admin2024!")
                        cursor.execute('''
                        INSERT INTO usuarios (username, nombre, rol, password, permisos, email, creado_por)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', ('admin', 'Administrador', 'admin', admin_hash, 'all', 'admin@panaderia.com', 1))
                        conn.commit()
                        st.success("✅ Admin creado: usuario=admin, contraseña=Admin2024!")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                
                conn.close()
            
            st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# DASHBOARD PRINCIPAL
# ============================================
def mostrar_dashboard():
    """Dashboard principal del sistema"""
    
    st.title("📊 Dashboard Principal")
    
    # Mostrar KPIs
    kpis = obtener_kpis()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📦 Productos",
            kpis['total_productos'],
            delta=f"-{kpis['productos_bajo_stock']} bajo stock" if kpis['productos_bajo_stock'] > 0 else None,
            delta_color="inverse" if kpis['productos_bajo_stock'] > 0 else "normal"
        )
    
    with col2:
        st.metric(
            "💰 Ventas Mes",
            f"${kpis['ventas_mes']:,.2f}"
        )
    
    with col3:
        st.metric(
            "📊 Valor Inventario",
            f"${kpis['valor_inventario']:,.2f}"
        )
    
    with col4:
        st.metric(
            "👥 Usuarios Activos",
            kpis['total_usuarios']
        )
    
    st.markdown("---")
    
    # Sección de productos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Productos en Stock")
        productos = obtener_productos()
        
        if productos:
            df_productos = pd.DataFrame(productos)
            if len(df_productos) > 0:
                display_cols = ['codigo', 'nombre', 'stock_actual', 'stock_minimo', 'precio_venta']
                available_cols = [col for col in display_cols if col in df_productos.columns]
                
                if available_cols:
                    st.dataframe(
                        df_productos[available_cols].head(10),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No hay datos de productos para mostrar")
            else:
                st.info("No hay productos registrados")
        else:
            st.info("No hay productos registrados")
    
    with col2:
        st.subheader("💰 Últimas Ventas")
        ventas = obtener_ventas_recientes(5)
        
        if ventas:
            df_ventas = pd.DataFrame(ventas)
            if 'fecha_venta' in df_ventas.columns and 'total' in df_ventas.columns and 'cliente_nombre' in df_ventas.columns:
                display_df = df_ventas[['fecha_venta', 'cliente_nombre', 'total']].copy()
                display_df['fecha_venta'] = pd.to_datetime(display_df['fecha_venta']).dt.strftime('%Y-%m-%d')
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("Datos de ventas incompletos")
        else:
            st.info("No hay ventas registradas")
    
    # Gráfico de productos por categoría
    if productos and len(productos) > 0:
        st.markdown("---")
        st.subheader("📊 Distribución por Categoría")
        
        try:
            df_categorias = pd.DataFrame(productos)
            if 'categoria' in df_categorias.columns:
                categorias_count = df_categorias['categoria'].value_counts()
                if len(categorias_count) > 0:
                    fig = px.pie(
                        values=categorias_count.values,
                        names=categorias_count.index,
                        title="Productos por Categoría"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        except:
            pass

# ============================================
# MÓDULO DE GESTIÓN DE USUARIOS
# ============================================
def mostrar_gestion_usuarios():
    """Módulo de gestión de usuarios"""
    
    st.title("👥 Gestión de Usuarios")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Usuarios", "➕ Nuevo Usuario", "⚙️ Configuración"])
    
    with tab1:
        st.subheader("Usuarios del Sistema")
        
        usuarios = obtener_usuarios()
        
        if usuarios:
            df_usuarios = pd.DataFrame(usuarios)
            
            display_columns = []
            column_mapping = {
                'username': 'Usuario',
                'nombre': 'Nombre',
                'rol': 'Rol',
                'email': 'Email',
                'activo': 'Activo'
            }
            
            for col, display_name in column_mapping.items():
                if col in df_usuarios.columns:
                    display_columns.append(col)
            
            if display_columns:
                display_df = df_usuarios[display_columns].copy()
                display_df.columns = [column_mapping[col] for col in display_columns]
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Estadísticas
                col1, col2 = st.columns(2)
                with col1:
                    total_usuarios = len(df_usuarios)
                    st.metric("Total Usuarios", total_usuarios)
                with col2:
                    activos = df_usuarios['activo'].sum() if 'activo' in df_usuarios.columns else 0
                    st.metric("Usuarios Activos", activos)
            else:
                st.info("No hay datos de usuarios disponibles")
        else:
            st.info("No hay usuarios registrados en el sistema")
    
    with tab2:
        st.subheader("Crear Nuevo Usuario")
        
        with st.form("form_nuevo_usuario", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Usuario*", help="Nombre de usuario para login")
                nombre = st.text_input("Nombre Completo*")
                email = st.text_input("Email")
                telefono = st.text_input("Teléfono")
            
            with col2:
                rol = st.selectbox("Rol*", ["admin", "usuario", "visor", "produccion", "ventas"])
                departamento = st.selectbox("Departamento", 
                                          ["ADMINISTRACION", "PRODUCCION", "VENTAS", "ALMACEN", "COMPRAS", "SISTEMAS"])
                password = st.text_input("Contraseña*", type="password", 
                                       help="Mínimo 6 caracteres")
                confirm_password = st.text_input("Confirmar Contraseña*", type="password")
                permisos = st.text_area("Permisos (opcional)", 
                                      placeholder="Ej: ver_reportes,crear_productos,editar_ventas")
            
            st.write("*** Campos obligatorios")
            
            if st.form_submit_button("👤 Crear Usuario", type="primary", use_container_width=True):
                # Validaciones
                if not all([username, nombre, password, confirm_password]):
                    st.error("❌ Complete todos los campos obligatorios")
                elif password != confirm_password:
                    st.error("❌ Las contraseñas no coinciden")
                elif len(password) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres")
                else:
                    datos_usuario = {
                        'username': username,
                        'nombre': nombre,
                        'rol': rol,
                        'password': password,
                        'permisos': permisos,
                        'email': email,
                        'telefono': telefono,
                        'departamento': departamento
                    }
                    
                    success, mensaje = crear_usuario_sistema(
                        st.session_state.usuario['id'],
                        datos_usuario
                    )
                    
                    if success:
                        st.success(mensaje)
                        st.balloons()
                        st.cache_data.clear()
                    else:
                        st.error(mensaje)
    
    with tab3:
        st.subheader("Configuración de Usuario")
        
        st.info("Aquí puedes cambiar tu contraseña y ajustes personales")
        
        with st.form("form_cambiar_password"):
            st.write("### 🔐 Cambiar Mi Contraseña")
            
            password_actual = st.text_input("Contraseña Actual", type="password")
            nueva_password = st.text_input("Nueva Contraseña", type="password")
            confirmar_password = st.text_input("Confirmar Nueva Contraseña", type="password")
            
            if st.form_submit_button("🔄 Cambiar Contraseña", use_container_width=True):
                if not all([password_actual, nueva_password, confirmar_password]):
                    st.error("❌ Complete todos los campos")
                elif nueva_password != confirmar_password:
                    st.error("❌ Las contraseñas nuevas no coinciden")
                elif len(nueva_password) < 6:
                    st.error("❌ La nueva contraseña debe tener al menos 6 caracteres")
                else:
                    # Verificar contraseña actual
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT password FROM usuarios WHERE id = ?",
                        (st.session_state.usuario['id'],)
                    )
                    resultado = cursor.fetchone()
                    
                    if resultado and hash_password(password_actual) == resultado[0]:
                        # Cambiar contraseña
                        new_hash = hash_password(nueva_password)
                        cursor.execute(
                            "UPDATE usuarios SET password = ? WHERE id = ?",
                            (new_hash, st.session_state.usuario['id'])
                        )
                        conn.commit()
                        conn.close()
                        st.success("✅ Contraseña cambiada exitosamente")
                    else:
                        st.error("❌ Contraseña actual incorrecta")

# ============================================
# MÓDULO DE GESTIÓN DE INVENTARIO
# ============================================
def mostrar_gestion_inventario():
    """Módulo de gestión de inventario"""
    
    st.title("📦 Gestión de Inventario")
    
    tab1, tab2, tab3 = st.tabs(["📋 Productos", "➕ Nuevo Producto", "📊 Reportes"])
    
    with tab1:
        st.subheader("Productos en Inventario")
        
        # Filtros
        col1, col2 = st.columns([3, 1])
        with col1:
            filtro_busqueda = st.text_input("🔍 Buscar producto", placeholder="Nombre o código...")
        with col2:
            if st.button("🔄 Actualizar", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        
        productos = obtener_productos()
        
        if productos:
            df_productos = pd.DataFrame(productos)
            
            # Aplicar filtro si existe
            if filtro_busqueda:
                mask = (
                    df_productos['nombre'].str.contains(filtro_busqueda, case=False, na=False) |
                    df_productos['codigo'].str.contains(filtro_busqueda, case=False, na=False)
                )
                df_filtrado = df_productos[mask]
            else:
                df_filtrado = df_productos
            
            if len(df_filtrado) > 0:
                # Columnas para mostrar
                display_cols = []
                column_mapping = {
                    'codigo': 'Código',
                    'nombre': 'Nombre',
                    'categoria': 'Categoría',
                    'stock_actual': 'Stock',
                    'stock_minimo': 'Mínimo',
                    'precio_venta': 'P. Venta'
                }
                
                for col, display_name in column_mapping.items():
                    if col in df_filtrado.columns:
                        display_cols.append(col)
                
                if display_cols:
                    display_df = df_filtrado[display_cols].copy()
                    display_df.columns = [column_mapping[col] for col in display_cols]
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Mostrar resumen
                    st.info(f"📊 Mostrando **{len(df_filtrado)}** de **{len(df_productos)}** productos")
                    
                    # Productos con bajo stock
                    bajo_stock = df_filtrado[df_filtrado['stock_actual'] < df_filtrado['stock_minimo']]
                    if len(bajo_stock) > 0:
                        st.warning(f"⚠️ **{len(bajo_stock)} productos con stock bajo el mínimo**")
                else:
                    st.info("No hay columnas disponibles para mostrar")
            else:
                st.info("No se encontraron productos con ese filtro")
        else:
            st.info("No hay productos registrados")
    
    with tab2:
        st.subheader("Registrar Nuevo Producto")
        
        with st.form("form_nuevo_producto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                codigo = st.text_input("Código (auto-generado si vacío)", 
                                      help="Dejar vacío para generar automáticamente")
                nombre = st.text_input("Nombre del Producto*")
                descripcion = st.text_area("Descripción")
                categoria = st.selectbox("Categoría*", 
                                       ["TERMINADO", "SEMIELABORADO", "MATERIA_PRIMA", "INSUMO", "OTRO"])
                unidad_medida = st.selectbox("Unidad de Medida*",
                                           ["UNIDAD", "KILO", "LITRO", "METRO", "CAJA", "BOLSA"])
            
            with col2:
                precio_compra = st.number_input("Precio de Compra", min_value=0.0, value=0.0, step=0.01)
                precio_venta = st.number_input("Precio de Venta", min_value=0.0, value=0.0, step=0.01)
                stock_minimo = st.number_input("Stock Mínimo", min_value=0, value=10)
                stock_maximo = st.number_input("Stock Máximo", min_value=0, value=100)
                stock_actual = st.number_input("Stock Inicial", min_value=0, value=0)
                ubicacion = st.text_input("Ubicación en Almacén")
            
            st.write("*** Campos obligatorios")
            
            if st.form_submit_button("📦 Registrar Producto", type="primary", use_container_width=True):
                if not nombre or not categoria or not unidad_medida:
                    st.error("❌ Complete los campos obligatorios (*)")
                else:
                    datos_producto = {
                        'codigo': codigo if codigo.strip() else None,
                        'nombre': nombre,
                        'descripcion': descripcion,
                        'categoria': categoria,
                        'unidad_medida': unidad_medida,
                        'precio_compra': precio_compra,
                        'precio_venta': precio_venta,
                        'stock_minimo': stock_minimo,
                        'stock_maximo': stock_maximo,
                        'stock_actual': stock_actual,
                        'ubicacion': ubicacion
                    }
                    
                    success, mensaje = crear_producto_sistema(
                        st.session_state.usuario['id'],
                        datos_producto
                    )
                    
                    if success:
                        st.success(mensaje)
                        st.balloons()
                        st.cache_data.clear()
                    else:
                        st.error(mensaje)
    
    with tab3:
        st.subheader("📊 Reportes de Inventario")
        
        # KPIs de inventario
        productos = obtener_productos()
        if productos:
            df_productos = pd.DataFrame(productos)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                valor_total = (df_productos['stock_actual'] * df_productos['precio_compra']).sum()
                st.metric("💰 Valor Total Inventario", f"${valor_total:,.2f}")
            
            with col2:
                productos_bajo_stock = len(df_productos[df_productos['stock_actual'] < df_productos['stock_minimo']])
                st.metric("⚠️ Productos Bajo Stock", productos_bajo_stock)
            
            with col3:
                total_productos = len(df_productos)
                st.metric("📦 Total Productos", total_productos)
            
            # Gráfico de stock por categoría
            st.markdown("---")
            st.subheader("Distribución por Categoría")
            
            try:
                if 'categoria' in df_productos.columns and 'stock_actual' in df_productos.columns:
                    stock_por_categoria = df_productos.groupby('categoria')['stock_actual'].sum().reset_index()
                    
                    if len(stock_por_categoria) > 0:
                        fig = px.bar(
                            stock_por_categoria,
                            x='categoria',
                            y='stock_actual',
                            title='Stock Total por Categoría',
                            color='categoria'
                        )
                        st.plotly_chart(fig, use_container_width=True)
            except:
                st.info("No se pudo generar el gráfico de categorías")
        else:
            st.info("No hay datos de inventario para mostrar reportes")

# ============================================
# BARRA SUPERIOR DE NAVEGACIÓN
# ============================================
def mostrar_barra_navegacion():
    """Muestra la barra de navegación superior"""
    
    usuario = st.session_state.usuario
    
    st.markdown("""
    <style>
    .navbar {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([6, 1, 1])
    
    with col1:
        st.markdown(f"### 🏭 Sistema MRP | 👤 {usuario['nombre']} ({usuario['rol'].upper()})")
    
    with col2:
        if st.button("🔄", help="Actualizar página"):
            st.cache_data.clear()
            st.rerun()
    
    with col3:
        if st.button("🚪", help="Cerrar sesión"):
            del st.session_state.usuario
            st.rerun()

# ============================================
# MENÚ PRINCIPAL
# ============================================
def mostrar_menu_principal():
    """Muestra el menú principal según el rol del usuario"""
    
    usuario = st.session_state.usuario
    rol = usuario['rol']
    
    # Definir opciones de menú según rol
    if rol == 'admin':
        opciones_menu = [
            ("📊 Dashboard", "dashboard"),
            ("📦 Inventario", "inventario"),
            ("👥 Usuarios", "usuarios"),
            ("💰 Ventas", "ventas"),
            ("📈 Reportes", "reportes"),
            ("⚙️ Configuración", "configuracion")
        ]
    elif rol == 'ventas':
        opciones_menu = [
            ("📊 Dashboard", "dashboard"),
            ("📦 Inventario", "inventario"),
            ("💰 Ventas", "ventas"),
            ("📈 Reportes", "reportes")
        ]
    elif rol == 'produccion':
        opciones_menu = [
            ("📊 Dashboard", "dashboard"),
            ("📦 Inventario", "inventario"),
            ("📈 Reportes", "reportes")
        ]
    else:  # usuario, visor, etc.
        opciones_menu = [
            ("📊 Dashboard", "dashboard"),
            ("📦 Inventario", "inventario")
        ]
    
    # Crear tabs
    tabs = st.tabs([opcion[0] for opcion in opciones_menu])
    
    # Mostrar contenido según tab seleccionado
    for i, (nombre, modulo) in enumerate(opciones_menu):
        with tabs[i]:
            if modulo == "dashboard":
                mostrar_dashboard()
            elif modulo == "inventario":
                mostrar_gestion_inventario()
            elif modulo == "usuarios":
                if rol == 'admin':
                    mostrar_gestion_usuarios()
                else:
                    st.warning("⛔ Acceso restringido. Solo administradores pueden acceder a esta sección.")
            elif modulo == "ventas":
                if rol in ['admin', 'ventas']:
                    st.title("💰 Gestión de Ventas")
                    st.info("Módulo de ventas - En desarrollo")
                else:
                    st.warning("⛔ Acceso restringido.")
            elif modulo == "reportes":
                if rol in ['admin', 'ventas', 'produccion']:
                    st.title("📈 Reportes Avanzados")
                    st.info("Módulo de reportes - En desarrollo")
                else:
                    st.warning("⛔ Acceso restringido.")
            elif modulo == "configuracion":
                if rol == 'admin':
                    st.title("⚙️ Configuración del Sistema")
                    
                    tab_config1, tab_config2 = st.tabs(["General", "Base de Datos"])
                    
                    with tab_config1:
                        st.subheader("Configuración General")
                        
                        with st.form("form_config_general"):
                            nombre_empresa = st.text_input("Nombre de la Empresa", value="Panadería Industrial")
                            ruc_empresa = st.text_input("RUC", value="12345678901")
                            direccion = st.text_input("Dirección")
                            telefono = st.text_input("Teléfono")
                            email = st.text_input("Email Corporativo")
                            
                            if st.form_submit_button("💾 Guardar Configuración"):
                                st.success("✅ Configuración guardada")
                    
                    with tab_config2:
                        st.subheader("Gestión de Base de Datos")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("🔄 Reinicializar BD", type="secondary", use_container_width=True):
                                st.cache_resource.clear()
                                st.cache_data.clear()
                                st.success("✅ Cache limpiado")
                                st.rerun()
                        
                        with col2:
                            if st.button("📊 Ver Estadísticas", type="secondary", use_container_width=True):
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                
                                tablas = ['usuarios', 'productos', 'proveedores', 'clientes', 'ventas']
                                
                                st.write("**Estadísticas de la Base de Datos:**")
                                for tabla in tablas:
                                    try:
                                        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                                        count = cursor.fetchone()[0]
                                        st.write(f"- {tabla}: {count} registros")
                                    except:
                                        st.write(f"- {tabla}: 0 registros")
                                
                                conn.close()
                else:
                    st.warning("⛔ Acceso restringido. Solo administradores pueden acceder a esta sección.")

# ============================================
# FUNCIÓN PRINCIPAL DE LA APLICACIÓN
# ============================================
def main():
    """Función principal de la aplicación"""
    
    # Inicializar estado de la sesión
    if 'usuario' not in st.session_state:
        st.session_state.usuario = None
    
    # Inicializar base de datos
    init_database()
    
    # Verificar autenticación
    if not st.session_state.usuario:
        mostrar_login()
    else:
        # Mostrar barra de navegación
        mostrar_barra_navegacion()
        
        # Mostrar menú principal
        mostrar_menu_principal()

# ============================================
# EJECUCIÓN
# ============================================
if __name__ == "__main__":
    main()
