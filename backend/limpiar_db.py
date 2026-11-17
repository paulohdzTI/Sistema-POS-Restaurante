import os

print("Limpiando la base de datos antigua...")

if os.path.exists("restaurante.db"):
    os.remove("restaurante.db")
    print("Base de datos borrada con éxito.")
else:
    print("La base de datos no existía.")

print("Por favor, ejecuta ahora 'python productos.py' y 'python usuarios.py' para recrear la estructura y los datos iniciales.")