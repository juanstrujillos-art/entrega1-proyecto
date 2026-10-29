# Funciones del servidor VirtualLab.
# La información persistente se guarda en archivos de texto JSONL.
# No se utiliza ningún motor de bases de datos.

import os
import json
import zipfile
from io import BytesIO

USERS_FILE = "server/users.txt"
LABS_FILE = "server/labs.txt"
ASSIGNMENTS_FILE = "server/assignments.txt"
LABS_DIR = "server/labs"

# Las sesiones activas se mantienen mientras el servidor está ejecutándose.
active_sessions = set()


def _read_records(path):
    """Lee un archivo JSONL y devuelve una lista de diccionarios."""
    records = []
    try:
        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    except FileNotFoundError:
        pass
    return records


def _append_record(path, record):
    """Añade un diccionario como una línea JSON al archivo indicado."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def _find_user(user_id):
    """Busca un usuario por identificación."""
    user_id = str(user_id)
    for user in _read_records(USERS_FILE):
        if str(user.get("id")) == user_id:
            return user
    return None


def _lab_filename(lab_name):
    """Normaliza un nombre de práctica y devuelve un nombre ZIP seguro."""
    filename = os.path.basename(str(lab_name))
    if not filename.lower().endswith(".zip"):
        filename += ".zip"
    return filename


def _lab_exists(filename):
    """Comprueba que exista el ZIP y que esté registrado en los metadatos."""
    path = os.path.join(LABS_DIR, filename)
    if not os.path.isfile(path):
        return False
    return any(lab.get("filename") == filename for lab in _read_records(LABS_FILE))


def writeUserDataToFile(user_data):
    """Guarda los datos de un usuario en el archivo de usuarios."""
    _append_record(USERS_FILE, user_data)


# Registra un usuario si su identificación no existe.
def registerUser(name, id, role, password):
    if role not in ("student", "professor"):
        return "error"

    if _find_user(id) is not None:
        return "User already registered"

    user_data = {
        "name": str(name),
        "id": str(id),
        "role": role,
        "password": str(password)
    }
    writeUserDataToFile(user_data)
    return f"User {name} with role {role} registered"


# Abre una sesión cuando la identificación y la contraseña son correctas.
def openSession(id, password):
    user = _find_user(id)
    if user is None or user.get("password") != str(password):
        return "error"

    active_sessions.add(str(id))
    return "Session was succesfully opened"


# Cierra una sesión que esté abierta.
def closeSession(id):
    user_id = str(id)
    if user_id not in active_sessions:
        return "error"

    active_sessions.remove(user_id)
    return "Session was succesfully closed"


# Recibe una práctica ZIP de un profesor con sesión abierta.
def uploadLab(id, file_name, file_data):
    user_id = str(id)
    user = _find_user(user_id)
    if user is None or user.get("role") != "professor" or user_id not in active_sessions:
        return "error"

    filename = _lab_filename(file_name)
    # Evita aceptar archivos que no sean ZIP válidos.
    try:
        with zipfile.ZipFile(BytesIO(file_data), "r") as archive:
            if archive.testzip() is not None:
                return "error"
    except (zipfile.BadZipFile, OSError, TypeError):
        return "error"

    os.makedirs(LABS_DIR, exist_ok=True)
    target_path = os.path.join(LABS_DIR, filename)
    with open(target_path, "wb") as file:
        file.write(file_data)

    # Guarda quién cargó el archivo para poder listar las prácticas del profesor.
    labs = _read_records(LABS_FILE)
    existing = next((lab for lab in labs if lab.get("filename") == filename), None)
    if existing is None:
        _append_record(LABS_FILE, {
            "filename": filename,
            "name": os.path.splitext(filename)[0],
            "professor_id": user_id
        })
    else:
        # Si se vuelve a cargar el mismo nombre, se actualiza su profesor propietario.
        existing["professor_id"] = user_id
        existing["name"] = os.path.splitext(filename)[0]
        with open(LABS_FILE, "w", encoding="utf-8") as file:
            for lab in labs:
                file.write(json.dumps(lab, ensure_ascii=False) + "\n")

    return "File was succesfully received"


# Envía un ZIP únicamente al estudiante que tenga asignada esa práctica.
def downloadLab(id, file_name):
    user_id = str(id)
    user = _find_user(user_id)
    if user is None or user.get("role") != "student" or user_id not in active_sessions:
        return "error"

    filename = _lab_filename(file_name)
    lab_name = os.path.splitext(filename)[0]
    assignments = _read_records(ASSIGNMENTS_FILE)
    is_assigned = any(
        str(item.get("student_id")) == user_id and item.get("lab_name") == lab_name
        for item in assignments
    )
    if not is_assigned or not _lab_exists(filename):
        return "error"

    target_path = os.path.join(LABS_DIR, filename)
    try:
        with open(target_path, "rb") as file:
            return file.read()
    except OSError:
        return "error"


# Lista las prácticas asignadas al estudiante con sesión abierta.
def listStudentLabs(id):
    user_id = str(id)
    user = _find_user(user_id)
    if user is None or user.get("role") != "student" or user_id not in active_sessions:
        return "error"

    assignments = _read_records(ASSIGNMENTS_FILE)
    assigned_names = [
        item["lab_name"] for item in assignments
        if str(item.get("student_id")) == user_id
    ]
    return assigned_names


# Lista las prácticas cargadas por el profesor que tiene sesión abierta.
def listProfessorsLabs(id):
    user_id = str(id)
    user = _find_user(user_id)
    if user is None or user.get("role") != "professor" or user_id not in active_sessions:
        return "error"

    labs = _read_records(LABS_FILE)
    return [
        lab["name"] for lab in labs
        if str(lab.get("professor_id")) == user_id
    ]


# Lista los estudiantes registrados si el profesor tiene sesión abierta.
def listStudents(id):
    user_id = str(id)
    user = _find_user(user_id)
    if user is None or user.get("role") != "professor" or user_id not in active_sessions:
        return "error"

    students = []
    for user_record in _read_records(USERS_FILE):
        if user_record.get("role") == "student":
            students.append({
                "name": user_record.get("name"),
                "id": user_record.get("id")
            })
    return students


# Asigna una práctica existente a un estudiante existente.
def assignLab(id, lab_name, student_id):
    professor_id = str(id)
    professor = _find_user(professor_id)
    student = _find_user(student_id)

    if (professor is None or professor.get("role") != "professor"
            or professor_id not in active_sessions):
        return "error"
    if student is None or student.get("role") != "student":
        return "error"

    filename = _lab_filename(lab_name)
    if not _lab_exists(filename):
        return "error"

    normalized_lab_name = os.path.splitext(filename)[0]
    assignments = _read_records(ASSIGNMENTS_FILE)
    for assignment in assignments:
        if (str(assignment.get("student_id")) == str(student_id)
                and assignment.get("lab_name") == normalized_lab_name):
            return "error"

    _append_record(ASSIGNMENTS_FILE, {
        "professor_id": professor_id,
        "student_id": str(student_id),
        "lab_name": normalized_lab_name
    })
    return f"Lab {normalized_lab_name} assigned to student {student_id}"
