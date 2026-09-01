from functools import wraps
from flask import session, flash, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Por favor inicia sesión para acceder al sistema.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                flash("Por favor inicia sesión.", "warning")
                return redirect(url_for('auth.login'))
            if session.get('rol_nombre') not in roles_permitidos:
                flash("No tienes permisos suficientes para realizar esta acción.", "danger")
                return redirect(url_for('pacientes.historial'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def registrar_auditoria(cursor, id_usuario, accion, detalles):
    cursor.execute('''
        INSERT INTO auditoria_sistema (id_usuario, accion, detalles, fecha)
        VALUES (%s, %s, %s, NOW())
    ''', (id_usuario, accion, detalles))