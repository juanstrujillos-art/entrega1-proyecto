import io
import os
import tempfile
import threading
import unittest
import zipfile


from pathlib import Path
from unittest.mock import Mock, patch


import virtuallab_client
import virtuallab_functions_implementado as functions
from virtuallab_server import Server, RequestHandler








class TestVirtualLabFunctions(unittest.TestCase):


    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)


        self.original_cwd = os.getcwd()
        os.chdir(self.base)


        self.labs_dir = self.base / "server" / "labs"
        self.labs_dir.mkdir(parents=True)


        self.users_file = self.base / "users.txt"
        self.sessions_file = self.base / "sessions.txt"
        self.assignments_file = self.base / "assignments.txt"


        for file_path in (
            self.users_file,
            self.sessions_file,
            self.assignments_file
        ):
            file_path.write_text("", encoding="utf-8")


        self.patches = [
            patch.object(functions, "usersFile", str(self.users_file)),
            patch.object(functions, "sessionsFile", str(self.sessions_file)),
            patch.object(functions, "assignmentsFile", str(self.assignments_file))
        ]


        for item in self.patches:
            item.start()


        self.professor_id = "787878"
        self.student_id = "898989"


        functions.registerUser(
            "Alexander",
            self.professor_id,
            "professor",
            "professor_pass"
        )


        functions.registerUser(
            "Juanita",
            self.student_id,
            "student",
            "student_pass"
        )


    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()


        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()


    def login_professor(self):
        return functions.openSession(
            self.professor_id,
            "professor_pass"
        )


    def login_student(self):
        return functions.openSession(
            self.student_id,
            "student_pass"
        )


    def test_get_user_existing_and_missing(self):
        self.assertEqual(
            functions.getUser(self.student_id)["name"],
            "Juanita"
        )


        self.assertIsNone(
            functions.getUser("000000")
        )




    def test_register_user_success_and_duplicate(self):
        result = functions.registerUser(
            "Helena",
            "999999",
            "student",
            "pass"
        )


        self.assertEqual(
            result,
            "User Helena with role student registered"
        )


        duplicate = functions.registerUser(
            "Helena",
            "999999",
            "student",
            "pass"
        )


        self.assertEqual(
            duplicate,
            "User already registered"
        )


    def test_is_logged_in(self):
        self.assertFalse(
            functions.isLoggedIn(self.student_id)
        )


        self.login_student()


        self.assertTrue(
            functions.isLoggedIn(self.student_id)
        )


    def test_open_session_valid_and_invalid_password(self):
        self.assertEqual(
            functions.openSession(
                self.student_id,
                "student_pass"
            ),
            "Session was succesfully opened"
        )


        self.assertEqual(
            functions.openSession("000000", "wrong"),
            "error"
        )


        self.assertEqual(
            functions.openSession(
                self.student_id,
                "wrong"
            ),
            "error"
        )




    def test_close_session(self):
        self.login_student()


        self.assertEqual(
            functions.closeSession(self.student_id),
            "Session was succesfully closed"
        )


        self.assertFalse(
            functions.isLoggedIn(self.student_id)
        )


        self.assertEqual(
            functions.closeSession(self.student_id),
            "error"
        )




    def test_upload_lab_authorized_professor(self):
        self.login_professor()


        data = b"contenido de prueba"


        result = functions.uploadLab(
            self.professor_id,
            "circuito.zip",
            data
        )


        self.assertEqual(
            result,
            "File was succesfully received"
        )


        self.assertEqual(
            (self.labs_dir / "circuito.zip").read_bytes(),
            data
        )


    def test_upload_lab_rejects_student_or_logged_out_professor(self):
        self.login_student()


        self.assertEqual(
            functions.uploadLab(
                self.student_id,
                "circuito.zip",
                b"data"
            ),
            "error"
        )


        self.assertEqual(
            functions.uploadLab(
                self.professor_id,
                "circuito.zip",
                b"data"
            ),
            "error"
        )




    def test_download_lab_assigned_to_student(self):
        self.login_professor()
        self.login_student()


        file_data = b"archivo de prueba"


        (self.labs_dir / "circuito.zip").write_bytes(file_data)


        functions.assignLab(
            self.professor_id,
            "circuito",
            self.student_id
        )


        result = functions.downloadLab(
            self.student_id,
            "circuito.zip"
        )


        self.assertEqual(
            result,
            file_data
        )


    def test_download_lab_rejects_unassigned_or_missing_file(self):
        self.login_student()


        self.assertEqual(
            functions.downloadLab(
                self.student_id,
                "circuito.zip"
            ),
            "error"
        )


        self.login_professor()


        functions.assignLab(
            self.professor_id,
            "inexistente",
            self.student_id
        )


        self.assertEqual(
            functions.downloadLab(
                self.student_id,
                "inexistente.zip"
            ),
            "error"
        )




    def test_list_student_labs(self):
        self.login_professor()
        self.login_student()


        self.assertEqual(
            functions.listStudentLabs(self.student_id),
            "No labs assigned"
        )


        functions.assignLab(
            self.professor_id,
            "circuito",
            self.student_id
        )


        self.assertEqual(
            functions.listStudentLabs(self.student_id),
            "circuito"
        )


        self.assertEqual(
            functions.listStudentLabs("000000"),
            "error"
        )




    def test_list_professors_labs(self):
        self.login_professor()


        self.assertEqual(
            functions.listProfessorsLabs(self.professor_id),
            "No labs uploaded"
        )


        (self.labs_dir / "circuito.zip").write_bytes(b"zip")


        self.assertEqual(
            functions.listProfessorsLabs(self.professor_id),
            "circuito.zip"
        )


        self.assertEqual(
            functions.listProfessorsLabs(self.student_id),
            "error"
        )


    def test_list_students(self):
        self.login_professor()


        self.assertEqual(
            functions.listStudents(self.professor_id),
            "Juanita, 898989"
        )


        self.assertEqual(
            functions.listStudents(self.student_id),
            "error"
        )




    def test_assign_lab(self):
        self.login_professor()


        self.assertEqual(
            functions.assignLab(
                self.professor_id,
                "circuito",
                self.student_id
            ),
            "Lab assigned successfully"
        )


        self.assertEqual(
            functions.assignLab(
                self.professor_id,
                "circuito",
                "000000"
            ),
            "error"
        )


        self.assertEqual(
            functions.assignLab(
                self.student_id,
                "circuito",
                self.student_id
            ),
            "error"
        )




