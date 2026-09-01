from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required, registrar_auditoria

pacientes_bp = Blueprint('pacientes', __name__)

@pacientes_bp.route('/historial', methods=['GET'])
@login_required
def historial():
    paciente_id = request.args.get('paciente_id', type=int)
    busqueda = request.args.get('busqueda', '').strip()
    registros_historial = []
    paciente_info = None
    lista_pacientes = []
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if busqueda:
            cursor.execute('''
                SELECT id_paciente, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, numero_documento 
                FROM pacientes 
                WHERE CONCAT_WS(' ', primer_nombre, segundo_nombre, primer_apellido, segundo_apellido) ILIKE %s 
                   OR numero_documento ILIKE %s
                ORDER BY primer_apellido ASC
            ''', (f"%{busqueda}%", f"%{busqueda}%"))
        else:
            cursor.execute("SELECT id_paciente, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, numero_documento FROM pacientes ORDER BY primer_apellido ASC LIMIT 50")
            
        lista_pacientes = cursor.fetchall()

        if paciente_id:
            cursor.execute('''
                SELECT p.*, a.nombre AS aseguradora_nombre, h.id_historial
                FROM pacientes p
                LEFT JOIN aseguradoras a ON p.id_aseguradora = a.id_aseguradora
                LEFT JOIN historial_clinico h ON p.id_paciente = h.id_paciente
                WHERE p.id_paciente = %s
            ''', (paciente_id,))
        elif lista_pacientes:
            cursor.execute('''
                SELECT p.*, a.nombre AS aseguradora_nombre, h.id_historial
                FROM pacientes p
                LEFT JOIN aseguradoras a ON p.id_aseguradora = a.id_aseguradora
                LEFT JOIN historial_clinico h ON p.id_paciente = h.id_paciente
                WHERE p.id_paciente = %s
            ''', (lista_pacientes[0]['id_paciente'],))
        
        paciente_info = cursor.fetchone()

        if paciente_info and paciente_info.get('id_historial'):
            cursor.execute('''
                SELECT n.id_nota, n.subjetivo, n.objetivo, n.analisis, n.plan, n.fecha_registro,
                       n.tipo_nota, u.nombres AS autor_nombre, u.apellidos AS autor_apellido, r.nombre AS rol_autor
                FROM notas_clinicas n
                JOIN atenciones at ON n.id_atencion = at.id_atencion
                JOIN usuarios u ON n.id_medico = u.id_usuario
                JOIN roles r ON u.id_rol = r.id_rol
                WHERE at.id_historial = %s
                ORDER BY n.id_nota DESC
            ''', (paciente_info['id_historial'],))
            registros_historial = cursor.fetchall()

        cursor.close()
    except Exception as e:
        flash(f"Error al cargar el historial clínico: {str(e)}", "warning")
    finally:
        if conn: release_db_connection(conn)

    return render_template('historial.html', 
                           historial=registros_historial, 
                           paciente=paciente_info, 
                           pacientes=lista_pacientes)

@pacientes_bp.route('/guardar_paciente', methods=['POST'])
@login_required
@role_required(['Medico', 'Administrador', 'Enfermera'])
def guardar_paciente():
    tipo_doc = request.form.get('tipo_documento')
    num_doc = request.form.get('numero_documento')
    primer_nombre = request.form.get('primer_nombre')
    segundo_nombre = request.form.get('segundo_nombre', '')
    primer_apellido = request.form.get('primer_apellido')
    segundo_apellido = request.form.get('segundo_apellido', '')
    fecha_nacimiento = request.form.get('fecha_nacimiento')
    genero = request.form.get('genero')
    id_aseguradora = request.form.get('id_aseguradora', 1)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO pacientes (tipo_documento, numero_documento, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, fecha_nacimiento, genero, id_aseguradora)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_paciente
        ''', (tipo_doc, num_doc, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, fecha_nacimiento, genero, id_aseguradora))
        
        nuevo_paciente = cursor.fetchone()
        
        cursor.execute('''
            INSERT INTO historial_clinico (id_paciente, fecha_apertura)
            VALUES (%s, NOW())
        ''', (nuevo_paciente['id_paciente'],))

        registrar_auditoria(cursor, session['usuario_id'], 'INSERT_PACIENTE', f'Registro de paciente ID: {nuevo_paciente["id_paciente"]}')
        conn.commit()
        cursor.close()
        flash("Paciente e historial clínico registrados con éxito.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al registrar paciente: {str(e)}", "danger")
    finally:
        if conn: release_db_connection(conn)

    return redirect(url_for('pacientes.historial'))

@pacientes_bp.route('/guardar_nota', methods=['POST'])
@login_required
@role_required(['Medico', 'Psicologo'])
def guardar_nota():
    subjetivo = request.form.get('subjetivo', '').strip()
    objetivo = request.form.get('objetivo', '').strip() or 'Sin novedades en examen físico'
    analisis = request.form.get('analisis', '').strip() or 'Evolución clínica estándar'
    plan = request.form.get('plan', '').strip() or 'Continuar manejo'
    tipo_nota = request.form.get('tipo_nota', 'Evolución')
    id_atencion = request.form.get('id_atencion', 1)

    if subjetivo:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO notas_clinicas (id_atencion, id_medico, tipo_nota, subjetivo, objetivo, analisis, plan, fecha_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ''', (id_atencion, session['usuario_id'], tipo_nota, subjetivo, objetivo, analisis, plan))
            
            registrar_auditoria(cursor, session['usuario_id'], 'INSERT_NOTA', f'Nota médica registrada para atención ID: {id_atencion}')
            conn.commit()
            cursor.close()
            flash("Nota médica registrada correctamente.", "success")
        except Exception as e:
            if conn: conn.rollback()
            flash(f"Error al registrar la nota clínica: {str(e)}", "danger")
        finally:
            if conn: release_db_connection(conn)

    return redirect(url_for('pacientes.historial'))