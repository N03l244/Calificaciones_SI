from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuración de la base de datos (MySQL con Laragon)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/sistema_experto'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelos
class Alumno(db.Model):
    __tablename__ = 'alumnos'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
     # Nuevos atributos
    matricula = db.Column(db.String(9), unique=True, nullable=False)
    carrera = db.Column(db.String(100), nullable=False)
    cuatrimestre = db.Column(db.String(20), nullable=False)
    materias = db.relationship('Materia', backref='alumno', lazy=True)

class Materia(db.Model):
    __tablename__ = 'materias'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    calificaciones = db.relationship('Calificacion', backref='materia', lazy=True)

class Calificacion(db.Model):
    __tablename__ = 'calificaciones'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parcial1 = db.Column(db.Integer, nullable=True)
    parcial2 = db.Column(db.Integer, nullable=True)
    parcial3 = db.Column(db.Integer, nullable=True)
    materia_id = db.Column(db.Integer, db.ForeignKey('materias.id'), nullable=False)

# Función para calcular probabilidad de aprobar
def calcular_probabilidad(p1, p2, p3):
    parciales = [p1, p2, p3]
    aprobados = sum(1 for p in parciales if p is not None and p >= 60)
    return (aprobados / 3) * 100 if parciales else 0

# Ruta principal (Lista de alumnos)
@app.route('/')
def index():
    alumnos = Alumno.query.all()
    return render_template('index.html', alumnos=alumnos)

@app.route('/alumno/<int:id>', methods=['GET', 'POST'])
def alumno_detalle(id):
    alumno = Alumno.query.get_or_404(id)

    if request.method == 'POST':
        for materia in alumno.materias:
            p1 = request.form.get(f'parcial1_{materia.id}', type=int)
            p2 = request.form.get(f'parcial2_{materia.id}', type=int)
            p3 = request.form.get(f'parcial3_{materia.id}', type=int)
            
            # Actualizar las calificaciones si la materia ya tiene calificaciones asociadas
            if materia.calificaciones:
                calificacion = materia.calificaciones[0]
                calificacion.parcial1 = p1
                calificacion.parcial2 = p2
                calificacion.parcial3 = p3
            # Si no tiene calificaciones, asignar las nuevas
            else:
                nueva_calificacion = Calificacion(parcial1=p1, parcial2=p2, parcial3=p3, materia=materia)
                db.session.add(nueva_calificacion)

        db.session.commit()
        return redirect(url_for('alumno_detalle', id=alumno.id))

    return render_template('alumno_detalle.html', alumno=alumno, calcular_probabilidad=calcular_probabilidad)



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

    if request.method == 'POST':
        # Obtener el nombre de la materia desde el formulario
        nombre_materia = request.form['nombre']
        
        # Crear una nueva materia y asociarla con el alumno
        nueva_materia = Materia(nombre=nombre_materia, alumno_id=alumno.id)
        
        # Crear calificaciones predeterminadas (puedes establecer valores por defecto o dejarlas vacías)
        nueva_calificacion = Calificacion(parcial1=None, parcial2=None, parcial3=None, materia=nueva_materia)

        # Guardar la materia y las calificaciones
        db.session.add(nueva_materia)
        db.session.add(nueva_calificacion)
        db.session.commit()

        # Redirigir al detalle del alumno después de agregar la materia
        return redirect(url_for('alumno_detalle', id=alumno.id))

    return render_template('agregar_materia.html', alumno=alumno)

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

# Crear tablas
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
