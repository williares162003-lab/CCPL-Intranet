-- ============================================================
--  Portal CCPL  |  Base de datos: colegiocontadores
--  Ejecutar en phpMyAdmin con la BD "colegiocontadores" activa
-- ============================================================

USE colegiocontadores;

-- -------------------------------------------------------
-- 1. Eliminar tablas en orden (FK primero)
-- -------------------------------------------------------
DROP TABLE IF EXISTS facturacion_sunat_logs;
DROP TABLE IF EXISTS comprobante_fiscal_detalle;
DROP TABLE IF EXISTS comprobantes_fiscales;
DROP TABLE IF EXISTS configuracion_facturacion;
DROP TABLE IF EXISTS ordenes_mercado_pago;
DROP TABLE IF EXISTS configuracion_mercado_pago;
DROP TABLE IF EXISTS comprobantes_pago;
DROP TABLE IF EXISTS transacciones_pago;
DROP TABLE IF EXISTS evidencias_pago;
DROP TABLE IF EXISTS notificaciones;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS tramites;
DROP TABLE IF EXISTS solicitudes_baja;
DROP TABLE IF EXISTS inscripciones_curso;
DROP TABLE IF EXISTS entregas_tarea;
DROP TABLE IF EXISTS tareas_curso;
DROP TABLE IF EXISTS contenido_curso;
DROP TABLE IF EXISTS curso_unidades;
DROP TABLE IF EXISTS cursos;
DROP TABLE IF EXISTS cuotas;
DROP TABLE IF EXISTS medios_pago;
DROP TABLE IF EXISTS registros_demo;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS colegiados;
DROP TABLE IF EXISTS especialidades_colegiado;

