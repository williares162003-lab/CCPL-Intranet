-- ============================================================
--  Portal CCPL | Reset de datos de prueba para presentacion
--  Ejecutar en phpMyAdmin con la BD "colegiocontadores" activa
--  IMPORTANTE: limpia los datos actuales y vuelve a poblar la BD.
-- ============================================================

USE colegiocontadores;

CREATE TABLE IF NOT EXISTS especialidades_colegiado (
  id        INT          AUTO_INCREMENT PRIMARY KEY,
  nombre    VARCHAR(120) NOT NULL,
  activo    TINYINT(1)   NOT NULL DEFAULT 1,
  creado_en TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_especialidad_colegiado_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @col_esp_id := (
  SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'colegiados'
     AND COLUMN_NAME = 'especialidad_id'
);

SET @col_esp_id_sql := IF(
  @col_esp_id = 0,
  'ALTER TABLE colegiados ADD COLUMN especialidad_id INT NULL AFTER documento',
  'SELECT 1'
);

PREPARE col_esp_id_stmt FROM @col_esp_id_sql;
EXECUTE col_esp_id_stmt;
DEALLOCATE PREPARE col_esp_id_stmt;

SET @col_direccion := (
  SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'colegiados'
     AND COLUMN_NAME = 'direccion'
);

SET @col_direccion_sql := IF(
  @col_direccion = 0,
  "ALTER TABLE colegiados ADD COLUMN direccion VARCHAR(255) NOT NULL DEFAULT 'Sin registrar' AFTER telefono",
  'SELECT 1'
);

PREPARE col_direccion_stmt FROM @col_direccion_sql;
EXECUTE col_direccion_stmt;
DEALLOCATE PREPARE col_direccion_stmt;

-- Asegura columnas de auditoria para evidencias de pago.
SET @audit_cols := (
  SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'evidencias_pago'
     AND COLUMN_NAME = 'revisado_por_matricula'
);

SET @audit_sql := IF(
  @audit_cols = 0,
  'ALTER TABLE evidencias_pago
     ADD COLUMN accion_revision VARCHAR(30) NULL AFTER estado,
     ADD COLUMN revisado_por_matricula VARCHAR(30) NULL AFTER accion_revision,
     ADD COLUMN revisado_por_nombre VARCHAR(150) NULL AFTER revisado_por_matricula,
     ADD COLUMN detalle_revision TEXT NULL AFTER revisado_por_nombre,
     ADD COLUMN revisado_en TIMESTAMP NULL AFTER detalle_revision',
  'SELECT 1'
);

PREPARE audit_stmt FROM @audit_sql;
EXECUTE audit_stmt;
DEALLOCATE PREPARE audit_stmt;

-- Asegura columnas para comunicacion con SUNAT beta.
CREATE TABLE IF NOT EXISTS configuracion_facturacion (
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

SET @fact_usuario_sol := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN usuario_sol VARCHAR(80) NULL AFTER modo_envio",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'usuario_sol'
);
PREPARE fact_usuario_sol_stmt FROM @fact_usuario_sol;
EXECUTE fact_usuario_sol_stmt;
DEALLOCATE PREPARE fact_usuario_sol_stmt;

SET @fact_clave_sol := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN clave_sol VARCHAR(120) NULL AFTER usuario_sol",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'clave_sol'
);
PREPARE fact_clave_sol_stmt FROM @fact_clave_sol;
EXECUTE fact_clave_sol_stmt;
DEALLOCATE PREPARE fact_clave_sol_stmt;

SET @fact_cert_ruta := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN certificado_ruta VARCHAR(255) NULL AFTER clave_sol",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'certificado_ruta'
);
PREPARE fact_cert_ruta_stmt FROM @fact_cert_ruta;
EXECUTE fact_cert_ruta_stmt;
DEALLOCATE PREPARE fact_cert_ruta_stmt;

SET @fact_cert_clave := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN certificado_clave VARCHAR(120) NULL AFTER certificado_ruta",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'certificado_clave'
);
PREPARE fact_cert_clave_stmt FROM @fact_cert_clave;
EXECUTE fact_cert_clave_stmt;
DEALLOCATE PREPARE fact_cert_clave_stmt;

SET @fact_endpoint_beta := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN endpoint_beta VARCHAR(255) NOT NULL DEFAULT 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService' AFTER certificado_clave",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'endpoint_beta'
);
PREPARE fact_endpoint_beta_stmt FROM @fact_endpoint_beta;
EXECUTE fact_endpoint_beta_stmt;
DEALLOCATE PREPARE fact_endpoint_beta_stmt;

