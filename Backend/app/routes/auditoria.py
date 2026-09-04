from flask import Blueprint, render_template
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required

auditoria_bp = Blueprint('auditoria', __name__)


@auditoria_bp.route('/auditoria')
@login_required
@role_required(['Administrador'])
def auditoria():
    lista_logs = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 
                a.id_log,
                a.accion,
                a.tabla_afectada,
                a.registro_id,
                a.datos_nuevos,
                a.direccion_ip,
                a.fecha_hora,
                u.nombres,
                u.apellidos
            FROM auditoria_logs a
            LEFT JOIN usuarios u ON a.id_usuario = u.id_usuario
            ORDER BY a.fecha_hora DESC
            LIMIT 200
        ''')
        lista_logs = cursor.fetchall()
        cursor.close()

    except Exception as e:
        from flask import flash
        flash(f"Error al cargar auditoría del sistema: {str(e)}", "warning")

    finally:
        if conn:
            release_db_connection(conn)

    return render_template('auditoria.html', logs=lista_logs)