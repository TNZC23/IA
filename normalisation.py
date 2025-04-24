import spacy
from nltk.corpus import stopwords

# Charger le modèle de langue français de spaCy
nlp = spacy.load("fr_core_news_sm")

# Définir les stopwords en français
stop_words = set(stopwords.words('french'))

def normaliser_texte(texte):
    doc = nlp(texte.lower())  # Mise en minuscule et analyse
    mots_normaux = [token.lemma_ for token in doc if token.text not in stop_words and token.is_alpha]
    return mots_normaux

# Exemple d'utilisation
phrase = "le chat dort"
resultat = normaliser_texte(phrase)
print(resultat)  # Output : ['chat', 'dormir']