CREATE TABLE IF NOT EXISTS transacciones_pago (
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

CREATE TABLE IF NOT EXISTS comprobantes_pago (
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

SET @trx_evi_cols := (
  SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'transacciones_pago'
     AND COLUMN_NAME = 'evidencia_id'
);

SET @trx_evi_sql := IF(
  @trx_evi_cols = 0,
  'ALTER TABLE transacciones_pago
     ADD COLUMN evidencia_id INT NULL AFTER colegiado_id,
     ADD INDEX idx_transacciones_evidencia (evidencia_id)',
  'SELECT 1'
);

PREPARE trx_evi_stmt FROM @trx_evi_sql;
EXECUTE trx_evi_stmt;
DEALLOCATE PREPARE trx_evi_stmt;

SET @comp_evi_cols := (
  SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'comprobantes_pago'
     AND COLUMN_NAME = 'evidencia_id'
);

SET @comp_evi_sql := IF(
  @comp_evi_cols = 0,
  'ALTER TABLE comprobantes_pago
     ADD COLUMN evidencia_id INT NULL AFTER colegiado_id,
     ADD INDEX idx_comprobantes_evidencia (evidencia_id)',
  'SELECT 1'
);

PREPARE comp_evi_stmt FROM @comp_evi_sql;
EXECUTE comp_evi_stmt;
DEALLOCATE PREPARE comp_evi_stmt;

SET @comp_audit_cols := (
  SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'comprobantes_pago'
     AND COLUMN_NAME = 'anulado_por_matricula'
);

SET @comp_audit_sql := IF(
  @comp_audit_cols = 0,
  'ALTER TABLE comprobantes_pago
     ADD COLUMN anulado_por_matricula VARCHAR(30) NULL AFTER codigo_hash,
     ADD COLUMN anulado_por_nombre VARCHAR(150) NULL AFTER anulado_por_matricula,
     ADD COLUMN motivo_anulacion TEXT NULL AFTER anulado_por_nombre,
     ADD COLUMN anulado_en TIMESTAMP NULL AFTER motivo_anulacion',
  'SELECT 1'
);

PREPARE comp_audit_stmt FROM @comp_audit_sql;
EXECUTE comp_audit_stmt;
DEALLOCATE PREPARE comp_audit_stmt;

SET @col_fecha_col := (
  SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'colegiados'
     AND COLUMN_NAME = 'fecha_colegiatura'
);

SET @sql_fecha_col := IF(
  @col_fecha_col = 0,
  'ALTER TABLE colegiados ADD COLUMN fecha_colegiatura DATE NULL AFTER direccion',
  'SELECT 1'
);

PREPARE stmt_fecha_col FROM @sql_fecha_col;
EXECUTE stmt_fecha_col;
DEALLOCATE PREPARE stmt_fecha_col;

SET @idx_fecha_col := (
  SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'colegiados'
     AND INDEX_NAME = 'idx_colegiados_fecha_col'
);

SET @sql_idx_fecha_col := IF(
  @idx_fecha_col = 0,
  'ALTER TABLE colegiados ADD INDEX idx_colegiados_fecha_col (fecha_colegiatura, estado)',
  'SELECT 1'
);

PREPARE stmt_idx_fecha_col FROM @sql_idx_fecha_col;
EXECUTE stmt_idx_fecha_col;
DEALLOCATE PREPARE stmt_idx_fecha_col;

CREATE TABLE IF NOT EXISTS tramites (
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
  creado_en       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  actualizado_en  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_tramites_matricula (matricula),
  INDEX idx_tramites_estado_fecha (estado, fecha_solicitud),
  INDEX idx_tramites_tipo_estado (tipo_tramite, estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Limpiar datos
-- ------------------------------------------------------------
SET FOREIGN_KEY_CHECKS = 0;

SET @del_mp_orden := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_mercado_pago') = 1,
  'DELETE FROM ordenes_mercado_pago',
  'SELECT 1'
);
PREPARE del_mp_orden_stmt FROM @del_mp_orden;
EXECUTE del_mp_orden_stmt;
DEALLOCATE PREPARE del_mp_orden_stmt;

SET @del_mp_cfg := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_mercado_pago') = 1,
  'DELETE FROM configuracion_mercado_pago',
  'SELECT 1'
);
PREPARE del_mp_cfg_stmt FROM @del_mp_cfg;
EXECUTE del_mp_cfg_stmt;
DEALLOCATE PREPARE del_mp_cfg_stmt;

SET @del_fact_logs := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'facturacion_sunat_logs') = 1,
  'DELETE FROM facturacion_sunat_logs',
  'SELECT 1'
);
PREPARE del_fact_logs_stmt FROM @del_fact_logs;
EXECUTE del_fact_logs_stmt;
DEALLOCATE PREPARE del_fact_logs_stmt;

SET @del_fact_det := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'comprobante_fiscal_detalle') = 1,
  'DELETE FROM comprobante_fiscal_detalle',
  'SELECT 1'
);
PREPARE del_fact_det_stmt FROM @del_fact_det;
EXECUTE del_fact_det_stmt;
DEALLOCATE PREPARE del_fact_det_stmt;

SET @del_fact_comp := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'comprobantes_fiscales') = 1,
  'DELETE FROM comprobantes_fiscales',
  'SELECT 1'
);
PREPARE del_fact_comp_stmt FROM @del_fact_comp;
EXECUTE del_fact_comp_stmt;
DEALLOCATE PREPARE del_fact_comp_stmt;

SET @del_fact_cfg := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_facturacion') = 1,
  'DELETE FROM configuracion_facturacion',
  'SELECT 1'
);
PREPARE del_fact_cfg_stmt FROM @del_fact_cfg;
EXECUTE del_fact_cfg_stmt;
DEALLOCATE PREPARE del_fact_cfg_stmt;

DELETE FROM comprobantes_pago;
DELETE FROM transacciones_pago;
DELETE FROM evidencias_pago;
DELETE FROM notificaciones;
DELETE FROM tickets;
DELETE FROM tramites;
DELETE FROM contenido_curso;
DELETE FROM inscripciones_curso;
DELETE FROM cuotas;
DELETE FROM cursos;
DELETE FROM medios_pago;
DELETE FROM usuarios;
DELETE FROM colegiados;
DELETE FROM especialidades_colegiado;
SET FOREIGN_KEY_CHECKS = 1;

ALTER TABLE especialidades_colegiado AUTO_INCREMENT = 1;
ALTER TABLE colegiados AUTO_INCREMENT = 1;
ALTER TABLE usuarios AUTO_INCREMENT = 1;
ALTER TABLE cuotas AUTO_INCREMENT = 1;
ALTER TABLE transacciones_pago AUTO_INCREMENT = 1;
ALTER TABLE comprobantes_pago AUTO_INCREMENT = 1;

SET @ai_mp_cfg := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_mercado_pago') = 1,
  'ALTER TABLE configuracion_mercado_pago AUTO_INCREMENT = 1',
  'SELECT 1'
);
PREPARE ai_mp_cfg_stmt FROM @ai_mp_cfg;
EXECUTE ai_mp_cfg_stmt;
DEALLOCATE PREPARE ai_mp_cfg_stmt;

