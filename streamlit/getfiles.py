import requests
import pandas as pd
from bs4 import BeautifulSoup
import streamlit as st

@st.cache_data()
def get_csv_link():
    url = "https://www.vero.fi/tietoa-verohallinnosta/tilastot/avoin_dat/"

    # Send a GET request to the URL
    response = requests.get(url)

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")

    # Find all the h3 elements
    h3_elements = soup.find_all('h3')

    # Extract the year and the href for each h3 element
    csv_links = []
    for h3 in h3_elements:
        year = h3.text
        csv_link = h3.find_next('a', href=True)
        if csv_link:
            href = csv_link['href']
            csv_links.append({'Vuosi': year, 'Lähde': 'https://www.vero.fi' + href})

    return pd.DataFrame(csv_links)




