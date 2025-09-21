import os
import requests
import time
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

app = Flask(__name__)

CHROME_BINARY_PATH = "selenium/chrome"
CHROMEDRIVER_PATH = "selenium/chromedriver"

def download_file(url, filename):
    print(f"Descargando {filename}...")
    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Descarga completada: {filename}")
        if "chromedriver" in filename:
            os.chmod(filename, 0o755)
            print(f"Permisos ejecutables asignados a {filename}")
    except Exception as e:
        print(f"Error descargando {filename}: {e}")

if not os.path.exists("selenium"):
    os.makedirs("selenium", exist_ok=True)

if not os.path.exists("selenium/chrome"):
    print("Chrome no encontrado, descargando...")
    download_file("https://github.com/nakigeplayer/flask-scrap/releases/download/Selenium/chrome", "selenium/chrome")
    
if not os.path.exists("selenium/chromedriver"):
    print("Chromedriver no encontrado, descargando...")
    download_file("https://github.com/nakigeplayer/flask-scrap/releases/download/Selenium/chromedriver", "selenium/chromedriver")

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')
    chrome_options.add_argument('--accept-language=en-US,en;q=0.9')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.binary_location = CHROME_BINARY_PATH

    try:
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("Driver configurado exitosamente")
        return driver
    except Exception as e:
        print(f"Error al configurar el driver: {e}")
        return None

def scrape_nhentai_with_selenium(search_term, page=1):
    print(f"Iniciando scraping para: {search_term}, página: {page}")
    driver = setup_driver()
    if not driver:
        print("Error: No se pudo inicializar el driver")
        return []
    
    try:
        url = f"https://nhentai.net/search/?q={search_term}&page={page}"
        print(f"Accediendo a URL: {url}")
        
        driver.get(url)
        print("Página cargada, esperando 5 segundos...")
        time.sleep(5)
        
        page_source = driver.page_source
        if "Just a moment" in page_source or "Verifying" in page_source or "Cloudflare" in page_source:
            print("Cloudflare detectado, esperando 15 segundos...")
            time.sleep(15)
        
        try:
            print("Esperando elementos gallery...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "gallery"))
            )
            print("Elementos gallery encontrados")
        except Exception as e:
            print(f"Timeout esperando galleries: {e}")
            print("HTML de la página:", driver.page_source[:1000])
            return []
        
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        gallery_divs = soup.find_all('div', class_='gallery')
        
        print(f"Encontrados {len(gallery_divs)} divs con clase gallery")
        
        if not gallery_divs:
            print("No se encontraron galleries, buscando cualquier div con data-tags...")
            gallery_divs = soup.find_all('div', {'data-tags': True})
            print(f"Encontrados {len(gallery_divs)} divs con data-tags")
        
        if not gallery_divs:
            print("No se encontraron galleries después de búsqueda alternativa")
            return []
        
        results = []
        
        for gallery in gallery_divs:
            try:
                data_tags = gallery.get('data-tags', '').split()
                link_tag = gallery.find('a', class_='cover')
                if not link_tag:
                    link_tag = gallery.find('a')
                    if not link_tag:
                        continue
                
                href = link_tag.get('href', '')
                gallery_code = href.split('/')[-2] if href.startswith('/g/') else 'N/A'
                
                img_tags = gallery.find_all('img')
                image_links = []
                
                for img in img_tags:
                    src = img.get('src', '') or img.get('data-src', '')
                    if src:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://nhentai.net' + src
                        image_links.append(src)
                
                caption_div = gallery.find('div', class_='caption')
                if not caption_div:
                    caption_div = gallery.find('div', class_='title')
                name = caption_div.text.strip() if caption_div else 'N/A'
                
                result = {
                    'image_links': list(set(image_links)),
                    'name': name,
                    'code': gallery_code,
                    'tags': data_tags
                }
                
                results.append(result)
                print(f"Gallery procesado: {name}")
                
            except Exception as e:
                print(f"Error procesando gallery: {e}")
                continue
        
        print(f"Scraping completado. {len(results)} resultados obtenidos")
        return results
        
    except Exception as e:
        print(f"Error durante el scraping: {e}")
        return []
    
    finally:
        try:
            driver.quit()
            print("Driver cerrado")
        except:
            pass

@app.route('/')
def home():
    return "Servidor Flask corriendo"

@app.route('/snh')
def nhentai_mirror():
    search_term = request.args.get('q', '')
    page = request.args.get('p', 1, type=int)
    
    if not search_term:
        return jsonify({"error": "Parámetro 'q' requerido"}), 400
    
    print(f"Solicitud recibida: buscar '{search_term}' en página {page}")
    
    results = scrape_nhentai_with_selenium(search_term, page)
    
    print(f"Request completado. Enviando {len(results)} resultados")
    
    return jsonify({
        "search_term": search_term,
        "page": page,
        "results": results,
        "count": len(results)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
