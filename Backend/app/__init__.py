import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from flask import Flask

db_pool = None

def create_app():
    global db_pool
    
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app = Flask(__name__, 
                template_folder=os.path.join(base_dir, 'templates'),
                static_folder=os.path.join(base_dir, 'static'))
                
    app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_sigap_proyecto_2026')

    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_NAME = os.environ.get("DB_NAME", "sigam_db")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASS = os.environ.get("DB_PASS", "1234")
    DB_PORT = os.environ.get("DB_PORT", "5432")

    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT,
            cursor_factory=RealDictCursor
        )
        print("-> Conexión a PostgreSQL (sigam_db) inicializada correctamente.")
    except Exception as e:
        print(f"Error al conectar con PostgreSQL: {e}")
        db_pool = None

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
    if db_pool:
        return db_pool.getconn()
    raise Exception("Piscina de conexiones a base de datos no disponible.")

def release_db_connection(conn):
    if db_pool and conn:
        db_pool.putconn(conn)