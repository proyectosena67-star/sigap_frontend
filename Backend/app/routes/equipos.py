from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

equipos_bp = Blueprint('equipos', __name__)

@equipos_bp.route('/equipos')
@login_required
@role_required(['Administrador', 'IngenieriaBiomedica'])
def equipos():
    lista_equipos = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM equipos_medicos ORDER BY id_equipo DESC")
        lista_equipos = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error al cargar equipos biomédicos: {str(e)}", "warning")
    finally:
        if conn: release_db_connection(conn)

    return render_template('equipos.html', equipos=lista_equipos)

@equipos_bp.route('/guardar_equipo', methods=['POST'])
@login_required
@role_required(['Administrador', 'IngenieriaBiomedica'])
def guardar_equipo():
    nombre = request.form.get('nombre_equipo')
    serial = request.form.get('numero_serial')
    ubicacion = request.form.get('ubicacion_servicio')
    estado = request.form.get('estado_operativo', 'OPERATIVO')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO equipos_medicos (nombre_equipo, numero_serial, ubicacion_servicio, estado_operativo, fecha_registro)
            VALUES (%s, %s, %s, %s, NOW())
        ''', (nombre, serial, ubicacion, estado))
        
        registrar_auditoria(cursor, session['usuario_id'], 'EQUIPO_MEDICO', f'Equipo registrado: {nombre} (Serial: {serial})')
        conn.commit()
        cursor.close()
        flash("Equipo médico registrado correctamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al registrar equipo: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('equipos.equipos'))
