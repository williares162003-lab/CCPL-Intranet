

# ============================================================
# MODELOS DEL COLEGIADO
# ============================================================

class clsColegiado:
    def __init__(self, p_id=None, p_nombre=None, p_matricula=None, p_documento=None,
                 p_especialidad=None, p_correo=None, p_telefono=None,
                 p_vigencia=None, p_estado=None, p_epc_points=None,
                 p_direccion=None, p_especialidad_id=None,
                 p_fecha_colegiatura=None):
        self.id = p_id
        self.nombre = p_nombre
        self.matricula = p_matricula
        self.documento = p_documento
        self.especialidad_id = p_especialidad_id
        self.especialidad = p_especialidad
        self.correo = p_correo
        self.telefono = p_telefono
        self.vigencia = p_vigencia
        self.estado = p_estado
        self.epc_points = p_epc_points
        self.direccion = p_direccion
        self.fecha_colegiatura = p_fecha_colegiatura


class clsTramite:
    def __init__(self, p_id=None, p_matricula=None, p_nombre=None,
                 p_tipo_tramite=None, p_asunto=None, p_descripcion=None,
                 p_archivo_solicitud=None, p_estado=None,
                 p_fecha_solicitud=None):
        self.id = p_id
        self.matricula = p_matricula
        self.nombre = p_nombre
        self.tipo_tramite = p_tipo_tramite
        self.asunto = p_asunto
        self.descripcion = p_descripcion
        self.archivo_solicitud = p_archivo_solicitud
        self.estado = p_estado
        self.fecha_solicitud = p_fecha_solicitud
