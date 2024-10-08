from typing import Any, Dict, List
from uuid import UUID
import streamlit as st
from langchain.storage import LocalFileStore
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_openai import OpenAIEmbeddings
from langchain.embeddings import CacheBackedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda,RunnablePassthrough
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.base import BaseCallbackHandler
import os



st.set_page_config(
    page_title="DocumentGPT",
    page_icon="📃",
)



with st.sidebar:
    api_key = st.text_input("Enter your Open API Key")
    file = ""
    if api_key:
        st.write(f"API Key : {api_key}")
        file = st.file_uploader(":red[**Upload a .txt .pdf or .docx file.**]",type=["pdf","txt","docx"])


class ChatCallbackHandler(BaseCallbackHandler):
    message = ""

    def on_llm_start(self, *args, **kwargs):
        self.message_box=st.empty()

    def on_llm_end(self, *args, **kwargs):
        save_message(self.message,"ai")

    def on_llm_new_token(self,token:str, *args, **kwargs):
        self.message += token
        self.message_box.markdown(self.message)

llm = ChatOpenAI(openai_api_key=api_key,
                 temperature = 0.1,
                 streaming=True,
                 callbacks=[ChatCallbackHandler()])

@st.cache_resource(show_spinner="Embedding file...") #동일한 file 일 경우, 중복동작하지 않고 이전 값을 return함
def embed_file(file,api_key):
    file_content = file.read()
    file_path = f"./.cache/files/{file.name}"
    folder_path = os.path.dirname(file_path)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    with open(file_path,"wb") as f:
        f.write(file_content)
    cache_dir = LocalFileStore(f"./.cache/embeddings/{file.name}")
    splitter = CharacterTextSplitter.from_tiktoken_encoder(
        separator="\n",
        chunk_size=600,
        chunk_overlap=100,
    )
    loader = UnstructuredFileLoader(file_path)
    docs = loader.load_and_split(text_splitter=splitter)
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    cached_embeddings = CacheBackedEmbeddings.from_bytes_store(embeddings,cache_dir)
    vectorstore = FAISS.from_documents(docs,cached_embeddings)
    retriever = vectorstore.as_retriever()
    return retriever

def save_message(message,role):
    st.session_state["messages"].append({"message":message,"role":role})


def send_message(message,role,save=True):
    with st.chat_message(role):
        st.markdown(message)
    if save:
        save_message(message,role)

def paint_history():
    for message in st.session_state["messages"]:
        send_message(message["message"],message["role"],save=False)

def format_docs(docs):
    return "\n\n".join(document.page_content for document in docs)


prompt = ChatPromptTemplate.from_messages([
    ("system","""
All answer in Korean.
Answer the question using ONLY the following context.
If you don't know the answer just say you dont't know.
Don't make anything up.
     
     Context: {context}
"""),
    ("human","{question}")
])

st.title("Document GPT")




if file:
    retriever = embed_file(file,api_key)

    send_message("I'm ready! Ask away!","ai",save=False)
    paint_history()

    message = st.chat_input("Ask anything about your file...")

    if message:
        send_message(message,"human")
        chain={
            "context" : retriever | RunnableLambda(format_docs),
            "question":RunnablePassthrough()
        } |prompt|llm
        with st.chat_message("ai"):
            chain.invoke(message)
else:
    st.session_state["messages"] = []
    st.markdown("""
Welcome!

Use this chatbot to ask questions to an AI about your files!
            
First, :red[Enter your OpenAI API Key]
and :red[Upload your files on the sidebar].
"""
)
   

