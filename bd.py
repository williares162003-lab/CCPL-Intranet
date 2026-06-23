import pymysql.cursors

def obtenerconexion():
   try:
       connection = pymysql.connect(host='localhost',
                                    user='root',
                                    port=3306,
                                    password='',
                                    database='colegiocontadores',
                                    cursorclass=pymysql.cursors.DictCursor)
       return connection
   except:
       raise
