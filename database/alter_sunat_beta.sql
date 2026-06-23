-- ============================================================
--  Portal CCPL | Configuracion para comunicacion SUNAT beta
--  Ejecutar en phpMyAdmin con la BD "colegiocontadores" activa.
-- ============================================================

USE colegiocontadores;

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

SET @sql := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN usuario_sol VARCHAR(80) NULL AFTER modo_envio",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'usuario_sol'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN clave_sol VARCHAR(120) NULL AFTER usuario_sol",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'clave_sol'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN certificado_ruta VARCHAR(255) NULL AFTER clave_sol",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'certificado_ruta'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN certificado_clave VARCHAR(120) NULL AFTER certificado_ruta",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'certificado_clave'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(COUNT(*) = 0,
    "ALTER TABLE configuracion_facturacion ADD COLUMN endpoint_beta VARCHAR(255) NOT NULL DEFAULT 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService' AFTER certificado_clave",
    "SELECT 1")
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'configuracion_facturacion'
     AND COLUMN_NAME = 'endpoint_beta'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE configuracion_facturacion
   SET modo_envio = 'SUNAT_BETA',
       endpoint_beta = COALESCE(NULLIF(endpoint_beta, ''), 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService')
 WHERE activo = 1;

-- Cuando tengas credenciales reales, cambia los valores:
-- UPDATE configuracion_facturacion
--    SET ruc = 'RUC_DEL_COLEGIO',
--        usuario_sol = 'USUARIO_SOL_SECUNDARIO',
--        clave_sol = 'CLAVE_SOL',
--        certificado_ruta = 'C:/ruta/certificado.pfx',
--        certificado_clave = 'CLAVE_DEL_CERTIFICADO',
--        modo_envio = 'SUNAT_BETA'
--  WHERE activo = 1;