-- -------------------------------------------------------
-- 2. TABLA: especialidades_colegiado
-- -------------------------------------------------------
CREATE TABLE especialidades_colegiado (
  id        INT          AUTO_INCREMENT PRIMARY KEY,
  nombre    VARCHAR(120) NOT NULL,
  activo    TINYINT(1)   NOT NULL DEFAULT 1,
  creado_en TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_especialidad_colegiado_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO especialidades_colegiado (id, nombre, activo) VALUES
  (1, 'Contador Publico Colegiado', 1),
  (2, 'Perito Contable', 1),
  (3, 'Auditor Independiente', 1),
  (4, 'Auditor Financiero', 1),
  (5, 'Tributacion Empresarial', 1),
  (6, 'Contabilidad Gubernamental', 1),
  (7, 'Finanzas Corporativas', 1),
  (8, 'Costos y Presupuestos', 1),
  (9, 'NIIF y Reportes Financieros', 1),
  (10, 'Control Interno', 1);

-- -------------------------------------------------------
-- 3. TABLA: colegiados
-- -------------------------------------------------------
CREATE TABLE colegiados (
  id           INT           AUTO_INCREMENT PRIMARY KEY,
  nombre       VARCHAR(150)  NOT NULL,
  matricula    VARCHAR(30)   NOT NULL,
  documento    VARCHAR(20)   NOT NULL,
  especialidad_id INT,
  especialidad VARCHAR(200)  NOT NULL,
  correo       VARCHAR(120)  NOT NULL,
  telefono     VARCHAR(30),
  direccion    VARCHAR(255)  NOT NULL DEFAULT 'Sin registrar',
  fecha_colegiatura DATE,
  vigencia     VARCHAR(60)   DEFAULT '31 de Diciembre de 2025',
  estado       VARCHAR(20)   DEFAULT 'Vigente',
  epc_points   INT           DEFAULT 0,
  creado_en    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_matricula (matricula),
  UNIQUE KEY uq_documento (documento),
  INDEX idx_colegiados_nombre (nombre),
  INDEX idx_colegiados_especialidad_estado (especialidad, estado),
  INDEX idx_colegiados_especialidad_id (especialidad_id),
  INDEX idx_colegiados_fecha_col (fecha_colegiatura, estado),
  CONSTRAINT fk_colegiados_especialidad
    FOREIGN KEY (especialidad_id) REFERENCES especialidades_colegiado(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 4. TABLA: usuarios
-- -------------------------------------------------------
CREATE TABLE usuarios (
  id        INT          AUTO_INCREMENT PRIMARY KEY,
  matricula VARCHAR(30)  NOT NULL,
  password  VARCHAR(100) NOT NULL,
  rol       ENUM('colegiado','admin','ponente') DEFAULT 'colegiado',
  activo    TINYINT(1)   DEFAULT 1,
  creado_en TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_usuario_matricula (matricula)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE recuperacion_password (
  id INT AUTO_INCREMENT PRIMARY KEY,
  matricula VARCHAR(30) NOT NULL,
  correo VARCHAR(120) NOT NULL,
  codigo_hash VARCHAR(128) NOT NULL,
  usado TINYINT(1) NOT NULL DEFAULT 0,
  fecha_expiracion DATETIME NOT NULL,
  usado_en DATETIME NULL,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_recuperacion_matricula (matricula, usado, fecha_expiracion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 4. TABLA: cuotas
-- -------------------------------------------------------
CREATE TABLE cuotas (
  id           INT           AUTO_INCREMENT PRIMARY KEY,
  colegiado_id INT           NOT NULL,
  fecha        DATE          NOT NULL,
  fecha_emision DATE,
  fecha_vencimiento DATE,
  fecha_pago   DATE,
  concepto     VARCHAR(200)  NOT NULL,
  monto        DECIMAL(10,2) NOT NULL,
  estado       VARCHAR(20)   NOT NULL DEFAULT 'Pendiente',
  tipo         VARCHAR(20)   NOT NULL DEFAULT 'otro',
  periodo_mes  INT,
  periodo_anio INT,
  curso_id     INT,
  inscripcion_id INT,
  creado_en    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_cuotas_tipo_periodo (tipo, periodo_anio, periodo_mes),
  INDEX idx_cuotas_curso (curso_id, inscripcion_id),
  INDEX idx_cuotas_estado_fecha (estado, fecha),
  CONSTRAINT fk_cuotas_colegiados
    FOREIGN KEY (colegiado_id) REFERENCES colegiados(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 5. TABLA: medios_pago
-- -------------------------------------------------------
CREATE TABLE medios_pago (
  id            INT           AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(100)  NOT NULL,
  descripcion   VARCHAR(255),
  numero_cuenta VARCHAR(80)   NOT NULL,
  titular       VARCHAR(150)  NOT NULL,
  activo        TINYINT(1)    NOT NULL DEFAULT 1,
  creado_en     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 6. TABLA: evidencias_pago
-- -------------------------------------------------------
CREATE TABLE evidencias_pago (
  id               INT           AUTO_INCREMENT PRIMARY KEY,
  cuota_id         INT           NOT NULL,
  colegiado_id     INT           NOT NULL,
  medio_pago_id    INT           NOT NULL,
  fecha_pago       DATE          NOT NULL,
  numero_operacion VARCHAR(80)   NOT NULL,
  monto            DECIMAL(10,2) NOT NULL,
  comentario       TEXT,
  archivo          VARCHAR(255),
  estado           VARCHAR(20)   NOT NULL DEFAULT 'Pendiente',
  accion_revision  VARCHAR(30),
  revisado_por_matricula VARCHAR(30),
  revisado_por_nombre VARCHAR(150),
  detalle_revision TEXT,
  revisado_en      TIMESTAMP NULL,
  creado_en        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_evidencia_cuota (cuota_id),
  INDEX idx_evidencia_colegiado (colegiado_id),
  INDEX idx_evidencias_estado_fecha (estado, creado_en),
  CONSTRAINT fk_evidencias_cuotas
    FOREIGN KEY (cuota_id) REFERENCES cuotas(id) ON DELETE CASCADE,
  CONSTRAINT fk_evidencias_colegiados
    FOREIGN KEY (colegiado_id) REFERENCES colegiados(id) ON DELETE CASCADE,
  CONSTRAINT fk_evidencias_medios
    FOREIGN KEY (medio_pago_id) REFERENCES medios_pago(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 7. TABLA: transacciones_pago
-- -------------------------------------------------------
CREATE TABLE transacciones_pago (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  cuota_id            INT NOT NULL,
  colegiado_id        INT NOT NULL,
  evidencia_id        INT,
  proveedor           VARCHAR(80) NOT NULL DEFAULT 'Pasarela Interna CCPL',
  metodo              VARCHAR(60) NOT NULL,
  codigo_transaccion  VARCHAR(80) NOT NULL,
  codigo_autorizacion VARCHAR(80),
  monto               DECIMAL(10,2) NOT NULL,
  moneda              VARCHAR(10) NOT NULL DEFAULT 'PEN',
  estado              VARCHAR(20) NOT NULL DEFAULT 'Pendiente',
  respuesta_pasarela  TEXT,
  pagado_en           DATETIME NULL,
  creado_en           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_transaccion_codigo (codigo_transaccion),
  INDEX idx_transacciones_cuota (cuota_id),
  INDEX idx_transacciones_colegiado (colegiado_id),
  INDEX idx_transacciones_evidencia (evidencia_id),
  INDEX idx_transacciones_estado (estado, creado_en),
  CONSTRAINT fk_transacciones_cuotas
    FOREIGN KEY (cuota_id) REFERENCES cuotas(id) ON DELETE CASCADE,
  CONSTRAINT fk_transacciones_colegiados
    FOREIGN KEY (colegiado_id) REFERENCES colegiados(id) ON DELETE CASCADE,
  CONSTRAINT fk_transacciones_evidencias
    FOREIGN KEY (evidencia_id) REFERENCES evidencias_pago(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 8. TABLA: comprobantes_pago
-- -------------------------------------------------------
CREATE TABLE comprobantes_pago (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  transaccion_id    INT NOT NULL,
  cuota_id          INT NOT NULL,
  colegiado_id      INT NOT NULL,
  evidencia_id      INT,
  tipo_comprobante  VARCHAR(30) NOT NULL DEFAULT 'Boleta Interna',
  serie             VARCHAR(10) NOT NULL,
  numero            INT NOT NULL,
  fecha_emision     DATE NOT NULL,
  concepto          VARCHAR(200) NOT NULL,
  subtotal          DECIMAL(10,2) NOT NULL,
  igv               DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  total             DECIMAL(10,2) NOT NULL,
  moneda            VARCHAR(10) NOT NULL DEFAULT 'PEN',
  estado            VARCHAR(20) NOT NULL DEFAULT 'Emitido',
  codigo_hash       VARCHAR(120),
  anulado_por_matricula VARCHAR(30),
  anulado_por_nombre VARCHAR(150),
  motivo_anulacion  TEXT,
  anulado_en        TIMESTAMP NULL,
  creado_en         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_comprobante_numero (tipo_comprobante, serie, numero),
  INDEX idx_comprobantes_cuota (cuota_id),
  INDEX idx_comprobantes_colegiado (colegiado_id),
  INDEX idx_comprobantes_evidencia (evidencia_id),
  CONSTRAINT fk_comprobantes_transacciones
    FOREIGN KEY (transaccion_id) REFERENCES transacciones_pago(id) ON DELETE CASCADE,
  CONSTRAINT fk_comprobantes_cuotas
    FOREIGN KEY (cuota_id) REFERENCES cuotas(id) ON DELETE CASCADE,
  CONSTRAINT fk_comprobantes_colegiados
    FOREIGN KEY (colegiado_id) REFERENCES colegiados(id) ON DELETE CASCADE,
  CONSTRAINT fk_comprobantes_evidencias
    FOREIGN KEY (evidencia_id) REFERENCES evidencias_pago(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 9. TABLAS: Mercado Pago
-- -------------------------------------------------------
CREATE TABLE configuracion_mercado_pago (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  access_token VARCHAR(255),
  public_key   VARCHAR(255),
  modo         VARCHAR(20) NOT NULL DEFAULT 'TEST',
  activo       TINYINT(1) NOT NULL DEFAULT 1,
  creado_en    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO configuracion_mercado_pago
(access_token, public_key, modo, activo)
VALUES (NULL, NULL, 'TEST', 1);

CREATE TABLE ordenes_mercado_pago (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  cuota_id            INT NOT NULL,
  colegiado_id        INT NOT NULL,
  external_reference  VARCHAR(120) NOT NULL,
  preference_id       VARCHAR(120),
  init_point          TEXT,
  sandbox_init_point  TEXT,
  estado              VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
  mp_payment_id       VARCHAR(80),
  mp_status           VARCHAR(50),
  mp_status_detail    VARCHAR(120),
  merchant_order_id   VARCHAR(80),
  respuesta_preferencia MEDIUMTEXT,
  respuesta_pago      MEDIUMTEXT,
  creado_en           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  actualizado_en      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_mp_external_reference (external_reference),
  INDEX idx_mp_cuota (cuota_id),
  INDEX idx_mp_estado (estado, creado_en),
  CONSTRAINT fk_mp_orden_cuota
    FOREIGN KEY (cuota_id) REFERENCES cuotas(id) ON DELETE CASCADE,
  CONSTRAINT fk_mp_orden_colegiado
    FOREIGN KEY (colegiado_id) REFERENCES colegiados(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 10. TABLAS: facturacion preparada para SUNAT
-- -------------------------------------------------------
CREATE TABLE configuracion_facturacion (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  ruc                  VARCHAR(11)  NOT NULL DEFAULT '00000000000',
  razon_social         VARCHAR(200) NOT NULL DEFAULT 'Colegio de Contadores Publicos de Lambayeque',
  nombre_comercial     VARCHAR(150) NOT NULL DEFAULT 'CCPL',
  direccion            VARCHAR(255) DEFAULT 'Lambayeque',
  serie_boleta         VARCHAR(10)  NOT NULL DEFAULT 'B001',
  serie_factura        VARCHAR(10)  NOT NULL DEFAULT 'F001',
  correlativo_boleta   INT          NOT NULL DEFAULT 1,
  correlativo_factura  INT          NOT NULL DEFAULT 1,
  modo_envio           VARCHAR(20)  NOT NULL DEFAULT 'SUNAT_BETA',
  usuario_sol          VARCHAR(80)  NULL,
  clave_sol            VARCHAR(120) NULL,
  certificado_ruta     VARCHAR(255) NULL,
  certificado_clave    VARCHAR(120) NULL,
  endpoint_beta        VARCHAR(255) NOT NULL DEFAULT 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService',
  activo               TINYINT(1)   NOT NULL DEFAULT 1,
  actualizado_en       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO configuracion_facturacion
(ruc, razon_social, nombre_comercial, direccion, serie_boleta, serie_factura,
 correlativo_boleta, correlativo_factura, modo_envio, endpoint_beta, activo)
VALUES
('00000000000', 'Colegio de Contadores Publicos de Lambayeque', 'CCPL',
 'Lambayeque', 'B001', 'F001', 1, 1, 'SUNAT_BETA',
 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService', 1);

CREATE TABLE comprobantes_fiscales (
  id                       INT AUTO_INCREMENT PRIMARY KEY,
  comprobante_pago_id      INT NOT NULL,
  transaccion_id           INT NOT NULL,
  cuota_id                 INT NOT NULL,
  colegiado_id             INT NOT NULL,
  tipo_comprobante         VARCHAR(20) NOT NULL,
  serie                    VARCHAR(10) NOT NULL,
  numero                   INT NOT NULL,
  fecha_emision            DATE NOT NULL,
  enviado_en               DATETIME NULL,
  tipo_documento_cliente   VARCHAR(20),
  numero_documento_cliente VARCHAR(20),
  cliente_nombre           VARCHAR(150) NOT NULL,
  cliente_correo           VARCHAR(120),
  concepto                 VARCHAR(200) NOT NULL,
  subtotal                 DECIMAL(10,2) NOT NULL,
  igv                      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  total                    DECIMAL(10,2) NOT NULL,
  moneda                   VARCHAR(10) NOT NULL DEFAULT 'PEN',
  estado                   VARCHAR(20) NOT NULL DEFAULT 'Pendiente',
  ticket_sunat             VARCHAR(80),
  codigo_sunat             VARCHAR(80),
  cdr_estado               VARCHAR(40),
  cdr_descripcion          TEXT,
  codigo_hash              VARCHAR(120),
  xml_archivo              VARCHAR(255),
  pdf_archivo              VARCHAR(255),
  json_envio               MEDIUMTEXT,
  respuesta_sunat          MEDIUMTEXT,
  emitido_por_matricula    VARCHAR(30),
  emitido_por_nombre       VARCHAR(150),
  anulado_por_matricula    VARCHAR(30),
  anulado_por_nombre       VARCHAR(150),
  motivo_anulacion         TEXT,
  anulado_en               TIMESTAMP NULL,
  creado_en                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_cf_comprobante_pago (comprobante_pago_id),
  UNIQUE KEY uq_cf_numero (tipo_comprobante, serie, numero),
  INDEX idx_cf_estado_fecha (estado, fecha_emision),
  INDEX idx_cf_colegiado (colegiado_id),
  CONSTRAINT fk_cf_comprobante_pago
    FOREIGN KEY (comprobante_pago_id) REFERENCES comprobantes_pago(id) ON DELETE CASCADE,
  CONSTRAINT fk_cf_transaccion
    FOREIGN KEY (transaccion_id) REFERENCES transacciones_pago(id) ON DELETE CASCADE,
  CONSTRAINT fk_cf_cuota
    FOREIGN KEY (cuota_id) REFERENCES cuotas(id) ON DELETE CASCADE,
  CONSTRAINT fk_cf_colegiado
    FOREIGN KEY (colegiado_id) REFERENCES colegiados(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE comprobante_fiscal_detalle (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  comprobante_fiscal_id INT NOT NULL,
  descripcion           VARCHAR(220) NOT NULL,
  cantidad              DECIMAL(10,2) NOT NULL DEFAULT 1.00,
  valor_unitario        DECIMAL(10,2) NOT NULL,
  subtotal              DECIMAL(10,2) NOT NULL,
  igv                   DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  total                 DECIMAL(10,2) NOT NULL,
  CONSTRAINT fk_cf_detalle
    FOREIGN KEY (comprobante_fiscal_id) REFERENCES comprobantes_fiscales(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE facturacion_sunat_logs (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  comprobante_fiscal_id INT NOT NULL,
  accion                VARCHAR(40) NOT NULL,
  estado                VARCHAR(30) NOT NULL,
  mensaje               TEXT,
  payload               MEDIUMTEXT,
  creado_en             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_fact_logs_cf (comprobante_fiscal_id),
  CONSTRAINT fk_fact_logs_cf
    FOREIGN KEY (comprobante_fiscal_id) REFERENCES comprobantes_fiscales(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 11. TABLA: cursos
-- -------------------------------------------------------
CREATE TABLE cursos (
  id           INT          AUTO_INCREMENT PRIMARY KEY,
  categoria    VARCHAR(80)  NOT NULL,
  titulo       VARCHAR(200) NOT NULL,
  descripcion  TEXT,
  monto        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  monto_inhabil DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  ponente      VARCHAR(150) NOT NULL DEFAULT 'Por definir',
  modalidad    VARCHAR(20)  NOT NULL DEFAULT 'Virtual',
  duracion_horas INT        NOT NULL DEFAULT 1,
  fecha_inicio DATE,
  fecha_fin    DATE,
  cupos        INT          NOT NULL DEFAULT 1,
  fecha_evento VARCHAR(100),
  estado       VARCHAR(20)  NOT NULL DEFAULT 'Activo',
  creado_en    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_cursos_titulo (titulo),
  INDEX idx_cursos_estado_inicio (estado, fecha_inicio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 10. TABLA: contenido_curso
-- -------------------------------------------------------
CREATE TABLE contenido_curso (
  id          INT          AUTO_INCREMENT PRIMARY KEY,
  curso_id    INT          NOT NULL,
  titulo      VARCHAR(160) NOT NULL,
  descripcion TEXT         NOT NULL,
  enlace      VARCHAR(255),
  archivo     VARCHAR(255),
  creado_en   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_contenido_curso (curso_id),
  CONSTRAINT fk_contenido_cursos
    FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 11. TABLA: inscripciones_curso
-- -------------------------------------------------------
CREATE TABLE inscripciones_curso (
  id           INT          AUTO_INCREMENT PRIMARY KEY,
  curso_id     INT          NOT NULL,
  colegiado_id INT          NOT NULL,
  progreso     INT          NOT NULL DEFAULT 0,
  estado_pago  VARCHAR(20)  NOT NULL DEFAULT 'Pendiente',
  certificado   VARCHAR(255),
  creado_en    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_inscripcion (curso_id, colegiado_id),
  INDEX idx_inscripciones_colegiado_pago (colegiado_id, estado_pago),
  CONSTRAINT fk_inscripciones_cursos
    FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE RESTRICT,
  CONSTRAINT fk_inscripciones_colegiados
    FOREIGN KEY (colegiado_id) REFERENCES colegiados(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 12. TABLA: tramites
-- -------------------------------------------------------
CREATE TABLE tramites (
  id              INT          AUTO_INCREMENT PRIMARY KEY,
  matricula       VARCHAR(30)  NOT NULL,
  nombre          VARCHAR(150) NOT NULL,
  tipo_tramite    VARCHAR(80)  NOT NULL,
  asunto          VARCHAR(150) NOT NULL,
  descripcion     TEXT         NOT NULL,
  archivo_solicitud VARCHAR(255),
  archivo_respuesta VARCHAR(255),
  estado          VARCHAR(30)  DEFAULT 'Pendiente',
  accion_revision VARCHAR(30),
  revisado_por_matricula VARCHAR(30),
  revisado_por_nombre VARCHAR(150),
  detalle_revision TEXT,
  revisado_en     TIMESTAMP NULL,
  fecha_solicitud DATE         NOT NULL,
  fecha_respuesta DATE         NULL,
  estado_firma    VARCHAR(30)  DEFAULT 'Pendiente',
  tipo_firma      VARCHAR(30),
  firmado_por_matricula VARCHAR(30),
  firmado_por_nombre VARCHAR(150),
  firmado_en      TIMESTAMP NULL,
  detalle_firma   TEXT,
  creado_en       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  actualizado_en  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_tramites_matricula (matricula),
  INDEX idx_tramites_estado_fecha (estado, fecha_solicitud),
  INDEX idx_tramites_tipo_estado (tipo_tramite, estado),
  INDEX idx_tramites_firma (estado_firma, tipo_firma)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 14. TABLA: tickets
-- -------------------------------------------------------
CREATE TABLE tickets (
  id          INT          AUTO_INCREMENT PRIMARY KEY,
  matricula   VARCHAR(30)  NOT NULL,
  categoria   VARCHAR(50)  DEFAULT 'general',
  asunto      VARCHAR(200) NOT NULL,
  descripcion TEXT         NOT NULL,
  estado      VARCHAR(20)  DEFAULT 'Abierto',
  respuesta_admin TEXT,
  creado_en   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  respondido_en TIMESTAMP  NULL,
  actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_matricula_ticket (matricula),
  INDEX idx_tickets_estado_fecha (estado, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 13. TABLA: notificaciones
-- -------------------------------------------------------
CREATE TABLE notificaciones (
  id            INT          AUTO_INCREMENT PRIMARY KEY,
  colegiado_id  INT          NOT NULL,
  tipo          VARCHAR(20)  NOT NULL,
  titulo        VARCHAR(200) NOT NULL,
  mensaje       TEXT         NOT NULL,
  link_endpoint VARCHAR(120),
  link_url      VARCHAR(500),
  link_text     VARCHAR(120),
  relacion_tipo VARCHAR(20),
  relacion_id   INT,
  leido         TINYINT(1)   DEFAULT 0,
  creado_en     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  leido_en      TIMESTAMP    NULL,
  INDEX idx_notifs_colegiado (colegiado_id),
  INDEX idx_notifs_leido (colegiado_id, leido),
  CONSTRAINT fk_notifs_colegiados
    FOREIGN KEY (colegiado_id) REFERENCES colegiados(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- DATOS DE EJEMPLO
-- ============================================================

-- -------------------------------------------------------
-- Colegiados
-- -------------------------------------------------------
INSERT INTO colegiados (nombre, matricula, documento, especialidad_id, especialidad, correo, telefono, direccion, vigencia, estado, epc_points) VALUES
  ('Ricardo Alberto Mendoza Villalobos', '12455-A', '45829301',
   5, 'Tributacion Empresarial',
   'r.mendoza@ccpl.pe', '987 654 321', 'Av. Salaverry 245, Chiclayo',
   '31 de Diciembre de 2025', 'Vigente', 124),
  ('Carlos Enrique Mendoza Ruiz', '45678-B', '47561230',
   4, 'Auditor Financiero',
   'c.mendoza@ccpl.pe', '987 111 222', 'Calle Los Cedros 118, Lambayeque',
   '31 de Diciembre de 2025', 'Vigente', 80),
  ('Maria Isabel Torres Llontop', '23456-C', '36781290',
   8, 'Costos y Presupuestos',
   'm.torres@ccpl.pe', '987 333 444', 'Urb. Santa Victoria Mz. C Lt. 9, Chiclayo',
   '31 de Diciembre de 2025', 'Vigente', 60),
  ('Jorge Luis Diaz Fernandez', '67890-D', '52134678',
   3, 'Auditor Independiente',
   'j.diaz@ccpl.pe', '987 555 666', 'Jr. San Jose 410, Ferrenafe',
   '31 de Diciembre de 2024', 'Inactivo', 0);

UPDATE colegiados
   SET fecha_colegiatura = CASE matricula
     WHEN '12455-A' THEN '1997-02-15'
     WHEN '45678-B' THEN '1996-09-20'
     WHEN '23456-C' THEN '2004-05-12'
     WHEN '67890-D' THEN '1990-03-08'
     ELSE fecha_colegiatura
   END;

-- -------------------------------------------------------
-- Usuarios
-- -------------------------------------------------------
INSERT INTO usuarios (matricula, password, rol) VALUES
  ('12455-A', 'cpc123',    'colegiado'),
  ('45678-B', 'cpc456',    'colegiado'),
  ('23456-C', 'cpc789',    'colegiado'),
  ('admin',   'admin2024', 'admin'),
  ('ponente',  'ponente123', 'ponente'),
  ('ponente1', 'ponente123', 'ponente'),
  ('ponente2', 'ponente123', 'ponente'),
  ('ponente3', 'ponente123', 'ponente'),
  ('ponente4', 'ponente123', 'ponente'),
  ('ponente5', 'ponente123', 'ponente');

-- -------------------------------------------------------
-- Cuotas de Ricardo (id=1)
-- -------------------------------------------------------
INSERT INTO cuotas (colegiado_id, fecha, concepto, monto, estado) VALUES
  (1, '2024-12-15', 'Cuotas Ordinarias - Diciembre 2024',      80.00, 'Pendiente'),
  (1, '2024-11-15', 'Cuotas Ordinarias - Noviembre 2024',      80.00, 'Pendiente'),
  (1, '2024-11-02', 'Inscripcion Curso: NIIF Avanzadas 2024', 120.00, 'Pagado'),
  (1, '2024-10-15', 'Cuotas Ordinarias - Octubre 2024',        80.00, 'Pagado'),
  (1, '2024-09-15', 'Cuotas Ordinarias - Septiembre 2024',     80.00, 'Pagado'),
  (1, '2024-08-02', 'Constancia de Habilidad',                 90.00, 'Pagado'),
  (1, '2024-07-15', 'Cuotas Ordinarias - Julio 2024',          80.00, 'Pagado'),
  (1, '2024-06-15', 'Cuotas Ordinarias - Junio 2024',          80.00, 'Pagado'),
  (1, '2024-05-15', 'Cuotas Ordinarias - Mayo 2024',           80.00, 'Pagado'),
  (1, '2024-04-15', 'Cuotas Ordinarias - Abril 2024',          80.00, 'Pagado'),
  (1, '2024-03-15', 'Cuotas Ordinarias - Marzo 2024',          80.00, 'Pagado'),
  (1, '2024-02-10', 'Constancia de Colegiatura',               90.00, 'Pagado'),
  (1, '2024-01-15', 'Cuotas Ordinarias - Enero 2024',          80.00, 'Pagado');

-- -------------------------------------------------------
-- Cuotas de Carlos (id=2)
-- -------------------------------------------------------
INSERT INTO cuotas (colegiado_id, fecha, concepto, monto, estado) VALUES
  (2, '2024-12-15', 'Cuotas Ordinarias - Diciembre 2024',       80.00, 'Pendiente'),
  (2, '2024-11-15', 'Cuotas Ordinarias - Noviembre 2024',       80.00, 'Pagado'),
  (2, '2024-10-15', 'Cuotas Ordinarias - Octubre 2024',         80.00, 'Pagado'),
  (2, '2024-09-15', 'Cuotas Ordinarias - Septiembre 2024',      80.00, 'Pagado'),
  (2, '2024-08-15', 'Cuotas Ordinarias - Agosto 2024',          80.00, 'Pagado'),
  (2, '2024-07-15', 'Cuotas Ordinarias - Julio 2024',           80.00, 'Pagado'),
  (2, '2024-06-20', 'Constancia de Habilidad Profesional',      90.00, 'Pagado'),
  (2, '2024-05-15', 'Cuotas Ordinarias - Mayo 2024',            80.00, 'Pagado'),
  (2, '2024-04-12', 'Inscripcion Curso: NIIF para Pymes',      130.00, 'Pagado'),
  (2, '2024-03-15', 'Cuotas Ordinarias - Marzo 2024',           80.00, 'Pagado'),
  (2, '2024-02-15', 'Cuotas Ordinarias - Febrero 2024',         80.00, 'Pagado'),
  (2, '2024-01-15', 'Cuotas Ordinarias - Enero 2024',           80.00, 'Pagado');

-- -------------------------------------------------------
-- Cuotas de Maria (id=3)
-- -------------------------------------------------------
INSERT INTO cuotas (colegiado_id, fecha, concepto, monto, estado) VALUES
  (3, '2024-12-15', 'Cuotas Ordinarias - Diciembre 2024',        80.00, 'Pagado'),
  (3, '2024-11-02', 'Inscripcion Curso: Control Interno 2024',  150.00, 'Pagado'),
  (3, '2024-10-15', 'Cuotas Ordinarias - Octubre 2024',          80.00, 'Pagado'),
  (3, '2024-09-15', 'Cuotas Ordinarias - Septiembre 2024',       80.00, 'Pagado'),
  (3, '2024-08-20', 'Constancia de Habilidad Profesional',       90.00, 'Pagado'),
  (3, '2024-07-15', 'Cuotas Ordinarias - Julio 2024',            80.00, 'Pagado'),
  (3, '2024-06-15', 'Cuotas Ordinarias - Junio 2024',            80.00, 'Pagado'),
  (3, '2024-05-10', 'Inscripcion Seminario: Auditoria Moderna', 120.00, 'Pagado'),
  (3, '2024-04-15', 'Cuotas Ordinarias - Abril 2024',            80.00, 'Pagado'),
  (3, '2024-03-15', 'Cuotas Ordinarias - Marzo 2024',            80.00, 'Pagado'),
  (3, '2024-02-15', 'Cuotas Ordinarias - Febrero 2024',          80.00, 'Pagado'),
  (3, '2024-01-15', 'Cuotas Ordinarias - Enero 2024',            80.00, 'Pagado');

-- -------------------------------------------------------
-- Medios de pago
-- -------------------------------------------------------
INSERT INTO medios_pago (nombre, descripcion, numero_cuenta, titular, activo) VALUES
  ('Banco de Credito del Peru', 'Cuenta corriente institucional', '191-12345678-0-12', 'Colegio de Contadores Publicos de Lambayeque', 1),
  ('Yape Institucional', 'Pagos por aplicativo movil', '987654321', 'Colegio de Contadores Publicos de Lambayeque', 1),
  ('Plin Institucional', 'Pagos por aplicativo movil', '987654322', 'Colegio de Contadores Publicos de Lambayeque', 1);

-- -------------------------------------------------------
-- Catalogo de cursos
-- -------------------------------------------------------
INSERT INTO cursos (categoria, titulo, descripcion, monto, monto_inhabil, ponente, modalidad, duracion_horas, fecha_inicio, fecha_fin, cupos, fecha_evento, estado) VALUES
  ('Especializacion',       'Actualizacion Tributaria: Cierre Contable 2023', 'Curso de actualizacion tributaria y cierre contable.', 180.00, 220.00, 'CPC Luis Salazar', 'Virtual', 12, '2024-03-01', '2024-03-15', 40, 'Del 2024-03-01 al 2024-03-15', 'Activo'),
  ('Seminario Web',         'Auditoria Financiera Basada en Riesgos (NIIF)',  'Seminario sobre auditoria financiera bajo enfoque de riesgos.', 95.00, 120.00, 'CPC Ana Rojas', 'Virtual', 4, '2024-04-22', '2024-04-22', 80, 'Fecha: 2024-04-22', 'Activo'),
  ('Certificacion Externa', 'Herramientas Digitales para Gestion Tributaria', 'Certificacion sobre herramientas digitales tributarias.', 220.00, 270.00, 'Mg. Marco Silva', 'Mixta', 18, '2024-05-05', '2024-05-30', 35, 'Del 2024-05-05 al 2024-05-30', 'Activo'),
  ('Especializacion',       'NIIF Avanzadas para Reportes Financieros',       'Especializacion en reportes financieros bajo NIIF.', 250.00, 310.00, 'CPC Patricia Leon', 'Presencial', 20, '2024-06-12', '2024-06-28', 30, 'Del 2024-06-12 al 2024-06-28', 'Activo'),
  ('Taller Practico',       'Uso de Excel para Auditoria Profesional',        'Taller practico de Excel aplicado a auditoria.', 120.00, 150.00, 'CPC Rosa Medina', 'Presencial', 8, '2024-01-30', '2024-01-30', 25, 'Fecha: 2024-01-30', 'Activo'),
  ('Especializacion',       'NIIF para Pymes: Aplicacion Practica',           'Curso de aplicacion practica de NIIF para pymes.', 200.00, 245.00, 'CPC Luis Salazar', 'Virtual', 16, '2024-06-01', '2024-06-30', 45, 'Del 2024-06-01 al 2024-06-30', 'Activo'),
  ('Seminario Web',         'Tributacion Internacional',                      'Seminario de tributacion internacional.', 100.00, 130.00, 'CPC Ana Rojas', 'Virtual', 5, '2024-02-01', '2024-02-01', 70, 'Fecha: 2024-02-01', 'Activo'),
  ('Taller Practico',       'Gestion Tributaria Digital',                     'Taller sobre gestion tributaria digital.', 140.00, 175.00, 'Mg. Marco Silva', 'Mixta', 10, '2024-09-20', '2024-09-21', 35, 'Del 2024-09-20 al 2024-09-21', 'Activo'),
  ('Seminario Web',         'Control Interno y Gestion de Riesgos',           'Seminario sobre control interno y riesgos.', 90.00, 115.00, 'CPC Patricia Leon', 'Virtual', 4, '2024-05-10', '2024-05-10', 80, 'Fecha: 2024-05-10', 'Activo'),
  ('Certificacion',         'Gestion Financiera Moderna',                     'Certificacion en gestion financiera moderna.', 260.00, 320.00, 'CPC Rosa Medina', 'Mixta', 24, '2024-07-25', '2024-08-20', 30, 'Del 2024-07-25 al 2024-08-20', 'Activo');

-- -------------------------------------------------------
-- Contenido de cursos
-- -------------------------------------------------------
INSERT INTO contenido_curso (curso_id, titulo, descripcion, enlace) VALUES
  (1, 'Tema 1 - Planeamiento tributario', 'Revision de obligaciones tributarias y calendario de cierre contable.', ''),
  (1, 'Tema 2 - Casos practicos', 'Aplicacion de ajustes tributarios con ejemplos para empresas locales.', ''),
  (2, 'Material base de auditoria', 'Lectura inicial sobre enfoque basado en riesgos y papeles de trabajo.', ''),
  (6, 'Introduccion a NIIF para Pymes', 'Conceptos clave y alcance de la norma para pequenas y medianas empresas.', '');

-- -------------------------------------------------------
-- Inscripciones de ejemplo
-- -------------------------------------------------------
INSERT INTO inscripciones_curso (curso_id, colegiado_id, progreso, estado_pago) VALUES
  (1, 1, 100, 'Pagado'),
  (2, 1, 45,  'Pagado'),
  (3, 1, 15,  'Pendiente'),
  (4, 1, 70,  'Pagado'),
  (5, 1, 100, 'Pagado'),
  (6, 2, 80,  'Pagado'),
  (7, 2, 100, 'Pagado'),
  (8, 2, 40,  'Pendiente'),
  (9, 3, 60,  'Pagado'),
  (10, 3, 20, 'Pendiente');

-- -------------------------------------------------------
-- Tramites
-- -------------------------------------------------------
INSERT INTO tramites
(matricula, nombre, tipo_tramite, asunto, descripcion, archivo_solicitud,
 estado, detalle_revision, fecha_solicitud, fecha_respuesta)
VALUES
  ('12455-A', 'Ricardo Alberto Mendoza Villalobos', 'certificado_habilidad',
   'Certificado de habilidad para licitacion',
   'Solicito certificado de habilidad para presentarlo en un proceso de licitacion publica.',
   '', 'Pendiente', NULL, '2026-06-10', NULL),
  ('23456-C', 'Maria Isabel Torres Llontop', 'constancia_colegiatura',
   'Constancia de colegiatura',
   'Necesito constancia de colegiatura para un tramite notarial.',
   '', 'Aprobado', 'Constancia emitida por administracion.', '2026-06-08', '2026-06-09'),
  ('67890-D', 'Jorge Luis Diaz Fernandez', 'baja_colegiatura',
   'Baja definitiva por jubilacion',
   'Solicito baja de colegiatura por jubilacion y cierre de actividades profesionales.',
   'uploads/tramites/demo_sustento_baja_jorge.pdf',
   'En Revision', 'Tramite tomado para revision administrativa.', '2026-06-05', NULL),
  ('45678-B', 'Carlos Enrique Mendoza Ruiz', 'traslado_colegio',
   'Traslado a otro colegio profesional',
   'Solicito traslado al Colegio de Contadores de Lima por cambio de domicilio laboral.',
   'uploads/tramites/demo_sustento_traslado_carlos.pdf',
   'Pendiente', NULL, '2026-06-11', NULL);

-- -------------------------------------------------------
-- Tickets de soporte
-- -------------------------------------------------------
INSERT INTO tickets (matricula, categoria, asunto, descripcion, estado, respuesta_admin, respondido_en) VALUES
  ('12455-A', 'pagos',    'No puedo registrar pago de cuota', 'Al intentar registrar el pago del mes de diciembre el sistema me devuelve un error.', 'Abierto', NULL, NULL),
  ('45678-B', 'acceso',   'No puedo ingresar al sistema',     'Mi contrasenia no funciona desde ayer, necesito que la reseteen.', 'En Revision', 'Se revisara el acceso y se notificara cuando se actualice la cuenta.', NOW()),
  ('23456-C', 'constancia','Solicitud de constancia urgente', 'Necesito la constancia de habilidad para tramite notarial urgente.', 'Cerrado', 'Su constancia ya fue validada. Puede descargarla desde el modulo de constancia.', NOW()),
  ('12455-A', 'cursos',   'Error al descargar certificado',   'El boton de descarga del certificado del curso NIIF no responde.', 'Abierto', NULL, NULL);

-- -------------------------------------------------------
-- Notificaciones de Ricardo (id=1)
-- -------------------------------------------------------
INSERT INTO notificaciones (colegiado_id, tipo, titulo, mensaje, link_endpoint, link_text, relacion_tipo, relacion_id, leido) VALUES
  (1, 'cuota', 'Cuota pendiente de pago',
   'Tienes una cuota pendiente de <strong>S/ 80.00</strong> correspondiente a Cuotas Ordinarias - Diciembre 2024.',
   'estado_cuenta', 'Ver Estado de Cuenta', 'cuota', 1, 0),
  (1, 'cuota', 'Cuota pendiente de pago',
   'Tienes una cuota pendiente de <strong>S/ 80.00</strong> correspondiente a Cuotas Ordinarias - Noviembre 2024.',
   'estado_cuenta', 'Ver Estado de Cuenta', 'cuota', 2, 0),
  (1, 'sistema', 'Bienvenido al portal CCPL',
   'Bienvenido a la Intranet del Colegio de Contadores de Lambayeque. Aqui puedes gestionar tus cuotas, cursos, constancias y mas.',
   'dashboard', 'Ir al Panel', NULL, NULL, 1),
  (1, 'curso', 'Curso con pago pendiente',
   'El curso <strong>Herramientas Digitales para Gestion Tributaria</strong> tiene un pago pendiente.',
   'educacion_continua', 'Ver Cursos', 'curso', 3, 0),
  (1, 'sistema', 'Actualizacion de datos disponible',
   'Te recordamos mantener actualizados tus datos personales en el sistema del colegio profesional.',
   'perfil_soporte', 'Actualizar Perfil', NULL, NULL, 0),
  (1, 'curso', 'Nuevo material disponible',
   'Se ha subido nuevo material del curso <strong>Auditoria Financiera Basada en Riesgos</strong>.',
   'educacion_continua', 'Ver Curso', 'curso', 2, 0);

-- -------------------------------------------------------
-- Notificaciones de Carlos (id=2)
-- -------------------------------------------------------
INSERT INTO notificaciones (colegiado_id, tipo, titulo, mensaje, link_endpoint, link_text, relacion_tipo, relacion_id, leido) VALUES
  (2, 'cuota', 'Cuota pendiente de pago',
   'Tienes una cuota pendiente de <strong>S/ 80.00</strong> correspondiente a Cuotas Ordinarias - Diciembre 2024.',
   'estado_cuenta', 'Ver Estado de Cuenta', 'cuota', 7, 0),
  (2, 'sistema', 'Bienvenido al portal CCPL',
   'Bienvenido a la Intranet del Colegio de Contadores de Lambayeque.',
   'dashboard', 'Ir al Panel', NULL, NULL, 1),
  (2, 'curso', 'Curso actualizado',
   'El curso <strong>NIIF para Pymes: Aplicacion Practica</strong> ha actualizado su contenido recientemente.',
   'educacion_continua', 'Ver Curso', 'curso', 1, 0),
  (2, 'sistema', 'Perfil incompleto',
   'Te recomendamos completar tu informacion personal en el sistema del colegio profesional.',
   'perfil_soporte', 'Completar Perfil', NULL, NULL, 0);

-- -------------------------------------------------------
-- Notificaciones de Maria (id=3)
-- -------------------------------------------------------
INSERT INTO notificaciones (colegiado_id, tipo, titulo, mensaje, link_endpoint, link_text, relacion_tipo, relacion_id, leido) VALUES
  (3, 'sistema', 'Bienvenido al portal CCPL',
   'Bienvenido a la Intranet del Colegio de Contadores de Lambayeque.',
   'dashboard', 'Ir al Panel', NULL, NULL, 1),
  (3, 'curso', 'Curso con pago pendiente',
   'El curso <strong>Contabilidad de Costos Avanzada</strong> tiene un pago pendiente. Regulariza para continuar.',
   'educacion_continua', 'Ver Cursos', 'curso', NULL, 0),
  (3, 'curso', 'Nuevo curso disponible',
   'Se ha habilitado contenido actualizado en el curso <strong>Control Interno y Gestion de Riesgos</strong>.',
   'educacion_continua', 'Ver Curso', 'curso', 1, 0),
  (3, 'sistema', 'Recordatorio de perfil',
   'Mantén tus datos actualizados para acceder a todos los servicios del colegio profesional.',
   'perfil_soporte', 'Actualizar Datos', NULL, NULL, 0),
  (3, 'cuota', 'Estado de cuenta disponible',
   'Revisa tu estado de cuenta actualizado y verifica tus pagos registrados.',
   'estado_cuenta', 'Ver Estado', 'cuota', NULL, 0);