SET @ai_mp_orden := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_mercado_pago') = 1,
  'ALTER TABLE ordenes_mercado_pago AUTO_INCREMENT = 1',
  'SELECT 1'
);
PREPARE ai_mp_orden_stmt FROM @ai_mp_orden;
EXECUTE ai_mp_orden_stmt;
DEALLOCATE PREPARE ai_mp_orden_stmt;

SET @ai_fact_cfg := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_facturacion') = 1,
  'ALTER TABLE configuracion_facturacion AUTO_INCREMENT = 1',
  'SELECT 1'
);
PREPARE ai_fact_cfg_stmt FROM @ai_fact_cfg;
EXECUTE ai_fact_cfg_stmt;
DEALLOCATE PREPARE ai_fact_cfg_stmt;

SET @ai_fact_comp := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'comprobantes_fiscales') = 1,
  'ALTER TABLE comprobantes_fiscales AUTO_INCREMENT = 1',
  'SELECT 1'
);
PREPARE ai_fact_comp_stmt FROM @ai_fact_comp;
EXECUTE ai_fact_comp_stmt;
DEALLOCATE PREPARE ai_fact_comp_stmt;

SET @ai_fact_det := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'comprobante_fiscal_detalle') = 1,
  'ALTER TABLE comprobante_fiscal_detalle AUTO_INCREMENT = 1',
  'SELECT 1'
);
PREPARE ai_fact_det_stmt FROM @ai_fact_det;
EXECUTE ai_fact_det_stmt;
DEALLOCATE PREPARE ai_fact_det_stmt;

SET @ai_fact_logs := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'facturacion_sunat_logs') = 1,
  'ALTER TABLE facturacion_sunat_logs AUTO_INCREMENT = 1',
  'SELECT 1'
);
PREPARE ai_fact_logs_stmt FROM @ai_fact_logs;
EXECUTE ai_fact_logs_stmt;
DEALLOCATE PREPARE ai_fact_logs_stmt;

ALTER TABLE medios_pago AUTO_INCREMENT = 1;
ALTER TABLE evidencias_pago AUTO_INCREMENT = 1;
ALTER TABLE cursos AUTO_INCREMENT = 1;
ALTER TABLE contenido_curso AUTO_INCREMENT = 1;
ALTER TABLE inscripciones_curso AUTO_INCREMENT = 1;
ALTER TABLE tramites AUTO_INCREMENT = 1;
ALTER TABLE tickets AUTO_INCREMENT = 1;
ALTER TABLE notificaciones AUTO_INCREMENT = 1;

SET @ins_fact_cfg := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_facturacion') = 1,
  "INSERT INTO configuracion_facturacion
   (ruc, razon_social, nombre_comercial, direccion, serie_boleta, serie_factura,
    correlativo_boleta, correlativo_factura, modo_envio, endpoint_beta, activo)
   VALUES
   ('00000000000', 'Colegio de Contadores Publicos de Lambayeque', 'CCPL',
    'Lambayeque', 'B001', 'F001', 1, 1, 'SUNAT_BETA',
    'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService', 1)",
  'SELECT 1'
);
PREPARE ins_fact_cfg_stmt FROM @ins_fact_cfg;
EXECUTE ins_fact_cfg_stmt;
DEALLOCATE PREPARE ins_fact_cfg_stmt;

SET @ins_mp_cfg := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'configuracion_mercado_pago') = 1,
  "INSERT INTO configuracion_mercado_pago
   (access_token, public_key, modo, activo)
   VALUES (NULL, NULL, 'TEST', 1)",
  'SELECT 1'
);
PREPARE ins_mp_cfg_stmt FROM @ins_mp_cfg;
EXECUTE ins_mp_cfg_stmt;
DEALLOCATE PREPARE ins_mp_cfg_stmt;

-- ------------------------------------------------------------
-- Colegiados
-- ------------------------------------------------------------
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

