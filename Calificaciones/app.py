from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from math import comb

app = Flask(__name__)

# Configuración de la base de datos (MySQL con Laragon)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/sistema_experto'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelos
class Alumno(db.Model):
    __tablename__ = 'alumnos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    matricula = db.Column(db.String(255), nullable=False)
    carrera = db.Column(db.String(255), nullable=False)
    cuatrimestre = db.Column(db.String(255), nullable=False)
    # Relación con calificaciones
    calificaciones = db.relationship('Calificacion', backref='alumno', lazy=True)

class Materia(db.Model):
    __tablename__ = 'materias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    # Relación con calificaciones
    calificaciones = db.relationship('Calificacion', backref='materia', lazy=True)

class Calificacion(db.Model):
    __tablename__ = 'calificaciones'
    id = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    id_materia = db.Column(db.Integer, db.ForeignKey('materias.id'), nullable=False)
    parcial1 = db.Column(db.Numeric(5, 2))
    parcial2 = db.Column(db.Numeric(5, 2))
    parcial3 = db.Column(db.Numeric(5, 2))


# Función para calcular probabilidad de aprobar
def calcular_probabilidad(p1, p2, p3):
    parciales = [p1, p2, p3]
    aprobados = sum(1 for p in parciales if p is not None and p >= 70)
    return (aprobados / 3) * 100 if parciales else 0

# Ruta principal (Lista de alumnos)
@app.route('/')
def index():
    alumnos = Alumno.query.all()
    return render_template('index.html', alumnos=alumnos)

# Ruta para la gestión de materias
@app.route('/materias')
def gestion_materias():
    materias = Materia.query.all()  # Obtener todas las materias
    return render_template('gestionar_materias.html', materias=materias)

# Ruta para el detalle del alumno
@app.route('/alumno/<int:id>', methods=['GET', 'POST'])
def alumno_detalle(id):
    alumno = Alumno.query.get_or_404(id)
    
    # Obtener las materias asociadas al alumno a través de las calificaciones
    calificaciones = Calificacion.query.filter_by(id_alumno=alumno.id).all()
    
    # Crear un diccionario para almacenar las calificaciones por materia
    materias_con_calificaciones = {}
    for calificacion in calificaciones:
        materia = Materia.query.get(calificacion.id_materia)
        if materia:
            materias_con_calificaciones[materia.id] = {
                'materia': materia,
                'calificacion': calificacion
            }
    
    if request.method == 'POST':
        for materia_id, datos in materias_con_calificaciones.items():
            p1 = request.form.get(f'parcial1_{materia_id}', type=float)
            p2 = request.form.get(f'parcial2_{materia_id}', type=float)
            p3 = request.form.get(f'parcial3_{materia_id}', type=float)

            calificacion = datos['calificacion']
            if calificacion:
                # Actualizar solo los valores no nulos
                if p1 is not None: calificacion.parcial1 = p1
                if p2 is not None: calificacion.parcial2 = p2
                if p3 is not None: calificacion.parcial3 = p3

        db.session.commit()
        return redirect(url_for('alumno_detalle', id=alumno.id))

    # Calcular la probabilidad de aprobar el cuatrimestre
    probabilidad, estado = calcular_probabilidad_cuatrimestre(alumno)

    return render_template(
        'alumno_detalle.html',
        alumno=alumno,
        calcular_probabilidad=calcular_probabilidad,
        materias_con_calificaciones=materias_con_calificaciones,
        probabilidad_cuatrimestre=probabilidad,
        estado_cuatrimestre=estado
    )
# Ruta para agregar un nuevo alumno
@app.route('/agregar', methods=['GET', 'POST'])
def agregar_alumno():
    if request.method == 'POST':
        # Obtener los datos del formulario
        nombre = request.form['nombre']
        email = request.form['email']
        matricula = request.form['matricula']
        carrera = request.form['carrera']
        cuatrimestre = request.form['cuatrimestre']
        
        # Verificar si el email ya existe
        existing_alumno = Alumno.query.filter_by(email=email).first()
        if existing_alumno:
            # Si ya existe, devolver un mensaje de error
            return render_template('agregar_alumno.html', error="El correo electrónico ya está registrado.")
        
        # Crear un nuevo objeto Alumno
        nuevo_alumno = Alumno(
            nombre=nombre,
            email=email,
            matricula=matricula,
            carrera=carrera,
            cuatrimestre=cuatrimestre
        )
        
        # Agregarlo a la base de datos
        db.session.add(nuevo_alumno)
        db.session.commit()

        # Redirigir a la página principal después de agregar al alumno
        return redirect(url_for('index'))

    return render_template('agregar_alumno.html')


@app.route('/alumno/<int:id>/agregar_materia', methods=['GET', 'POST'])
def agregar_materia(id):
    alumno = Alumno.query.get_or_404(id)

    # Obtener todas las materias existentes
    materias_existentes = Materia.query.all()

    if request.method == 'POST':
        # Obtener el id de la materia seleccionada o el nombre de una nueva
        materia_id = request.form.get('materia_existente')
        nombre_materia = request.form.get('nombre')

        # Si selecciona una materia existente
        if materia_id:
            materia_existente = Materia.query.get(materia_id)

            # Verificar si ya está asociada al alumno
            calificacion_existente = Calificacion.query.filter_by(id_alumno=alumno.id, id_materia=materia_existente.id).first()

            if calificacion_existente:
                return render_template('agregar_materia.html', alumno=alumno, materias_existentes=materias_existentes, error="La materia ya está asociada al alumno.")
        
            nueva_calificacion = Calificacion(id_alumno=alumno.id, id_materia=materia_existente.id)
            db.session.add(nueva_calificacion)

        # Si agrega una materia nueva
        elif nombre_materia:
            # Verificar si la materia ya existe
            materia_existente = Materia.query.filter_by(nombre=nombre_materia).first()

            if materia_existente:
                nueva_calificacion = Calificacion(id_alumno=alumno.id, id_materia=materia_existente.id)
                db.session.add(nueva_calificacion)
            else:
                # Crear nueva materia y asociarla
                nueva_materia = Materia(nombre=nombre_materia)
                db.session.add(nueva_materia)
                db.session.flush()  # Obtiene el id antes de commit
                nueva_calificacion = Calificacion(id_alumno=alumno.id, id_materia=nueva_materia.id)
                db.session.add(nueva_calificacion)

        db.session.commit()
        return redirect(url_for('alumno_detalle', id=alumno.id))

    return render_template('agregar_materia.html', alumno=alumno, materias_existentes=materias_existentes)

