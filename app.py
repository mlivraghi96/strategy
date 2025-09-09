import json
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
import time
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📈 PV + BESS Strategy")

# ---- Dati iniziali
default_data_str = "105.000000,96.890000,94.370000,94.020000,94.600000,100.000000,110.304680,125.710000,127.400000,104.000000,94.990000,88.890000,81.700000,82.740000,88.280000,84.114960,94.970000,105.100000,121.987090,152.941150,159.723640,123.594350,115.350120,110.796190"
default_prices = [float(x) for x in default_data_str.split(",")]
pv_profile = [0,0,0,0,0,0,25.57948906,54.67371386,69.94165438,77.54612584,80.71999784,82.77323408,83.116512,83.83018936,85.77769024,86.72839536,84.73501656,77.86880278,63.14636576,21.77632165,0,0,0,0]

# Tabelle modificabili (senza indice, due colonne)

target_avg_price = st.number_input("Average price (€/MWh)", min_value=20.0, max_value=300.0, value=np.mean(default_prices))

scaling_pv = st.number_input("Scaling factor PV (%)", min_value=0.0, max_value=150.0, value=100.0)
factor_pv = scaling_pv / 100

pv = np.array(pv_profile) * factor_pv

# Ricalcolo curva prezzi con nuovo prezzo medio
scaling_factor = target_avg_price / np.mean(np.array(default_prices))
adjusted_prices = np.array(default_prices) * scaling_factor

prices = list(adjusted_prices)

# ---- Stato prezzi (Python)
if "prezzi" not in st.session_state:
    st.session_state.prezzi = prices[:]

if "last_update" not in st.session_state:
    st.session_state.last_update = 0

# ---- Parametri contrattuali (sidebar)
with st.sidebar:
    st.header("⚙️ Parameters")
    ppa_base_price  = st.number_input("PPA Baseload Price (€/MWh)", value=99.2, key="ppa_base")
    ppa_base_qty    = st.number_input("PPA Baseload quantity (MW)", value=20, key="ppa_qty")
    ppa_solar_price = st.number_input("PPA PV Price (€/MWh)", value=70.0, key="ppa_solar")
    swap_price      = st.number_input("Swap BESS Price (€/MWh)", value=40.0, key="swap")
    bess_size       = st.number_input("BESS size (MW)", value=40, key="size")
    bess_pe         = st.number_input("BESS E/P ratio (h)", value=4, key="ep")
    bess_eff        = st.number_input("BESS efficiency", value=0.87, key="eff")
    
    if st.button("⏮️ Reset curve", type="secondary"):
        st.session_state.prezzi = prices[:]
        st.session_state.last_update = time.time()
        st.rerun()
    if st.button("🔄 Update calc", type="secondary"):
        st.session_state.last_update = time.time()
        st.rerun()

# ---- Container per il grafico e il polling
col1, col2 = st.columns([3, 1])

with col1:
    # Placeholder per il grafico
    chart_container = st.container()
    
with col2:
    # Status indicator
    status_container = st.container()

# ---- Grafico interattivo con Chart.js
with chart_container:
    chart_data_json = json.dumps(st.session_state.prezzi)
    
    html_code = f"""
    <style>
        #chartContainer {{
            padding: 10px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        #status {{
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            background: #4CAF50;
            color: white;
            border-radius: 4px;
            font-size: 12px;
            opacity: 0;
            transition: opacity 0.3s;
        }}
        #status.active {{
            opacity: 1;
        }}
    </style>
    <div id="chartContainer">
        <div id="status">Aggiornato!</div>
        <canvas id="chart" width="900" height="400"></canvas>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-dragdata@2.3.0/dist/chartjs-plugin-dragdata.min.js"></script>
    <script>
        (function() {{
            const ctx = document.getElementById('chart').getContext('2d');
            const statusEl = document.getElementById('status');
            
            // Dati iniziali
            const chartData = {chart_data_json};
            
            // Funzione per salvare i dati nel localStorage e notificare il parent
            function saveData(prices) {{
                const timestamp = Date.now();
                const dataToSave = {{
                    prices: prices,
                    timestamp: timestamp
                }};
                
                // Salva nel localStorage
                try {{
                    localStorage.setItem('chartPrices', JSON.stringify(dataToSave));
                    
                    // Mostra indicatore di aggiornamento
                    statusEl.classList.add('active');
                    setTimeout(() => statusEl.classList.remove('active'), 1000);
                    
                    // Notifica il parent window
                    if (window.parent !== window) {{
                        window.parent.postMessage({{
                            type: 'chartUpdate',
                            prices: prices,
                            timestamp: timestamp
                        }}, '*');
                    }}
                }} catch(e) {{
                    console.error('Error saving data:', e);
                }}
            }}
            
            // Configurazione del grafico
            const data = {{
                labels: Array.from({{length: 24}}, (_, i) => i.toString().padStart(2, '0') + ':00'),
                datasets: [{{
                    label: 'Hourly Price (€/MWh)',
                    data: chartData,
                    borderColor: '#2b6cb0',
                    backgroundColor: 'rgba(43, 108, 176, 0.1)',
                    pointRadius: 6,
                    pointHoverRadius: 9,
                    pointBackgroundColor: '#2b6cb0',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    fill: true,
                    tension: 0.2
                }}]
            }};
            
            const config = {{
                type: 'line',
                data: data,
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{
                        intersect: false,
                        mode: 'index'
                    }},
                    scales: {{
                        x: {{
                            title: {{
                                display: true,
                                text: 'Hour',
                                font: {{ size: 14, weight: 'bold' }}
                            }},
                            grid: {{
                                display: true,
                                color: 'rgba(0, 0, 0, 0.05)'
                            }}
                        }},
                        y: {{
                            title: {{
                                display: true,
                                text: 'Price (€/MWh)',
                                font: {{ size: 14, weight: 'bold' }}
                            }},
                            min: 0,
                            max: 200,
                            grid: {{
                                display: true,
                                color: 'rgba(0, 0, 0, 0.05)'
                            }}
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'top'
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#fff',
                            bodyColor: '#fff',
                            borderColor: '#2b6cb0',
                            borderWidth: 1,
                            padding: 10,
                            displayColors: false,
                            callbacks: {{
                                label: function(context) {{
                                    return 'Prezzo: €' + context.parsed.y.toFixed(2) + '/MWh';
                                }}
                            }}
                        }},
                        dragData: {{
                            round: 1,
                            showTooltip: true,
                            dragX: false,
                            onDragStart: function(e, datasetIndex, index, value) {{
                                // Opzionale: feedback visivo
                            }},
                            onDrag: function(e, datasetIndex, index, value) {{
                                // Limita il valore tra 0 e 200
                                value = Math.max(0, Math.min(200, value));
                                data.datasets[0].data[index] = value;
                                return value;
                            }},
                            onDragEnd: function(e, datasetIndex, index, value) {{
                                // Salva i dati quando finisce il drag
                                saveData(data.datasets[0].data.slice());
                            }}
                        }}
                    }}
                }}
            }};
            
            const chart = new Chart(ctx, config);
            
            // Salva i dati iniziali
            saveData(chartData);
        }})();
    </script>
    """
    
    st.components.v1.html(html_code, height=450, scrolling=False)