INSERT INTO colegiados
(nombre, matricula, documento, especialidad_id, especialidad, correo, telefono, direccion, vigencia, estado, epc_points)
VALUES
('Ricardo Alberto Mendoza Villalobos', '12455-A', '45829301', 5, 'Tributacion Empresarial', 'ricardo.mendoza@ccpl.pe', '987654321', 'Av. Salaverry 245, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 124),
('Carlos Enrique Mendoza Ruiz', '45678-B', '47561230', 4, 'Auditor Financiero', 'carlos.mendoza@ccpl.pe', '987111222', 'Calle Los Cedros 118, Lambayeque', '31 de Diciembre de 2026', 'Vigente', 86),
('Maria Isabel Torres Llontop', '23456-C', '36781290', 8, 'Costos y Presupuestos', 'maria.torres@ccpl.pe', '987333444', 'Urb. Santa Victoria Mz. C Lt. 9, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 72),
('Jorge Luis Diaz Fernandez', '67890-D', '52134678', 3, 'Auditor Independiente', 'jorge.diaz@ccpl.pe', '987555666', 'Jr. San Jose 410, Ferrenafe', '31 de Diciembre de 2025', 'Inactivo', 12),
('Maria Fernanda Torres Prado', '90001-T', '70900001', 7, 'Finanzas Corporativas', 'maria.fernanda@ccpl.pe', '987200001', 'Av. Grau 765, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 110),
('Jose Antonio Rivas Campos', '90002-T', '70900002', 5, 'Tributacion Empresarial', 'jose.rivas@ccpl.pe', '987200002', 'Calle San Martin 220, Lambayeque', '31 de Diciembre de 2026', 'Vigente', 95),
('Ana Lucia Perez Salas', '90003-T', '70900003', 6, 'Contabilidad Gubernamental', 'ana.perez@ccpl.pe', '987200003', 'Urb. Los Parques Mz. D Lt. 14, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 68),
('Luis Alberto Chavez Nunez', '90004-T', '70900004', 7, 'Finanzas Corporativas', 'luis.chavez@ccpl.pe', '987200004', 'Av. Bolognesi 521, Jose Leonardo Ortiz', '31 de Diciembre de 2026', 'Vigente', 84),
('Rosa Milagros Herrera Vega', '90005-T', '70900005', 1, 'Contador Publico Colegiado', 'rosa.herrera@ccpl.pe', '987200005', 'Calle Union 174, Pimentel', '31 de Diciembre de 2026', 'Vigente', 51),
('Marco Antonio Silva Paredes', '90006-T', '70900006', 2, 'Perito Contable', 'marco.silva@ccpl.pe', '987200006', 'Av. Balta 982, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 76),
('Karla Patricia Leon Diaz', '90007-T', '70900007', 9, 'NIIF y Reportes Financieros', 'karla.leon@ccpl.pe', '987200007', 'Urb. Latina Mz. B Lt. 5, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 132),
('Victor Manuel Ramos Garcia', '90008-T', '70900008', 8, 'Costos y Presupuestos', 'victor.ramos@ccpl.pe', '987200008', 'Calle Tacna 336, Lambayeque', '31 de Diciembre de 2026', 'Vigente', 64),
('Elena Sofia Medina Castro', '90009-T', '70900009', 10, 'Control Interno', 'elena.medina@ccpl.pe', '987200009', 'Av. America 150, La Victoria', '31 de Diciembre de 2026', 'Vigente', 70),
('Fernando Isaac Pinedo Reyna', '90010-T', '70900010', 7, 'Finanzas Corporativas', 'fernando.pinedo@ccpl.pe', '987200010', 'Jr. Atahualpa 345, Monsefu', '31 de Diciembre de 2026', 'Vigente', 40),
('Diana Carolina Bravo Ruiz', '90011-T', '70900011', 4, 'Auditor Financiero', 'diana.bravo@ccpl.pe', '987200011', 'Av. Leguia 602, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 88),
('Cesar Augusto Castillo Muro', '90012-T', '70900012', 1, 'Contador Publico Colegiado', 'cesar.castillo@ccpl.pe', '987200012', 'Calle Elias Aguirre 711, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 55),
('Paola Andrea Vasquez Rojas', '90013-T', '70900013', 10, 'Control Interno', 'paola.vasquez@ccpl.pe', '987200013', 'Urb. Federico Villarreal Mz. H Lt. 3, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 102),
('Miguel Angel Carranza Soto', '90014-T', '70900014', 5, 'Tributacion Empresarial', 'miguel.carranza@ccpl.pe', '987200014', 'Av. Progreso 251, Lambayeque', '31 de Diciembre de 2025', 'Inactivo', 18),
('Teresa Milagros Guevara Diaz', '90015-T', '70900015', 3, 'Auditor Independiente', 'teresa.guevara@ccpl.pe', '987200015', 'Calle Comercio 412, Tuman', '31 de Diciembre de 2026', 'Vigente', 77),
('Oscar Eduardo Salazar Prieto', '90016-T', '70900016', 1, 'Contador Publico Colegiado', 'oscar.salazar@ccpl.pe', '987200016', 'Av. Elvira Garcia 834, Chiclayo', '31 de Diciembre de 2026', 'Vigente', 48);

UPDATE colegiados
   SET fecha_colegiatura = CASE matricula
     WHEN '12455-A' THEN '1997-02-15'
     WHEN '45678-B' THEN '1996-09-20'
     WHEN '23456-C' THEN '2004-05-12'
     WHEN '67890-D' THEN '1990-03-08'
     WHEN '90001-T' THEN '1997-01-18'
     WHEN '90002-T' THEN '1996-12-05'
     WHEN '90003-T' THEN '2001-07-24'
     WHEN '90004-T' THEN '1998-11-11'
     WHEN '90005-T' THEN '2006-03-19'
     WHEN '90006-T' THEN '1997-06-30'
     WHEN '90007-T' THEN '2000-09-04'
     WHEN '90008-T' THEN '2002-02-21'
     WHEN '90009-T' THEN '2005-08-15'
     WHEN '90010-T' THEN '1999-10-10'
     WHEN '90011-T' THEN '1996-08-28'
     WHEN '90012-T' THEN '2003-01-17'
     WHEN '90013-T' THEN '1997-04-02'
     WHEN '90014-T' THEN '1995-12-14'
     WHEN '90015-T' THEN '1998-05-09'
     WHEN '90016-T' THEN '2007-06-01'
     ELSE fecha_colegiatura
   END;

-- ------------------------------------------------------------
-- Usuarios principales de prueba
-- ------------------------------------------------------------
INSERT INTO usuarios (matricula, password, rol, activo)
VALUES
('admin', 'admin2024', 'admin', 1),
('12455-A', 'cpc123', 'colegiado', 1),
('45678-B', 'cpc456', 'colegiado', 1),
('23456-C', 'cpc789', 'colegiado', 1),
('90001-T', 'cpc123', 'colegiado', 1),
('90002-T', 'cpc123', 'colegiado', 1),
('90003-T', 'cpc123', 'colegiado', 1),
('90004-T', 'cpc123', 'colegiado', 1),
('90005-T', 'cpc123', 'colegiado', 1),
('90006-T', 'cpc123', 'colegiado', 1),
('90007-T', 'cpc123', 'colegiado', 1),
('90008-T', 'cpc123', 'colegiado', 1),
('90009-T', 'cpc123', 'colegiado', 1),
('90010-T', 'cpc123', 'colegiado', 1),
('90011-T', 'cpc123', 'colegiado', 1),
('90012-T', 'cpc123', 'colegiado', 1),
('90013-T', 'cpc123', 'colegiado', 1),
('90014-T', 'cpc123', 'colegiado', 0),
('90015-T', 'cpc123', 'colegiado', 1),
('90016-T', 'cpc123', 'colegiado', 1),
('ponente', 'ponente123', 'ponente', 1),
('ponente1', 'ponente123', 'ponente', 1),
('ponente2', 'ponente123', 'ponente', 1),
('ponente3', 'ponente123', 'ponente', 1),
('ponente4', 'ponente123', 'ponente', 1),
('ponente5', 'ponente123', 'ponente', 1);

-- ------------------------------------------------------------
-- Medios de pago
-- ------------------------------------------------------------
INSERT INTO medios_pago (nombre, descripcion, numero_cuenta, titular, activo)
VALUES
('Banco de Credito del Peru', 'Cuenta corriente institucional', '191-12345678-0-12', 'Colegio de Contadores Publicos de Lambayeque', 1),
('Yape Institucional', 'Pagos por aplicativo movil', '987654321', 'Colegio de Contadores Publicos de Lambayeque', 1),
('Plin Institucional', 'Pagos por aplicativo movil', '987654322', 'Colegio de Contadores Publicos de Lambayeque', 1),
('Caja CCPL', 'Pago presencial en oficina administrativa', 'CAJA-CCPL-001', 'Colegio de Contadores Publicos de Lambayeque', 1),
('Cuenta antigua', 'Medio de pago deshabilitado para pruebas', '000-000000', 'Colegio de Contadores Publicos de Lambayeque', 0);

-- ------------------------------------------------------------
-- Cursos
-- ------------------------------------------------------------
INSERT INTO cursos
(categoria, titulo, descripcion, monto, monto_inhabil, ponente, modalidad, duracion_horas, fecha_inicio, fecha_fin, cupos, fecha_evento, estado)
VALUES
('Certificacion', 'Curso Integral CCPL', 'Curso integral para probar inscripciones, pagos, materiales y certificados.', 160.00, 195.00, 'CPC Luis Salazar', 'Virtual', 18, '2026-06-10', '2026-07-05', 30, 'Del 2026-06-10 al 2026-07-05', 'Activo'),
('Especializacion', 'Actualizacion Tributaria 2026', 'Programa de actualizacion sobre renta, IGV, libros electronicos y fiscalizacion SUNAT.', 220.00, 270.00, 'CPC Ana Rojas', 'Virtual', 24, '2026-06-15', '2026-07-20', 35, 'Del 2026-06-15 al 2026-07-20', 'Activo'),
('Taller Practico', 'Excel Financiero para Contadores', 'Taller aplicado para conciliaciones, control de pagos, tablas dinamicas e indicadores.', 120.00, 150.00, 'Mg. Marco Silva', 'Presencial', 10, '2026-06-22', '2026-06-23', 25, 'Del 2026-06-22 al 2026-06-23', 'Activo'),
('Seminario Web', 'NIIF para Pymes Aplicacion Practica', 'Seminario con casos practicos de medicion, reconocimiento y revelacion bajo NIIF para Pymes.', 95.00, 120.00, 'CPC Patricia Leon', 'Virtual', 6, '2026-07-02', '2026-07-02', 80, 'Fecha: 2026-07-02', 'Activo'),
('Certificacion', 'Auditoria Financiera Basada en Riesgos', 'Certificacion con enfoque moderno de planeamiento, ejecucion y cierre de auditoria.', 260.00, 320.00, 'CPC Rosa Medina', 'Mixta', 30, '2026-07-08', '2026-08-12', 28, 'Del 2026-07-08 al 2026-08-12', 'Activo'),
('Especializacion', 'Gestion de Costos para Empresas Locales', 'Especializacion en costos, presupuestos y control gerencial para empresas comerciales.', 210.00, 260.00, 'CPC Luis Salazar', 'Presencial', 20, '2026-08-05', '2026-08-28', 32, 'Del 2026-08-05 al 2026-08-28', 'Activo'),
('Seminario Web', 'Fiscalizacion Electronica SUNAT', 'Seminario sobre notificaciones electronicas, esquelas, cartas inductivas y respuestas.', 90.00, 115.00, 'CPC Ana Rojas', 'Virtual', 4, '2026-05-18', '2026-05-18', 70, 'Fecha: 2026-05-18', 'Activo'),
('Taller Practico', 'Control Interno y Gestion de Riesgos', 'Taller para disenar matrices de riesgo y controles internos verificables.', 140.00, 175.00, 'Mg. Marco Silva', 'Mixta', 12, '2026-05-01', '2026-05-16', 30, 'Del 2026-05-01 al 2026-05-16', 'Activo'),
('Certificacion', 'Gestion Financiera Moderna', 'Certificacion sobre presupuesto, flujo de caja, rentabilidad e indicadores financieros.', 280.00, 340.00, 'CPC Patricia Leon', 'Virtual', 26, '2026-04-05', '2026-05-05', 30, 'Del 2026-04-05 al 2026-05-05', 'Activo'),
('Especializacion', 'Planeamiento Tributario Empresarial', 'Especializacion en planeamiento tributario preventivo para empresas regionales.', 240.00, 295.00, 'CPC Rosa Medina', 'Presencial', 22, '2026-03-10', '2026-04-10', 30, 'Del 2026-03-10 al 2026-04-10', 'Finalizado'),
('Seminario Web', 'Etica Profesional y Responsabilidad del Contador', 'Seminario institucional sobre etica, responsabilidad profesional y buenas practicas.', 60.00, 85.00, 'CPC Luis Salazar', 'Virtual', 3, '2026-02-15', '2026-02-15', 100, 'Fecha: 2026-02-15', 'Finalizado'),
('Taller Practico', 'Peritaje Contable Judicial', 'Taller introductorio para elaboracion de informes periciales contables.', 180.00, 220.00, 'CPC Ana Rojas', 'Presencial', 14, '2026-09-12', '2026-09-20', 22, 'Del 2026-09-12 al 2026-09-20', 'Activo');

-- ------------------------------------------------------------
-- Materiales de curso
-- ------------------------------------------------------------
INSERT INTO contenido_curso (curso_id, titulo, descripcion, enlace, archivo)
SELECT c.id,
       CONCAT('Material base - ', c.titulo),
       CONCAT('Lectura, guia y resumen del curso ', c.titulo),
       'https://www.ccplambayeque.org.pe/materiales',
       ''
  FROM cursos c;

INSERT INTO contenido_curso (curso_id, titulo, descripcion, enlace, archivo)
SELECT c.id,
       CONCAT('Caso practico - ', c.titulo),
       'Ejercicio aplicado o documento de apoyo para reforzar el tema tratado.',
       '',
       ''
  FROM cursos c
 WHERE c.estado <> 'Finalizado';

-- ------------------------------------------------------------
-- Inscripciones a cursos
-- ------------------------------------------------------------
INSERT INTO inscripciones_curso (curso_id, colegiado_id, progreso, estado_pago, certificado)
VALUES
(1, 1, 100, 'Pagado', 'uploads/certificados/demo_12455_curso_integral.pdf'),
(1, 5, 100, 'Pagado', 'uploads/certificados/demo_90001_curso_integral.pdf'),
(1, 6, 70, 'Pagado', NULL),
(1, 7, 35, 'Pagado', NULL),
(1, 8, 10, 'Pendiente', NULL),
(1, 9, 0, 'Pendiente', NULL),
(2, 1, 80, 'Pagado', NULL),
(2, 2, 45, 'Pagado', NULL),
(2, 3, 20, 'Pendiente', NULL),
(2, 10, 65, 'Pagado', NULL),
(2, 11, 0, 'Pendiente', NULL),
(3, 2, 100, 'Pagado', 'uploads/certificados/demo_45678_excel.pdf'),
(3, 5, 60, 'Pagado', NULL),
(3, 12, 20, 'Pendiente', NULL),
(4, 3, 100, 'Pagado', 'uploads/certificados/demo_23456_niif.pdf'),
(4, 6, 40, 'Pagado', NULL),
(4, 13, 0, 'Pendiente', NULL),
(5, 1, 30, 'Pendiente', NULL),
(5, 7, 55, 'Pagado', NULL),
(5, 14, 15, 'Pendiente', NULL),
(6, 8, 0, 'Pendiente', NULL),
(6, 9, 25, 'Pagado', NULL),
(6, 15, 70, 'Pagado', NULL),
(7, 2, 100, 'Pagado', 'uploads/certificados/demo_45678_sunat.pdf'),
(7, 10, 100, 'Pagado', NULL),
(7, 16, 60, 'Pagado', NULL),
(8, 3, 85, 'Pagado', NULL),
(8, 11, 30, 'Pendiente', NULL),
(8, 17, 45, 'Pagado', NULL),
(9, 5, 100, 'Pagado', 'uploads/certificados/demo_90001_financiera.pdf'),
(9, 12, 100, 'Pagado', NULL),
(9, 18, 40, 'Pendiente', NULL),
(10, 6, 100, 'Pagado', 'uploads/certificados/demo_90002_planeamiento.pdf'),
(10, 13, 100, 'Pagado', NULL),
(10, 19, 100, 'Pagado', NULL),
(11, 1, 100, 'Pagado', 'uploads/certificados/demo_12455_etica.pdf'),
(11, 2, 100, 'Pagado', NULL),
(11, 3, 100, 'Pagado', NULL),
(12, 4, 0, 'Pendiente', NULL),
(12, 20, 10, 'Pendiente', NULL);

-- ------------------------------------------------------------
-- Cuotas mensuales 2026
-- ------------------------------------------------------------
DROP TEMPORARY TABLE IF EXISTS tmp_meses;
CREATE TEMPORARY TABLE tmp_meses (
  mes INT NOT NULL,
  nombre VARCHAR(20) NOT NULL
);

INSERT INTO tmp_meses (mes, nombre)
VALUES
(1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
(5, 'Mayo'), (6, 'Junio');

INSERT INTO cuotas
(colegiado_id, fecha, fecha_emision, fecha_vencimiento, fecha_pago, concepto, monto, estado, tipo, periodo_mes, periodo_anio)
SELECT c.id,
       STR_TO_DATE(CONCAT('2026-', LPAD(m.mes, 2, '0'), '-01'), '%Y-%m-%d') AS fecha,
       STR_TO_DATE(CONCAT('2026-', LPAD(m.mes, 2, '0'), '-01'), '%Y-%m-%d') AS fecha_emision,
       LAST_DAY(STR_TO_DATE(CONCAT('2026-', LPAD(m.mes, 2, '0'), '-01'), '%Y-%m-%d')) AS fecha_vencimiento,
       CASE
         WHEN m.mes <= 4 OR (m.mes = 5 AND (c.id % 3) <> 0) OR (m.mes = 6 AND (c.id % 5) IN (0, 1))
         THEN DATE_ADD(STR_TO_DATE(CONCAT('2026-', LPAD(m.mes, 2, '0'), '-01'), '%Y-%m-%d'), INTERVAL 4 DAY)
         ELSE NULL
       END AS fecha_pago,
       CONCAT('Cuota ordinaria ', m.nombre, ' 2026') AS concepto,
       80.00 AS monto,
       CASE
         WHEN m.mes <= 4 OR (m.mes = 5 AND (c.id % 3) <> 0) OR (m.mes = 6 AND (c.id % 5) IN (0, 1))
         THEN 'Pagado'
         ELSE 'Pendiente'
       END AS estado,
       'mensual' AS tipo,
       m.mes AS periodo_mes,
       2026 AS periodo_anio
  FROM colegiados c
  JOIN tmp_meses m
 WHERE c.estado = 'Vigente';

-- Cuotas de cursos generadas desde inscripciones.
INSERT INTO cuotas
(colegiado_id, fecha, fecha_emision, fecha_vencimiento, fecha_pago, concepto, monto, estado, tipo, curso_id, inscripcion_id)
SELECT i.colegiado_id,
       c.fecha_inicio,
       c.fecha_inicio,
       DATE_ADD(c.fecha_inicio, INTERVAL 7 DAY),
       CASE WHEN i.estado_pago = 'Pagado' THEN DATE_SUB('2026-06-07', INTERVAL (i.id % 18) DAY) ELSE NULL END,
       CONCAT('Inscripcion Curso: ', c.titulo),
       c.monto,
       i.estado_pago,
       'curso',
       c.id,
       i.id
  FROM inscripciones_curso i
  JOIN cursos c ON c.id = i.curso_id;

-- ------------------------------------------------------------
-- Evidencias de pago con auditoria administrativa
-- ------------------------------------------------------------
INSERT INTO evidencias_pago
(cuota_id, colegiado_id, medio_pago_id, fecha_pago, numero_operacion, monto, comentario, archivo, estado,
 accion_revision, revisado_por_matricula, revisado_por_nombre, detalle_revision, revisado_en)
SELECT q.id, q.colegiado_id, 2, COALESCE(q.fecha_pago, '2026-06-06'),
       CONCAT('YAPE-', 100000 + q.id), q.monto,
       'Comprobante revisado para carga inicial.',
       CONCAT('uploads/evidencias/demo_aprobado_', q.id, '.pdf'),
       'Aprobado',
       'Aprobado',
       'admin',
       'Administrador CCPL',
       'Comprobante aprobado desde el panel administrativo.',
       '2026-06-06 10:30:00'
  FROM cuotas q
 WHERE q.estado = 'Pagado'
 ORDER BY q.id DESC
 LIMIT 18;

INSERT INTO evidencias_pago
(cuota_id, colegiado_id, medio_pago_id, fecha_pago, numero_operacion, monto, comentario, archivo, estado)
SELECT q.id, q.colegiado_id, 3, '2026-06-07',
       CONCAT('PLIN-', 200000 + q.id), q.monto,
       'Comprobante pendiente de revision por administracion.',
       CONCAT('uploads/evidencias/demo_pendiente_', q.id, '.pdf'),
       'Pendiente'
  FROM cuotas q
 WHERE q.estado = 'Pendiente'
 ORDER BY q.id DESC
 LIMIT 12;

INSERT INTO evidencias_pago
(cuota_id, colegiado_id, medio_pago_id, fecha_pago, numero_operacion, monto, comentario, archivo, estado,
 accion_revision, revisado_por_matricula, revisado_por_nombre, detalle_revision, revisado_en)
SELECT q.id, q.colegiado_id, 1, '2026-06-05',
       CONCAT('BCP-', 300000 + q.id), q.monto,
       'Monto no coincide con la cuota registrada.',
       CONCAT('uploads/evidencias/demo_anulado_', q.id, '.pdf'),
       'Rechazado',
       'Anulado',
       'admin',
       'Administrador CCPL',
       'Comprobante anulado porque el monto no coincide con la cuota.',
       '2026-06-05 16:20:00'
  FROM cuotas q
 WHERE q.estado = 'Pendiente'
 ORDER BY q.id ASC
 LIMIT 6;

-- ------------------------------------------------------------
-- Tramites
-- ------------------------------------------------------------
INSERT INTO tramites
(matricula, nombre, tipo_tramite, asunto, descripcion, archivo_solicitud, archivo_respuesta,
 estado, accion_revision, revisado_por_matricula, revisado_por_nombre, detalle_revision,
 revisado_en, fecha_solicitud, fecha_respuesta, estado_firma, tipo_firma,
 firmado_por_matricula, firmado_por_nombre, firmado_en, detalle_firma)
VALUES
('12455-A', 'Ricardo Alberto Mendoza Villalobos', 'certificado_habilidad', 'Certificado de habilidad para licitacion', 'Solicito certificado de habilidad para presentarlo en licitacion municipal.', '', '', 'Pendiente', NULL, NULL, NULL, NULL, NULL, '2026-06-08', NULL, 'Pendiente', NULL, NULL, NULL, NULL, NULL),
('23456-C', 'Maria Isabel Torres Llontop', 'constancia_colegiatura', 'Constancia de colegiatura', 'Necesito constancia para tramite notarial.', '', 'uploads/tramites/demo_constancia_maria.pdf', 'Aprobado', 'Aprobado', 'admin', 'Administrador CCPL', 'Constancia emitida por administracion.', '2026-06-09 10:30:00', '2026-06-07', '2026-06-09', 'No aplica', NULL, NULL, NULL, NULL, NULL),
('90003-T', 'Ana Lucia Perez Salas', 'certificado_habilidad', 'Certificado de habilidad para convocatoria', 'Solicito certificado de habilidad para convocatoria laboral.', '', '', 'En Revision', 'En Revision', 'admin', 'Administrador CCPL', 'Tramite tomado para revision administrativa.', '2026-06-10 09:20:00', '2026-06-09', NULL, 'Pendiente', NULL, NULL, NULL, NULL, NULL),
('67890-D', 'Jorge Luis Diaz Fernandez', 'baja_colegiatura', 'Baja definitiva por jubilacion', 'Solicito baja definitiva por jubilacion.', 'uploads/tramites/demo_sustento_baja_jorge.pdf', '', 'Pendiente', NULL, NULL, NULL, NULL, NULL, '2026-06-10', NULL, 'No aplica', NULL, NULL, NULL, NULL, NULL),
('90014-T', 'Miguel Angel Carranza Soto', 'traslado_colegio', 'Traslado a otro colegio', 'Solicito traslado a otro colegio de contadores por cambio de domicilio laboral.', 'uploads/tramites/demo_sustento_traslado_miguel.pdf', '', 'En Revision', 'En Revision', 'admin', 'Administrador CCPL', 'Documento recibido y en validacion administrativa.', '2026-06-10 15:35:00', '2026-06-10', NULL, 'No aplica', NULL, NULL, NULL, NULL, NULL),
('90008-T', 'Victor Manuel Ramos Garcia', 'otro', 'Rectificacion de datos registrados', 'Solicito corregir una observacion en mi informacion de contacto.', '', '', 'Rechazado', 'Rechazado', 'admin', 'Administrador CCPL', 'Debe actualizar primero su ficha de colegiado.', '2026-06-06 16:10:00', '2026-06-05', NULL, 'No aplica', NULL, NULL, NULL, NULL, NULL);

-- ------------------------------------------------------------
-- Tickets de soporte
-- ------------------------------------------------------------
INSERT INTO tickets
(matricula, categoria, asunto, descripcion, estado, respuesta_admin, respondido_en)
VALUES
('12455-A', 'pagos', 'No puedo registrar pago de cuota', 'Al subir la evidencia de pago la pantalla se queda cargando.', 'Abierto', NULL, NULL),
('45678-B', 'acceso', 'No puedo ingresar al sistema', 'Mi clave anterior dejo de funcionar y necesito ingresar al portal.', 'En Revision', 'Se esta validando la cuenta del colegiado.', '2026-06-06 09:10:00'),
('23456-C', 'constancia', 'Solicitud de constancia urgente', 'Necesito constancia para un tramite notarial.', 'Cerrado', 'La constancia fue generada y se encuentra disponible.', '2026-06-04 11:20:00'),
('90001-T', 'cursos', 'Error al descargar certificado', 'El certificado del curso integral aparece, pero no descarga.', 'Abierto', NULL, NULL),
('90003-T', 'pagos', 'Pago figura pendiente', 'Realice el pago por Plin, pero aun aparece pendiente.', 'En Revision', 'La evidencia esta pendiente de validacion por administracion.', '2026-06-06 15:30:00'),
('90007-T', 'perfil', 'Actualizar correo personal', 'Deseo cambiar el correo principal registrado.', 'Cerrado', 'El correo fue actualizado correctamente.', '2026-06-02 17:45:00'),
('90011-T', 'cursos', 'No veo mis materiales', 'Me inscribi a un curso, pero no aparecen los materiales publicados.', 'Abierto', NULL, NULL),
('90013-T', 'certificado', 'Certificado pendiente', 'Complete el curso, pero aun no aparece el certificado.', 'En Revision', 'El ponente esta validando el avance final.', '2026-06-05 10:00:00');

-- ------------------------------------------------------------
-- Notificaciones
-- ------------------------------------------------------------
INSERT INTO notificaciones
(colegiado_id, tipo, titulo, mensaje, link_endpoint, link_text, relacion_tipo, relacion_id, leido)
SELECT c.id, 'cuota', 'Cuota pendiente de pago',
       CONCAT('Tienes una cuota pendiente de <strong>S/ ', FORMAT(q.monto, 2), '</strong>: ', q.concepto, '.'),
       'estado_cuenta', 'Ver estado de cuenta', 'cuota', q.id, 0
  FROM cuotas q
  JOIN colegiados c ON c.id = q.colegiado_id
 WHERE q.estado = 'Pendiente'
 ORDER BY q.id DESC
 LIMIT 30;

INSERT INTO notificaciones
(colegiado_id, tipo, titulo, mensaje, link_endpoint, link_text, relacion_tipo, relacion_id, leido)
SELECT i.colegiado_id, 'curso', 'Curso asignado',
       CONCAT('Ya tienes acceso al curso <strong>', c.titulo, '</strong>. Revisa sus materiales publicados.'),
       'educacion_continua', 'Ver curso', 'curso', c.id, CASE WHEN i.progreso > 60 THEN 1 ELSE 0 END
  FROM inscripciones_curso i
  JOIN cursos c ON c.id = i.curso_id
 ORDER BY i.id DESC
 LIMIT 35;

INSERT INTO notificaciones
(colegiado_id, tipo, titulo, mensaje, link_endpoint, link_text, relacion_tipo, relacion_id, leido)
VALUES
(1, 'sistema', 'Bienvenido al portal CCPL', 'Puedes revisar tus cuotas, cursos, certificados y tickets desde la intranet.', 'dashboard', 'Ir al panel', NULL, NULL, 1),
(5, 'certificado', 'Certificado disponible', 'Tu certificado del Curso Integral CCPL ya esta disponible para descarga.', 'educacion_continua', 'Ver certificado', 'curso', 1, 0),
(6, 'ticket', 'Ticket en revision', 'Soporte esta revisando tu solicitud sobre acceso al sistema.', 'perfil_soporte', 'Ver soporte', 'ticket', 2, 0),
(7, 'curso', 'Material disponible', 'El ponente publico nuevo material para tu curso actual.', 'educacion_continua', 'Ver curso', 'curso', 1, 0),
(13, 'certificado', 'Certificado pendiente', 'Tu certificado se habilitara cuando el curso llegue a 100% y el pago este validado.', 'educacion_continua', 'Ver curso', 'curso', 5, 0);

DROP TEMPORARY TABLE IF EXISTS tmp_meses;

-- ------------------------------------------------------------
-- Accesos rapidos de prueba
-- ------------------------------------------------------------
-- Admin:      admin / admin2024
-- Ponente:    ponente / ponente123
-- Ponente 2:  ponente2 / ponente123
-- Colegiado:  12455-A / cpc123
-- Colegiado:  45678-B / cpc456
-- Colegiado:  23456-C / cpc789
-- Colegiado:  90001-T / cpc123
-- Colegiado:  90003-T / cpc123
