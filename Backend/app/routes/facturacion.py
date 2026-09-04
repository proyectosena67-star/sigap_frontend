from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import get_db_connection, release_db_connection

facturacion_bp = Blueprint('facturacion', __name__)

@facturacion_bp.route('/facturacion', methods=['GET'])
def facturacion():
    conn = get_db_connection()
    cursor = conn.cursor()
    facturas = []
    
    try:
        # Incluye absolutamente todas las combinaciones posibles de nombres de variables para el HTML
        cursor.execute("""
            SELECT 
                f.id_factura, 
                f.prefijo, 
                f.numero_factura, 
                COALESCE(CONCAT(p.primer_nombre, ' ', p.primer_apellido), 'Paciente No Registrado') AS paciente,
                COALESCE(CONCAT(p.primer_nombre, ' ', p.primer_apellido), 'Paciente No Registrado') AS paciente_nombre,
                COALESCE(CONCAT(p.primer_nombre, ' ', p.primer_apellido), 'Paciente No Registrado') AS nombre_paciente,
                COALESCE(CONCAT(p.primer_nombre, ' ', p.primer_apellido), 'Paciente No Registrado') AS nombre,
                COALESCE(CONCAT(p.primer_nombre, ' ', p.primer_apellido), 'Paciente No Registrado') AS nombres,
                COALESCE(CONCAT(p.primer_nombre, ' ', p.primer_apellido), 'Paciente No Registrado') AS nombre_completo,
                COALESCE(p.numero_documento, 'N/A') AS documento,
                COALESCE(p.numero_documento, 'N/A') AS numero_documento,
                f.subtotal, 
                0.00 AS impuestos,
                f.valor_total AS total,
                f.valor_total AS valor_total,
                f.estado_factura AS estado_dian,
                f.estado_factura AS estado_factura,
                f.fecha_emision
            FROM facturas f
            LEFT JOIN pacientes p ON f.id_paciente = p.id_paciente
            ORDER BY f.id_factura DESC;
        """)
        facturas = cursor.fetchall()
    except Exception as e:
        print(f"--> Error al obtener las facturas: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('facturacion.html', facturas=facturas)

@facturacion_bp.route('/facturacion/nueva', methods=['GET', 'POST'])
def guardar_factura():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            id_paciente = request.form.get('id_paciente')
            subtotal = request.form.get('subtotal', 0)
            valor_total = request.form.get('valor_total', 0)
            estado_factura = 'Generada'
            
            cursor.execute("""
                INSERT INTO facturas (id_paciente, id_atencion, subtotal, valor_total, estado_factura, numero_factura)
                VALUES (%s, 1, %s, %s, %s, (SELECT COALESCE(MAX(numero_factura), 1000) + 1 FROM facturas))
            """, (id_paciente, subtotal, valor_total, estado_factura))
            
            conn.commit()
            flash('Factura creada exitosamente.', 'success')
            return redirect(url_for('facturacion.facturacion'))
        except Exception as e:
            conn.rollback()
            print(f"--> Error al registrar factura: {e}")
            flash('Error al guardar la factura en la base de datos.', 'danger')
        finally:
            cursor.close()
            release_db_connection(conn)
            
    pacientes = []
    try:
        cursor.execute("SELECT id_paciente, CONCAT(primer_nombre, ' ', primer_apellido) AS nombre FROM pacientes ORDER BY id_paciente ASC;")
        pacientes = cursor.fetchall()
    except Exception as e:
        print(f"--> Error al cargar pacientes para nueva factura: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('nueva_factura.html', pacientes=pacientes)

@facturacion_bp.route('/facturacion/crear', methods=['GET'])
def nueva_factura():
    return guardar_factura()