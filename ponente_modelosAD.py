

# ============================================================
# MODELOS DEL AULA
# ============================================================

class clsContenidoCurso:
    def __init__(self, p_id=None, p_curso_id=None, p_titulo=None,
                 p_descripcion=None, p_enlace=None, p_archivo=None):
        self.id = p_id
        self.curso_id = p_curso_id
        self.titulo = p_titulo
        self.descripcion = p_descripcion
        self.enlace = p_enlace
        self.archivo = p_archivo
