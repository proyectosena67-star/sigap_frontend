from flask import Blueprint, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

citas_bp = Blueprint('citas', __name__)

@citas_bp.route('/guardar_cita', methods=['POST'])
@login_required
def guardar_cita():
    id_paciente = request.form.get('id_paciente')
    id_medico = request.form.get('id_medico', session['usuario_id'])
    fecha_cita = request.form.get('fecha_cita')
    motivo = request.form.get('motivo', 'Consulta General')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO citas_medicas (id_paciente, id_medico, fecha_cita, motivo, estado)
            VALUES (%s, %s, %s, %s, 'PROGRAMADA')
        ''', (id_paciente, id_medico, fecha_cita, motivo))
        
        registrar_auditoria(cursor, session['usuario_id'], 'INSERT_CITA', f'Cita agendada para paciente ID: {id_paciente}')
        conn.commit()
        cursor.close()
        flash("Cita médica agendada exitosamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al agendar cita: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('pacientes.historial'))

@citas_bp.route('/guardar_diagnostico', methods=['POST'])
@login_required
@role_required(['Medico'])
def guardar_diagnostico():
    id_atencion = request.form.get('id_atencion', 1)
    id_cie10 = request.form.get('id_cie10')
    tipo_dx = request.form.get('tipo_diagnostico', 'PRESUNTIVO')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO diagnosticos_atencion (id_atencion, id_cie10, tipo_diagnostico, fecha_registro)
            VALUES (%s, %s, %s, NOW())
        ''', (id_atencion, id_cie10, tipo_dx))
        
        registrar_auditoria(cursor, session['usuario_id'], 'INSERT_DX', f'Diagnóstico CIE-10 añadido a atención ID: {id_atencion}')
        conn.commit()
        cursor.close()
        flash("Diagnóstico asignado correctamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al registrar diagnóstico: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('pacientes.historial'))

@citas_bp.route('/guardar_internamiento', methods=['POST'])
@login_required
@role_required(['Medico', 'Enfermera'])
def guardar_internamiento():
    id_paciente = request.form.get('id_paciente')
    id_cama = request.form.get('id_cama')
    motivo = request.form.get('motivo_ingreso')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO internamientos (id_paciente, id_cama, fecha_ingreso, motivo_ingreso, estado)
            VALUES (%s, %s, NOW(), %s, 'ACTIVO')
        ''', (id_paciente, id_cama, motivo))
        
        cursor.execute('UPDATE camas SET estado = \'OCUPADA\' WHERE id_cama = %s', (id_cama,))
        registrar_auditoria(cursor, session['usuario_id'], 'INTERNAMIENTO', f'Paciente ID {id_paciente} asignado a cama ID {id_cama}')

        conn.commit()
        cursor.close()
        flash("Internamiento registrado y cama asignada.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al registrar internamiento: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('pacientes.historial'))