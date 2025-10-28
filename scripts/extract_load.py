import os
import pandas as pd
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# ---------- Cargar variables de entorno ----------
load_dotenv()

# Obtener credenciales desde el entorno
host = os.getenv('DB_HOST_MYSQL')
user = os.getenv('DB_USER')
password = os.getenv('PASSWORD_ECOMMERCE')
database = os.getenv('DB_ECOMMERCE_MYSQL')
port = int(os.getenv('DB_PORT_MYSQL', 3306))

# ---------- Leer CSV ----------
base_path = os.path.dirname(os.path.abspath(__file__))
csv_file = os.path.join(base_path, '..', 'data', 'ventas_ecommerce.csv')
df = pd.read_csv(csv_file)

print("Filas en CSV:", len(df))
print(df.head())

# ---------- Conexión a MySQL y carga ----------
try:
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port
    )

    if connection.is_connected():
        cursor = connection.cursor()

        # Verificar tabla
        cursor.execute("SELECT DATABASE();")
        db_actual = cursor.fetchone()[0]
        print("Base de datos usada:", db_actual)

        cursor.execute("SHOW TABLES;")
        tablas = [t[0] for t in cursor.fetchall()]
        print("Tablas disponibles:", tablas)

        if "ventas_staging" not in tablas:
            raise Exception("La tabla 'ventas_staging' no existe en la base de datos.")

        # Limpiar tabla antes de cargar
        cursor.execute("DELETE FROM ventas_staging;")
        connection.commit()
        print("Tabla ventas_staging limpiada correctamente.")

        # Insertar filas nuevas con manejo de duplicados
        insert_sql = """
            INSERT INTO ventas_staging (comprobante, fecha, producto, categoria, cantidad, precio_unitario, total)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                cantidad = VALUES(cantidad),
                precio_unitario = VALUES(precio_unitario),
                total = VALUES(total);
        """

        for index, row in df.iterrows():
            values = (
                row['comprobante'],
                row['fecha'],
                row['producto'],
                row['categoria'],
                row['cantidad'],
                row['precio_unitario'],
                row['total']
            )
            cursor.execute(insert_sql, values)

        connection.commit()
        print(f"{len(df)} filas insertadas/actualizadas correctamente en ventas_staging.")

        # Ver cantidad final de filas
        cursor.execute("SELECT COUNT(*) FROM ventas_staging;")
        filas_final = cursor.fetchone()[0]
        print("Filas finales en ventas_staging:", filas_final)

except Error as e:
    print("Error al conectar o insertar en MySQL:", e)

finally:
    if connection.is_connected():
        cursor.close()
        connection.close()
        print("Conexión a MySQL cerrada.")
