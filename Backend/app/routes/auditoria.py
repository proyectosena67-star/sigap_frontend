from flask import Blueprint, render_template, flash
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required

auditoria_bp = Blueprint('auditoria', __name__)

@auditoria_bp.route('/auditoria')
@login_required
@role_required(['Administrador'])
def auditoria():
    registros_auditoria = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, u.nombres, u.apellidos
            FROM auditoria_sistema a
            JOIN usuarios u ON a.id_usuario = u.id_usuario
            ORDER BY a.fecha_evento DESC LIMIT 50
        ''')
        registros_auditoria = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error al cargar auditoría: {str(e)}", "warning")
    finally:
        if conn: release_db_connection(conn)

    return render_template('auditoria.html', auditoria=registros_auditoria)
