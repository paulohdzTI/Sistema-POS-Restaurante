import json
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
import database, models

models.Base.metadata.create_all(bind=database.engine)
app = FastAPI(title="Restaurante POS API")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

class LoginRequest(BaseModel):
    usuario: str
    password: str

class ItemPedido(BaseModel):
    producto_id: int
    cantidad: int = 1
    notas: str = ""

class ComandaCreate(BaseModel):
    items: List[ItemPedido]
    mesero: str = "Desconocido"

class TiempoNotif(BaseModel):
    mesa: str
    minutos: int

class PropinaOp(BaseModel):
    monto: float
    operacion: str

class AgotadosUpdate(BaseModel):
    producto_id: int
    nombre: str
    agotado: bool

class DespachoBarraRequest(BaseModel):
    detalles_ids: List[int]
    bartender: str
    mesa: str
    mesero: str
    fecha_hora_creacion: str

class PagoRequest(BaseModel):
    metodo_pago: str
    propina: float

class EgresoRequest(BaseModel):
    concepto: str
    monto: float
    responsable: str = "Administrador"

# --- ESTADOS GLOBALES ---
propinas_globales = {"total": 0.0}
productos_agotados_cache = set()

# --- WEBSOCKETS ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try: await connection.send_json(message)
            except Exception: self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws/comandas")
async def websocket_comandas(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- RUTAS PRINCIPALES ---
@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.username == req.usuario, models.Usuario.password == req.password).first()
    if not user: raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return {"mensaje": "Login exitoso", "rol": user.rol, "nombre": user.nombre}

@app.get("/api/productos")
def listar_productos(db: Session = Depends(get_db)):
    return db.query(models.Producto).all()

@app.get("/api/mesas")
def listar_mesas(db: Session = Depends(get_db)):
    mesas = db.query(models.Mesa).all()
    resultado = []
    for m in mesas:
        mesero_nombre = ""
        if m.estado in ["ocupada", "limpieza"]:
            orden = db.query(models.Orden).filter(models.Orden.mesa_id == m.id, models.Orden.pagada == False).first()
            if orden: mesero_nombre = orden.mesero
            
        resultado.append({
            "id": m.numero,
            "numero": m.numero,
            "estado": m.estado,
            "capacidad": m.capacidad,
            "mesero": mesero_nombre
        })
    return resultado

@app.get("/api/propinas")
def obtener_propinas():
    return propinas_globales

@app.post("/api/propinas")
async def operar_propinas(op: PropinaOp):
    if op.operacion == "sumar": propinas_globales["total"] = round(propinas_globales["total"] + op.monto, 2)
    elif op.operacion == "restar": propinas_globales["total"] = max(0.0, round(propinas_globales["total"] - op.monto, 2))
    elif op.operacion == "corte": propinas_globales["total"] = 0.0
    await manager.broadcast({"tipo": "PROPINAS_ACTUALIZADAS", "total": propinas_globales["total"]})
    return propinas_globales

@app.get("/api/agotados")
def listar_agotados():
    return list(productos_agotados_cache)

@app.post("/api/agotados")
async def actualizar_agotado(item: AgotadosUpdate):
    if item.agotado: productos_agotados_cache.add(item.producto_id)
    else: productos_agotados_cache.discard(item.producto_id)
    await manager.broadcast({
        "tipo": "AGOTADO_ACTUALIZADO", "producto_id": item.producto_id, 
        "nombre": item.nombre, "agotado": item.agotado, "lista_agotados": list(productos_agotados_cache)
    })
    return {"mensaje": "Estado actualizado"}

@app.post("/api/mesas/{mesa_id}/liberar")
async def liberar_mesa(mesa_id: str, db: Session = Depends(get_db)):
    mesa = db.query(models.Mesa).filter(models.Mesa.numero == mesa_id).first()
    if mesa:
        mesa.estado = "libre"
        db.commit()
        await manager.broadcast({"tipo": "MESA_LIBERADA", "mesa": mesa_id})
    return {"mensaje": "Mesa liberada"}

