import streamlit as st
import requests
import os
from bs4 import BeautifulSoup
from google import genai
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- 1. SECURE CONFIGURATION ---
# This loads your local .env file. If on Streamlit Cloud, it safely ignores it.
load_dotenv()

st.set_page_config(page_title="SecOps Architect 2026", layout="wide")

# This checks your local .env OR your Streamlit Cloud Secrets box
API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if not API_KEY:
    st.error("No API Key found. Please check your .env file or Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)

# Initialize Digital Library (Vector Store) in Session State
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

# --- 2. CORE FUNCTIONS ---
def scrape_url(url):
    """Fetches text from Google Docs or GitHub Raw files."""
    try:
        if "github.com" in url and "/blob/" in url:
            url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        
        if "raw.githubusercontent" in url or url.endswith(('.txt', '.yaral', '.yaml')):
            return res.text
            
        soup = BeautifulSoup(res.text, 'html.parser')
        for tag in soup(['nav', 'footer', 'script', 'style']):
            tag.decompose()
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        return f"Error reading {url}: {e}"

def ingest_knowledge(urls):
    """Chunks text and stores it in the FAISS library."""
    all_text = ""
    url_list = [u.strip() for u in urls.split('\n') if u.strip()]
    
    if not url_list:
        st.warning("Please enter at least one URL.")
        return

    for url in url_list:
        with st.spinner(f"Reading: {url}..."):
            content = scrape_url(url)
            all_text += f"\n--- Source: {url} ---\n{content}\n"
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = text_splitter.split_text(all_text)
    
    with st.spinner("Indexing knowledge... (This may take a minute)"):
        # This handles the text-to-math conversion (Embeddings)
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        st.session_state.vector_store = FAISS.from_texts(chunks, embeddings)
    st.success(f"Successfully 'trained' on {len(url_list)} sources!")

# --- 3. UI LAYOUT ---
st.title("🛡️ Google SecOps Rule Architect")
st.subheader("Train & Validate with Live Documentation")

# Sidebar for Knowledge Ingestion
with st.sidebar:
    st.header("📚 Knowledge Hub")
    st.markdown("Paste URLs for the agent to use as a **Source of Truth**.")
    url_input = st.text_area("URLs (one per line)", 
                            placeholder="Example:\nhttps://cloud.google.com/chronicle/docs/detection/yara-l-2-0-syntax",
                            height=200)
    
    if st.button("Update Agent Brain"):
        ingest_knowledge(url_input)
    
    st.divider()
    if st.session_state.vector_store:
        st.write("✅ Agent is Grounded in your URLs.")
    else:
        st.write("❌ Agent is using general knowledge only.")

# Main Workspace
col1, col2 = st.columns([1, 1])
with col1:
    st.markdown("### ✍️ Request")
    task = st.selectbox("What is the goal?", ["Create New Rule", "Validate/Fix Existing Rule", "Optimize Thresholds"])
    user_input = st.text_area("Describe the logic or paste existing code:", height=300)
    
    generate_btn = st.button("Run Analysis")

with col2:
    st.markdown("### 🤖 Agent Output")
    if generate_btn:
        context = ""
        if st.session_state.vector_store:
            search_results = st.session_state.vector_store.similarity_search(user_input, k=5)
            context = "\n\n".join([doc.page_content for doc in search_results])
        
        system_instruction = f"""
        You are an expert Google SecOps Engineer. 
        Your task: {task}
        
        DOCUMENTATION CONTEXT:
        {context if context else "No specific URLs provided. Use standard YARA-L 2.0 knowledge."}
        
        USER REQUEST:
        {user_input}
        
        REQUIRED ACTIONS:
        1. Ensure strict YARA-L 2.0 syntax.
        2. Cross-reference the provided context. Documentation is the Law.
        3. Provide the final YARA-L code block.
        """
        
        with st.spinner("Consulting library..."):
            # Updated to stable 2026 model string
            response = client.models.generate_content(model="gemini-2.0-flash", contents=system_instruction)
            st.markdown(response.text)