# ---- Polling per aggiornamenti dal localStorage
with status_container:
    # Usa streamlit_js_eval per leggere dal localStorage
    poll_script = """
    (() => {
        try {
            const stored = localStorage.getItem('chartPrices');
            if (stored) {
                const data = JSON.parse(stored);
                return data;
            }
        } catch(e) {
            console.error('Error reading localStorage:', e);
        }
        return null;
    })()
    """
    
    # Poll per nuovi dati ogni 500ms
    chart_data = streamlit_js_eval(
        js_expressions=poll_script,
        key=f"poll_chart_{st.session_state.last_update}",
        want_output=True,
    )
    
    # Aggiorna lo stato se ci sono nuovi dati
    if chart_data and isinstance(chart_data, dict):
        new_prices = chart_data.get('prices', [])
        new_timestamp = chart_data.get('timestamp', 0)
        
        if (len(new_prices) == 24 and 
            new_timestamp > st.session_state.last_update):
            
            st.session_state.prezzi = [float(x) for x in new_prices]
            st.session_state.last_update = new_timestamp
            st.rerun()

# ---- Calcolo P&L
st.markdown("---")
st.subheader("💰 Profit & Loss")

prezzi = st.session_state.prezzi

#########################################
# PPA Baseload (vendita)
pnl_base = (ppa_base_price - np.mean(np.array(prezzi))) * (ppa_base_qty * 24)

# PPA Solare (acquisto)
pnl_solar = np.array(prezzi).dot(np.array(pv)) - ppa_solar_price * np.sum(np.array(pv))

# Swap con BESS (acquisto)
sort_prices = np.sort(prezzi)
spread = np.mean(sort_prices[-int(bess_pe):]) - np.mean(sort_prices[:int(bess_pe)]) 
pnl_swap = (spread - swap_price) * (bess_pe*bess_size*bess_eff)

total_pnl = pnl_base + pnl_solar + pnl_swap

#########################################

# ---- Display metriche
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    delta_color = "normal" if total_pnl >= 0 else "inverse"
    st.metric(
        label="📊 P&L Total", 
        value=f"€ {total_pnl:,.2f}",
        delta=f"{'Profit' if total_pnl >= 0 else 'Loss'}",
        delta_color=delta_color
    )

with col2:
    st.metric(
        label="⚡ PPA Baseload",
        value=f"€ {pnl_base:,.2f}",
        delta=f"{ppa_base_price - np.mean(np.array(prezzi)):.1f} EUR/MWh",
        delta_color="off"
    )

with col3:
    st.metric(
        label="☀️ PPA Solar",
        value=f"€ {pnl_solar:,.2f}",
        delta=f"{np.array(prezzi).dot(np.array(pv)) / np.sum(np.array(pv)) - ppa_solar_price:.1f} EUR/MWh",
        delta_color="off"
    )

with col4:
    st.metric(
        label="🔋 Swap BESS",
        value=f"€ {pnl_swap:,.2f}",
        delta=f"{spread - swap_price:.2f} EUR/MWh",
        delta_color="off"
    )

with col5:
    st.metric(
        label="Solar Cannibalization",
        value=f"{(1 - np.array(prezzi).dot(np.array(pv)) / np.sum(np.array(pv)) / np.mean(np.array(prezzi))) *100:.2f} %",
        delta="",
        delta_color="off"
    )

if st.button("Show PV chart"):

    # Grafico Produzione PV
    st.subheader("🌞 PV production")
    hours = np.arange(24)
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(hours, np.array(pv), label="PV", marker='x', color='tab:orange')
    ax2.set_xlabel("hour")
    ax2.set_ylabel("MWh")
    ax2.grid(True)
    ax2.legend()
    st.pyplot(fig2)

# ---- Auto-refresh per mantenere aggiornati i dati
st.markdown(
    """
    <script>
        // Auto-refresh ogni 500ms per catturare gli aggiornamenti
        setTimeout(() => {
            window.parent.location.reload();
        }, 500);
    </script>
    """,
    unsafe_allow_html=True
)
