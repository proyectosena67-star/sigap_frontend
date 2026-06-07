from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/historial')
def historial():
    return render_template('historial.html')

@app.route('/evaluaciones')
def evaluaciones():
    return render_template('evaluaciones.html')

@app.route('/medicamentos')
def medicamentos():
    return render_template('medicamentos.html')

if __name__ == '__main__':
    app.run(debug=True)