class TestVirtualLabClient(unittest.TestCase):


    def setUp(self):
        self.url = "http://localhost:80"


        self.response = Mock()
        self.response.content = b"respuesta de prueba"
        self.response.raise_for_status.return_value = None




    def test_register_user(self):
        with patch.object(
            virtuallab_client.requests,
            "post",
            return_value=self.response
        ) as request:


            result = virtuallab_client.registerUser(
                self.url,
                "Alexander",
                787878,
                "professor",
                "pass"
            )


        self.assertEqual(
            result,
            "respuesta de prueba"
        )


        request.assert_called_once()


        self.assertTrue(
            request.call_args.args[0].endswith("/register")
        )




    def test_open_session(self):
        with patch.object(
            virtuallab_client.requests,
            "post",
            return_value=self.response
        ) as request:


            result = virtuallab_client.openSession(
                self.url,
                787878,
                "pass"
            )


        self.assertEqual(
            result,
            "respuesta de prueba"
        )


        self.assertTrue(
            request.call_args.args[0].endswith("/login")
        )




    def test_close_session(self):
        with patch.object(
            virtuallab_client.requests,
            "post",
            return_value=self.response
        ) as request:


            result = virtuallab_client.closeSession(
                self.url,
                787878
            )


        self.assertEqual(
            result,
            "respuesta de prueba"
        )


        self.assertTrue(
            request.call_args.args[0].endswith("/logout")
        )


    def test_upload_lab(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "practica.zip"


            file_path.write_bytes(b"contenido de prueba")


            with patch.object(
                virtuallab_client.requests,
                "post",
                return_value=self.response
            ) as request:


                result = virtuallab_client.uploadLab(
                    self.url,
                    787878,
                    str(file_path)
                )


        self.assertEqual(
            result,
            "respuesta de prueba"
        )


        self.assertTrue(
            request.call_args.args[0].endswith("/upload_lab")
        )


        self.assertEqual(
            request.call_args.kwargs["headers"]["X-File-Name"],
            "practica.zip"
        )




    def test_download_lab(self):
        # Crear un ZIP válido en memoria
        zip_buffer = io.BytesIO()


        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr(
                "practica.cir",
                "Contenido de prueba del circuito"
            )


        # Simular la respuesta del servidor
        response = Mock()
        response.content = zip_buffer.getvalue()
        response.raise_for_status.return_value = None


        old_cwd = os.getcwd()


        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)


                with patch.object(
                    virtuallab_client.requests,
                    "get",
                    return_value=response
                ) as request:


                    result = virtuallab_client.downloadLab(
                        self.url,
                        898989,
                        "practica.zip"
                    )


                target_path = (
                    Path("client") / "labs" / "practica.zip"
                )


               
                self.assertEqual(
                    Path(result).name,
                    "practica.zip",
                    f"Resultado inesperado de la descarga: {result}"
                )


                request.assert_called_once()


                self.assertTrue(
                    target_path.exists()
                )


                self.assertTrue(
                    zipfile.is_zipfile(target_path)
                )


            finally:
                os.chdir(old_cwd)




    def test_list_student_labs(self):
        with patch.object(
            virtuallab_client.requests,
            "get",
            return_value=self.response
        ) as request:


            result = virtuallab_client.listStudentLabs(
                self.url,
                898989
            )


        self.assertEqual(
            result,
            "respuesta de prueba"
        )


        self.assertTrue(
            request.call_args.args[0].endswith("/list_student_labs")
        )


   
    def test_list_professors_labs(self):
        with patch.object(
            virtuallab_client.requests,
            "get",
            return_value=self.response
        ) as request:


            result = virtuallab_client.listProfessorsLabs(
                self.url,
                787878
            )


        self.assertEqual(
            result,
            "respuesta de prueba"
        )


        self.assertTrue(
            request.call_args.args[0].endswith("/list_professors_labs")
        )




    def test_list_students(self):
        with patch.object(
            virtuallab_client.requests,
            "get",
            return_value=self.response
        ) as request:


            result = virtuallab_client.listStudents(
                self.url,
                787878
            )


        self.assertEqual(
            result,
            "respuesta de prueba"
        )


        self.assertTrue(
            request.call_args.args[0].endswith("/list_students")
        )




    def test_assign_lab(self):
        with patch.object(
            virtuallab_client.requests,
            "post",
            return_value=self.response
        ) as request:


            result = virtuallab_client.assignLab(
                self.url,
                787878,
                "circuito",
                898989
            )


        self.assertEqual(
            result,
            "respuesta de prueba"
        )


        self.assertTrue(
            request.call_args.args[0].endswith("/assign_lab")
        )






