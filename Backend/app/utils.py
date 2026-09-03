import psycopg2
from functools import wraps
from flask import session, redirect, url_for, flash

def get_db_connection():
    """Obtiene una conexión directa a PostgreSQL usando tus credenciales reales de sigam_db."""
    return psycopg2.connect(
        host="localhost",
        database="sigam_db",
        user="postgres",
        password="1234",  # Reemplaza con tu contraseña real de DBeaver
        port=5432
    )

def release_db_connection(conn):
    """Cierra o libera la conexión a la base de datos."""
    if conn:
        conn.close()

def registrar_auditoria(cursor, id_usuario, accion, detalle=""):
    """Registra una acción de auditoría en la base de datos o consola de forma segura."""
    try:
        cursor.execute(
            "INSERT INTO auditoria (id_usuario, accion, descripcion, fecha) VALUES (%s, %s, %s, NOW())",
            (id_usuario, accion, detalle)
        )
    except Exception as e:
        print(f"[AUDITORÍA] Usuario {id_usuario} - {accion}: {detalle} | Error BD: {e}")

def login_required(f):
    """Decorador para restringir acceso solo a usuarios autenticados."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session and 'id_usuario' not in session and 'user_id' not in session:
            flash("Por favor inicia sesión para continuar.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles_permitidos):
    """Decorador flexible para restringir acceso según el rol del usuario."""
    if isinstance(roles_permitidos, str):
        roles_permitidos = [roles_permitidos]
        
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session and 'id_usuario' not in session and 'user_id' not in session:
                flash("Por favor inicia sesión para continuar.", "warning")
                return redirect(url_for('auth.login'))
            
            user_role = session.get('rol') or session.get('rol_nombre') or session.get('role') or ''
            
            rol_actual_clean = user_role.strip().lower()
            roles_permitidos_clean = [str(r).strip().lower() for r in roles_permitidos]
            
            es_admin_actual = any(a in rol_actual_clean for a in ['administrac', 'admin'])
            es_admin_requerido = any('administrac' in r or 'admin' in r for r in roles_permitidos_clean)

            if rol_actual_clean not in roles_permitidos_clean and not (es_admin_requerido and es_admin_actual):
                flash("No tienes permisos para acceder a esta sección.", "danger")
                return redirect(url_for('pacientes.pacientes'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator