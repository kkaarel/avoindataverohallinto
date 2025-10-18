import os
import openai
import streamlit as st
from streamlit.logger import get_logger
from langchain_openai import AzureChatOpenAI
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

logger = get_logger('Langchain-Chatbot')

#decorator
def enable_chat_history(func):
    if st.secrets["AZURE_OPENAI_API_KEY"]:

        # to clear chat history after swtching chatbot
        current_page = func.__qualname__
        if "current_page" not in st.session_state:
            st.session_state["current_page"] = current_page
        if st.session_state["current_page"] != current_page:
            try:
                st.cache_resource.clear()
                del st.session_state["current_page"]
                del st.session_state["messages"]
            except:
                pass

        # to show chat history on ui
        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
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
    azure_openai_api_key = st.secrets["AZURE_OPENAI_API_KEY"]
    azure_openai_endpoint = st.secrets["AZURE_OPENAI_ENDPOINT"]
    azure_openai_api_version = st.secrets["AZURE_OPENAI_API_VERSION"]
    azure_openai_deployment_name = st.secrets["AZURE_OPENAI_DEPLOYMENT_NAME"]

    model = azure_openai_deployment_name
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