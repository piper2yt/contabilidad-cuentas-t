import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date
import os
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ─── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ContaT · Cuentas T Contables",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded",
)

EXCEL_FILE = "movimientos_contables.xlsx"
CUENTAS_DEFAULT = ["Activos", "Pasivos", "Capital", "Ingresos", "Gastos"]
MOVIMIENTOS = ["CARGOS", "ABONOS"]

NATURALEZA = {
    "Activos": "deudora",
    "Gastos": "deudora",
    "Pasivos": "acreedora",
    "Capital": "acreedora",
    "Ingresos": "acreedora",
}

# ─── STYLES ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 { font-family: 'DM Serif Display', serif; }

.stApp { background: #0f1117; color: #e8e3d5; }

section[data-testid="stSidebar"] {
    background: #161922;
    border-right: 1px solid #2a2d3a;
}

.metric-card {
    background: linear-gradient(135deg, #1a1e2e 0%, #1f2438 100%);
    border: 1px solid #2e3347;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
}
.metric-card .label {
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 0.3rem;
}
.metric-card .value {
    font-size: 1.8rem;
    font-family: 'DM Serif Display', serif;
    font-weight: 400;
}
.positive { color: #34d399; }
.negative { color: #f87171; }
.neutral  { color: #93c5fd; }

.cuenta-t {
    background: #161922;
    border: 1px solid #2e3347;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 1rem;
}
.cuenta-t-header {
    background: linear-gradient(90deg, #1e3a5f, #1a2d4a);
    padding: 0.6rem 1rem;
    font-family: 'DM Serif Display', serif;
    font-size: 1rem;
    color: #93c5fd;
    border-bottom: 1px solid #2e3347;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.cuenta-t-body {
    display: grid;
    grid-template-columns: 1fr 1px 1fr;
    min-height: 100px;
}
.cuenta-t-col {
    padding: 0.8rem;
}
.cuenta-t-divider {
    background: #2e3347;
}
.cargo-label { color: #f87171; font-size:0.7rem; letter-spacing:0.1em; text-transform:uppercase; }
.abono-label { color: #34d399; font-size:0.7rem; letter-spacing:0.1em; text-transform:uppercase; }
.t-amount { font-size: 0.9rem; color: #e8e3d5; padding: 2px 0; }

.pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.pill-cargo { background: #3b1c1c; color: #f87171; }
.pill-abono { background: #1a3b2e; color: #34d399; }

.esf-ok {
    background: linear-gradient(90deg, #1a3b2e, #1f2438);
    border: 1px solid #34d399;
    border-radius: 8px;
    padding: 0.9rem 1.2rem;
    color: #34d399;
    font-weight: 600;
}
.esf-fail {
    background: linear-gradient(90deg, #3b1c1c, #1f2438);
    border: 1px solid #f87171;
    border-radius: 8px;
    padding: 0.9rem 1.2rem;
    color: #f87171;
    font-weight: 600;
}

div[data-testid="stForm"] {
    background: #161922;
    border: 1px solid #2e3347;
    border-radius: 12px;
    padding: 1.4rem;
}

.stButton > button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(37,99,235,0.4) !important;
}

.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input,
.stDateInput > div > div > input {
    background: #1f2438 !important;
    border: 1px solid #2e3347 !important;
    border-radius: 8px !important;
    color: #e8e3d5 !important;
}

.tab-header {
    font-size: 0.75rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 1.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #2e3347;
}

.stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ─── EXCEL HELPERS ────────────────────────────────────────────────────────────
def init_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.title = "Movimientos"
        headers = ["Fecha", "Cuenta", "Tipo", "Monto", "Mes", "Año", "Descripcion"]
        bold = Font(bold=True, color="FFFFFF")
        fill = PatternFill("solid", start_color="1E3A5F")
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = bold
            cell.fill = fill
            cell.alignment = Alignment(horizontal="center")
        widths = [14, 14, 10, 12, 8, 8, 30]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        wb.save(EXCEL_FILE)


def load_data() -> pd.DataFrame:
    init_excel()
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name="Movimientos")
        if df.empty or "Fecha" not in df.columns:
            return pd.DataFrame(columns=["Fecha","Cuenta","Tipo","Monto","Mes","Año","Descripcion"])
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame(columns=["Fecha","Cuenta","Tipo","Monto","Mes","Año","Descripcion"])


def save_to_excel(fecha, cuenta, tipo, monto, descripcion=""):
    init_excel()
    wb = load_workbook(EXCEL_FILE)
    ws = wb["Movimientos"]
    next_row = ws.max_row + 1
    dt = pd.to_datetime(fecha)
    row_data = [dt.strftime("%Y-%m-%d"), cuenta, tipo, monto, dt.month, dt.year, descripcion]
    cargo_fill = PatternFill("solid", start_color="3B1C1C")
    abono_fill = PatternFill("solid", start_color="1A3B2E")
    thin = Side(style="thin", color="2E3347")
    border = Border(bottom=Side(style="thin", color="2E3347"))
    for col, val in enumerate(row_data, 1):
        cell = ws.cell(row=next_row, column=col, value=val)
        cell.border = border
        if col == 3:
            cell.fill = cargo_fill if tipo == "CARGOS" else abono_fill
    wb.save(EXCEL_FILE)


# ─── LOGIC ────────────────────────────────────────────────────────────────────
def get_cuentas_list():
    if "cuentas_custom" not in st.session_state:
        st.session_state.cuentas_custom = []
    return CUENTAS_DEFAULT + st.session_state.cuentas_custom


def get_naturaleza(cuenta):
    return NATURALEZA.get(cuenta, "deudora")


def calcular_saldo(df: pd.DataFrame, cuenta: str) -> float:
    sub = df[df["Cuenta"] == cuenta]
    nat = get_naturaleza(cuenta)
    saldo = 0.0
    for _, row in sub.iterrows():
        if nat == "deudora":
            saldo += row["Monto"] if row["Tipo"] == "CARGOS" else -row["Monto"]
        else:
            saldo += row["Monto"] if row["Tipo"] == "ABONOS" else -row["Monto"]
    return saldo


def calcular_totales(df, cuenta):
    sub = df[df["Cuenta"] == cuenta]
    cargos = sub[sub["Tipo"] == "CARGOS"]["Monto"].sum()
    abonos = sub[sub["Tipo"] == "ABONOS"]["Monto"].sum()
    return cargos, abonos


# ─── COMPONENTS ───────────────────────────────────────────────────────────────
def render_cuenta_t(cuenta, df):
    cargos_val, abonos_val = calcular_totales(df, cuenta)
    saldo = calcular_saldo(df, cuenta)
    nat = get_naturaleza(cuenta)
    color_saldo = "positive" if saldo >= 0 else "negative"

    sub = df[df["Cuenta"] == cuenta]
    cargos_items = sub[sub["Tipo"] == "CARGOS"]["Monto"].tolist()
    abonos_items = sub[sub["Tipo"] == "ABONOS"]["Monto"].tolist()

    cargos_html = "".join(f'<div class="t-amount">$ {v:,.2f}</div>' for v in cargos_items) or '<div style="color:#4b5563;font-size:0.8rem;">—</div>'
    abonos_html = "".join(f'<div class="t-amount">$ {v:,.2f}</div>' for v in abonos_items) or '<div style="color:#4b5563;font-size:0.8rem;">—</div>'

    naturaleza_label = "Nat. Deudora" if nat == "deudora" else "Nat. Acreedora"

    st.markdown(f"""
    <div class="cuenta-t">
      <div class="cuenta-t-header">
        <span>{cuenta}</span>
        <span style="font-size:0.7rem;color:#6b7280;">{naturaleza_label}</span>
      </div>
      <div class="cuenta-t-body">
        <div class="cuenta-t-col">
          <div class="cargo-label">Cargos</div>
          {cargos_html}
          <div style="margin-top:0.5rem;border-top:1px solid #2e3347;padding-top:0.4rem;font-size:0.8rem;color:#f87171;">
            Total: $ {cargos_val:,.2f}
          </div>
        </div>
        <div class="cuenta-t-divider"></div>
        <div class="cuenta-t-col">
          <div class="abono-label">Abonos</div>
          {abonos_html}
          <div style="margin-top:0.5rem;border-top:1px solid #2e3347;padding-top:0.4rem;font-size:0.8rem;color:#34d399;">
            Total: $ {abonos_val:,.2f}
          </div>
        </div>
      </div>
      <div style="padding:0.5rem 1rem;border-top:1px solid #2e3347;display:flex;justify-content:space-between;align-items:center;font-size:0.85rem;">
        <span style="color:#6b7280;">Saldo</span>
        <span class="{color_saldo}" style="font-weight:600;">$ {saldo:,.2f}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📒 ContaT")
    st.markdown('<div style="font-size:0.75rem;color:#6b7280;margin-bottom:1.5rem;">Sistema Contable · Cuentas T</div>', unsafe_allow_html=True)

    st.markdown("### Nuevo Movimiento")
    with st.form("form_movimiento", clear_on_submit=True):
        cuentas_disponibles = get_cuentas_list()
        cuenta_sel = st.selectbox("Cuenta", cuentas_disponibles)
        tipo_sel = st.selectbox("Tipo de Movimiento", MOVIMIENTOS)
        monto_sel = st.number_input("Monto ($)", min_value=0.01, step=0.01, format="%.2f")
        fecha_sel = st.date_input("Fecha", value=date.today())
        desc_sel = st.text_input("Descripción (opcional)")
        submitted = st.form_submit_button("➕ Registrar Movimiento", use_container_width=True)

    if submitted:
        if monto_sel > 0:
            save_to_excel(fecha_sel, cuenta_sel, tipo_sel, monto_sel, desc_sel)
            st.success(f"✓ {tipo_sel} de ${monto_sel:,.2f} en {cuenta_sel}")
            st.rerun()
        else:
            st.error("El monto debe ser mayor a 0")

    st.divider()
    st.markdown("### Agregar Cuenta")
    with st.form("form_cuenta"):
        nueva_cuenta = st.text_input("Nombre de la cuenta")
        nat_nueva = st.selectbox("Naturaleza", ["deudora", "acreedora"])
        add_cuenta = st.form_submit_button("➕ Agregar Cuenta", use_container_width=True)

    if add_cuenta and nueva_cuenta.strip():
        nombre = nueva_cuenta.strip().capitalize()
        if nombre not in get_cuentas_list():
            st.session_state.cuentas_custom.append(nombre)
            NATURALEZA[nombre] = nat_nueva
            st.success(f"Cuenta '{nombre}' añadida")
            st.rerun()
        else:
            st.warning("La cuenta ya existe")

    if st.session_state.get("cuentas_custom"):
        st.markdown("**Cuentas personalizadas:**")
        for c in st.session_state.cuentas_custom:
            st.markdown(f"· {c} ({NATURALEZA.get(c,'—')})")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
df_all = load_data()

st.markdown("# ContaT")
st.markdown('<div class="tab-header">Sistema de Cuentas T · Contabilidad Financiera</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🧾 Cuentas T", "📈 Análisis", "📋 Historial"])

# ══════════════════════════════════════════════════════════════════════
# TAB 1 · DASHBOARD
# ══════════════════════════════════════════════════════════════════════
with tab1:
    cuentas_list = get_cuentas_list()

    # Métricas principales
    cols = st.columns(5)
    labels = ["Activos", "Pasivos", "Capital", "Ingresos", "Gastos"]
    colors = ["neutral", "negative", "positive", "positive", "negative"]
    for i, (col, lbl, clr) in enumerate(zip(cols, labels, colors)):
        saldo = calcular_saldo(df_all, lbl) if not df_all.empty else 0
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="label">{lbl}</div>
              <div class="value {clr}">$ {saldo:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ESF
    activos = calcular_saldo(df_all, "Activos")
    pasivos = calcular_saldo(df_all, "Pasivos")
    capital = calcular_saldo(df_all, "Capital")
    cuadrado = abs(activos - (pasivos + capital)) < 0.01

    col_esf, col_res = st.columns([1, 1])
    with col_esf:
        if cuadrado:
            st.markdown(f"""
            <div class="esf-ok">
              ✓ ESF Cuadrado · Activos = Pasivos + Capital<br>
              <span style="font-size:0.85rem;opacity:0.8;">
                $ {activos:,.2f} = $ {pasivos:,.2f} + $ {capital:,.2f}
              </span>
            </div>""", unsafe_allow_html=True)
        else:
            diff = activos - (pasivos + capital)
            st.markdown(f"""
            <div class="esf-fail">
              ✗ ESF No cuadrado · Diferencia: $ {diff:,.2f}<br>
              <span style="font-size:0.85rem;opacity:0.8;">
                Activos: $ {activos:,.2f} ≠ Pasivos + Capital: $ {pasivos + capital:,.2f}
              </span>
            </div>""", unsafe_allow_html=True)

    with col_res:
        ingresos = calcular_saldo(df_all, "Ingresos")
        gastos = calcular_saldo(df_all, "Gastos")
        utilidad = ingresos - gastos
        color_u = "positive" if utilidad >= 0 else "negative"
        tipo_u = "Utilidad Neta" if utilidad >= 0 else "Pérdida Neta"
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">{tipo_u}</div>
          <div class="value {color_u}">$ {utilidad:,.2f}</div>
          <div style="font-size:0.75rem;color:#6b7280;margin-top:0.4rem;">
            Ingresos $ {ingresos:,.2f} − Gastos $ {gastos:,.2f}
          </div>
        </div>""", unsafe_allow_html=True)

    # Mini gráfica de saldos
    if not df_all.empty:
        saldos_data = {c: calcular_saldo(df_all, c) for c in cuentas_list}
        fig_bar = px.bar(
            x=list(saldos_data.keys()),
            y=list(saldos_data.values()),
            labels={"x": "Cuenta", "y": "Saldo ($)"},
            color=list(saldos_data.values()),
            color_continuous_scale=["#f87171", "#fbbf24", "#34d399"],
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e8e3d5",
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=280,
            xaxis=dict(gridcolor="#2e3347"),
            yaxis=dict(gridcolor="#2e3347"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 2 · CUENTAS T
# ══════════════════════════════════════════════════════════════════════
with tab2:
    cuentas_list = get_cuentas_list()
    cols_per_row = 2
    rows = [cuentas_list[i:i+cols_per_row] for i in range(0, len(cuentas_list), cols_per_row)]
    for row in rows:
        cols = st.columns(cols_per_row)
        for col, cuenta in zip(cols, row):
            with col:
                render_cuenta_t(cuenta, df_all)


# ══════════════════════════════════════════════════════════════════════
# TAB 3 · ANÁLISIS
# ══════════════════════════════════════════════════════════════════════
with tab3:
    if df_all.empty:
        st.info("No hay datos registrados aún. Agrega movimientos desde el panel lateral.")
    else:
        col_ctrl1, col_ctrl2 = st.columns([1, 2])
        with col_ctrl1:
            periodo = st.selectbox("Ver por", ["Mes", "Año"])
        with col_ctrl2:
            cuentas_filtro = st.multiselect(
                "Filtrar cuentas",
                get_cuentas_list(),
                default=["Ingresos", "Gastos", "Activos"],
            )

        df_analysis = df_all.copy()

        MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
                 7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

        if periodo == "Mes":
            df_analysis["Periodo"] = df_analysis["Mes"].map(MESES) + " " + df_analysis["Año"].astype(str)
            df_analysis["sort_key"] = df_analysis["Año"] * 100 + df_analysis["Mes"]
        else:
            df_analysis["Periodo"] = df_analysis["Año"].astype(str)
            df_analysis["sort_key"] = df_analysis["Año"]

        if cuentas_filtro:
            df_filtered = df_analysis[df_analysis["Cuenta"].isin(cuentas_filtro)]
        else:
            df_filtered = df_analysis.copy()

        # Calcular saldo neto por período y cuenta según naturaleza
        def saldo_neto(row):
            nat = get_naturaleza(row["Cuenta"])
            if nat == "deudora":
                return row["Monto"] if row["Tipo"] == "CARGOS" else -row["Monto"]
            else:
                return row["Monto"] if row["Tipo"] == "ABONOS" else -row["Monto"]

        df_filtered = df_filtered.copy()
        df_filtered["Saldo"] = df_filtered.apply(saldo_neto, axis=1)

        pivot = df_filtered.groupby(["sort_key", "Periodo", "Cuenta"])["Saldo"].sum().reset_index()
        pivot = pivot.sort_values("sort_key")

        # Gráfico de líneas por cuenta
        fig_line = px.line(
            pivot,
            x="Periodo",
            y="Saldo",
            color="Cuenta",
            markers=True,
            title=f"Evolución de Saldos por {periodo}",
            color_discrete_sequence=["#93c5fd","#34d399","#f87171","#fbbf24","#c084fc","#fb923c"],
        )
        fig_line.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e8e3d5",
            title_font_family="DM Serif Display",
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="#2e3347"),
            yaxis=dict(gridcolor="#2e3347"),
            height=350,
        )
        st.plotly_chart(fig_line, use_container_width=True)

        col_a, col_b = st.columns(2)

        with col_a:
            # Barras apiladas Cargos vs Abonos
            df_tipo = df_filtered.groupby(["Periodo", "sort_key", "Tipo"])["Monto"].sum().reset_index().sort_values("sort_key")
            fig_stack = px.bar(
                df_tipo,
                x="Periodo",
                y="Monto",
                color="Tipo",
                barmode="group",
                title="Cargos vs Abonos",
                color_discrete_map={"CARGOS": "#f87171", "ABONOS": "#34d399"},
            )
            fig_stack.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e8e3d5",
                title_font_family="DM Serif Display",
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(gridcolor="#2e3347"),
                yaxis=dict(gridcolor="#2e3347"),
                height=300,
            )
            st.plotly_chart(fig_stack, use_container_width=True)

        with col_b:
            # Pie distribución por cuenta
            pie_data = df_filtered.groupby("Cuenta")["Monto"].sum().reset_index()
            fig_pie = px.pie(
                pie_data,
                values="Monto",
                names="Cuenta",
                title="Distribución por Cuenta",
                color_discrete_sequence=["#93c5fd","#34d399","#f87171","#fbbf24","#c084fc","#fb923c"],
                hole=0.4,
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e8e3d5",
                title_font_family="DM Serif Display",
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                height=300,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Tabla resumen
        st.markdown("#### Resumen por Período")
        tabla_resumen = pivot.pivot_table(
            index="Periodo", columns="Cuenta", values="Saldo", aggfunc="sum", fill_value=0
        )
        tabla_resumen.index.name = "Período"
        st.dataframe(
            tabla_resumen.style.format("${:,.2f}").background_gradient(cmap="RdYlGn", axis=None),
            use_container_width=True,
        )

        # Insights
        st.markdown("#### 🔍 Insights")
        if "Ingresos" in df_all["Cuenta"].values and "Gastos" in df_all["Cuenta"].values:
            df_ig = df_analysis[df_analysis["Cuenta"].isin(["Ingresos","Gastos"])].copy()
            df_ig["Saldo"] = df_ig.apply(saldo_neto, axis=1)
            if periodo == "Mes":
                top = df_ig[df_ig["Cuenta"]=="Ingresos"].groupby("Periodo")["Saldo"].sum()
                if not top.empty:
                    mes_max = top.idxmax()
                    st.success(f"📈 El período con más ingresos fue **{mes_max}** con **${top.max():,.2f}**")
                bottom = df_ig[df_ig["Cuenta"]=="Gastos"].groupby("Periodo")["Saldo"].sum()
                if not bottom.empty:
                    mes_gasto = bottom.idxmax()
                    st.warning(f"📉 El período con más gastos fue **{mes_gasto}** con **${bottom.max():,.2f}**")


# ══════════════════════════════════════════════════════════════════════
# TAB 4 · HISTORIAL
# ══════════════════════════════════════════════════════════════════════
with tab4:
    if df_all.empty:
        st.info("Sin movimientos registrados.")
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            cuentas_h = ["Todas"] + get_cuentas_list()
            filtro_cuenta = st.selectbox("Filtrar por cuenta", cuentas_h)
        with col_f2:
            filtro_tipo = st.selectbox("Filtrar por tipo", ["Todos", "CARGOS", "ABONOS"])
        with col_f3:
            años = sorted(df_all["Año"].dropna().unique().astype(int).tolist(), reverse=True)
            filtro_año = st.selectbox("Año", ["Todos"] + [str(a) for a in años])

        df_hist = df_all.copy()
        if filtro_cuenta != "Todas":
            df_hist = df_hist[df_hist["Cuenta"] == filtro_cuenta]
        if filtro_tipo != "Todos":
            df_hist = df_hist[df_hist["Tipo"] == filtro_tipo]
        if filtro_año != "Todos":
            df_hist = df_hist[df_hist["Año"] == int(filtro_año)]

        df_hist = df_hist.sort_values("Fecha", ascending=False)

        def color_tipo(val):
            if val == "CARGOS":
                return "color: #f87171"
            elif val == "ABONOS":
                return "color: #34d399"
            return ""

        st.dataframe(
            df_hist[["Fecha","Cuenta","Tipo","Monto","Descripcion"]].style
                .format({"Monto": "${:,.2f}", "Fecha": lambda x: str(x)[:10]})
                .applymap(color_tipo, subset=["Tipo"]),
            use_container_width=True,
            height=400,
        )

        st.markdown(f"**{len(df_hist)} movimientos** · Total cargos: **${df_hist[df_hist['Tipo']=='CARGOS']['Monto'].sum():,.2f}** · Total abonos: **${df_hist[df_hist['Tipo']=='ABONOS']['Monto'].sum():,.2f}**")

        col_dl1, col_dl2 = st.columns([1, 4])
        with col_dl1:
            csv_data = df_hist.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Descargar CSV",
                data=csv_data,
                file_name="historial_contable.csv",
                mime="text/csv",
                use_container_width=True,
            )
