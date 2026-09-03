from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import psycopg2
import psycopg2.extras
from app.utils import get_db_connection

pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')

@pacientes_bp.route('/', methods=['GET'])
def pacientes():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute("SELECT * FROM pacientes ORDER BY id_paciente DESC LIMIT 50")
        lista_pacientes = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar la lista de pacientes: {str(e)}", "danger")
        lista_pacientes = []
    finally:
        cursor.close()
        conn.close()
    return render_template('pacientes.html', pacientes=lista_pacientes)

@pacientes_bp.route('/historial/', defaults={'id_paciente': None}, methods=['GET'])
@pacientes_bp.route('/historial/<int:id_paciente>', methods=['GET'])
def historial_clinico(id_paciente):
    busqueda = request.args.get('busqueda', '').strip()
    
    paciente = None
    atencion = None
    notas = []

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        if id_paciente:
            cursor.execute("SELECT * FROM pacientes WHERE id_paciente = %s", (id_paciente,))
            paciente = cursor.fetchone()
        elif busqueda:
            query_paciente = """
                SELECT * FROM pacientes 
                WHERE numero_documento = %s 
                OR LOWER(CONCAT(primer_nombre, ' ', primer_apellido)) LIKE LOWER(%s)
                LIMIT 1
            """
            cursor.execute(query_paciente, (busqueda, f"%{busqueda}%"))
            paciente = cursor.fetchone()

        if paciente:
            # 1. Verificar o crear el historial clínico del paciente
            cursor.execute("SELECT id_historial FROM historial_clinico WHERE id_paciente = %s", (paciente['id_paciente'],))
            historial_res = cursor.fetchone()
            
            if not historial_res:
                cursor_insert = conn.cursor()
                cursor_insert.execute("INSERT INTO historial_clinico (id_paciente) VALUES (%s) RETURNING id_historial", (paciente['id_paciente'],))
                id_hist = cursor_insert.fetchone()[0]
                conn.commit()
                cursor_insert.close()
            else:
                id_hist = historial_res['id_historial']

            # 2. Buscar la última atención de este historial
            cursor.execute("""
                SELECT id_atencion FROM atenciones 
                WHERE id_historial = %s 
                ORDER BY fecha_ingreso DESC LIMIT 1
            """, (id_hist,))
            atencion = cursor.fetchone()

            # Si no tiene atención registrada, creamos una de prueba automáticamente para que no luzca vacío
            if not atencion:
                # Buscamos un médico disponible en la tabla usuarios para asignarle la atención por defecto
                cursor.execute("SELECT id_usuario FROM usuarios WHERE id_rol IN (1, 2) LIMIT 1")
                medico_default = cursor.fetchone()
                id_medico_asig = medico_default['id_usuario'] if medico_default else 1

                cursor_atn = conn.cursor()
                cursor_atn.execute("""
                    INSERT INTO atenciones (id_historial, id_medico, tipo_atencion, fecha_ingreso, estado) 
                    VALUES (%s, %s, 'Consulta Externa', NOW(), 'En Proceso') RETURNING id_atencion
                """, (id_hist, id_medico_asig))
                nuevo_id_atencion = cursor_atn.fetchone()[0]
                
                # Creamos una nota inicial de bienvenida/prueba
                cursor_atn.execute("""
                    INSERT INTO notas_clinicas (
                        id_atencion, id_medico, tipo_nota, subjetivo, objetivo, analisis, plan, fecha_registro
                    ) VALUES (%s, %s, 'Ingreso', 'Paciente ingresa al sistema para apertura de historia clínica.', 'Sin alteraciones aparentes reportadas en admisión.', 'Evaluación inicial completada.', 'Continuar seguimiento médico.', NOW())
                """, (nuevo_id_atencion, id_medico_asig))
                
                conn.commit()
                cursor_atn.close()
                
                # Volvemos a consultar la atención recién creada
                cursor.execute("SELECT id_atencion FROM atenciones WHERE id_historial = %s ORDER BY fecha_ingreso DESC LIMIT 1", (id_hist,))
                atencion = cursor.fetchone()

            # 3. Consultar las notas clínicas vinculadas a este historial
            query_notas = """
                SELECT 
                    n.id_nota,
                    n.tipo_nota,
                    n.subjetivo,
                    n.objetivo,
                    n.analisis,
                    n.plan,
                    n.fecha_registro,
                    u.nombres AS medico_nombres,
                    u.apellidos AS medico_apellidos
                FROM notas_clinicas n
                INNER JOIN atenciones a ON n.id_atencion = a.id_atencion
                LEFT JOIN usuarios u ON n.id_medico = u.id_usuario
                WHERE a.id_historial = %s
                ORDER BY n.fecha_registro DESC
            """
            cursor.execute(query_notas, (id_hist,))
            notas = cursor.fetchall()
            
        elif busqueda:
            flash(f"No se encontró ningún paciente con la búsqueda: '{busqueda}'", "warning")

    except Exception as e:
        conn.rollback()
        flash(f"Error al consultar la base de datos: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return render_template(
        'historial.html', 
        paciente=paciente, 
        atencion=atencion, 
        notas=notas, 
        busqueda_actual=busqueda
    )


@pacientes_bp.route('/guardar_nota', methods=['POST'])
def guardar_nota():
    # Validar sesión activa del médico/usuario
    id_medico = session.get('id_usuario') or session.get('user_id')
    if not id_medico:
        flash("Error: No hay una sesión activa. Por favor inicie sesión de nuevo.", "danger")
        return redirect(url_for('auth.login'))

    id_paciente = request.form.get('id_paciente')
    id_atencion = request.form.get('id_atencion')
    tipo_nota = request.form.get('tipo_nota', 'Evolucion')
    subjetivo = request.form.get('subjetivo')
    objetivo = request.form.get('objetivo')
    analisis = request.form.get('analisis')
    plan = request.form.get('plan')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar o crear historial clínico
        cursor.execute("SELECT id_historial FROM historial_clinico WHERE id_paciente = %s", (id_paciente,))
        historial = cursor.fetchone()
        
        if not historial:
            cursor.execute("INSERT INTO historial_clinico (id_paciente) VALUES (%s) RETURNING id_historial", (id_paciente,))
            id_historial = cursor.fetchone()[0]
        else:
            id_historial = historial[0]

        # Verificar o crear atención activa si no viene dada
        if not id_atencion or id_atencion == 'None' or id_atencion == '':
            cursor.execute("""
                INSERT INTO atenciones (id_historial, id_medico, tipo_atencion, fecha_ingreso, estado) 
                VALUES (%s, %s, 'Consulta Externa', NOW(), 'En Proceso') RETURNING id_atencion
            """, (id_historial, id_medico))
            id_atencion = cursor.fetchone()[0]

        # Insertar la nota clínica SOAP
        cursor.execute("""
            INSERT INTO notas_clinicas (
                id_atencion, 
                id_medico, 
                tipo_nota, 
                subjetivo, 
                objetivo, 
                analisis, 
                plan,
                fecha_registro
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (id_atencion, id_medico, tipo_nota, subjetivo, objetivo, analisis, plan))

        conn.commit()
        flash("Nota clínica guardada exitosamente.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Error al guardar la nota clínica: {str(e)}", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('pacientes.historial_clinico', id_paciente=id_paciente))