@app.post("/api/mesas/{mesa_id}/comanda")
async def crear_comanda(mesa_id: str, comanda: ComandaCreate, db: Session = Depends(get_db)):
    mesa_numero = "Delivery"
    mesa_db_id = None

    if mesa_id.upper() != "DELIVERY":
        mesa = db.query(models.Mesa).filter(models.Mesa.numero == mesa_id).first()
        if not mesa:
            mesa = models.Mesa(numero=mesa_id, capacidad=4, estado="ocupada")
            db.add(mesa)
            db.commit()
            db.refresh(mesa)
        else:
            mesa.estado = "ocupada"
            db.commit()
        mesa_numero = mesa.numero
        mesa_db_id = mesa.id

    orden = db.query(models.Orden).filter(models.Orden.mesa_id == mesa_db_id, models.Orden.pagada == False).first() if mesa_db_id else None
    
    if not orden or mesa_numero == "Delivery":
        ahora = datetime.now()
        orden = models.Orden(
            mesa_id=mesa_db_id, total=0.0, pagada=False,
            mesero=comanda.mesero, fecha=ahora.strftime("%d/%m/%Y"), hora=ahora.strftime("%I:%M %p")
        )
        db.add(orden)
        db.commit()
        db.refresh(orden)

    hay_cocina = False
    hay_barra = False

    for item in comanda.items:
        prod = db.query(models.Producto).filter(models.Producto.id == item.producto_id).first()
        if prod:
            detalle = models.OrdenDetalle(orden_id=orden.id, producto_id=prod.id, cantidad=item.cantidad, notas=item.notas, estado="pendiente")
            db.add(detalle)
            orden.total += (prod.precio * item.cantidad)
            if prod.categoria == "alimentos": hay_cocina = True
            elif prod.categoria == "bebidas": hay_barra = True
    db.commit()

    if hay_cocina: await manager.broadcast({"tipo": "NUEVA_COMANDA_COCINA", "mesa": mesa_numero})
    if hay_barra: await manager.broadcast({"tipo": "NUEVA_COMANDA_BARRA", "mesa": mesa_numero})

    return {"mensaje": "Comanda procesada", "orden_id": orden.id}

# =========================================================================
# --- CUENTA Y CAJA (MOVIDOS ARRIBA PARA EVITAR CONFLICTO DE RUTAS) ---
# =========================================================================
@app.get("/api/caja/pendientes")
def obtener_pendientes_caja(db: Session = Depends(get_db)):
    ordenes = db.query(models.Orden).filter(models.Orden.pagada == False).all()
    resultado = []
    for o in ordenes:
        mesa_str = str(o.mesa.numero) if o.mesa else "Delivery"
        resultado.append({
            "orden_id": o.id, "mesa": mesa_str, "mesero": o.mesero, "total": o.total
        })
    return resultado

@app.get("/api/cuenta/{orden_id}")
def obtener_cuenta_por_orden(orden_id: int, db: Session = Depends(get_db)):
    orden = db.query(models.Orden).filter(models.Orden.id == orden_id, models.Orden.pagada == False).first()
    if not orden: return {"error": "Orden no encontrada"}
    
    detalles = db.query(models.OrdenDetalle).filter(models.OrdenDetalle.orden_id == orden.id).all()
    items = []
    for d in detalles:
        items.append({
            "cantidad": d.cantidad, "producto": d.producto.nombre, "categoria": d.producto.categoria,
            "precio_unitario": d.producto.precio, "importe": d.cantidad * d.producto.precio
        })
    mesa_str = str(orden.mesa.numero) if orden.mesa else "Delivery"
    return {
        "orden_id": orden.id, "mesa": mesa_str, "mesero": orden.mesero,
        "fecha": orden.fecha, "hora": orden.hora, "items": items, "total": orden.total
    }

@app.post("/api/pagar/{orden_id}")
async def pagar_cuenta_orden(orden_id: int, req: PagoRequest, db: Session = Depends(get_db)):
    orden = db.query(models.Orden).filter(models.Orden.id == orden_id, models.Orden.pagada == False).first()
    if orden:
        mesa_str = str(orden.mesa.numero) if orden.mesa else "Delivery"
        nuevo_pago = models.HistorialCaja(
            mesa=mesa_str, mesero=orden.mesero, fecha=orden.fecha,
            hora_pago=datetime.now().strftime("%I:%M %p"),
            total=orden.total, propina=req.propina, metodo_pago=req.metodo_pago
        )
        db.add(nuevo_pago)
        
        if req.propina > 0:
            propinas_globales["total"] = round(propinas_globales["total"] + req.propina, 2)
        
        orden.pagada = True
        if orden.mesa:
            orden.mesa.estado = "limpieza"
        db.commit()
        
        await manager.broadcast({"tipo": "PROPINAS_ACTUALIZADAS", "total": propinas_globales["total"]})
        await manager.broadcast({"tipo": "MESA_PAGADA", "mesa": mesa_str})
    return {"mensaje": "Cuenta pagada con éxito"}

@app.get("/api/caja/historial")
def obtener_historial_caja(db: Session = Depends(get_db)):
    return db.query(models.HistorialCaja).order_by(models.HistorialCaja.id.desc()).all()

