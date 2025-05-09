import mysql.connector

host= "localhost"
user= "root"
password= ""
database="Empire"

try:    
    conexion = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

    if conexion.is_connected():
        print("conexion exitosa")



except mysql.connector.Error as err:
    print(f"Error {err} ")