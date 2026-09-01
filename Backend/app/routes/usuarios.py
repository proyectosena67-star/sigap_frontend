from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

usuarios_bp = Blueprint('usuarios', __name__)

@usuarios_bp.route('/usuarios')
@login_required
@role_required(['Administrador'])
def listar_usuarios():
    conn = None
    usuarios = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id_usuario, u.nombres, u.apellidos, u.correo, r.nombre AS rol_nombre, u.estado
            FROM usuarios u
            JOIN roles r ON u.id_rol = r.id_rol
            ORDER BY u.id_usuario DESC
        ''')
        usuarios = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error al cargar usuarios: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return render_template('usuarios.html', usuarios=usuarios)