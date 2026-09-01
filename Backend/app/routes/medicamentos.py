from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

medicamentos_bp = Blueprint('medicamentos', __name__)

@medicamentos_bp.route('/medicamentos')
@login_required
def medicamentos():
    lista_medicamentos = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.*, d.cantidad_entregada, d.lote, d.fecha_vencimiento
            FROM medicamentos_insumos m
            LEFT JOIN dispensaciones d ON m.id_item = d.id_item
            ORDER BY m.id_item DESC
        ''')
        lista_medicamentos = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error al cargar medicamentos: {str(e)}", "warning")
    finally:
        if conn: release_db_connection(conn)

    return render_template('medicamentos.html', medicamentos=lista_medicamentos)

@medicamentos_bp.route('/guardar_medicamento', methods=['POST'])
@login_required
@role_required(['Administrador', 'Farmaceutico'])
def guardar_medicamento():
    nombre = request.form.get('nombre')
    tipo_item = request.form.get('tipo_item', 'MEDICAMENTO')
    forma_farmaceutica = request.form.get('forma_farmaceutica')
    concentracion = request.form.get('concentracion')
    stock_actual = request.form.get('stock_actual', 0)
    stock_minimo = request.form.get('stock_minimo', 5)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO medicamentos_insumos (nombre, tipo_item, forma_farmaceutica, concentracion, stock_actual, stock_minimo)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (nombre, tipo_item, forma_farmaceutica, concentracion, stock_actual, stock_minimo))
        
        registrar_auditoria(cursor, session['usuario_id'], 'CATALOGO_MED', f'Nuevo ítem de inventario: {nombre}')
        conn.commit()
        cursor.close()
        flash("Medicamento / Insumo agregado correctamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al guardar medicamento: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('medicamentos.medicamentos'))

@medicamentos_bp.route('/guardar_prescripcion', methods=['POST'])
@login_required
@role_required(['Medico'])
def guardar_prescripcion():
    id_atencion = request.form.get('id_atencion', 1)
    id_item = request.form.get('id_item')
    dosis = request.form.get('dosis')
    frecuencia = request.form.get('frecuencia')
    duracion = request.form.get('duracion_dias')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO prescripciones_encabezado (id_atencion, id_medico, fecha_prescripcion)
            VALUES (%s, %s, NOW()) RETURNING id_prescripcion
        ''', (id_atencion, session['usuario_id']))
        prescripcion = cursor.fetchone()

        cursor.execute('''
            INSERT INTO prescripciones_detalle (id_prescripcion, id_item, dosis, frecuencia, duracion_dias)
            VALUES (%s, %s, %s, %s, %s)
        ''', (prescripcion['id_prescripcion'], id_item, dosis, frecuencia, duracion))

        registrar_auditoria(cursor, session['usuario_id'], 'PRESCRIPCION', f'Prescripción emitida para ítem ID {id_item}')
        conn.commit()
        cursor.close()
        flash("Prescripción médica guardada.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al guardar prescripción: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('medicamentos.medicamentos'))

@medicamentos_bp.route('/registrar_dispensacion', methods=['POST'])
@login_required
@role_required(['Farmaceutico', 'Enfermera'])
def registrar_dispensacion():
    id_item = request.form.get('id_item')
    id_atencion = request.form.get('id_atencion', 1)
    cantidad = request.form.get('cantidad', 1, type=int)
    lote = request.form.get('lote', 'N/A')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dispensaciones (id_atencion, id_item, id_enfermera, cantidad_entregada, lote, fecha_dispensacion)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''', (id_atencion, id_item, session['usuario_id'], cantidad, lote))
        
        cursor.execute('UPDATE medicamentos_insumos SET stock_actual = stock_actual - %s WHERE id_item = %s', (cantidad, id_item))
        registrar_auditoria(cursor, session['usuario_id'], 'DISPENSACION', f'Dispensados {cantidad} unidades del ítem ID {id_item}')

        conn.commit()
        cursor.close()
        flash("Dispensación registrada y stock actualizado.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error en dispensación: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('medicamentos.medicamentos'))
