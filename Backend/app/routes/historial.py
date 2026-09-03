from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import psycopg2
import psycopg2.extras
from app.utils import get_db_connection

historial_bp = Blueprint('historial', __name__, url_prefix='/historial')

@historial_bp.route('/buscar', methods=['GET'])
def buscar():
    busqueda = request.args.get('busqueda', '').strip()
    paciente_id = request.args.get('paciente_id')
    
    paciente = None
    atencion = None
    notas = []

    if not busqueda and not paciente_id:
        return render_template('historial.html', paciente=None)

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # Buscar Paciente por ID o por Cédula / Nombre
        if paciente_id:
            cursor.execute("SELECT * FROM pacientes WHERE id_paciente = %s", (paciente_id,))
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
            # Consultar la última atención del paciente
            cursor.execute("""
                SELECT id_atencion FROM atenciones 
                WHERE id_paciente = %s 
                ORDER BY fecha_atencion DESC LIMIT 1
            """, (paciente['id_paciente'],))
            atencion = cursor.fetchone()

            # Consultar Historial de Notas Clínicas
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
                WHERE a.id_paciente = %s
                ORDER BY n.fecha_registro DESC
            """
            cursor.execute(query_notas, (paciente['id_paciente'],))
            notas = cursor.fetchall()

    except Exception as e:
        flash(f"Error en la base de datos: {str(e)}", "danger")
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


@historial_bp.route('/guardar_nota', methods=['POST'])
def guardar_nota():
    id_medico = session.get('id_usuario') or session.get('user_id')
    id_paciente = request.form.get('id_paciente')
    id_atencion = request.form.get('id_atencion')
    tipo_nota = request.form.get('tipo_nota')
    subjetivo = request.form.get('subjetivo')
    objetivo = request.form.get('objetivo')
    analisis = request.form.get('analisis')
    plan = request.form.get('plan')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Si el paciente no tiene atención activa previa, se crea una automáticamente
        if not id_atencion or id_atencion == 'None' or id_atencion == '':
            cursor.execute("""
                INSERT INTO atenciones (id_paciente, id_medico, estado) 
                VALUES (%s, %s, 'En Proceso') RETURNING id_atencion
            """, (id_paciente, id_medico))
            id_atencion = cursor.fetchone()[0]

        # Guardar en la tabla notas_clinicas
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
        flash(f"Error al guardar la nota: {str(e)}", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('historial.buscar', paciente_id=id_paciente))