class TestVirtualLabIntegration(unittest.TestCase):


    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp_dir.name)


        cls.original_cwd = os.getcwd()
        os.chdir(cls.base)


        cls.labs_dir = cls.base / "server" / "labs"
        cls.labs_dir.mkdir(parents=True)


        # Crear la carpeta donde el cliente guardará los archivos
        (cls.base / "client" / "labs").mkdir(parents=True)


        cls.users_file = cls.base / "users.txt"
        cls.sessions_file = cls.base / "sessions.txt"
        cls.assignments_file = cls.base / "assignments.txt"


        for path in (
            cls.users_file,
            cls.sessions_file,
            cls.assignments_file
        ):
            path.write_text("", encoding="utf-8")


        cls.patches = [
            patch.object(
                functions,
                "usersFile",
                str(cls.users_file)
            ),
            patch.object(
                functions,
                "sessionsFile",
                str(cls.sessions_file)
            ),
            patch.object(
                functions,
                "assignmentsFile",
                str(cls.assignments_file)
            )
        ]


        for item in cls.patches:
            item.start()


        cls.server = Server(
            ("127.0.0.1", 0),
            RequestHandler
        )


        cls.port = cls.server.server_address[1]


        cls.thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True
        )


        cls.thread.start()


        cls.url = f"http://127.0.0.1:{cls.port}"


    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()


        cls.thread.join(timeout=2)


        for item in reversed(cls.patches):
            item.stop()


        os.chdir(cls.original_cwd)
        cls.temp_dir.cleanup()




    def test_complete_professor_student_workflow(self):


       


        professor_result = virtuallab_client.registerUser(
            self.url,
            "Alexander",
            787878,
            "professor",
            "professor_pass"
        )


        student_result = virtuallab_client.registerUser(
            self.url,
            "Juanita",
            898989,
            "student",
            "student_pass"
        )


        self.assertIn(
            "registered",
            professor_result
        )


        self.assertIn(
            "registered",
            student_result
        )


       


        self.assertIn(
            "succesfully opened",
            virtuallab_client.openSession(
                self.url,
                787878,
                "professor_pass"
            )
        )


        self.assertIn(
            "succesfully opened",
            virtuallab_client.openSession(
                self.url,
                898989,
                "student_pass"
            )
        )


       


        with tempfile.TemporaryDirectory() as directory:
            zip_path = Path(directory) / "circuito.zip"


            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr(
                    "circuito.cir",
                    "circuito de prueba"
                )


            upload_result = virtuallab_client.uploadLab(
                self.url,
                787878,
                str(zip_path)
            )


        self.assertIn(
            "succesfully received",
            upload_result
        )


       


        self.assertTrue(
            (self.labs_dir / "circuito.zip").exists(),
            "El archivo circuito.zip no existe en server/labs"
        )


        self.assertIn(
            "circuito.zip",
            virtuallab_client.listProfessorsLabs(
                self.url,
                787878
            )
        )


        self.assertIn(
            "Juanita",
            virtuallab_client.listStudents(
                self.url,
                787878
            )
        )


       


        assign_result = virtuallab_client.assignLab(
            self.url,
            787878,
            "circuito",
            898989
        )


        self.assertIn(
            "successfully",
            assign_result
        )






        self.assertTrue(
            functions.isLoggedIn("898989"),
            "El estudiante no tiene una sesión activa"
        )


        self.assertEqual(
            functions.listStudentLabs("898989"),
            "circuito",
            "El laboratorio no fue asignado correctamente"
        )


        self.assertEqual(
            virtuallab_client.listStudentLabs(
                self.url,
                898989
            ),
            "circuito"
        )


   


        download_result = virtuallab_client.downloadLab(
            self.url,
            898989,
            "circuito.zip"
        )


        self.assertEqual(
            Path(download_result).name,
            "circuito.zip",
            f"Resultado inesperado de la descarga: {download_result}"
        )


        downloaded_path = (
            self.base / "client" / "labs" / "circuito.zip"
        )


        self.assertTrue(
            downloaded_path.exists()
        )


        self.assertTrue(
            zipfile.is_zipfile(downloaded_path)
        )


       


        with zipfile.ZipFile(downloaded_path, "r") as archive:
            self.assertEqual(
                archive.read("circuito.cir").decode("utf-8"),
                "circuito de prueba"
            )


       


        self.assertIn(
            "succesfully closed",
            virtuallab_client.closeSession(
                self.url,
                898989
            )
        )


        self.assertIn(
            "succesfully closed",
            virtuallab_client.closeSession(
                self.url,
                787878
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