@app.get("/api/caja/egresos")
def obtener_egresos_caja(db: Session = Depends(get_db)):
    return db.query(models.EgresoCaja).order_by(models.EgresoCaja.id.desc()).all()

@app.post("/api/caja/egresos")
async def registrar_egreso_caja(req: EgresoRequest, db: Session = Depends(get_db)):
    ahora = datetime.now()
    nuevo_egreso = models.EgresoCaja(
        concepto=req.concepto,
        monto=req.monto,
        responsable=req.responsable,
        fecha=ahora.strftime("%d/%m/%Y"),
        hora=ahora.strftime("%I:%M %p")
    )
    db.add(nuevo_egreso)
    db.commit()
    await manager.broadcast({"tipo": "CAJA_ACTUALIZADA"})
    return {"mensaje": "Egreso registrado"}

@app.delete("/api/caja/egresos/{egreso_id}")
async def eliminar_egreso_caja(egreso_id: int, db: Session = Depends(get_db)):
    egreso = db.query(models.EgresoCaja).filter(models.EgresoCaja.id == egreso_id).first()
    if egreso:
        db.delete(egreso)
        db.commit()
        await manager.broadcast({"tipo": "CAJA_ACTUALIZADA"})
    return {"mensaje": "Egreso eliminado"}

@app.delete("/api/caja/corte")
async def hacer_corte_caja(db: Session = Depends(get_db)):
    # 1. Borrar historiales y egresos del día
    db.query(models.HistorialCaja).delete()
    db.query(models.EgresoCaja).delete()
    db.query(models.HistorialBarra).delete()
    
    # 2. Borrar detalles y órdenes del día para que el Folio reinicie desde #1 (0)
    db.query(models.OrdenDetalle).delete()
    db.query(models.Orden).delete()
    
    # 3. Liberar todas las mesas y reiniciar bote de propinas
    db.query(models.Mesa).update({models.Mesa.estado: "libre"})
    propinas_globales["total"] = 0.0
    db.commit()

    await manager.broadcast({"tipo": "PROPINAS_ACTUALIZADAS", "total": 0.0})
    await manager.broadcast({"tipo": "MESA_LIBERADA", "mesa": "TODAS"})
    await manager.broadcast({"tipo": "CORTE_CAJA_REALIZADO"})
    return {"mensaje": "Corte del día realizado y folios reiniciados desde 0"}

