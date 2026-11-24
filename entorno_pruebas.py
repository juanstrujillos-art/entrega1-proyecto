import os
import shutil
import sys
import tempfile
import unittest


# Carpeta raíz del proyecto (donde están virtuallab_*.py)
RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ_PROYECTO not in sys.path:
    sys.path.insert(0, RAIZ_PROYECTO)


# La implementación crea server/users.txt, sessions.txt y assignments.txt
# al importarse. La cargamos una primera vez desde una carpeta temporal para
# evitar que esa inicialización cree archivos dentro del proyecto real.
import importlib
_cwd_inicial = os.getcwd()
_carpeta_arranque = tempfile.mkdtemp(prefix="virtuallab_import_")
try:
    os.chdir(_carpeta_arranque)
    importlib.import_module("virtuallab_functions_implementado")
finally:
    os.chdir(_cwd_inicial)
    shutil.rmtree(_carpeta_arranque, ignore_errors=True)




class PruebaConCarpetaTemporal(unittest.TestCase):
    """TestCase base: crea una carpeta temporal con la estructura del servidor."""


    def setUp(self):
        self.carpeta_original = os.getcwd()
        self.carpeta_temporal = tempfile.mkdtemp(prefix="virtuallab_test_")
        os.chdir(self.carpeta_temporal)
        os.makedirs("server/labs", exist_ok=True)
        for archivo in ("server/users.txt", "server/sessions.txt", "server/assignments.txt"):
            open(archivo, "w").close()


    def tearDown(self):
        os.chdir(self.carpeta_original)
        shutil.rmtree(self.carpeta_temporal, ignore_errors=True)


    # --- Métodos de ayuda para leer los archivos del "servidor" ---
    @staticmethod
    def leer_lineas(ruta):
        with open(ruta, "r") as f:
            return [linea.strip() for linea in f if linea.strip()]
