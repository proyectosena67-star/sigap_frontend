import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from flask import Flask, g

# Variable global para administrar el pool de conexiones de PostgreSQL
db_pool = None

def create_app():
    global db_pool
    
    # 1. Determinar el directorio base del proyecto
    # __file__ está dentro de: .../sigap_frontend/Backend/app/__init__.py
    app_dir = os.path.dirname(os.path.abspath(__file__))               # Backend/app
    backend_dir = os.path.abspath(os.path.join(app_dir, '..'))          # Backend
    project_root = os.path.abspath(os.path.join(backend_dir, '..'))     # sigap_frontend

    # Definir rutas posibles para las plantillas (Frontend/templates o Backend/templates)
    frontend_templates = os.path.join(project_root, 'Frontend', 'templates')
    backend_templates = os.path.join(backend_dir, 'templates')
    
    # Seleccionar la carpeta de plantillas que realmente exista en el sistema
    if os.path.exists(frontend_templates):
        template_dir = frontend_templates
    elif os.path.exists(backend_templates):
        template_dir = backend_templates
    else:
        template_dir = frontend_templates

    # Definir carpeta de archivos estáticos (Frontend/static o Backend/static)
    frontend_static = os.path.join(project_root, 'Frontend', 'static')
    backend_static = os.path.join(backend_dir, 'static')
    static_dir = frontend_static if os.path.exists(frontend_static) else backend_static

    print(f"-> Cargando plantillas desde: {template_dir}")
    print(f"-> Cargando estáticos desde:   {static_dir}")

    # Configurar Flask con las rutas validadas
    app = Flask(
        __name__, 
        template_folder=template_dir,
        static_folder=static_dir
    )
                
    # Clave secreta para manejo de sesiones y alertas flash
    app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_sigap_proyecto_2026')

    # Parámetros de conexión a la base de datos PostgreSQL
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_NAME = os.environ.get("DB_NAME", "sigam_db")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASS = os.environ.get("DB_PASS", "1234")
    DB_PORT = os.environ.get("DB_PORT", "5432")

    # Inicialización del pool usando ThreadedConnectionPool para soportar múltiples hilos/peticiones
    try:
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            1, 20,
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            cursor_factory=RealDictCursor
        )
        print("-> Conexión a PostgreSQL (sigam_db) inicializada correctamente.")
    except Exception as e:
        print(f"Error crítico al conectar con PostgreSQL: {e}")
        db_pool = None

    # Teardown seguro: solo devuelve la conexión si se solicitó en 'g' y no ha sido liberada aún
    @app.teardown_appcontext
    def close_db_connection(exception=None):
        conn = g.pop('db_conn', None)
        if conn is not None and db_pool is not None and not conn.closed:
            try:
                db_pool.putconn(conn)
            except psycopg2.pool.PoolError:
                pass  # Previene excepciones si la conexión ya fue retornada manualmente

    # Importación de los Blueprints (rutas modulares de S.I.G.A.P.)
    from app.routes.auth import auth_bp
    from app.routes.pacientes import pacientes_bp
    from app.routes.citas import citas_bp
    from app.routes.medicamentos import medicamentos_bp
    from app.routes.evaluaciones import evaluaciones_bp
    from app.routes.auditoria import auditoria_bp
    from app.routes.usuarios import usuarios_bp

    from app.routes.facturacion import facturacion_bp
    from app.routes.triaje import triaje_bp
    from app.routes.quirurgico import quirurgico_bp
    from app.routes.vacunacion import vacunacion_bp
    from app.routes.equipos import equipos_bp

    # Registro de los Blueprints en la aplicación Flask
    app.register_blueprint(auth_bp)
    app.register_blueprint(pacientes_bp)
    app.register_blueprint(citas_bp)
    app.register_blueprint(medicamentos_bp)
    app.register_blueprint(evaluaciones_bp)
    app.register_blueprint(auditoria_bp)
    app.register_blueprint(usuarios_bp)
    
    app.register_blueprint(facturacion_bp)
    app.register_blueprint(triaje_bp)
    app.register_blueprint(quirurgico_bp)
    app.register_blueprint(vacunacion_bp)
    app.register_blueprint(equipos_bp)

    return app


def get_db_connection():
    """
    Obtiene una conexión activa desde el pool de conexiones y la asocia al contexto de la petición 'g'.
    """
    if 'db_conn' not in g or g.db_conn.closed:
        if db_pool:
            g.db_conn = db_pool.getconn()
        else:
            raise Exception("Piscina de conexiones a la base de datos no disponible.")
    return g.db_conn


def release_db_connection(conn=None):
    """
    Devuelve manualmente la conexión al pool si una ruta la libera antes del cierre del request.
    """
    if conn and db_pool and not conn.closed:
        try:
            db_pool.putconn(conn)
            if hasattr(g, 'db_conn') and g.db_conn == conn:
                g.db_conn = None
        except psycopg2.pool.PoolError:
            pass