# --- TICKET DIGITAL HTML PARA EL QR ---
@app.get("/api/ticket/{orden_id}", response_class=HTMLResponse)
def ver_ticket_digital(orden_id: int, db: Session = Depends(get_db)):
    orden = db.query(models.Orden).filter(models.Orden.id == orden_id).first()
    if not orden: return "<h1>Ticket no encontrado</h1>"
    
    detalles = db.query(models.OrdenDetalle).filter(models.OrdenDetalle.orden_id == orden.id).all()
    mesa_str = str(orden.mesa.numero) if orden.mesa else "Delivery"
    
    items_html = ""
    for d in detalles:
        imp = d.cantidad * d.producto.precio
        items_html += f"<tr style='border-bottom: 1px dotted #ccc;'><td style='padding:8px 0;'>{d.cantidad}</td><td>{d.producto.nombre}</td><td style='text-align:right;'>${imp:.2f}</td></tr>"
        
    html = f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body {{ font-family: monospace; padding: 20px; max-width: 400px; margin: 0 auto; background: #f9f8f6; color: #1a1a1a; }}
    .ticket {{ background: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 10px 20px rgba(0,0,0,0.1); border: 1px solid #ddd; }}
    h2 {{ text-align: center; border-bottom: 2px dashed #1a1a1a; padding-bottom: 10px; font-size: 24px; letter-spacing: 2px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
    th {{ text-align: left; padding-bottom: 5px; border-bottom: 2px dashed #1a1a1a; }}
    .totales {{ margin-top: 20px; font-weight: bold; font-size: 1.5em; text-align: right; color: #4A5D23; border-top: 2px dashed #1a1a1a; padding-top: 10px; }}
    .footer {{ text-align: center; margin-top: 30px; font-weight: bold; font-size: 1.1em; color: #5C4033; }}
    button {{ width: 100%; padding: 15px; margin-top: 20px; background: #4A5D23; color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 16px; cursor: pointer; }}
    @media print {{ button {{ display: none; }} body {{ background: white; }} .ticket {{ box-shadow: none; border: none; }} }}
    </style></head>
    <body>
        <div class="ticket">
            <h2>TICKET DE COMPRA</h2>
            <p><strong>Folio:</strong> #{orden.id}<br><strong>Fecha:</strong> {orden.fecha} {orden.hora}<br><strong>Mesa:</strong> {mesa_str}<br><strong>Atendió:</strong> {orden.mesero}</p>
            <table><tr><th>Cant</th><th>Descripción</th><th style="text-align:right;">Imp</th></tr>{items_html}</table>
            <div class="totales">Total: ${orden.total:.2f}</div>
            <div class="footer">¡Gracias por su visita!<br><span style="font-size: 12px; color: #888;">Vuelva pronto</span></div>
        </div>
        <button onclick="window.print()">Guardar como PDF / Imprimir</button>
    </body></html>
    """
    return html

# =========================================================================
# --- RUTAS DE ÁREA (AHORA ABAJO PARA QUE NO INTERFIERAN CON CAJA) ---
# =========================================================================
@app.get("/api/{area}/pendientes")
def obtener_pendientes(area: str, db: Session = Depends(get_db)):
    categoria_filtro = "alimentos" if area == "cocina" else "bebidas"
    detalles = db.query(models.OrdenDetalle).join(models.Producto).filter(models.OrdenDetalle.estado == "pendiente", models.Producto.categoria == categoria_filtro).all()
    
    ordenes_dict = {}
    for d in detalles:
        if d.orden_id not in ordenes_dict:
            mesa_str = str(d.orden.mesa.numero) if d.orden.mesa else "Delivery"
            ordenes_dict[d.orden_id] = {
                "orden_id": d.orden_id, "mesa": mesa_str, "mesero": d.orden.mesero, 
                "fecha": d.orden.fecha, "hora": d.orden.hora, "items": []
            }
        ordenes_dict[d.orden_id]["items"].append({
            "id_detalle": d.id, "producto": d.producto.nombre, "cantidad": d.cantidad, "notas": d.notas
        })
    return list(ordenes_dict.values())

@app.post("/api/despachar_item/{id_detalle}")
async def despachar_item(id_detalle: int, db: Session = Depends(get_db)):
    detalle = db.query(models.OrdenDetalle).filter(models.OrdenDetalle.id == id_detalle).first()
    if detalle:
        detalle.estado = "listo"
        db.commit()
        mesa_num = str(detalle.orden.mesa.numero) if detalle.orden.mesa else "Delivery"
        await manager.broadcast({"tipo": "ITEM_DESPACHADO", "mesa": mesa_num, "producto": detalle.producto.nombre})
    return {"mensaje": "Despachado"}

@app.post("/api/barra/despachar")
async def despachar_ticket_barra(req: DespachoBarraRequest, db: Session = Depends(get_db)):
    items_despachados = []
    for id_detalle in req.detalles_ids:
        detalle = db.query(models.OrdenDetalle).filter(models.OrdenDetalle.id == id_detalle).first()
        if detalle:
            detalle.estado = "listo"
            items_despachados.append(f"{detalle.cantidad}x {detalle.producto.nombre}")
            
    nuevo_historial = models.HistorialBarra(
        mesa_numero=req.mesa, mesero=req.mesero, bartender=req.bartender,
        fecha_hora_creacion=req.fecha_hora_creacion, detalle_items=json.dumps(items_despachados)
    )
    db.add(nuevo_historial)
    db.commit()
    await manager.broadcast({"tipo": "ITEM_DESPACHADO", "mesa": req.mesa})
    return {"mensaje": "Ticket archivado"}

@app.get("/api/barra/historial")
def obtener_historial_barra(db: Session = Depends(get_db)):
    historial = db.query(models.HistorialBarra).order_by(models.HistorialBarra.fecha_hora_despacho.desc()).all()
    resultado = []
    for h in historial:
        resultado.append({
            "id": h.id, "mesa": h.mesa_numero, "mesero": h.mesero, "bartender": h.bartender,
            "fecha_creacion": h.fecha_hora_creacion, "hora_despacho": h.fecha_hora_despacho.strftime("%I:%M %p"),
            "items": json.loads(h.detalle_items)
        })
    return resultado

@app.delete("/api/barra/historial/{historial_id}")
def borrar_item_historial_barra(historial_id: int, db: Session = Depends(get_db)):
    item = db.query(models.HistorialBarra).filter(models.HistorialBarra.id == historial_id).first()
    if item:
        db.delete(item)
        db.commit()
        return {"mensaje": "Borrado"}
    raise HTTPException(status_code=404)

@app.post("/api/notificar_tiempo")
async def notificar_tiempo(datos: TiempoNotif):
    await manager.broadcast({"tipo": "TIEMPO_PREP", "mesa": datos.mesa, "minutos": datos.minutos})
    return {"mensaje": "Aviso enviado"}