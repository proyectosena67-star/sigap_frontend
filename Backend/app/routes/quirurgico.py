from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

quirurgico_bp = Blueprint('quirurgico', __name__)

@quirurgico_bp.route('/quirurgico')
@login_required
def quirurgico():
    cirugias = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, p.primer_nombre, p.primer_apellido, u.nombres AS cirujano_nombre
            FROM programacion_quirurgica c
            JOIN pacientes p ON c.id_paciente = p.id_paciente
            JOIN usuarios u ON c.id_cirujano = u.id_usuario
            ORDER BY c.fecha_programada DESC
        ''')
        cirugias = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error al cargar programación quirúrgica: {str(e)}", "warning")
    finally:
        if conn: release_db_connection(conn)

    return render_template('quirurgico.html', cirugias=cirugias)

@quirurgico_bp.route('/guardar_cirugia', methods=['POST'])
@login_required
@role_required(['Medico'])
def guardar_cirugia():
    id_paciente = request.form.get('id_paciente')
    id_quirofano = request.form.get('id_quirofano')
    procedimiento = request.form.get('nombre_procedimiento')
    fecha_programada = request.form.get('fecha_programada')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO programacion_quirurgica (id_paciente, id_cirujano, id_quirofano, nombre_procedimiento, fecha_programada, estado)
            VALUES (%s, %s, %s, %s, %s, 'PROGRAMADA')
        ''', (id_paciente, session['usuario_id'], id_quirofano, procedimiento, fecha_programada))
        
        registrar_auditoria(cursor, session['usuario_id'], 'CIRUGIA', f'Cirugía programada: {procedimiento}')
        conn.commit()
        cursor.close()
        flash("Cirugía programada con éxito.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al programar cirugía: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('quirurgico.quirurgico'))
