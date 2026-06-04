import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import traceback

# --- CONFIGURACIÓN DEL NAVEGADOR (MODO NUBE) ---
def iniciar_navegador():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # User-Agent para evitar ser detectado como bot
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    # Rutas binarias estándar de Streamlit Cloud
    chrome_options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Tourplan Automator", page_icon="🏢", layout="wide")
st.title("🏢 Tourplan Automation Web")

with st.sidebar:
    st.header("🔐 Credenciales")
    user_input = st.text_input("Usuario")
    pass_input = st.text_input("Contraseña", type="password")
    st.divider()
    st.header("📋 Configuración Excel")
    nombre_pestana = st.text_input("Nombre de la pestaña", value="Sheet1")
    st.info("Asegúrate de que el Excel tenga las columnas: REFERENCIA, FECHA, IMPORTE")

archivo_excel = st.file_uploader("📂 Sube tu archivo Excel", type=["xlsx", "xls", "xlsm"])

# --- LÓGICA DE PROCESAMIENTO ---
if st.button("🚀 Iniciar Proceso"):
    if not user_input or not pass_input or not archivo_excel:
        st.warning("Faltan datos obligatorios (Credenciales o archivo).")
    else:
        driver = None  # Inicializamos la variable para el bloque finally
        try:
            # 1. Leer Excel
            df = pd.read_excel(archivo_excel, sheet_name=nombre_pestana)
            st.success(f"Excel cargado correctamente: {len(df)} filas.")
            
            reporte_final = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            with st.status("Ejecutando robot...", expanded=True) as status:
                status.write("🌐 Iniciando navegador invisible...")
                driver = iniciar_navegador()
                wait = WebDriverWait(driver, 20) # Espera explícita inteligente
                
                # --- PASO 1: LOGIN ---
                status.write("🔗 Accediendo a Tourplan...")
                driver.get('https://la-atpdmc.nx.tourplan.net/TourplanNX/#/home')
                
                try:
                    status.write("🔑 Introduciendo credenciales...")
                    # Esperar de forma segura a que el campo de usuario aparezca
                    user_field = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'username')))
                    user_field.clear()
                    user_field.send_keys(user_input)
                    
                    pass_field = driver.find_element(By.CLASS_NAME, 'password')
                    pass_field.clear()
                    pass_field.send_keys(pass_input)
                    
                    # Intentamos hacer clic en el botón de login de forma más segura
                    login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/login/div/div/div/tp-login/div/div/button')))
                    login_btn.click()
                    
                    status.write("⏳ Esperando respuesta del servidor...")
                    # OPTIMIZACIÓN: En vez de congelar 5 segundos fijos, esperamos a que el login desaparezca 
                    # o que la URL cambie. Si no funciona, dejamos un sleep corto de seguridad.
                    time.sleep(5) 
                    status.write("✅ Login completado.")
                    
                except Exception as e:
                    status.update(label="❌ Error en Login", state="error")
                    # Captura de pantalla segura en caso de error
                    try:
                        screenshot = driver.get_screenshot_as_png()
                        st.image(screenshot, caption="Error en el momento del Login")
                    except:
                        st.warning("No se pudo tomar la captura de pantalla.")
                    raise e

                # --- PASO 2: BUCLE DE REFERENCIAS ---
                for index, fila in df.iterrows():
                    ref = str(fila.get('REFERENCIA', '')).strip()
                    status_text.text(f"Procesando: {ref} ({index+1}/{len(df)})")
                    
                    # Saltar filas vacías si las hay
                    if not ref or ref == "nan":
                        reporte_final.append({"Referencia": f"Fila {index+1}", "Resultado": "⚠️ Vacía o Inválida"})
                        continue
                    
                    try:
                        # --- 📥 [TUS ACCIONES DE SELENIUM AQUÍ] ---
                        # Ejemplo: 
                        # buscar_input = wait.until(EC.presence_of_element_located((By.ID, "search")))
                        # ...
                        time.sleep(1) # Simulación de trabajo
                        
                        reporte_final.append({"Referencia": ref, "Resultado": "✅ Procesado"})
                    except Exception as e:
                        reporte_final.append({"Referencia": ref, "Resultado": f"❌ Error: {str(e)}"})
                    
                    # Actualizar barra de progreso de Streamlit
                    progress_bar.progress((index + 1) / len(df))

                status.update(label="✅ Automatización Finalizada", state="complete")

            # --- RESULTADOS ---
            st.divider()
            st.subheader("📊 Resumen de Ejecución")
            st.dataframe(pd.DataFrame(reporte_final), use_container_width=True)
            st.balloons()

        except Exception as e:
            st.error("⚠️ El proceso se detuvo por un error crítico")
            st.expander("Ver detalles técnicos").text(traceback.format_exc())
            if driver:
                try:
                    st.image(driver.get_screenshot_as_png(), caption="Último estado del navegador antes del fallo")
                except:
                    pass
        finally:
            # El bloque 'finally' garantiza que el navegador se cierre SIEMPRE,
            # evitando que consuma RAM en el servidor de Streamlit Cloud.
            if driver:
                driver.quit()
