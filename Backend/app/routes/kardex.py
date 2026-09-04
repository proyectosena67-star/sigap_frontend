from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime

# Asumiendo que usas tu conexión a base de datos existente (ej: db.py o sqlite3)
# import sqlite3

kardex_bp = Blueprint('kardex', __name__)

@kardex_bp.route('/kardex', methods=['GET'])
def kardex():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    # Sustituye estas consultas con tus llamadas reales a la base de datos
    # 1. Obtener lista de pacientes para el modal select
    # 2. Obtener lista de medicamentos para el modal select
    # 3. Obtener el historial de kardex ordenado por fecha
    
    # Ejemplo de estructura de datos que espera la plantilla:
    prescripciones = [
        {
            'id': 1,
            'paciente_nombre': 'Paola Andrea Murillo',
            'medicamento_nombre': 'Clonazepam 2mg',
            'dosis': '1 tableta',
            'frecuencia': 'Cada 10 h',
            'via': 'Oral',
            'horario_programado': '2026-09-03 12:10',
            'estado': 'Pendiente'
        },
        {
            'id': 2,
            'paciente_nombre': 'Andrés Felipe Córdoba',
            'medicamento_nombre': 'Alprazolam 0.5mg',
            'dosis': '500 mg',
            'frecuencia': 'Cada 10 h',
            'via': 'Oral',
            'horario_programado': '2026-09-03 17:49',
            'estado': 'Administrado'
        }
    ]
    
    pacientes = [{'id': 1, 'nombre': 'Paola Andrea Murillo'}, {'id': 2, 'nombre': 'Andrés Felipe Córdoba'}]
    medicamentos = [{'id': 1, 'nombre': 'Clonazepam 2mg'}, {'id': 2, 'nombre': 'Alprazolam 0.5mg'}]

    return render_template('kardex.html', prescripciones=prescripciones, pacientes=pacientes, medicamentos=medicamentos)


@kardex_bp.route('/kardex/nueva', methods=['POST'])
def nueva_prescripcion():
    paciente_id = request.form.get('paciente_id')
    medicamento_id = request.form.get('medicamento_id')
    dosis = request.form.get('dosis')
    frecuencia = request.form.get('frecuencia')
    via = request.form.get('via')
    horario = request.form.get('horario_programado')

    # Guardar en base de datos aquí...
    
    flash('Prescripción registrada correctamente en el Kardex.', 'success')
    return redirect(url_for('kardex.kardex'))


@kardex_bp.route('/kardex/administrar/<int:id>', methods=['POST'])
def administrar_medicamento(id):
    observaciones = request.form.get('observaciones')
    
    # Actualizar estado a 'Administrado' y guardar hora de aplicación en la BD...

    flash('Administración registrada con éxito.', 'success')
    return redirect(url_for('kardex.kardex'))