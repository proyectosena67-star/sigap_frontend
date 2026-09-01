from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

facturacion_bp = Blueprint('facturacion', __name__)

@facturacion_bp.route('/facturacion')
@login_required
@role_required(['Administrador', 'Facturador'])
def facturacion():
    facturas = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.*, p.primer_nombre, p.primer_apellido, p.numero_documento
            FROM facturacion_fev f
            JOIN pacientes p ON f.id_paciente = p.id_paciente
            ORDER BY f.id_factura DESC LIMIT 50
        ''')
        facturas = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error al cargar facturas: {str(e)}", "warning")
    finally:
        if conn: release_db_connection(conn)

    return render_template('facturacion.html', facturas=facturas)

@facturacion_bp.route('/guardar_factura', methods=['POST'])
@login_required
@role_required(['Administrador', 'Facturador'])
def guardar_factura():
    id_paciente = request.form.get('id_paciente')
    id_atencion = request.form.get('id_atencion')
    subtotal = request.form.get('subtotal', 0)
    impuestos = request.form.get('impuestos', 0)
    total = request.form.get('total', 0)
    cufe = request.form.get('cufe', 'CUFE_PENDIENTE_DIAN')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO facturacion_fev (id_paciente, id_atencion, subtotal, impuestos, total, cufe, estado_dian, fecha_emision)
            VALUES (%s, %s, %s, %s, %s, %s, 'EMITIDA', NOW())
        ''', (id_paciente, id_atencion, subtotal, impuestos, total, cufe))
        
        registrar_auditoria(cursor, session['usuario_id'], 'FACTURACION', f'Factura FEV generada para paciente ID {id_paciente}')
        conn.commit()
        cursor.close()
        flash("Factura electrónica registrada con éxito.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al registrar factura: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('facturacion.facturacion'))
