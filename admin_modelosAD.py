

# ============================================================
# MODELOS ADMINISTRATIVOS
# ============================================================

class clsUsuario:
    def __init__(self, p_id=None, p_matricula=None, p_password=None,
                 p_rol=None, p_activo=None):
        self.id = p_id
        self.matricula = p_matricula
        self.password = p_password
        self.rol = p_rol
        self.activo = p_activo


class clsCuota:
    def __init__(self, p_id=None, p_matricula=None, p_fecha=None,
                 p_concepto=None, p_monto=None, p_estado=None,
                 p_tipo="otro", p_periodo_mes=None, p_periodo_anio=None,
                 p_fecha_vencimiento=None):
        self.id = p_id
        self.matricula = p_matricula
        self.fecha = p_fecha
        self.concepto = p_concepto
        self.monto = p_monto
        self.estado = p_estado
        self.tipo = p_tipo
        self.periodo_mes = p_periodo_mes
        self.periodo_anio = p_periodo_anio
        self.fecha_vencimiento = p_fecha_vencimiento


class clsMedioPago:
    def __init__(self, p_id=None, p_nombre=None, p_descripcion=None,
                 p_numero_cuenta=None, p_titular=None, p_activo=1):
        self.id = p_id
        self.nombre = p_nombre
        self.descripcion = p_descripcion
        self.numero_cuenta = p_numero_cuenta
        self.titular = p_titular
        self.activo = p_activo


class clsCurso:
    def __init__(self, p_id=None, p_categoria=None, p_titulo=None,
                 p_descripcion=None, p_fecha_evento=None, p_estado=None,
                 p_monto=0, p_ponente=None, p_modalidad=None,
                 p_duracion_horas=0, p_fecha_inicio=None, p_fecha_fin=None,
                 p_cupos=0, p_monto_inhabil=None):
        self.id = p_id
        self.categoria = p_categoria
        self.titulo = p_titulo
        self.descripcion = p_descripcion
        self.fecha_evento = p_fecha_evento
        self.estado = p_estado
        self.monto = p_monto
        self.monto_inhabil = p_monto_inhabil
        self.ponente = p_ponente
        self.modalidad = p_modalidad
        self.duracion_horas = p_duracion_horas
        self.fecha_inicio = p_fecha_inicio
        self.fecha_fin = p_fecha_fin
        self.cupos = p_cupos
