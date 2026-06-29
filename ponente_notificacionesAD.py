from bd import obtenerconexion

# ============================================================
# NOTIFICACIONES DEL PONENTE
# ============================================================

def leer_notificaciones_ponente(p_ponente, p_limite=8):
    avisos = []
    try:
        resumen_seguimiento = resumir_seguimiento_ponente(p_ponente) or {}

        bajo = int(resumen_seguimiento.get("bajo_progreso") or 0)
        if bajo:
            avisos.append({
                "tipo": "curso",
                "titulo": "Bajo progreso",
                "mensaje": str(bajo) + " inscrito(s) tienen progreso menor a 50%.",
                "link_endpoint": "ponente_seguimiento",
                "link_text": "Ver seguimiento",
                "relacion_tipo": "seguimiento",
                "relacion_id": None,
                "leido": 0,
                "creado_en": "",
            })

        pagos = int(resumen_seguimiento.get("pagos_pendientes") or 0)
        if pagos:
            avisos.append({
                "tipo": "cuota",
                "titulo": "Pagos pendientes",
                "mensaje": str(pagos) + " inscrito(s) aún figuran con pago pendiente.",
                "link_endpoint": "ponente_seguimiento",
                "link_text": "Ver inscritos",
                "relacion_tipo": "pagos",
                "relacion_id": None,
                "leido": 0,
                "creado_en": "",
            })

        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cu.id, cu.titulo, cu.fecha_fin "
                    sql += "   FROM cursos cu "
                    sql += "  WHERE cu.ponente = %s "
                    sql += "    AND cu.estado = 'Activo' "
                    sql += "    AND cu.fecha_fin IS NOT NULL "
                    sql += "    AND cu.fecha_fin BETWEEN CURDATE() "
                    sql += "        AND DATE_ADD(CURDATE(), INTERVAL 7 DAY) "
                    sql += "  ORDER BY cu.fecha_fin ASC "
                    sql += "  LIMIT 3 "
                    cursor.execute(sql, (p_ponente,))
                    for curso in cursor.fetchall():
                        avisos.append({
                            "tipo": "curso",
                            "titulo": "Curso por finalizar",
                            "mensaje": str(curso["titulo"]) + " finaliza el " +
                                       str(curso["fecha_fin"]) + ".",
                            "link_endpoint": "ponente_curso",
                            "link_text": "Ver curso",
                            "relacion_tipo": "curso",
                            "relacion_id": curso["id"],
                            "leido": 0,
                            "creado_en": "",
                        })

        return avisos[:int(p_limite)]
    except Exception as e:
        print(repr(e))
        return avisos[:int(p_limite)]


def contar_notificaciones_ponente(p_ponente):
    return len(leer_notificaciones_ponente(p_ponente, p_limite=20))
