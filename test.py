import os
import io
import time
import requests
import json
from flask import Flask, render_template, request, Response
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import easyocr
from datetime import datetime
from lxml import html

# 🔹 Initialisation de Flask
app = Flask(__name__)

# 🔹 Configuration Selenium
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--enable-javascript")
driver = webdriver.Chrome(options=options)



# 🔹 Configuration OCR
reader = easyocr.Reader(['fr'])

# 🔹 Liste des sites disponibles (incluant Agglo_Sainte_Arretés et Charente_Maritime)
sites = {
    "Publiact_TulleAgglo": 'https://publiact.fr/i/1306_649ea512a195f',
    "Publiact_Saintes": 'https://publiact.fr/i/1040_62f22409bed5d',
    "GrandAngouleme_Decisions": 'https://actes.grandangouleme.fr/category/decisions/',
    "GrandAngouleme_Arrêtes": 'https://actes.grandangouleme.fr/category/arretes/',  
    "Conseil_Departemental_HauteVienne_Arretes": "https://arretes.haute-vienne.fr/webdelibplus/jsp/summary_orders.jsp?role=usager",
    "Agglo_Sainte_Arretés": "https://www.agglo-saintes.fr/nous-connaitre/organisation-politique/actes-reglementaires/585-arretes.html",
    "Charente_Maritime": "https://la.charente-maritime.fr/informations-officielles/deliberations-et-actes"
}

# 🔹 URL de base pour le téléchargement des fichiers Publiact
base_download_url = 'https://publiact.fr/api/document/download'


# --- 📌 Fonction pour Agglo_Sainte_Arretes ---
def fetch_agglo_sainte_arretes(site_url):
    """ Récupère les arrêtés publiés sur le site Agglo Sainte """
    response = requests.get(site_url, verify=False)

    if response.status_code == 200:
        tree = html.fromstring(response.content)
        
        # Extraction des noms et liens des documents
        document_names = tree.xpath("//ul[@class='csc-uploads csc-uploads-0']//a/span[@class='csc-uploads-fileSize']/preceding-sibling::text()")
        document_links = tree.xpath("//ul[@class='csc-uploads csc-uploads-0']//a/@href")
        
        documents = []
        for name, link in zip(document_names, document_links):
            documents.append({"title": name.strip(), "link": link})

        return documents
    else:
        print(f"Erreur lors de la récupération de la page: {response.status_code}")
        return []


# --- 📌 Fonction pour Publiact ---
def fetch_publiact_documents(site_url):
    """ Récupère les documents Publiact """
    driver.get(site_url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'table')))
    
    # Sélectionner 100 documents par page
    try:
        select_100 = driver.find_element(By.XPATH, "//select/option[text()='100']")
        select_100.click()
        time.sleep(2)
    except Exception as e:
        print(f"Erreur lors de la sélection du nombre de documents par page : {e}")
    
    documents = []
    current_page = 1

    while True:
        rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
        for row in rows:
            try:
                name = row.find_element(By.XPATH, "./td[2]").text
                link = row.find_element(By.XPATH, "./td[5]/div/a").get_attribute('href')
                document_id = link.split('/')[-1]
                download_link = f"{base_download_url}/{document_id}"
                documents.append((name, link, download_link))
            except Exception as e:
                print(f"Erreur lors de l'extraction d'un document : {e}")
                continue

        try:
            next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Suivant')]")
            next_button.click()
            current_page += 1
            time.sleep(2)
        except:
            break

    return documents


# --- 📌 Fonction pour GrandAngouleme Décisions ---
def fetch_grandangouleme_decisions(site_url):
    """ Récupère les documents du site GrandAngouleme - Décisions """
    driver.get(site_url)
    time.sleep(3)

    documents = []
    articles = driver.find_elements(By.TAG_NAME, "article")

    for article in articles:
        try:
            title_element = article.find_element(By.CSS_SELECTOR, "h1.entry-subtitle a")
            title = title_element.text.strip()
            link = title_element.get_attribute("href")
            documents.append((title, link, link))  
        except:
            continue

    return documents


# --- 📌 Fonction pour GrandAngouleme Arrêtés ---
def fetch_grandangouleme_arretes(site_url):
    """ Récupère les documents du site GrandAngouleme - Arrêtés """
    driver.get(site_url)
    time.sleep(3)

    documents = []
    articles = driver.find_elements(By.TAG_NAME, "article")

    for article in articles:
        try:
            title_element = article.find_element(By.CSS_SELECTOR, "h1.entry-subtitle a")
            title = title_element.text.strip()
            link = title_element.get_attribute("href")
            documents.append((title, link, link))  
        except:
            continue

    return documents

