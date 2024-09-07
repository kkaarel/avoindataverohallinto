import pandas as pd
import streamlit as st
import os
from pandas.api.types import (

    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import zipfile

from getfiles import get_csv_link



st.set_page_config(page_title="Verohallinnon avoin data", layout="wide")




def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Aineistojen suodatus")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col], format='%Y-%m-%d')
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Suodata", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            left.write("↳")
            # Treat columns with < 10 unique values as categorical
            if isinstance(df[column].dtype, pd.CategoricalDtype) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Arvo: {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Arvo: {column}",
                    _min,
                    _max,
                    (_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Arvo: {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]


            else:
                user_text_input = right.text_input(
                    f"Teksti haku {column}",
                )
                if user_text_input:
                    df = df[df[column].str.contains(user_text_input)]

    return df






@st.cache_data(ttl=2592000)
def read_csv(link):
    return pd.read_csv(link, sep=';', encoding='ISO-8859-1', decimal=',')




def main():

    df_filttered = get_csv_link()
    df_filttered = df_filttered[df_filttered['Vuosi'] > '2021']
    max_value = df_filttered['Vuosi'].max()
    min_value = df_filttered['Vuosi'].min()



    st.title("Apistä löytyy yritysten: verotettava tulo, maksuunpannut verot, ennakkot yhteensä, veronpalautukset ja jäännöstverot ", anchor=False)
    st.title(f"Ainesto on vuosilta: {min_value} - {max_value}", anchor=False)


    with st.expander("Lähteet"):
        st.dataframe(df_filttered,column_config={'Lähde': st.column_config.LinkColumn()}, hide_index=True)


    with st.expander("Esimerkki haku"):
        st.image("Screenshot.png", caption="Esimerkki tulos")



    dfs = []
    for link in df_filttered['Lähde']:
        dfs.append(read_csv(link))

    df = pd.concat(dfs)


    filtered_df = filter_dataframe(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.write(f"Rivimäärä: {filtered_df.shape[0]}")
    col2.write(f"Yritysten määrä: {filtered_df['Y-tunnus | FO-nummer'].nunique()}")
    col3.write(f"Verotettava tulo yhteensä: {filtered_df['Verotettava tulo | Beskattningsbar inkomst'].sum()}")
    col4.write(f"Verot yhteensä: {filtered_df['Maksuunpannut verot yhteensä | Debiterade skatter '].sum()}")


    with st.spinner('Ladataan dataa...'):
        st.dataframe(filtered_df)






    st.write(
        """Avoin data: [here](https://www.vero.fi/tietoa-verohallinnosta/tilastot/avoin_dat/)

        """
    )

    st.write(
        """Kehittäjä Kaarel Kõrvemaa: [here](https://www.linkedin.com/in/korvemaa/)

        """
    )

    st.write(
        """Github: [here](https://github.com/kkaarel/avoindataverohallinto)

        """
    )



    st.caption(
        """This app is a reference of a blog [here](https://blog.streamlit.io/auto-generate-a-dataframe-filtering-ui-in-streamlit-with-filter_dataframe/)
        and walks you through one example of how the Streamlit
        Data Science Team builds add-on functions to Streamlit.
        """
    )

if __name__ == "__main__":
    main()