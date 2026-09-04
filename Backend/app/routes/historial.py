# Backend/app/routes/historial.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import psycopg2
import psycopg2.extras
from app.utils import get_db_connection

historial_bp = Blueprint('historial', __name__, url_prefix='/pacientes/historial')

@historial_bp.route('/<int:paciente_id>', methods=['GET'])
def historial_clinico(paciente_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    paciente = None
    atencion = None
    notas = []

    try:
        cursor.execute("SELECT * FROM pacientes WHERE id_paciente = %s", (paciente_id,))
        paciente = cursor.fetchone()

        if paciente:
            cursor.execute("""
                SELECT id_atencion FROM atenciones 
                WHERE id_paciente = %s 
                ORDER BY fecha_atencion DESC LIMIT 1
            """, (paciente_id,))
            atencion = cursor.fetchone()

            query_notas = """
                SELECT 
                    n.id_nota,
                    n.tipo_nota,
                    n.subjetivo,
                    n.objetivo,
                    n.analisis,
                    n.plan,
                    n.fecha_registro,
                    u.primer_nombre AS medico_nombres,
                    u.primer_apellido AS medico_apellidos,
                    u.rol AS medico_rol
                FROM notas_clinicas n
                LEFT JOIN atenciones a ON n.id_atencion = a.id_atencion
                LEFT JOIN usuarios u ON n.id_medico = u.id_usuario
                WHERE n.id_paciente = %s OR a.id_paciente = %s
                ORDER BY n.fecha_registro DESC
            """
            cursor.execute(query_notas, (paciente_id, paciente_id))
            notas = cursor.fetchall()

    except Exception as e:
        print(f"--> Error al cargar historial clínico: {e}")
        flash(f"Error en la base de datos: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return render_template(
        'historial.html',
        paciente=paciente,
        atencion=atencion,
        notas=notas,
        busqueda_actual=str(paciente_id)
    )


@historial_bp.route('/buscar', methods=['GET'])
def buscar():
    busqueda = request.args.get('busqueda', '').strip()
    if not busqueda:
        return redirect(url_for('historial.historial_clinico', paciente_id=1))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute("""
            SELECT id_paciente FROM pacientes 
            WHERE numero_documento = %s OR LOWER(CONCAT(primer_nombre, ' ', primer_apellido)) LIKE LOWER(%s)
            LIMIT 1
        """, (busqueda, f"%{busqueda}%"))
        paciente = cursor.fetchone()
        
        if paciente:
            return redirect(url_for('historial.historial_clinico', paciente_id=paciente['id_paciente']))
        else:
            flash("Paciente no encontrado.", "warning")
    except Exception as e:
        print(f"--> Error en búsqueda: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('historial.historial_clinico', paciente_id=1))


@historial_bp.route('/guardar_nota', methods=['POST'])
def guardar_nota():
    id_medico = session.get('id_usuario') or session.get('user_id')
    id_paciente = request.form.get('id_paciente')
    id_atencion = request.form.get('id_atencion')
    tipo_nota = request.form.get('tipo_nota', 'Evolución')
    
    subjetivo = request.form.get('subjetivo') or request.form.get('nota_texto')
    objetivo = request.form.get('objetivo')
    analisis = request.form.get('analisis')
    plan = request.form.get('plan')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if not id_atencion or id_atencion == 'None' or id_atencion == '':
            cursor.execute("""
                INSERT INTO atenciones (id_paciente, id_medico, estado) 
                VALUES (%s, %s, 'En Proceso') RETURNING id_atencion
            """, (id_paciente, id_medico))
            id_atencion = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO notas_clinicas (
                id_paciente,
                id_atencion, 
                id_medico, 
                tipo_nota, 
                subjetivo, 
                objetivo, 
                analisis, 
                plan,
                fecha_registro
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (id_paciente, id_atencion, id_medico, tipo_nota, subjetivo, objetivo, analisis, plan))

        conn.commit()
        flash("Nota clínica guardada exitosamente.", "success")

    except Exception as e:
        conn.rollback()
        print(f"--> Error al guardar la nota: {e}")
        flash(f"Error al guardar la nota: {str(e)}", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('historial.historial_clinico', paciente_id=id_paciente))