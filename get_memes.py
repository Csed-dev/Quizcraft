import requests
from bs4 import BeautifulSoup

def get_memes():
    url = 'https://imgflip.com/tag/random'
    response = requests.get(url)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    memes = []

    # Finde alle img-Tags mit der Klasse 'base-img'
    meme_imgs = soup.find_all('img', class_='base-img', limit=5)

    for img in meme_imgs:
        meme_url = 'https:' + img['src']  # Füge 'https:' vor dem src-Attribut hinzu
        memes.append(meme_url)

    return memes