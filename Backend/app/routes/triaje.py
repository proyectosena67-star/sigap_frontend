from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

triaje_bp = Blueprint('triaje', __name__)

@triaje_bp.route('/triaje')
@login_required
def triaje():
    lista_triajes = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*, p.primer_nombre, p.primer_apellido, p.numero_documento, u.nombres AS enfermero_nombre
            FROM triaje_urgencias t
            JOIN pacientes p ON t.id_paciente = p.id_paciente
            JOIN usuarios u ON t.id_enfermera = u.id_usuario
            ORDER BY t.id_triaje DESC LIMIT 50
        ''')
        lista_triajes = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error al cargar registros de triaje: {str(e)}", "warning")
    finally:
        if conn: release_db_connection(conn)

    return render_template('triaje.html', triajes=lista_triajes)

@triaje_bp.route('/guardar_triaje', methods=['POST'])
@login_required
@role_required(['Enfermera', 'Medico'])
def guardar_triaje():
    id_paciente = request.form.get('id_paciente')
    clasificacion = request.form.get('clasificacion_nivel') # Ej: Triage I, II, III, IV, V
    motivo = request.form.get('motivo_consulta')
    fc = request.form.get('frecuencia_cardiaca')
    pa = request.form.get('presion_arterial')
    temperatura = request.form.get('temperatura')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO triaje_urgencias (id_paciente, id_enfermera, clasificacion_nivel, motivo_consulta, frecuencia_cardiaca, presion_arterial, temperatura, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ''', (id_paciente, session['usuario_id'], clasificacion, motivo, fc, pa, temperatura))
        
        registrar_auditoria(cursor, session['usuario_id'], 'TRIAJE', f'Clasificación de triaje {clasificacion} aplicada a paciente ID {id_paciente}')
        conn.commit()
        cursor.close()
        flash("Triaje registrado exitosamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al guardar triaje: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('triaje.triaje'))
