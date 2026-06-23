USE colegiocontadores;

CREATE TABLE IF NOT EXISTS recuperacion_password (
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
