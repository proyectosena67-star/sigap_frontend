from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import get_db_connection, release_db_connection
from app.utils import login_required, role_required

usuarios_bp = Blueprint('usuarios', __name__)

@usuarios_bp.route('/usuarios', methods=['GET'])
@login_required
# @role_required(['Administración'])  # Comentado temporalmente para descartar bloqueos de rol
def listar_usuarios():
    conn = None
    usuarios = []
    search_query = request.args.get('q', '').strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if search_query:
            query = '''
                SELECT 
                    u.id_usuario, 
                    COALESCE(u.documento, '') AS cedula, 
                    COALESCE(u.tipo_documento, 'CC') AS tipo_documento,
                    u.nombres, 
                    u.apellidos, 
                    u.correo, 
                    COALESCE(r.nombre, 'Sin Rol') AS rol_nombre, 
                    COALESCE(u.estado, 'activo') AS estado
                FROM usuarios u
                LEFT JOIN roles r ON u.id_rol = r.id_rol
                WHERE u.nombres ILIKE %s 
                   OR u.apellidos ILIKE %s 
                   OR u.correo ILIKE %s
                   OR u.documento ILIKE %s
                ORDER BY u.id_usuario DESC
            '''
            pattern = f"%{search_query}%"
            cursor.execute(query, (pattern, pattern, pattern, pattern))
        else:
            query = '''
                SELECT 
                    u.id_usuario, 
                    COALESCE(u.documento, '') AS cedula, 
                    COALESCE(u.tipo_documento, 'CC') AS tipo_documento,
                    u.nombres, 
                    u.apellidos, 
                    u.correo, 
                    COALESCE(r.nombre, 'Sin Rol') AS rol_nombre, 
                    COALESCE(u.estado, 'activo') AS estado
                FROM usuarios u
                LEFT JOIN roles r ON u.id_rol = r.id_rol
                ORDER BY u.id_usuario DESC
            '''
            cursor.execute(query)
            
        usuarios = cursor.fetchall()
        cursor.close()

        print(f"--> [DEBUG sigam_db] Registros de usuarios obtenidos: {len(usuarios)}")
    except Exception as e:
        print(f"--> [ERROR PostgreSQL - usuarios.py]: {str(e)}")
        flash(f"Error al conectar con la base de datos: {str(e)}", "danger")
    finally:
        if conn:
            release_db_connection(conn)

    return render_template('usuarios.html', usuarios=usuarios, search_query=search_query)


@usuarios_bp.route('/usuarios/crear', methods=['POST'])
@login_required
# @role_required(['Administración'])  # Comentado temporalmente para descartar bloqueos de rol
def crear_usuario():
    conn = None
    try:
        nombres = request.form.get('nombres')
        apellidos = request.form.get('apellidos')
        documento = request.form.get('cedula')
        tipo_documento = request.form.get('tipo_documento', 'CC')
        correo = request.form.get('correo')
        password = request.form.get('password') 
        id_rol = request.form.get('id_rol', 1)

        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            INSERT INTO usuarios (tipo_documento, documento, nombres, apellidos, correo, password_hash, id_rol, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'activo')
        '''
        cursor.execute(query, (tipo_documento, documento, nombres, apellidos, correo, password, id_rol))
        conn.commit()
        cursor.close()

        flash("Usuario registrado exitosamente en el sistema.", "success")
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"--> [ERROR al crear usuario]: {str(e)}")
        flash(f"Error al registrar usuario: {str(e)}", "danger")
    finally:
        if conn:
            release_db_connection(conn)

    return redirect(url_for('usuarios.listar_usuarios'))