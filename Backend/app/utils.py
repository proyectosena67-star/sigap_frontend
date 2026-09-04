import json
from functools import wraps
from flask import session, redirect, url_for, flash
# Importamos las funciones de conexión gestionadas por la app en __init__.py
from app import get_db_connection, release_db_connection  


def registrar_auditoria(cursor, id_usuario, accion, tabla_afectada=None, registro_id=None, datos_anteriores=None, datos_nuevos=None, direccion_ip=None):
    """Registra una acción de auditoría adaptada a PostgreSQL."""
    try:
        # Serializar dicts a JSON si vienen datos estructurados
        datos_ant_json = json.dumps(datos_anteriores) if isinstance(datos_anteriores, (dict, list)) else datos_anteriores
        datos_nuev_json = json.dumps(datos_nuevos) if isinstance(datos_nuevos, (dict, list)) else datos_nuevos

        query = """
            INSERT INTO auditoria_logs 
            (id_usuario, accion, tabla_afectada, registro_id, datos_anteriores, datos_nuevos, direccion_ip) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            query, 
            (id_usuario, accion, tabla_afectada, registro_id, datos_ant_json, datos_nuev_json, direccion_ip)
        )
    except Exception as e:
        print(f"[AUDITORÍA] Usuario {id_usuario} - {accion}: Error BD: {e}")


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

            user_role = str(session.get('rol') or session.get('rol_nombre') or session.get('role') or '')

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