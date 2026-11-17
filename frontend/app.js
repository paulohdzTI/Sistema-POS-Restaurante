const hostBackend = window.location.hostname || "127.0.0.1";
const API_URL = `http://${hostBackend}:8000/api`;
const WS_URL = `ws://${hostBackend}:8000/ws/comandas`;

let estado = {
  rol: "mesero",
  mesas: [],
  productos: [],
  mesaSeleccionada: null,
  comandaPendiente: [],
  comandasCocina: [],
  cuentaActual: null,
  metodoPagoSeleccionado: "efectivo"
};

document.addEventListener("DOMContentLoaded", async () => {
  lucide.createIcons();
  await cargarDatos();
  await cargarCocina();
  iniciarWebSocket();
});

async function cargarDatos() {
  try {
    const [resMesas, resProd] = await Promise.all([
      fetch(`${API_URL}/mesas`),
      fetch(`${API_URL}/productos`)
    ]);
    estado.mesas = await resMesas.json();
    estado.productos = await resProd.json();
    renderizarMesas();
    renderizarCatalogo();
    renderizarCaja();
  } catch (err) {
    console.error("Error al cargar datos:", err);
  }
}

async function cargarCocina() {
  try {
    const res = await fetch(`${API_URL}/cocina/pendientes`);
    estado.comandasCocina = await res.json();
    renderizarCocina();
  } catch (err) {
    console.error("Error al cargar cocina:", err);
  }
}

// --- WEBSOCKETS EN TIEMPO REAL ---
function iniciarWebSocket() {
  const socket = new WebSocket(WS_URL);

  socket.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    if (data.tipo === "NUEVA_COMANDA") {
      reproducirAlerta();
      await cargarCocina();
      await cargarDatos();
    } else if (data.tipo === "ORDEN_DESPACHADA" || data.tipo === "MESA_LIBERADA") {
      await cargarCocina();
      await cargarDatos();
    }
  };

  socket.onclose = () => {
    setTimeout(iniciarWebSocket, 2000);
  };
}

function reproducirAlerta() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.setValueAtTime(587.33, ctx.currentTime);
    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    osc.start();
    osc.stop(ctx.currentTime + 0.3);
  } catch(e){}
}

// --- MESERO ---
function renderizarMesas() {
  const contenedor = document.getElementById("grid-mesas");
  contenedor.innerHTML = estado.mesas.map(m => {
    const colorEstado = m.estado === 'libre' 
      ? 'border-emerald-600/40 bg-emerald-950/20 hover:border-emerald-500' 
      : 'border-amber-600/50 bg-amber-950/20 hover:border-amber-500';
    
    return `
      <div onclick="seleccionarMesa(${m.id})" class="p-4 rounded-xl border ${colorEstado} cursor-pointer transition flex flex-col justify-between h-28">
        <div class="flex justify-between items-start">
          <span class="font-bold text-lg text-stone-100">Mesa ${m.numero}</span>
          <span class="text-xs px-2 py-0.5 rounded-full capitalize ${m.estado === 'libre' ? 'bg-emerald-800/40 text-emerald-300' : 'bg-amber-800/40 text-amber-300'}">${m.estado}</span>
        </div>
        <p class="text-xs text-stone-400">Capacidad: ${m.capacidad} personas</p>
      </div>
    `;
  }).join('');
}

function renderizarCatalogo() {
  const cont = document.getElementById("catalogo-mini");
  cont.innerHTML = estado.productos.map(p => `
    <button onclick="agregarAComanda(${p.id})" class="p-2 bg-[#1e1714] border border-[#3d2f27] hover:border-amber-500/50 rounded-lg text-left transition flex flex-col justify-between">
      <span class="font-semibold text-xs text-amber-100 truncate w-full">${p.nombre}</span>
      <span class="text-xs text-amber-400 font-bold">$${p.precio.toFixed(2)}</span>
    </button>
  `).join('');
}

