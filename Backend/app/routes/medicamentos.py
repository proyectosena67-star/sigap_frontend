from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import get_db_connection, release_db_connection

medicamentos_bp = Blueprint('medicamentos', __name__)

@medicamentos_bp.route('/medicamentos', methods=['GET', 'POST'])
def medicamentos():
    categoria_sel = request.args.get('categoria', '').strip()

    conn = None
    medicamentos_list = []
    nombres_meds = []
    categorias = []

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if request.method == 'POST':
                nombre = request.form.get('nombre_medicamento', '').strip()
                categoria = request.form.get('categoria', '').strip()
                cantidad = int(request.form.get('cantidad', 0))

                # Verificar si ya existe en la tabla medicamentos_insumos
                cur.execute("SELECT id_item, stock_actual FROM medicamentos_insumos WHERE LOWER(nombre_generico) = LOWER(%s);", (nombre,))
                item = cur.fetchone()

                if item:
                    nuevo_stock = item['stock_actual'] + cantidad
                    cur.execute("UPDATE medicamentos_insumos SET stock_actual = %s WHERE id_item = %s;", (nuevo_stock, item['id_item']))
                    flash(f"Se sumaron {cantidad} unidades a {nombre}.", "success")
                else:
                    cur.execute("""
                        INSERT INTO medicamentos_insumos (nombre_generico, presentacion, tipo_item, stock_actual)
                        VALUES (%s, %s, 'Medicamento', %s);
                    """, (nombre, categoria, cantidad))
                    flash(f"Medicamento {nombre} creado con exito.", "success")
                
                conn.commit()
                return redirect(url_for('medicamentos.medicamentos'))

            # Obtener datos para listas y desplegables
            cur.execute("SELECT DISTINCT presentacion FROM medicamentos_insumos WHERE presentacion IS NOT NULL AND presentacion != '';")
            categorias = [r['presentacion'] for r in cur.fetchall()]

            cur.execute("SELECT id_item, nombre_generico, presentacion FROM medicamentos_insumos ORDER BY nombre_generico ASC;")
            nombres_meds = cur.fetchall()

            # Filtrado principal
            if categoria_sel:
                cur.execute("SELECT * FROM medicamentos_insumos WHERE presentacion ILIKE %s ORDER BY id_item DESC;", (categoria_sel,))
            else:
                cur.execute("SELECT * FROM medicamentos_insumos ORDER BY id_item DESC;")

            medicamentos_list = cur.fetchall()

    except Exception as e:
        print(f"Error en Módulo Medicamentos: {e}")
        flash("Ocurrió un error al procesar el inventario de medicamentos.", "danger")
    finally:
        if conn:
            release_db_connection(conn)

    return render_template(
        'medicamentos.html',
        medicamentos=medicamentos_list,
        nombres_meds=nombres_meds,
        categorias=categorias,
        categoria_sel=categoria_sel
    )