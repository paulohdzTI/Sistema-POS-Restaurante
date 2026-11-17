import database, models

# Esto asegura que la tabla nueva se genere en el archivo SQLite
models.Base.metadata.create_all(bind=database.engine)
db = database.SessionLocal()

usuarios_base = [
    # 3 Administradores / Gerentes
    {"nombre": "Admin General", "username": "admin1", "password": "123", "rol": "administrador"},
    {"nombre": "Gerente Turno", "username": "admin2", "password": "123", "rol": "administrador"},
    {"nombre": "Auditor", "username": "admin3", "password": "123", "rol": "administrador"},
    
    # 3 Meseros
    {"nombre": "Juan (Mesero)", "username": "mesero1", "password": "123", "rol": "mesero"},
    {"nombre": "María (Mesera)", "username": "mesero2", "password": "123", "rol": "mesero"},
    {"nombre": "Pedro (Mesero)", "username": "mesero3", "password": "123", "rol": "mesero"},
    
    # 2 Cocineras
    {"nombre": "Doña Carmen", "username": "cocina1", "password": "123", "rol": "cocinera"},
    {"nombre": "Lupita", "username": "cocina2", "password": "123", "rol": "cocinera"},
    
    # 2 Bartenders
    {"nombre": "Carlos (Bar)", "username": "bar1", "password": "123", "rol": "bartender"},
    {"nombre": "Luis (Bar)", "username": "bar2", "password": "123", "rol": "bartender"}
]

# Insertamos los usuarios si la tabla está vacía
if db.query(models.Usuario).count() == 0:
    for u in usuarios_base:
        nuevo_user = models.Usuario(**u)
        db.add(nuevo_user)
    db.commit()
    print("¡Éxito! 10 usuarios creados en la base de datos.")
else:
    print("Los usuarios ya existen en la base de datos.")

db.close()