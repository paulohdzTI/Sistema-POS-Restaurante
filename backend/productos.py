import database, models

models.Base.metadata.create_all(bind=database.engine)
db = database.SessionLocal()

productos_base = [
    # --- ENTRADAS Y BOTANAS ---
    {"nombre": "Papas Preparadas", "precio": 70.0, "categoria": "alimentos"},
    {"nombre": "Papas a la francesa", "precio": 60.0, "categoria": "alimentos"},
    {"nombre": "Papas La TDDC", "precio": 90.0, "categoria": "alimentos"},
    {"nombre": "Nachos Sencillos", "precio": 85.0, "categoria": "alimentos"},
    {"nombre": "Nachos c/Arrachera", "precio": 100.0, "categoria": "alimentos"},
    {"nombre": "Botana La TDDC", "precio": 45.0, "categoria": "alimentos"},

    # --- FUERTES (COMPLETOS Y MEDIAS ÓRDENES) ---
    {"nombre": "Pozole (Completo)", "precio": 120.0, "categoria": "alimentos"},
    {"nombre": "Pozole (Media Ord)", "precio": 65.0, "categoria": "alimentos"},
    {"nombre": "Flautas (Completo)", "precio": 100.0, "categoria": "alimentos"},
    {"nombre": "Flautas (Media Ord)", "precio": 65.0, "categoria": "alimentos"},
    {"nombre": "Enchiladas (Completo)", "precio": 100.0, "categoria": "alimentos"},
    {"nombre": "Enchiladas (Media Ord)", "precio": 65.0, "categoria": "alimentos"},
    {"nombre": "Tacos Arrachera (Comp)", "precio": 100.0, "categoria": "alimentos"},
    {"nombre": "Tacos Arrachera (Media)", "precio": 65.0, "categoria": "alimentos"},

    # --- POLLO ---
    {"nombre": "Ord. Tiras", "precio": 115.0, "categoria": "alimentos"},
    {"nombre": "Media Ord. Tiras", "precio": 75.0, "categoria": "alimentos"},
    {"nombre": "Ord. Boneless", "precio": 150.0, "categoria": "alimentos"},
    {"nombre": "Media Ord. Boneless", "precio": 95.0, "categoria": "alimentos"},
    {"nombre": "Ord. Alitas", "precio": 110.0, "categoria": "alimentos"},
    {"nombre": "Media Ord. Alitas", "precio": 65.0, "categoria": "alimentos"},

    # --- HAMBURGUESAS Y OTROS ---
    {"nombre": "Hamburguesa Pollo", "precio": 89.0, "categoria": "alimentos"},
    {"nombre": "Hamburguesa Res", "precio": 89.0, "categoria": "alimentos"},
    {"nombre": "Hamburguesa Arrachera", "precio": 99.0, "categoria": "alimentos"},
    {"nombre": "Ensalada César", "precio": 120.0, "categoria": "alimentos"},
    {"nombre": "Combo Hamburguesas", "precio": 190.0, "categoria": "alimentos"},
    {"nombre": "Postre del Día", "precio": 50.0, "categoria": "alimentos"},

    # --- BEBIDAS SIMPLES ---
    {"nombre": "Refresco", "precio": 30.0, "categoria": "bebidas"},
    {"nombre": "Agua Natural (Bot)", "precio": 15.0, "categoria": "bebidas"},
    {"nombre": "Agua Mineral (Bot)", "precio": 35.0, "categoria": "bebidas"},
    {"nombre": "Agua de Sabor (Vaso)", "precio": 70.0, "categoria": "bebidas"},
    {"nombre": "Malteada", "precio": 60.0, "categoria": "bebidas"},
    {"nombre": "Café de Olla", "precio": 30.0, "categoria": "bebidas"},
    {"nombre": "Capuchino (Caliente)", "precio": 60.0, "categoria": "bebidas"},

    # --- CERVEZAS Y COCTELERÍA ---
    {"nombre": "Cerveza (Botella)", "precio": 35.0, "categoria": "bebidas"},
    {"nombre": "Caguama", "precio": 80.0, "categoria": "bebidas"},
    {"nombre": "Cubeta de Cerveza", "precio": 400.0, "categoria": "bebidas"},
    {"nombre": "Preparado (c/Clamato)", "precio": 40.0, "categoria": "bebidas"},
    {"nombre": "Preparado s/Clamato", "precio": 40.0, "categoria": "bebidas"},
    {"nombre": "Michelada", "precio": 80.0, "categoria": "bebidas"},
    {"nombre": "Michelada s/Clamato", "precio": 80.0, "categoria": "bebidas"},
    {"nombre": "Michelada s/Alcohol", "precio": 80.0, "categoria": "bebidas"}, # Modificado
    {"nombre": "Mojito", "precio": 95.0, "categoria": "bebidas"},
    {"nombre": "Mojito s/Alcohol", "precio": 95.0, "categoria": "bebidas"}, # Modificado
    {"nombre": "Azulito", "precio": 95.0, "categoria": "bebidas"},
    {"nombre": "Azulito s/Alcohol", "precio": 95.0, "categoria": "bebidas"}, # Modificado
    {"nombre": "Piña Colada", "precio": 95.0, "categoria": "bebidas"},
    {"nombre": "Piña Colada s/Alcohol", "precio": 95.0, "categoria": "bebidas"}, # Modificado
    {"nombre": "Extra: Descarche", "precio": 5.0, "categoria": "bebidas"},
]

# Borramos los viejos e insertamos los nuevos
db.query(models.Producto).delete()
for p in productos_base:
    db.add(models.Producto(**p))
db.commit()
print("¡Éxito! Precios actualizados.")
db.close()