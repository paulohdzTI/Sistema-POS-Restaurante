from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Mesa(Base):
    __tablename__ = "mesas"
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String, unique=True, index=True)
    capacidad = Column(Integer, default=4)
    estado = Column(String, default="libre")
    ordenes = relationship("Orden", back_populates="mesa")

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    precio = Column(Float)
    categoria = Column(String)
    stock = Column(Integer, default=50)

class Orden(Base):
    __tablename__ = "ordenes"
    id = Column(Integer, primary_key=True, index=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"))
    total = Column(Float, default=0.0)
    pagada = Column(Boolean, default=False)
    mesero = Column(String, default="Desconocido")
    fecha = Column(String, default="--/--/----")
    hora = Column(String, default="--:--")
    
    mesa = relationship("Mesa", back_populates="ordenes")
    detalles = relationship("OrdenDetalle", back_populates="orden")

class OrdenDetalle(Base):
    __tablename__ = "orden_detalles"
    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    cantidad = Column(Integer, default=1)
    notas = Column(String, default="")
    estado = Column(String, default="pendiente")

    orden = relationship("Orden", back_populates="detalles")
    producto = relationship("Producto")

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    rol = Column(String)       

class HistorialBarra(Base):
    __tablename__ = "historial_barra"
    id = Column(Integer, primary_key=True, index=True)
    mesa_numero = Column(String, index=True)
    mesero = Column(String)
    bartender = Column(String)
    fecha_hora_creacion = Column(String)
    fecha_hora_despacho = Column(DateTime, default=datetime.now)
    detalle_items = Column(String)

# NUEVA TABLA PARA CORTES DE CAJA
class HistorialCaja(Base):
    __tablename__ = "historial_caja"
    id = Column(Integer, primary_key=True, index=True)
    mesa = Column(String)
    mesero = Column(String)
    fecha = Column(String)
    hora_pago = Column(String)
    total = Column(Float)
    propina = Column(Float)
    metodo_pago = Column(String)

# TABLA PARA EGRESOS / GASTOS DE CAJA
class EgresoCaja(Base):
    __tablename__ = "egresos_caja"
    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String)
    monto = Column(Float)
    responsable = Column(String)
    fecha = Column(String)
    hora = Column(String)