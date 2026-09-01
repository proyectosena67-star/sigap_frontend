from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

vacunacion_bp = Blueprint('vacunacion', __name__)

@vacunacion_bp.route('/vacunacion')
@login_required
def vacunacion():
    registros = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.*, p.primer_nombre, p.primer_apellido, u.nombres AS aplicador_nombre
            FROM historial_vacunacion v
            JOIN pacientes p ON v.id_paciente = p.id_paciente
            JOIN usuarios u ON v.id_usuario_registra = u.id_usuario
            ORDER BY v.fecha_aplicacion DESC
        ''')
        registros = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error al cargar vacunación: {str(e)}", "warning")
    finally:
        if conn: release_db_connection(conn)

    return render_template('vacunacion.html', vacunacion=registros)

@vacunacion_bp.route('/guardar_vacuna', methods=['POST'])
@login_required
@role_required(['Enfermera', 'Medico'])
def guardar_vacuna():
    id_paciente = request.form.get('id_paciente')
    nombre_vacuna = request.form.get('nombre_vacuna')
    dosis_nro = request.form.get('dosis_numero', 1)
    lote = request.form.get('lote')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO historial_vacunacion (id_paciente, id_usuario_registra, nombre_vacuna, dosis_numero, lote, fecha_aplicacion)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''', (id_paciente, session['usuario_id'], nombre_vacuna, dosis_nro, lote))
        
        registrar_auditoria(cursor, session['usuario_id'], 'VACUNA', f'Vacuna aplicada: {nombre_vacuna} (Dosis {dosis_nro})')
        conn.commit()
        cursor.close()
        flash("Registro de vacunación guardado.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al registrar vacuna: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('vacunacion.vacunacion'))
