import pandas as pd
import streamlit as st
import os
import warnings
from pandas.api.types import (

    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import zipfile

from getfiles import get_csv_link

# Suppress DuckDB engine warnings about index reflection
warnings.filterwarnings('ignore', category=UserWarning, module='duckdb_engine')



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
                # Filter out NaN values from unique values
                unique_values = df[column].dropna().unique().tolist()
                # Convert numeric whole numbers to integers for display
                display_values = []
                value_mapping = {}  # Map display values to original values
                for val in unique_values:
                    if isinstance(val, (int, float)):
                        # Check if it's a whole number
                        if isinstance(val, float) and val.is_integer():
                            display_val = int(val)
                        elif isinstance(val, int):
                            display_val = val
                        else:
                            display_val = val
                        display_values.append(display_val)
                        value_mapping[display_val] = val
                    else:
                        display_values.append(val)
                        value_mapping[val] = val
                
                user_cat_input = right.multiselect(
                    f"Arvo: {column}",
                    display_values,
                    default=display_values,
                )
                # Convert selected display values back to original values for filtering
                original_selected = [value_mapping[val] for val in user_cat_input]
                df = df[df[column].isin(original_selected)]
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
                    # Handle NaN values by filling them with empty string before text search
                    df = df[df[column].fillna('').str.contains(user_text_input, case=False, na=False)]

    return df




@st.cache_data(ttl=2592000)
def read_csv(link):
    return pd.read_csv(link, sep=';', encoding='ISO-8859-1', decimal=',')

@st.cache_data(ttl=3600)  # Cache for 1 hour to reduce concurrent access
def check_duckdb_data():
    """Check if data already exists in DuckDB and return it if available"""
    import duckdb
    import os
    
    # Find DuckDB file path
    db_paths = [
        os.path.join(os.path.dirname(__file__), "module_chat", "tax_data.duckdb"),
        os.path.join(os.path.dirname(__file__), "tax_data.duckdb")
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        return None
    
    try:
        # Use read-only mode to allow concurrent access
        with duckdb.connect(db_path, read_only=True) as conn:
            # Check if tables exist and have data
            tables = conn.execute("SHOW TABLES").fetchall()
            if tables:
                table_names = [table[0] for table in tables]
                
                # Try using SQL UNION first (more efficient)
                try:
                    if len(table_names) == 1:
                        # Single table - just select from it
                        query = f"SELECT * FROM {table_names[0]}"
                        df = conn.execute(query).fetchdf()
                    else:
                        # Multiple tables - use UNION to combine and remove duplicates
                        union_parts = [f"SELECT * FROM {name}" for name in table_names]
                        query = " UNION ".join(union_parts)
                        df = conn.execute(query).fetchdf()
                except Exception:
                    # Fallback: if UNION fails (e.g., schema differences), use pandas concat
                    all_data = []
                    for table_name in table_names:
                        data = conn.execute(f"SELECT * FROM {table_name}").fetchdf()
                        all_data.append(data)
                    df = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
                
                if df.empty:
                    return None
                
                # Additional deduplication using pandas (in case UNION didn't catch all duplicates)
                # Use a combination of key columns if available, otherwise use all columns
                if 'Y-tunnus | FO-nummer' in df.columns and 'Verovuosi | Skatteår' in df.columns:
                    # Deduplicate based on company ID and year
                    df = df.drop_duplicates(subset=['Y-tunnus | FO-nummer', 'Verovuosi | Skatteår'], keep='first')
                else:
                    # Fallback: deduplicate on all columns
                    df = df.drop_duplicates(keep='first')
                
                return df if not df.empty else None
    except Exception:
        return None
    
    return None




def main():
    # Check if data is already cached in session state
    if 'df' not in st.session_state or 'min_value' not in st.session_state or 'max_value' not in st.session_state:
        # Try DuckDB first
        df_from_duckdb = check_duckdb_data()
        
        if df_from_duckdb is not None:
           # st.info("Using data from DuckDB database")
            df = df_from_duckdb
            # Get year range from the data, handling NaN
            verovuosi_max = df['Verovuosi | Skatteår'].max()
            verovuosi_min = df['Verovuosi | Skatteår'].min()
            
            if pd.isna(verovuosi_max) or pd.isna(verovuosi_min):
                st.error("No valid year data found in database")
                st.stop()
                return
            
            max_value = int(verovuosi_max)
            min_value = int(verovuosi_min)

            df.drop(columns=['BUSINESSID','TOIMIALA','COMPANYNAME'], inplace=True)

            df_filttered = df

        else:
           # st.info("DuckDB data not available, downloading from CSVs")
            df_filttered = get_csv_link()
            df_filttered = df_filttered[df_filttered['Vuosi'] > '2021']
            
            # Convert Vuosi to numeric, filtering out non-numeric values
            df_filttered['Vuosi'] = pd.to_numeric(df_filttered['Vuosi'], errors='coerce')
            df_filttered = df_filttered.dropna(subset=['Vuosi'])
            
            # Check if dataframe is empty first
            if df_filttered.empty:
                st.error("No valid data found")
                st.stop()
                return
            
            # Get max/min values, handling NaN
            vuosi_max = df_filttered['Vuosi'].max()
            vuosi_min = df_filttered['Vuosi'].min()
            
            if pd.isna(vuosi_max) or pd.isna(vuosi_min):
                st.error("No valid year data found")
                st.stop()
                return
            
            max_value = int(vuosi_max)
            min_value = int(vuosi_min)
            
            dfs = []
            for link in df_filttered['Lähde']:
                dfs.append(read_csv(link))
            
            df = pd.concat(dfs)

            with st.expander("Lähteet"):
                st.dataframe(df_filttered,column_config={'Lähde': st.column_config.LinkColumn()}, hide_index=True)

            with st.expander("Esimerkki haku"):
                st.image("https://github.com/kkaarel/avoindataverohallinto/blob/main/streamlit/Screenshot.png?raw=true", caption="Esimerkki tulos")

            dfs = []
            for link in df_filttered['Lähde']:
                dfs.append(read_csv(link))
            df = pd.concat(dfs)
        
        # Cache data in session state
        st.session_state['df'] = df
        st.session_state['min_value'] = min_value
        st.session_state['max_value'] = max_value
    else:
        # Use cached data
        df = st.session_state['df']
        min_value = st.session_state['min_value']
        max_value = st.session_state['max_value']
    st.title("Apistä löytyy yritysten: verotettava tulo, maksuunpannut verot, ennakkot yhteensä, veronpalautukset ja jäännöstverot ", anchor=False)
    st.title(f"Ainesto on vuosilta: {min_value} - {max_value}", anchor=False)
    

    filtered_df = filter_dataframe(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.write(f"Rivimäärä: {filtered_df.shape[0]}")
    col2.write(f"Yritysten määrä: {filtered_df['Y-tunnus | FO-nummer'].nunique()}")
    col3.write(f"Verotettava tulo yhteensä: {filtered_df['Verotettava tulo | Beskattningsbar inkomst'].sum()}")
    col4.write(f"Verot yhteensä: {filtered_df['Maksuunpannut verot yhteensä | Debiterade skatter'].sum()}")

    with st.spinner('Ladataan dataa...',show_time=True):
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

    # Add a separator before the chat
    st.divider()
    
    # Add a title for the chat section
    st.title("💬 Keskustele verotietojen kanssa")
    st.write(f"Kysy kysymyksiä Suomen verotiedoista vuosilta {min_value}-{max_value}. Voin auttaa sinua analysoimaan tietoja, löytämään tiettyjä yrityksiä tai vastaamaan verotilastoja koskeviin kysymyksiin.")
    
    # Initialize and run the chat at the very end
    from module_chat.chat import SqlChatbot
    sql_chatbot = SqlChatbot()
    sql_chatbot.main()


if __name__ == "__main__":
    main()