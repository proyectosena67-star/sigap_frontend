from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

evaluaciones_bp = Blueprint('evaluaciones', __name__)

@evaluaciones_bp.route('/evaluaciones')
@login_required
def evaluaciones():
    lista_evaluaciones = []
    examen_mental = None
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.*, at.id_atencion, p.primer_nombre, p.primer_apellido
            FROM escalas_psicometricas e
            JOIN atenciones at ON e.id_atencion = at.id_atencion
            JOIN historial_clinico h ON at.id_historial = h.id_historial
            JOIN pacientes p ON h.id_paciente = p.id_paciente
            ORDER BY e.id_escala DESC
        ''')
        lista_evaluaciones = cursor.fetchall()

        cursor.execute('''
            SELECT eem.*, p.primer_nombre, p.primer_apellido 
            FROM examen_estado_mental eem
            JOIN atenciones at ON eem.id_atencion = at.id_atencion
            JOIN historial_clinico h ON at.id_historial = h.id_historial
            JOIN pacientes p ON h.id_paciente = p.id_paciente
            ORDER BY eem.id_eem DESC LIMIT 1
        ''')
        examen_mental = cursor.fetchone()
        cursor.close()
    except Exception as e:
        flash(f"Error al cargar evaluaciones clínicas: {str(e)}", "warning")
    finally:
        if conn: release_db_connection(conn)

    return render_template('evaluaciones.html', evaluaciones=lista_evaluaciones, eem=examen_mental)

@evaluaciones_bp.route('/guardar_evaluacion', methods=['POST'])
@login_required
@role_required(['Psicologo', 'Medico'])
def guardar_evaluacion():
    id_atencion = request.form.get('id_atencion', 1)
    nombre_escala = request.form.get('nombre_escala')
    puntuacion_total = request.form.get('puntuacion_total')
    interpretacion = request.form.get('interpretacion')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO escalas_psicometricas (id_atencion, id_evaluador, nombre_escala, puntuacion_total, interpretacion, fecha_aplicacion)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''', (id_atencion, session['usuario_id'], nombre_escala, puntuacion_total, interpretacion))
        
        registrar_auditoria(cursor, session['usuario_id'], 'ESCALA', f'Escala psicométrica {nombre_escala} aplicada')
        conn.commit()
        cursor.close()
        flash("Evaluación psicométrica guardada correctamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al registrar evaluación: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('evaluaciones.evaluaciones'))

@evaluaciones_bp.route('/guardar_eem', methods=['POST'])
@login_required
@role_required(['Medico', 'Psicologo'])
def guardar_eem():
    id_atencion = request.form.get('id_atencion', 1)
    apariencia = request.form.get('apariencia_porte', '')
    actitud = request.form.get('actitud', '')
    estado_animo = request.form.get('estado_animo', '')
    pensamiento = request.form.get('curso_pensamiento', '')
    percepcion = request.form.get('percepcion', '')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO examen_estado_mental (id_atencion, id_evaluador, apariencia_porte, actitud, estado_animo, curso_pensamiento, percepcion, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ''', (id_atencion, session['usuario_id'], apariencia, actitud, estado_animo, pensamiento, percepcion))
        
        registrar_auditoria(cursor, session['usuario_id'], 'EEM', f'Examen del estado mental registrado para atención ID {id_atencion}')
        conn.commit()
        cursor.close()
        flash("Examen del Estado Mental guardado exitosamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al registrar Examen del Estado Mental: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('evaluaciones.evaluaciones'))

@evaluaciones_bp.route('/guardar_orden_laboratorio', methods=['POST'])
@login_required
@role_required(['Medico'])
def guardar_orden_laboratorio():
    id_atencion = request.form.get('id_atencion', 1)
    tipo_examen = request.form.get('tipo_examen')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ordenes_laboratorio (id_atencion, id_medico, tipo_examen, estado, fecha_orden)
            VALUES (%s, %s, %s, 'PENDIENTE', NOW())
        ''', (id_atencion, session['usuario_id'], tipo_examen))
        
        registrar_auditoria(cursor, session['usuario_id'], 'LAB_ORDEN', f'Orden de laboratorio generada: {tipo_examen}')
        conn.commit()
        cursor.close()
        flash("Orden de laboratorio generada.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al solicitar laboratorio: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('evaluaciones.evaluaciones'))

@evaluaciones_bp.route('/guardar_resultado_laboratorio', methods=['POST'])
@login_required
@role_required(['Laboratorista', 'Administrador'])
def guardar_resultado_laboratorio():
    id_orden = request.form.get('id_orden')
    resultado = request.form.get('resultado')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO resultados_laboratorio (id_orden, resultado, fecha_resultado) VALUES (%s, %s, NOW())', (id_orden, resultado))
        cursor.execute('UPDATE ordenes_laboratorio SET estado = \'COMPLETADO\' WHERE id_orden = %s', (id_orden,))
        registrar_auditoria(cursor, session['usuario_id'], 'LAB_RESULTADO', f'Resultado cargado para orden ID {id_orden}')

        conn.commit()
        cursor.close()
        flash("Resultado de laboratorio registrado.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al registrar resultado: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('evaluaciones.evaluaciones'))