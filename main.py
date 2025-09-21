import os
import requests
import subprocess
from flask import Flask, jsonify, request
from selenium_scraper import scrape_nhentai_with_selenium

app = Flask(__name__)

def download_file(url, filename):
    print(f"Descargando {filename}...")
    try:
        response = requests.get(url, stream=True)
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

@app.route('/')
def home():
    return "Servidor Flask corriendo"

@app.route('/snh')
def nhentai_mirror():
    search_term = request.args.get('q', '')
    page = request.args.get('p', 1, type=int)
    
    if not search_term:
        return jsonify({"error": "Parámetro 'q' (query) requerido"}), 400
    
    print(f"Buscando: '{search_term}' en página {page}")
    
    results = scrape_nhentai_with_selenium(search_term, page)
    
    print(f"Resultados encontrados: {len(results)}")
    
    return jsonify({
        "search_term": search_term,
        "page": page,
        "results": results,
        "count": len(results)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
