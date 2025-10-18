import os
import openai
import streamlit as st
from streamlit.logger import get_logger
from langchain_openai import AzureChatOpenAI
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

logger = get_logger('Langchain-Chatbot')

#decorator
def enable_chat_history(func):
    # Always initialize messages, regardless of API key
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
    
    # Show chat history on UI
    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    def execute(*args, **kwargs):
        func(*args, **kwargs)
    return execute

def display_msg(msg, author):
    """Method to display message on the UI

    Args:
        msg (str): message to display
        author (str): author of the message -user/assistant
    """
    st.session_state.messages.append({"role": author, "content": msg})
    st.chat_message(author).write(msg)

def choose_custom_azure_openai_key():
    azure_openai_api_key = st.secrets.get("AZURE_OPENAI_API_KEY")
    azure_openai_endpoint = st.secrets.get("AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version = st.secrets.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    azure_openai_deployment_name = st.secrets.get("AZURE_OPENAI_DEPLOYMENT_NAME")

    if not azure_openai_api_key:
        st.error("Please add your Azure OpenAI API key to continue.")
        st.info("Obtain your key from Azure OpenAI Studio")
        st.stop()
    
    if not azure_openai_endpoint:
        st.error("Please add your Azure OpenAI endpoint to continue.")
        st.info("Find your endpoint in Azure OpenAI Studio")
        st.stop()
    
    if not azure_openai_deployment_name:
        st.error("Please add your Azure OpenAI deployment name to continue.")
        st.info("Find your deployment name in Azure OpenAI Studio")
        st.stop()

    model = azure_openai_deployment_name
    try:
        client = openai.AzureOpenAI(
            api_key=azure_openai_api_key,
            api_version=azure_openai_api_version,
            azure_endpoint=azure_openai_endpoint
        )
        
        # For Azure OpenAI, we typically use the deployment name as the model
        model = st.sidebar.selectbox(
            label="Model Deployment",
            options=[azure_openai_deployment_name],
            key="SELECTED_AZURE_OPENAI_MODEL"
        )
    except openai.AuthenticationError as e:
        st.error(f"Authentication error: {e}")
        st.stop()
    except Exception as e:
        print(e)
        st.error("Something went wrong. Please try again later.")
        st.stop()
    return model, azure_openai_api_key, azure_openai_endpoint, azure_openai_api_version

def configure_llm():
    # Remove the radio button selection - just use Azure OpenAI directly
    llm = AzureChatOpenAI(
        azure_deployment=st.secrets["AZURE_OPENAI_DEPLOYMENT_NAME"],
        azure_endpoint=st.secrets["AZURE_OPENAI_ENDPOINT"],
        api_key=st.secrets["AZURE_OPENAI_API_KEY"],
        api_version=st.secrets.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        temperature=0,
        streaming=True
    )
    return llm

def print_qa(cls, question, answer):
    log_str = "\nUsecase: {}\nQuestion: {}\nAnswer: {}\n" + "------"*10
    logger.info(log_str.format(cls.__name__, question, answer))

@st.cache_resource
def configure_embedding_model():
    embedding_model = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return embedding_model

def sync_st_session():
    for k, v in st.session_state.items():
        st.session_state[k] = v