# Ruta para agregar una nueva materia (sin ID de alumno)
@app.route('/materia/agregar', methods=['GET', 'POST'])
def agregar_materiaSinID():
    if request.method == 'POST':
        nombre_materia = request.form.get('nombre')
        
        # Verificar si la materia ya existe
        materia_existente = Materia.query.filter_by(nombre=nombre_materia).first()
        
        if materia_existente:
            return render_template('agregar_materia_sin_id.html', error="La materia ya existe.")
        
        # Crear una nueva materia
        nueva_materia = Materia(nombre=nombre_materia)
        db.session.add(nueva_materia)
        db.session.commit()
        
        return redirect(url_for('gestion_materias'))
    
    return render_template('agregar_materia_sin_id.html')

# Ruta para eliminar una materia
@app.route('/materia/<int:id>/eliminar', methods=['POST'])
def eliminar_materia(id):
    materia = Materia.query.get_or_404(id)
    
    # Eliminar todas las calificaciones asociadas a la materia
    Calificacion.query.filter_by(id_materia=id).delete()
    
    # Eliminar la materia
    db.session.delete(materia)
    db.session.commit()
    
    return redirect(url_for('gestion_materias'))  # Redirigir a la gestión de materias

# Ruta para editar una materia
@app.route('/materia/<int:id>/editar', methods=['GET', 'POST'])
def editar_materia(id):
    materia = Materia.query.get_or_404(id)
    
    if request.method == 'POST':
        materia.nombre = request.form['nombre']
        db.session.commit()
        return redirect(url_for('gestion_materias'))  # Redirigir a la gestión de materias
    
    return render_template('editar_materia.html', materia=materia)


@app.route('/editar_alumno/<int:alumno_id>', methods=['GET', 'POST'])
def editar_alumno(alumno_id):
    alumno = Alumno.query.get_or_404(alumno_id)
    if request.method == 'POST':
        alumno.nombre = request.form['nombre']
        alumno.email = request.form['email']
        alumno.matricula = request.form['matricula']
        alumno.carrera = request.form['carrera']
        alumno.cuatrimestre = request.form['cuatrimestre']
        db.session.commit()
        return redirect(url_for('alumno_detalle', id=alumno.id))
    
    return render_template('editar_alumno.html', alumno=alumno)

# Ruta para eliminar un alumno
@app.route('/alumno/<int:id>/eliminar', methods=['POST'])
def eliminar_alumno(id):
    alumno = Alumno.query.get_or_404(id)
    
    # Eliminar todas las calificaciones asociadas al alumno
    Calificacion.query.filter_by(id_alumno=id).delete()
    
    # Eliminar el alumno
    db.session.delete(alumno)
    db.session.commit()
    
    return redirect(url_for('index'))

# Función para calcular la probabilidad de aprobar el cuatrimestre
def calcular_probabilidad_cuatrimestre(alumno):
    calificaciones = Calificacion.query.filter_by(id_alumno=alumno.id).all()
    total_asignaturas = len(calificaciones)
    aprobadas = 0
    reprobadas = 0
    en_evaluacion_final = 0

    for calificacion in calificaciones:
        parciales = [calificacion.parcial1, calificacion.parcial2, calificacion.parcial3]
        aprobados = sum(1 for p in parciales if p is not None and p >= 70)

        if aprobados == 3:
            aprobadas += 1
        elif aprobados == 0:
            reprobadas += 1
        else:
            en_evaluacion_final += 1

    # Calcular la probabilidad de aprobar el cuatrimestre
    if total_asignaturas == 0:
        return 0, "Sin asignaturas"

    # Ajustar la regla del 50% de las materias
    umbral_aprobacion = (total_asignaturas // 2) if total_asignaturas % 2 == 0 else (total_asignaturas // 2) + 1

    # Si el alumno aprueba al menos el umbral, se garantiza el 100% de probabilidad
    if aprobadas >= umbral_aprobacion:
        return 100, "Aprobado"

    # Calcular la probabilidad usando distribución binomial
    probabilidad_aprobar_final = 0.5  # Suponiendo 50% de probabilidad de aprobar en evaluación final

    probabilidad = (aprobadas + sum(comb(3, aprobados) * (probabilidad_aprobar_final ** aprobados) * ((1 - probabilidad_aprobar_final) ** (3 - aprobados)) for _ in range(en_evaluacion_final))) / total_asignaturas * 100

    # Determinar el estado del cuatrimestre
    if reprobadas > total_asignaturas / 2:
        estado = "Reprobado"
    elif en_evaluacion_final > 0 or reprobadas > 0:
        estado = "En Riesgo"
    else:
        estado = "Aprobado"

    return probabilidad, estado



# Crear tablas
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
