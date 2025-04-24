import os
import time
import random
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === PARAMÈTRES ===
URL = 'https://publiact.fr/i/1306_649ea512a195f'
BASE_DOWNLOAD_URL = 'https://publiact.fr/api/document/download'

# === DRIVER CHROME AVEC DOSSIER DE TÉLÉCHARGEMENT CONFIGURÉ ===
def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--enable-javascript")
    return webdriver.Chrome(options=options)

# === DEMANDER MOIS/ANNÉE À L'UTILISATEUR ===
def get_target_month_year():
    mois = input("Entrez le mois (en chiffre, ex: 03) : ").zfill(2)
    annee = input("Entrez l'année (ex: 2025) : ")
    return annee, mois

# === CRÉATION DOSSIER PAR DATE ===
def create_download_folder(base_path, year, month):
    folder = os.path.join(base_path, f"{year}-{month}")
    os.makedirs(folder, exist_ok=True)
    return folder

# === EXTRACTION DES DOCUMENTS ===
def extract_links(driver, base_download_url):
    links = {}
    item = 1
    while True:
        try:
            item_link = driver.find_element(
                By.XPATH, f"/html/body/div/div[2]/main/div/div/div/div[2]/div[1]/fieldset/div[2]/table/tbody/tr[{item}]/td[5]/div/a").get_attribute('href')
            name = driver.find_element(
                By.XPATH, f"/html/body/div/div[2]/main/div/div/div/div[2]/div[1]/fieldset/div[2]/table/tbody/tr[{item}]/td[2]/div/div").text
            if not name:
                name = driver.find_element(
                    By.XPATH, f"/html/body/div/div[2]/main/div/div/div/div[2]/div[1]/fieldset/div[2]/table/tbody/tr[{item}]/td[2]/div/div[2]").text
            publication_date = driver.find_element(
                By.XPATH, f"/html/body/div/div[2]/main/div/div/div/div[2]/div[1]/fieldset/div[2]/table/tbody/tr[{item}]/td[3]/div").text
            document_id = item_link.split('/')[-1]
            links[f"{base_download_url}/{document_id}"] = {
                "name": name,
                "publication_date": publication_date
            }
            item += 1
        except:
            break
    return links

# === FILTRER PAR MOIS/ANNÉE ===
def filter_links_by_month(links, year, month):
    filtered = {}
    for url, meta in links.items():
        try:
            doc_date = datetime.strptime(meta["publication_date"], "%d/%m/%Y")
            if doc_date.year == int(year) and doc_date.month == int(month):
                filtered[url] = meta
        except:
            continue
    return filtered

# === CONVERTIR COOKIES SELENIUM EN COOKIES POUR REQUESTS ===
def selenium_cookies_to_requests(driver):
    cookies = driver.get_cookies()
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])
    return session

# === TÉLÉCHARGEMENT VIA REQUESTS + COOKIES SELENIUM ===
def download_documents_with_requests(session, filtered_links, folder):
    for url, meta in filtered_links.items():
        name = meta["name"].replace(" ", "_").replace("/", "-")
        file_path = os.path.join(folder, f"{name}.pdf")
        print(f"Téléchargement : {name}")

        for attempt in range(5):  # jusqu'à 5 essais
            try:
                response = session.get(url)
                if response.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    break  # succès, on passe au suivant
                elif response.status_code == 429:
                    wait_time = 10 * (attempt + 1) + random.randint(1, 5)
                    print(f"Erreur 429 (trop de requêtes), attente de {wait_time}s avant nouvel essai...")
                    time.sleep(wait_time)
                else:
                    print(f"Erreur HTTP pour {name} : {response.status_code}")
                    break
            except Exception as e:
                print(f"Erreur pour {name} : {e}")
                break
        else:
            print(f"Échec après plusieurs tentatives pour {name}")

        time.sleep(random.uniform(2, 4))  # pause entre les téléchargements

# === MAIN ===
def main():
    annee, mois = get_target_month_year()
    download_folder = create_download_folder("Documents", annee, mois)
    driver = create_driver()

    print("Chargement de la page...")
    driver.get(URL)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, 'table')))

    select_100 = driver.find_element(
        By.XPATH, '/html/body/div/div[2]/main/div/div/div/div[2]/div[1]/fieldset/div[3]/div/div[1]/select/option[4]')
    select_100.click()
    time.sleep(2)

    all_links = extract_links(driver, BASE_DOWNLOAD_URL)
    print(f"Total documents trouvés : {len(all_links)}")

    filtered_links = filter_links_by_month(all_links, annee, mois)
    print(f"Documents pour {mois}/{annee} : {len(filtered_links)}")

    session = selenium_cookies_to_requests(driver)
    download_documents_with_requests(session, filtered_links, download_folder)
    
    driver.quit()

if __name__ == "__main__":
    main()
