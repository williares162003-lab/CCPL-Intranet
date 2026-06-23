# Firmador eDNI CCPL

Este paquete permite firmar certificados de habilidad desde la computadora del administrador usando el DNI electronico.

El sistema web puede estar publicado en PythonAnywhere, pero la firma se hace en la PC donde estan conectados el lector USB y el DNIe.

## Archivos incluidos

- `firmador_edni_local.py`: servicio local que lee el DNIe y firma el PDF.
- `instalar_firmador_edni.bat`: instala las dependencias de Python necesarias.
- `iniciar_firmador_edni.bat`: inicia el firmador local en `http://127.0.0.1:8765`.
- `requirements_firmador.txt`: librerias usadas por el firmador.
- `opensc-dnie-peru.conf`: configuracion de apoyo para lectores compatibles.

## Requisitos previos

1. Tener Python instalado en Windows.
2. Tener conectado el lector de tarjeta inteligente.
3. Instalar el driver oficial del DNIe desde la pagina de RENIEC:
   `https://identidad.reniec.gob.pe/dni-electronico`
4. Insertar el DNIe y conocer el PIN de firma.

## Instalacion

1. Descomprimir este ZIP en una carpeta de la computadora del administrador.
2. Ejecutar `instalar_firmador_edni.bat`.
3. Esperar a que termine la instalacion.
4. Ejecutar `iniciar_firmador_edni.bat`.
5. Dejar abierta esa ventana mientras se firme desde el sistema.

## Uso desde el sistema

1. Entrar al sistema publicado.
2. Ir a `Tramites`.
3. Abrir el tramite de certificado de habilidad.
4. Presionar `Firmar con eDNI`.
5. Presionar `Verificar`.
6. Si el DNIe esta listo, ingresar el PIN y presionar `Firmar con eDNI`.

El PDF firmado se registra automaticamente en el tramite y queda disponible para el colegiado.

## Seguridad

El PIN no se guarda en el sistema. Solo se envia al firmador local durante la firma.

La clave privada del DNIe nunca sale del chip. El servidor recibe solamente el PDF ya firmado.

## Problemas comunes

- `Modulo de firma no disponible`: abra `iniciar_firmador_edni.bat`.
- `Lector no conectado`: revise el cable USB o cambie de puerto.
- `DNIe no insertado`: inserte correctamente el DNIe en el lector.
- `Middleware requerido`: instale o reinstale el driver oficial de RENIEC / IDPlug.
- `PIN incorrecto`: verifique el PIN de firma del DNIe.
