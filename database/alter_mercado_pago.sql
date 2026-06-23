USE colegiocontadores;

CREATE TABLE IF NOT EXISTS configuracion_mercado_pago (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  access_token    VARCHAR(255),
  public_key      VARCHAR(255),
  modo            VARCHAR(20) NOT NULL DEFAULT 'TEST',
  activo          TINYINT(1) NOT NULL DEFAULT 1,
  creado_en       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  actualizado_en  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ordenes_mercado_pago (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  cuota_id              INT NOT NULL,
  colegiado_id          INT NOT NULL,
  external_reference    VARCHAR(120) NOT NULL,
  preference_id         VARCHAR(120),
  init_point            TEXT,
  sandbox_init_point    TEXT,
  estado                VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
  mp_payment_id         VARCHAR(80),
  mp_status             VARCHAR(50),
  mp_status_detail      VARCHAR(120),
  merchant_order_id     VARCHAR(80),
  respuesta_preferencia MEDIUMTEXT,
  respuesta_pago        MEDIUMTEXT,
  creado_en             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  actualizado_en        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_mp_external_reference (external_reference),
  INDEX idx_mp_cuota (cuota_id),
  INDEX idx_mp_estado (estado, creado_en),
  CONSTRAINT fk_mp_orden_cuota
    FOREIGN KEY (cuota_id) REFERENCES cuotas(id) ON DELETE CASCADE,
  CONSTRAINT fk_mp_orden_colegiado
    FOREIGN KEY (colegiado_id) REFERENCES colegiados(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO configuracion_mercado_pago (access_token, public_key, modo, activo)
SELECT NULL, NULL, 'TEST', 1
WHERE NOT EXISTS (SELECT 1 FROM configuracion_mercado_pago);
