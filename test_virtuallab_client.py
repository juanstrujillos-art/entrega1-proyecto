import virtuallab_client
import zipfile
import os
from PySpice.Unit import *
from PySpice.Spice.Parser import SpiceParser


# Dirección del servidor
url = "http://localhost:80"


# =====================================================================
# 1. LISTA DE ESTUDIANTES Y PROFESORES
# =====================================================================
estudiantes = [
    {"name": "Helena", "id": 999999, "password": "student_pass"},
    {"name": "Juanita", "id": 898989, "password": "student_pass"},
    {"name": "Sebastian", "id": 303030, "password": "student_pass"},
    {"name": "Felipe", "id": 171717, "password": "student_pass"}
]




profesores = [
    {
        "name": "Alexander",
        "id": 787878,
        "password": "professor_pass",
        "lab": "voltage_divider",
        "student_ids": [898989, 3]  
    },
    {
        "name": "Catalina",
        "id": 242424,
        "password": "pass_catalina",
        "lab": "voltage_divider",
        "student_ids": [999999]          
    },
    {
            "name": "Fernando",
            "id": 444444,
            "password": "pass_fernando",
            "lab": "rc",
            "student_ids": [171717]          
        }
]


# =====================================================================
# 2. REGISTRO DE USUARIOS
# =====================================================================
print("--- REGISTRO DE PROFESORES ---")
for prof in profesores:
    print(virtuallab_client.registerUser(url, prof["name"], prof["id"], "professor", prof["password"]))


print("\n--- REGISTRO DE ESTUDIANTES ---")
for est in estudiantes:
    print(virtuallab_client.registerUser(url, est["name"], est["id"], "student", est["password"]))


# =====================================================================
# 3. GESTIÓN DE CADA PROFESOR
# =====================================================================
print("\n--- GESTIÓN DE PROFESORES ---")
for prof in profesores:
    print(f"\nProfesor activo: {prof['name']} ({prof['id']})")
    print(virtuallab_client.openSession(url, prof["id"], prof["password"]))
   
    lab_name = prof["lab"]
    file_path = f"client/{lab_name}.zip"
   
    if not os.path.exists(file_path):
        raise SystemExit(f"No existe {file_path}. Coloque el zip de la práctica en la carpeta client/")
       
    # El profesor sube el laboratorio una sola vez
    print(virtuallab_client.uploadLab(url, prof["id"], file_path))
   
    # Lista laboratorios y estudiantes
    print("Laboratorios en el servidor:\n" + virtuallab_client.listProfessorsLabs(url, prof["id"]))
    print("Estudiantes registrados:\n" + virtuallab_client.listStudents(url, prof["id"]))
   
    # Recorre la lista "student_ids" y le asigna el laboratorio a cada ID
    for id_destino in prof["student_ids"]:
        res_assign = virtuallab_client.assignLab(url, prof["id"], lab_name, id_destino)
        print(f"Profesor {prof['name']} asignando '{lab_name}' al estudiante ID {id_destino}: {res_assign}")
       
    print(virtuallab_client.closeSession(url, prof["id"]))


# =====================================================================
# 4. SESIÓN DE CADA ESTUDIANTE (Descargar y simular lo que tenga asignado)
# =====================================================================
print("\n--- PRUEBA Y SIMULACIÓN POR ESTUDIANTE ---")
for est in estudiantes:
    print(f"\nEstudiante activo: {est['name']} ({est['id']})")
    print(virtuallab_client.openSession(url, est["id"], est["password"]))
   
    # Consultar en el servidor qué laboratorios tiene asignados este estudiante
    labs_respuesta = virtuallab_client.listStudentLabs(url, est["id"])
    print("Prácticas asignadas:", labs_respuesta)
   
    # Si tiene al menos un laboratorio asignado, lo descarga y lo simula
    if labs_respuesta not in ["No labs assigned", "error"]:
        for lab_name in labs_respuesta.splitlines():
            lab_name = lab_name.strip()
            file_name = lab_name + ".zip"
           
            print(virtuallab_client.downloadLab(url, est["id"], file_name))
           
            downloaded_path = f"client/labs/{file_name}"
            if not zipfile.is_zipfile(downloaded_path):
                raise SystemExit(f"La descarga de {file_name} para {est['name']} no es un zip válido.")


            with zipfile.ZipFile(downloaded_path, "r") as zip_ref:
                with zip_ref.open(lab_name + ".cir") as file:
                    netlist = file.read().decode("utf-8")
                    print("Starting simulation for lab:", lab_name)
                    parser = SpiceParser(source=netlist)
                    circuit = parser.build_circuit()
                    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
                    analysis = simulator.operating_point()
                    for node in analysis.nodes.values():
                        print(f'Node {node}: {float(node[0]):.4f} V')
                    print("Simulation completed for lab:", lab_name)
                   
    print(virtuallab_client.closeSession(url, est["id"]))

