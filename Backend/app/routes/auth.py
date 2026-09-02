from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from app import get_db_connection, release_db_connection
from app.utils import registrar_auditoria

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    # 1. Si el usuario ya tiene sesión activa, lo redirigimos directamente a pacientes
    if request.method == 'GET' and 'usuario_id' in session:
        return redirect(url_for('pacientes.pacientes'))

    if request.method == 'POST':
        correo_ingresado = (request.form.get('correo') or request.form.get('email') or '').strip()
        password_ingresada = (request.form.get('password') or request.form.get('clave') or '').strip()
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.*, r.nombre AS rol_nombre 
                FROM usuarios u
                JOIN roles r ON u.id_rol = r.id_rol
                WHERE LOWER(u.correo) = LOWER(%s)
            ''', (correo_ingresado,))
            usuario = cursor.fetchone()

            if usuario is None:
                flash("El correo institucional no se encuentra registrado.", "danger")
            else:
                clave_bd = (usuario.get('password_hash') or '').strip()
                es_valida = (clave_bd == password_ingresada) or check_password_hash(clave_bd, password_ingresada)
                
                if not es_valida:
                    flash("La contraseña ingresada es incorrecta.", "danger")
                else:
                    session['usuario_id'] = usuario['id_usuario']
                    session['nombre'] = f"{usuario['nombres']} {usuario['apellidos']}"
                    session['rol_id'] = usuario['id_rol']
                    session['rol_nombre'] = usuario['rol_nombre']
                    
                    registrar_auditoria(cursor, usuario['id_usuario'], 'LOGIN', 'Inicio de sesión exitoso al sistema.')
                    conn.commit()
                    cursor.close()
                    # 2. Redirección al inicio de sesión exitoso corregida
                    return redirect(url_for('pacientes.pacientes'))
            cursor.close()
        except Exception as e:
            if conn: 
                conn.rollback()
            flash(f"Error al verificar credenciales: {str(e)}", "danger")
        finally:
            if conn: 
                release_db_connection(conn)

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for('auth.login'))