function seleccionarMesa(id) {
  estado.mesaSeleccionada = estado.mesas.find(m => m.id === id);
  document.getElementById("comanda-titulo").innerText = `Mesa ${estado.mesaSeleccionada.numero}`;
  document.getElementById("comanda-subtitulo").innerText = `Capacidad: ${estado.mesaSeleccionada.capacidad} personas`;
  document.getElementById("badge-estado").innerText = estado.mesaSeleccionada.estado;
  estado.comandaPendiente = [];
  renderizarItemsComanda();
}

function agregarAComanda(productoId) {
  if (!estado.mesaSeleccionada) {
    alert("Primero selecciona una mesa");
    return;
  }
  const prod = estado.productos.find(p => p.id === productoId);
  const existente = estado.comandaPendiente.find(i => i.producto_id === productoId);

  if (existente) {
    existente.cantidad += 1;
  } else {
    estado.comandaPendiente.push({
      producto_id: prod.id,
      nombre: prod.nombre,
      precio: prod.precio,
      cantidad: 1,
      notas: ""
    });
  }
  renderizarItemsComanda();
}

function renderizarItemsComanda() {
  const cont = document.getElementById("items-comanda");
  const btn = document.getElementById("btn-enviar-comanda");

  if (estado.comandaPendiente.length === 0) {
    cont.innerHTML = `<p class="text-stone-500 text-center text-sm py-20">Selecciona productos para armar el pedido</p>`;
    btn.disabled = true;
    return;
  }

  btn.disabled = false;
  cont.innerHTML = estado.comandaPendiente.map((item, idx) => `
    <div class="bg-[#1a1411] p-2.5 rounded-xl border border-[#3d2f27] space-y-1">
      <div class="flex justify-between text-sm">
        <span class="font-medium text-amber-100">${item.nombre} x${item.cantidad}</span>
        <span class="text-amber-400 font-bold">$${(item.precio * item.cantidad).toFixed(2)}</span>
      </div>
      <input type="text" placeholder="Notas (ej. sin cebolla)" value="${item.notas}" 
        onchange="estado.comandaPendiente[${idx}].notas = this.value"
        class="w-full bg-[#120f0d] text-xs px-2 py-1 rounded border border-[#3d2f27] focus:outline-none focus:border-amber-500 text-stone-300">
    </div>
  `).join('');
}

async function enviarComandaCocina() {
  if (!estado.mesaSeleccionada || estado.comandaPendiente.length === 0) return;

  const payload = {
    items: estado.comandaPendiente.map(i => ({
      producto_id: i.producto_id,
      cantidad: i.cantidad,
      notas: i.notas
    }))
  };

  const res = await fetch(`${API_URL}/mesas/${estado.mesaSeleccionada.id}/comanda`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    estado.comandaPendiente = [];
    renderizarItemsComanda();
    await cargarDatos();
    await cargarCocina();
  }
}

// --- COCINA ---
function renderizarCocina() {
  const grid = document.getElementById("grid-cocina");
  if (!estado.comandasCocina || estado.comandasCocina.length === 0) {
    grid.innerHTML = `<div class="col-span-full py-20 text-center text-stone-500 text-sm">No hay órdenes pendientes en cocina</div>`;
    return;
  }

  grid.innerHTML = estado.comandasCocina.map(ticket => `
    <div class="bg-[#241c18] border border-orange-600/40 rounded-2xl p-5 shadow-lg space-y-3">
      <div class="flex justify-between items-center border-b border-[#3d2f27] pb-2">
        <span class="font-bold text-lg text-orange-200">Mesa ${ticket.mesa}</span>
        <span class="text-xs bg-orange-950 text-orange-400 px-2 py-0.5 rounded font-mono">Orden #${ticket.orden_id}</span>
      </div>
      <div class="space-y-2 py-1">
        ${ticket.items.map(it => `
          <div class="text-sm">
            <span class="font-bold text-amber-100">${it.cantidad}x ${it.producto}</span>${it.notas ? `<p class="text-xs text-orange-300 italic pl-3">↳ "${it.notas}"</p>` : ''}
          </div>
        `).join('')}
      </div>
      <button onclick="despacharTicket(${ticket.orden_id})" class="w-full mt-2 py-2.5 bg-emerald-700 hover:bg-emerald-600 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-2">
        <i data-lucide="check" class="w-4 h-4"></i> Listo / Despachar
      </button>
    </div>
  `).join('');
  lucide.createIcons();
}