# --- 📌 Fonction pour Conseil Départemental de la Haute Vienne - Arrêtés ---
def fetch_haute_vienne_arretes(site_url):
    """ Récupère les documents du site Conseil Départemental de la Haute Vienne - Arrêtés """
    driver.get(site_url)
    time.sleep(3)  # Attendre le chargement de la page

    documents = {}
    rows = driver.find_elements(By.XPATH, "//html/body/main/section/table/tbody/tr")  # Récupérer toutes les lignes du tableau

    for index, row in enumerate(rows, start=1):
        try:
            title_element = row.find_element(By.XPATH, "./td[2]")
            title = title_element.text.strip()

            link_element = row.find_element(By.XPATH, "./td[2]/a")
            link = link_element.get_attribute("href")

            date_element = row.find_element(By.XPATH, "./td[4]")
            publication_date = date_element.text.strip()

            documents[link] = {"title": title, "publication_date": publication_date}
        except Exception as e:
            print(f"⚠️ Erreur sur la ligne {index} : {e}")

    return documents


# --- 📌 Fonction pour Charente_Maritime ---
def fetch_charente_maritime_documents(site_url, search_term):
    """ Récupère les documents du site Charente Maritime """
    response = requests.get(site_url)

    if response.status_code == 200:
        tree = html.fromstring(response.content)
        
        # Extraction des titres des documents et leurs liens
        documents = tree.xpath('//article[@class="node node--type-deliberations node--view-mode-teaser"]/h2/a')
        
        result_docs = []
        for doc in documents:
            title = doc.text.strip()
            link = doc.get("href")
            
            # Si le terme de recherche est présent dans le titre
            if search_term.lower() in title.lower():
                result_docs.append({
                    "title": title,
                    "link": f"{site_url}{link}"  # Construire l'URL complète du lien
                })

        return result_docs
    else:
        print(f"Erreur lors de la récupération de la page Charente Maritime: {response.status_code}")
        return []

# --- 📌 Fonction pour télécharger et extraire du texte des PDF ---
def download_and_extract_text(pdf_url):
    try:
        response = requests.get(pdf_url, stream=True)
        if response.status_code == 200:
            with io.BytesIO(response.content) as pdf_stream:
                doc = fitz.open(stream=pdf_stream, filetype="pdf")
                text = []
                for page_num in range(min(doc.page_count, 3)):  
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=100)
                    img = Image.open(io.BytesIO(pix.tobytes())).convert("L")
                    text.append(" ".join(reader.readtext(np.array(img), detail=0)))
                return "\n".join(text)
        return ""
    except:
        return ""
    
    
# --- 📌 Fonction principale de recherche ---
def search_documents(site_key, search_term):
    if site_key == "Agglo_Sainte_Arretés":
        documents = fetch_agglo_sainte_arretes(sites[site_key])
        result_docs = []
        for doc in documents:
            if search_term.lower() in doc["title"].lower():
                result_docs.append({
                    "title": doc["title"],
                    "link": doc["link"]
                })
        return json.dumps(result_docs)

    elif site_key == "Conseil_Departemental_HauteVienne_Arretes":
        documents = fetch_haute_vienne_arretes(sites[site_key])
        result_docs = []
        
        for link, info in documents.items():
            title = info["title"]
            if search_term.lower() in title.lower():
                result_docs.append({
                    "title": title,
                    "link": link,
                    "publication_date": info["publication_date"]
                })
        return json.dumps(result_docs)

    elif site_key == "Charente_Maritime":
        documents = fetch_charente_maritime_documents(sites[site_key], search_term)
        result_docs = []

        for doc in documents:
            result_docs.append({
                "title": doc["title"],
                "link": doc["link"]
            })
        return json.dumps(result_docs)

    elif site_key in ["Publiact_TulleAgglo", "Publiact_Saintes"]:
        documents = fetch_publiact_documents(sites[site_key])
    elif site_key == "GrandAngouleme_Decisions":
        documents = fetch_grandangouleme_decisions(sites[site_key])
    elif site_key == "GrandAngouleme_Arrêtes":
        documents = fetch_grandangouleme_arretes(sites[site_key])
    else:
        return []

    result_docs = []
    
    for name, link, download_link in documents:
        if site_key.startswith("Publiact"):
            text = download_and_extract_text(link)
        else:
            driver.get(link)
            time.sleep(3)
            try:
                pdf_element = driver.find_element(By.XPATH, "//a[contains(@href, '.pdf')]")
                pdf_url = pdf_element.get_attribute("href")
                text = download_and_extract_text(pdf_url)
            except:
                continue

        if search_term.lower() in text.lower():
            result_docs.append({
                "title": name,
                "link": link,
                "download_link": download_link
            })

    return json.dumps(result_docs)


# --- 📌 Routes Flask ---
@app.route('/')
def home():
    return render_template('index.html', sites=sites.keys())


@app.route('/search', methods=['POST'])
def search_action():
    search_term = request.form['search_term']
    selected_site = request.form['selected_site']

    if not search_term:
        return Response("Veuillez entrer un terme de recherche.", status=400)

    results = search_documents(selected_site, search_term)
    return Response(results, mimetype='application/json')


# --- 📌 Démarrage de l'application ---
if __name__ == "__main__":
    app.run(debug=True)
