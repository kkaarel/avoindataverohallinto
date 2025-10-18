import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import utils
import streamlit as st
from pathlib import Path
from sqlalchemy import create_engine

from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.callbacks import StreamlitCallbackHandler
from langchain_community.utilities.sql_database import SQLDatabase

# Tracking elements moved to class methods to avoid module-level execution


class SqlChatbot:

    def __init__(self):
        utils.sync_st_session()
        self.llm = utils.configure_llm()
    
    def setup_db(_self, db_uri):
        if db_uri == 'USE_TAX_DB':
            # Use the official DuckDB connection method
            from sqlalchemy import create_engine, text
            import os
            
            # Get the absolute path to the DuckDB file
            # Try both possible locations
            db_paths = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "tax_data.duckdb"),  # streamlit/tax_data.duckdb
                os.path.join(os.path.dirname(__file__), "tax_data.duckdb")  # streamlit/module_chat/tax_data.duckdb
            ]
            
            db_path = None
            for path in db_paths:
                if os.path.exists(path):
                    db_path = path
                    break
            
            if not db_path:
                raise FileNotFoundError("Could not find tax_data.duckdb file")
            
            # Simple connection string with absolute path
            engine = create_engine(f"duckdb:///{db_path}")
            
            # Test the connection and get tables
            with engine.connect() as conn:
                # Get table names
                result = conn.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result.fetchall()]
                #st.write(f"Tables found: {tables}")
            
            db = SQLDatabase(engine)
        else:
            db = SQLDatabase.from_uri(database_uri=db_uri)
        

        return db

    def setup_sql_agent(_self, db):
        agent = create_sql_agent(
            llm=_self.llm,
            db=db,
            top_k=10,
            verbose=False,
            agent_type="openai-tools",
            handle_parsing_errors=True,
            handle_sql_errors=True
        )
        return agent
        
    def setup_duckdb_chat(_self):
        """Create a custom DuckDB chat interface"""
        import duckdb
        import os
        
        def query_duckdb(question):
            # Get the absolute path to the DuckDB file
            db_paths = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "tax_data.duckdb"),  # streamlit/tax_data.duckdb
                os.path.join(os.path.dirname(__file__), "tax_data.duckdb")  # streamlit/module_chat/tax_data.duckdb
            ]
            
            db_path = None
            for path in db_paths:
                if os.path.exists(path):
                    db_path = path
                    break
            
            if not db_path:
                return "Error: Could not find tax_data.duckdb file"
            
            # Connect to DuckDB with absolute path
            conn = duckdb.connect(db_path)
            
            # Get table schemas for context
            schema_2022 = conn.execute("DESCRIBE tax_data_2022").fetchall()
            schema_2023 = conn.execute("DESCRIBE tax_data_2023").fetchall()
            
            # Create a prompt for the LLM
            prompt = f"""
            You are a SQL expert. Based on this question: "{question}"
            
            Database schema:
            tax_data_2022: {schema_2022}
            tax_data_2023: {schema_2023}
            
            Generate a SQL query to answer the question. Only return the SQL query, nothing else.
            """
            
            # Get SQL query from LLM
            response = _self.llm.invoke(prompt)
            sql_query = response.content.strip()
            
            # Execute query
            try:
                result = conn.execute(sql_query).fetchall()
                conn.close()
                return result
            except Exception as e:
                conn.close()
                return f"Error executing query: {e}"
        
        return query_duckdb

    def enhance_response_with_context(self, user_query, db_response):
        """Return the database response without web search enhancement"""
        return f"""
**Analyysitulokset:**
{db_response}

*Huomio! Tämä analyysi perustuu Suomen verotietoihin vuosilta 2022–2023.*
"""


    @utils.enable_chat_history
    def main(self):

        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]


        st.divider()
        
        db_uri = 'USE_TAX_DB'
        db = self.setup_db(db_uri)
        agent = self.setup_sql_agent(db)

        user_query = st.chat_input(placeholder="Ask me anything!")

        if user_query:
            st.session_state.messages.append({"role": "user", "content": user_query})
            st.chat_message("user").write(user_query)

            with st.chat_message("assistant"):
                # First get the database response
                #st_cb = StreamlitCallbackHandler(st.container())
                #result = agent.invoke(
                #    {"input": user_query},
                #    {"callbacks": [st_cb]}
               # )
                result = agent.invoke({"input": user_query})
                db_response = result["output"]
                
                
                # Format the response
                enhanced_response = self.enhance_response_with_context(user_query, db_response)
                
                st.session_state.messages.append({"role": "assistant", "content": enhanced_response})
                st.write(enhanced_response)
                utils.print_qa(SqlChatbot, user_query, enhanced_response)


if __name__ == "__main__":
    obj = SqlChatbot()
    obj.main()