async function despacharTicket(ordenId) {
  const res = await fetch(`${API_URL}/cocina/despachar/${ordenId}`, { method: "POST" });
  if (res.ok) {
    await cargarCocina();
  }
}

// --- CAJA Y TICKET TÉRMICO COMPLETO ---
function renderizarCaja() {
  const cont = document.getElementById("caja-mesas-lista");
  const ocupadas = estado.mesas.filter(m => m.estado === 'ocupada');

  if (ocupadas.length === 0) {
    cont.innerHTML = `<div class="p-6 bg-[#241c18] border border-[#3d2f27] rounded-xl text-center text-stone-500 text-sm">No hay mesas con cuenta abierta</div>`;
    document.getElementById("caja-detalle").classList.add("hidden");
    return;
  }

  cont.innerHTML = ocupadas.map(m => `
    <div onclick="mostrarCobro(${m.id})" class="p-4 bg-[#241c18] border border-[#3d2f27] hover:border-amber-500 rounded-xl cursor-pointer transition flex justify-between items-center">
      <div>
        <h4 class="font-bold text-amber-100">Mesa ${m.numero}</h4>
        <p class="text-xs text-amber-400 font-medium">Cuenta pendiente</p>
      </div>
      <i data-lucide="chevron-right" class="w-5 h-5 text-stone-500"></i>
    </div>
  `).join('');
  lucide.createIcons();
}

async function mostrarCobro(mesaId) {
  try {
    const res = await fetch(`${API_URL}/mesas/${mesaId}/cuenta`);
    if (!res.ok) return;
    const cuenta = await res.json();
    estado.cuentaActual = cuenta;
    estado.metodoPagoSeleccionado = "efectivo";

    const panel = document.getElementById("caja-detalle");
    panel.classList.remove("hidden");

    panel.innerHTML = `
      <div class="flex flex-col items-center">
        <!-- TICKET TÉRMICO ESTILO 80MM -->
        <div id="ticket-imprimible" class="bg-white text-black p-6 rounded shadow-2xl font-mono text-xs w-[320px] border border-gray-300">
          <div class="text-center space-y-1 mb-3">
            <h2 class="text-base font-bold tracking-wider">FUEGO & CARBÓN RESTAURANTE</h2>
            <p class="text-[10px] text-gray-500">RFC: FCR-990101-ABC</p>
            <p class="text-[10px] text-gray-500">Av. Gastronómica #123</p>
            <p class="text-[10px]">--------------------------------</p>
            <div class="flex justify-between text-[11px] font-bold">
              <span>FOLIO: #${cuenta.folio}</span>
              <span>MESA: ${cuenta.mesa}</span>
            </div>
            <p class="text-[10px] text-gray-500 text-left">${new Date().toLocaleString()}</p>
            <p class="text-[10px]">--------------------------------</p>
          </div>

          <!-- DETALLE DE PLATILLOS -->
          <div class="space-y-1.5 mb-3">
            <div class="flex justify-between font-bold border-b pb-1 text-[11px]">
              <span>CANT / DESCRIPCIÓN</span>
              <span>IMPORTE</span>
            </div>
            ${cuenta.items.map(it => `
              <div class="flex justify-between items-start">
                <div class="w-3/4">
                  <span>${it.cantidad}x ${it.nombre}</span>${it.notas ? `<p class="text-[9px] text-gray-500 italic pl-2">"${it.notas}"</p>` : ''}
                </div>
                <span class="font-bold">$${it.subtotal.toFixed(2)}</span>
              </div>
            `).join('')}
          </div>

          <!-- TOTALES E IMPUESTOS -->
          <div class="border-t border-dashed pt-2 space-y-1 mb-3">
            <div class="flex justify-between">
              <span>SUBTOTAL:</span>
              <span>$${cuenta.subtotal.toFixed(2)}</span>
            </div>
            <div class="flex justify-between">
              <span>IVA (16%):</span>
              <span>$${cuenta.iva.toFixed(2)}</span>
            </div>
            <div class="flex justify-between font-bold text-sm border-t pt-1">
              <span>TOTAL A PAGAR:</span>
              <span>$${cuenta.total.toFixed(2)}</span>
            </div>
          </div>

          <div class="text-center text-[10px] text-gray-500 border-t border-dashed pt-2">
            <p>¡Gracias por su visita!</p>
            <p>Este comprobante es válido para facturación</p>
          </div>
        </div>

        <!-- ACCIONES DE COBRO -->
        <div class="w-full max-w-[320px] mt-4 space-y-3">
          <p class="text-xs font-semibold text-stone-300">Seleccionar Método de Pago:</p>
          <div class="grid grid-cols-3 gap-2">
            <button onclick="seleccionarMetodo('efectivo')" id="metodo-efectivo" class="py-2 text-xs font-bold rounded-lg border border-amber-600 bg-amber-600 text-white transition">Efectivo</button>
            <button onclick="seleccionarMetodo('tarjeta')" id="metodo-tarjeta" class="py-2 text-xs font-bold rounded-lg border border-[#3d2f27] bg-[#1a1411] text-stone-300 transition">Tarjeta</button>
            <button onclick="seleccionarMetodo('transferencia')" id="metodo-transferencia" class="py-2 text-xs font-bold rounded-lg border border-[#3d2f27] bg-[#1a1411] text-stone-300 transition">Transf.</button>
          </div>

          <div class="flex gap-2 pt-2">
            <button onclick="window.print()" class="flex-1 py-2.5 bg-stone-700 hover:bg-stone-600 text-white text-xs font-bold rounded-xl transition flex items-center justify-center gap-1.5">
              <i data-lucide="printer" class="w-4 h-4"></i> Imprimir
            </button>
            <button onclick="confirmarCobro(${mesaId})" class="flex-1 py-2.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold rounded-xl transition flex items-center justify-center gap-1.5 shadow-lg shadow-amber-600/30">
              <i data-lucide="check-circle" class="w-4 h-4"></i> Cobrar y Salir
            </button>
          </div>
        </div>
      </div>
    `;
    lucide.createIcons();
  } catch(err) {
    console.error(err);
  }
}

