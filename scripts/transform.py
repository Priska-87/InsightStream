import os
import pandas as pd
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import unidecode  # para quitar acentos

# ---------- Cargar variables de entorno ----------
load_dotenv()

host = os.getenv('DB_HOST_MYSQL')
user = os.getenv('DB_USER')
password = os.getenv('PASSWORD_ECOMMERCE')
database = os.getenv('DB_ECOMMERCE_MYSQL')
port = int(os.getenv('DB_PORT_MYSQL', 3306))

try:
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port
    )

    if connection.is_connected():
        cursor = connection.cursor(dictionary=True)

        print("Extrayendo datos desde ventas_staging...")
        cursor.execute("SELECT * FROM ventas_staging;")
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)

        print(f"Filas recibidas: {len(df)}")

        # ---------- LIMPIEZA ----------
        df.dropna(inplace=True)  # elimina nulos
        df['producto'] = df['producto'].apply(lambda x: unidecode.unidecode(str(x)).title())
        df['categoria'] = df['categoria'].apply(lambda x: unidecode.unidecode(str(x)).title())

        # ---------- TRANSFORMACIONES ----------

        # Limpiar y convertir columnas numéricas
        df['cantidad'] = pd.to_numeric(df['cantidad'].astype(str).str.replace(',', '').str.strip(), errors='coerce')
        df['precio_unitario'] = pd.to_numeric(df['precio_unitario'].astype(str).str.replace(',', '').str.strip(), errors='coerce')
        df['total'] = pd.to_numeric(df['total'].astype(str).str.replace(',', '').str.strip(), errors='coerce')

        # Calcular coherencia y ticket promedio
        df['total_check'] = df['cantidad'] * df['precio_unitario']
        df['coherente'] = df['total'].round(2) == df['total_check'].round(2)
        df['ticket_promedio'] = (df['total'] / df['cantidad']).round(2)

        # Formatear columna total como moneda
        df['total_formateado'] = df['total'].apply(
            lambda x: f"$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        )

        # ---------- CARGA DE RESULTADOS ----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas_transformadas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                comprobante VARCHAR(20),
                fecha DATE,
                producto VARCHAR(100),
                categoria VARCHAR(50),
                cantidad INT,
                precio_unitario DECIMAL(10,2),
                total DECIMAL(10,2),
                ticket_promedio DECIMAL(10,2),
                total_formateado VARCHAR(20),
                coherente BOOLEAN
            );
        """)
        connection.commit()

        # Vaciar tabla antes de recargar
        cursor.execute("DELETE FROM ventas_transformadas;")
        connection.commit()

        # Insertar datos transformados
        insert_sql = """
            INSERT INTO ventas_transformadas
            (comprobante, fecha, producto, categoria, cantidad, precio_unitario, total, ticket_promedio, total_formateado, coherente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for _, row in df.iterrows():
            cursor.execute(insert_sql, (
                row['comprobante'], row['fecha'], row['producto'], row['categoria'],
                row['cantidad'], row['precio_unitario'], row['total'],
                row['ticket_promedio'], row['total_formateado'], row['coherente']
            ))

        connection.commit()
        print("Datos transformados cargados correctamente en ventas_transformadas.")

except Error as e:
    print("Error en el proceso de transformación:", e)

finally:
    if connection.is_connected():
        cursor.close()
        connection.close()
        print("Conexión cerrada.")

# Exportar tabla final a CSV para Power BI
output_path = r"C:\xxxx\xxxx\OneDrive\InsightStream\datasets\ventas_transformadas.csv"

df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"Archivo exportado correctamente a {output_path}")

