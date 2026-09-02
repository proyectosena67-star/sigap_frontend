from flask import Blueprint, render_template, request, flash
from app import get_db_connection, release_db_connection

pacientes_bp = Blueprint('pacientes', __name__)

@pacientes_bp.route('/pacientes', methods=['GET'])
def pacientes():
    # 1. Parámetros de búsqueda y filtrado desde la URL
    search_query = request.args.get('q', '').strip()
    filtro_estado = request.args.get('estado', 'todos').lower()
    id_seleccionado = request.args.get('id', type=int)
    
    pacientes = []
    paciente_activo = None
    total_registrados = 0
    total_hospitalizados = 0
    ultimo_ingreso = None

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 2. Consulta principal ajustada al esquema sigam_db
            query_sql = """
                SELECT 
                    p.id_paciente, 
                    p.tipo_documento, 
                    p.numero_documento, 
                    p.primer_nombre,
                    p.primer_apellido,
                    TRIM(CONCAT(p.primer_nombre, ' ', p.segundo_nombre, ' ', p.primer_apellido, ' ', p.segundo_apellido)) AS nombre,
                    CASE 
                        WHEN p.fecha_nacimiento IS NOT NULL 
                        THEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, p.fecha_nacimiento))::INT 
                        ELSE NULL 
                    END AS edad,
                    p.sexo_biologico AS genero, 
                    
                    -- Estado dinámico según atenciones activas
                    CASE 
                        WHEN a_hosp.id_atencion IS NOT NULL THEN 'Hospitalizado'
                        WHEN p.estado IS NOT NULL AND p.estado != '' THEN p.estado
                        ELSE 'Alta'
                    END AS estado,
                    
                    -- Último diagnóstico registrado en la tabla diagnosticos
                    COALESCE(d.descripcion, 'Sin diagnóstico') AS diagnostico,
                    p.fecha_registro
                FROM pacientes p
                
                -- Verificar si el paciente está actualmente en hospitalización (En Proceso)
                LEFT JOIN LATERAL (
                    SELECT a.id_atencion 
                    FROM historial_clinico hc
                    JOIN atenciones a ON hc.id_historial = a.id_historial
                    WHERE hc.id_paciente = p.id_paciente 
                      AND a.tipo_atencion = 'Hospitalizacion'
                      AND a.estado = 'En Proceso'
                    ORDER BY a.id_atencion DESC
                    LIMIT 1
                ) a_hosp ON TRUE
                
                -- Obtener el diagnóstico de la última atención registrada
                LEFT JOIN LATERAL (
                    SELECT diag.descripcion 
                    FROM historial_clinico hc
                    JOIN atenciones a ON hc.id_historial = a.id_historial
                    JOIN diagnosticos diag ON a.id_atencion = diag.id_atencion
                    WHERE hc.id_paciente = p.id_paciente
                    ORDER BY a.id_atencion DESC, diag.id_diagnostico DESC
                    LIMIT 1
                ) d ON TRUE
                
                WHERE 1=1
            """
            params = []

            # Filtro de búsqueda por nombre, apellido o número de documento
            if search_query:
                query_sql += """
                    AND (
                        p.primer_nombre ILIKE %s OR 
                        p.primer_apellido ILIKE %s OR 
                        p.numero_documento ILIKE %s
                    )
                """
                pattern = f"%{search_query}%"
                params.extend([pattern, pattern, pattern])

            # Filtro según la pestaña activa
            if filtro_estado == 'hospitalizados':
                query_sql += " AND a_hosp.id_atencion IS NOT NULL"
            elif filtro_estado == 'alta':
                query_sql += " AND a_hosp.id_atencion IS NULL"

            query_sql += " ORDER BY p.id_paciente DESC;"
            cur.execute(query_sql, tuple(params))
            pacientes = cur.fetchall()

            # 3. Obtener el paciente activo (si se pasa un id o el primero de la lista)
            if id_seleccionado:
                cur.execute("SELECT * FROM pacientes WHERE id_paciente = %s;", (id_seleccionado,))
                paciente_activo = cur.fetchone()
            elif pacientes:
                paciente_activo = pacientes[0]

            # 4. Indicadores para el panel lateral
            # Total de pacientes en la base de datos
            cur.execute("SELECT COUNT(*) AS total FROM pacientes;")
            res_total = cur.fetchone()
            total_registrados = res_total['total'] if res_total else 0

            # Pacientes con hospitalización abierta en atenciones
            cur.execute("""
                SELECT COUNT(DISTINCT hc.id_paciente) AS total 
                FROM historial_clinico hc
                JOIN atenciones a ON hc.id_historial = a.id_historial
                WHERE a.tipo_atencion = 'Hospitalizacion' 
                  AND a.estado = 'En Proceso';
            """)
            res_hosp = cur.fetchone()
            total_hospitalizados = res_hosp['total'] if res_hosp else 0

            # Detalle del último ingreso de atención
            cur.execute("""
                SELECT p.primer_nombre, p.primer_apellido, a.fecha_ingreso 
                FROM atenciones a
                JOIN historial_clinico hc ON a.id_historial = hc.id_historial
                JOIN pacientes p ON hc.id_paciente = p.id_paciente
                ORDER BY a.id_atencion DESC LIMIT 1;
            """)
            res_ultimo = cur.fetchone()
            if res_ultimo and res_ultimo.get('fecha_ingreso'):
                fecha_raw = res_ultimo['fecha_ingreso']
                fecha_str = fecha_raw.strftime('%Y-%m-%d') if hasattr(fecha_raw, 'strftime') else str(fecha_raw)
                ultimo_ingreso = f"{res_ultimo['primer_nombre']} {res_ultimo['primer_apellido']} ({fecha_str})"

    except Exception as e:
        print(f"Error al consultar pacientes en PostgreSQL: {e}")
        flash("Ocurrió un error al consultar la información de pacientes.", "danger")
    finally:
        if conn:
            release_db_connection(conn)

    # 5. Renderizado final
    return render_template(
        'pacientes.html',
        pacientes=pacientes,
        paciente_activo=paciente_activo,
        search_query=search_query,
        filtro_estado=filtro_estado,
        total_registrados=total_registrados,
        total_hospitalizados=total_hospitalizados,
        ultimo_ingreso=ultimo_ingreso
    )