function seleccionarMetodo(metodo) {
  estado.metodoPagoSeleccionado = metodo;
  ["efectivo", "tarjeta", "transferencia"].forEach(m => {
    const btn = document.getElementById(`metodo-${m}`);
    if (m === metodo) {
      btn.className = "py-2 text-xs font-bold rounded-lg border border-amber-600 bg-amber-600 text-white transition";
    } else {
      btn.className = "py-2 text-xs font-bold rounded-lg border border-[#3d2f27] bg-[#1a1411] text-stone-300 transition";
    }
  });
}

async function confirmarCobro(mesaId) {
  const payload = { metodo_pago: estado.metodoPagoSeleccionado };
  const res = await fetch(`${API_URL}/mesas/${mesaId}/cobrar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    const data = await res.json();
    alert(`Cobro registrado con éxito:\nFolio: #${data.folio}\nTotal: $${data.total}\nMétodo: ${data.metodo_pago.toUpperCase()}`);
    document.getElementById("caja-detalle").classList.add("hidden");
    await cargarDatos();
  }
}

// --- NAVEGACIÓN ---
function cambiarRol(rol) {
  estado.rol = rol;
  document.getElementById("vista-mesero").classList.toggle("hidden", rol !== 'mesero');
  document.getElementById("vista-cocina").classList.toggle("hidden", rol !== 'cocina');
  document.getElementById("vista-caja").classList.toggle("hidden", rol !== 'caja');

  ["mesero", "cocina", "caja"].forEach(r => {
    const btn = document.getElementById(`btn-${r}`);
    if (r === rol) {
      btn.className = "px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition bg-amber-600 text-white shadow";
    } else {
      btn.className = "px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition text-stone-400 hover:text-white";
    }
  });
  lucide.createIcons();
}