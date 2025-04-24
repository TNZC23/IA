import os
import pytesseract
import fitz  # PyMuPDF
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import glob
import io


app = Flask(__name__)

# Dossier contenant les documents scannés
DOCUMENTS_FOLDER = 'documents'

# Fonction pour extraire du texte via OCR d'un fichier PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ''
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        
        # Convertir le Pixmap en image PIL
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes("png")))  # Convertir Pixmap en image PNG via bytes
        
        # Utiliser pytesseract pour extraire du texte à partir de l'image PIL
        text += pytesseract.image_to_string(img)
    return text

# Fonction pour rechercher un mot-clé dans tous les PDF d'un sous-dossier
def search_documents(directory, search_term):
    results = []
    # Recherche dans tous les fichiers PDF du dossier
    pdf_files = glob.glob(os.path.join(directory, '**', '*.pdf'), recursive=True)
    
    for pdf_file in pdf_files:
        text = extract_text_from_pdf(pdf_file)
        if search_term.lower() in text.lower():
            results.append({
                'title': os.path.basename(pdf_file),
                'link': pdf_file,
                'download_link': f'/download/{os.path.basename(pdf_file)}'
            })
    return results

# Route pour afficher la page d'accueil
@app.route('/')
def index():
    # Récupérer les sous-dossiers de l'année et mois dans le dossier de documents
    months_folders = sorted(os.listdir(DOCUMENTS_FOLDER))
    return render_template('index.html', months=months_folders)

# Route pour traiter la recherche
@app.route('/search', methods=['POST'])
def search():
    selected_site = request.form.get('selected_site')
    search_term = request.form.get('search_term')
    
    # Recherche dans le dossier sélectionné
    search_results = search_documents(os.path.join(DOCUMENTS_FOLDER, selected_site), search_term)
    return jsonify(search_results)

# Route pour télécharger un fichier
@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(DOCUMENTS_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
