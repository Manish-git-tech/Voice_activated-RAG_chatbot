import streamlit as st
import ollama
import mysql.connector
import speech_recognition as sr
import pyttsx3
import re
import PyPDF2
import docx2txt
from io import BytesIO
from mysql.connector import Error
import chromadb

# Initialize models and session state
embeddings_model = 'mxbai-embed-large'
chat_model = 'gemma2'
client = chromadb.Client()

# A sample system prompt (you can adjust as needed)
chats = [
    {
        'role': 'system',
        'content': ('You are an AI assistant that analyzes documents. Use uploaded documents, '
                    'chat history, and stored past conversations to answer user queries concisely.')
    }
]

if 'chats' not in st.session_state:
    st.session_state.chats = [{
        'role': 'system',
        'content': ('You are an AI assistant that analyzes documents. Use uploaded documents and chat history '
                    'to answer questions.')
    }]

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'document_text' not in st.session_state:
    st.session_state.document_text = ""

if 'last_voice' not in st.session_state:
    st.session_state.last_voice = False

if 'voice_language' not in st.session_state:
    st.session_state.voice_language = None  # Tracks the language of the last voice input

# --------------------
# Helper functions
# --------------------
def crop_response(response):
    # Splits on '</think>' if present and returns the latter part.
    if '</think>' in response:
        return response.split('</think>')[-1].strip()
    return response

def clean_for_tts(text):
    return re.sub(r'\*+', '', text)

# --------------------
# Database functions
# --------------------
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Manish",
        database="AI_db3"
    )

def fetch_conversations():
    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM conversations")
        conversations = cursor.fetchall()
        return conversations
    except Error as e:
        st.error(f"Database Error: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def store_conversations(prompt, response):
    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO conversations (prompt, response) VALUES (%s, %s);", 
                       (prompt, response))
        connection.commit()
    except Error as e:
        st.error(f"Database Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# --------------------
# Document processing
# --------------------
def process_document(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.getvalue()))
            pages_text = [page.extract_text() for page in pdf_reader.pages if page.extract_text() is not None]
            return "\n".join(pages_text)
        elif uploaded_file.type == "text/plain":
            return uploaded_file.getvalue().decode("utf-8")
        elif uploaded_file.type.endswith('vnd.openxmlformats-officedocument.wordprocessingml.document'):
            text = docx2txt.process(uploaded_file)
            return text
    except Exception as e:
        st.error(f"Document processing error: {str(e)}")
        return ""

# --------------------
# Voice recognition and TTS
# --------------------
def recognize_speech(language):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            recognizer.pause_threshold = 0.8
            recognizer.non_speaking_duration = 0.3
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening...")
            audio = recognizer.listen(source)
            return recognizer.recognize_google(audio, language=language)
        except sr.WaitTimeoutError:
            st.error("No speech detected")
        except sr.UnknownValueError:
            st.error("Could not understand audio")
        except Exception as e:
            st.error(f"Recognition error: {str(e)}")
    return None

def text_to_speech(text):
    engine = pyttsx3.init()
    engine.say(clean_for_tts(text))
    engine.runAndWait()

# --------------------
# Embedding and retrieval functions
# --------------------
def create_vector_db(conversations):
    vector_db_name = 'conversations'
    # Avoid creating duplicates by deleting the collection if it exists.
    try:
        client.delete_collection(name=vector_db_name)
    except ValueError:
        pass

    vector_db = client.create_collection(name=vector_db_name)

    for c in conversations:
        # c[2]: prompt, c[3]: response from SQL row
        serialize_chats = f'prompt: {c[2]} response: {c[3]}'
        response = ollama.embeddings(model=embeddings_model, prompt=serialize_chats)
        embedding = response['embedding']
        vector_db.add(
            ids=[str(c[0])],
            embeddings=[embedding],
            documents=[serialize_chats]
        )

def retreive_embeddings(prompt):
    # First, generate a retrieval-friendly version of the prompt.
    retreive_prompt = ollama.generate(
        model=chat_model,
        prompt=(f'You are part of an information retrieval system. Convert the user query into keywords for semantic search. '
                f'For example, if the query is "name some of my friends", return "friends, colleagues, peers". '
                f'Now process this user query: "{prompt}" without any explanation.')
    )
    response = retreive_prompt['response']
    st.write("Retrieval conversion:", response)
    response = crop_response(response)
    full_prompt = response + prompt
    emb_response = ollama.embeddings(model=embeddings_model, prompt=full_prompt)
    prompt_embedding = emb_response['embedding']

    vector_db = client.get_collection(name='conversations')
    results = vector_db.query(query_embeddings=[prompt_embedding], n_results=3)
    if results['documents']:
        best_embedding = results['documents'][0]
    else:
        best_embedding = ""
    st.write("Best retrieved context:", best_embedding)
    return best_embedding

# --------------------
# Query processing function
# --------------------
def process_query(prompt):
    # Fetch stored conversations from SQL and build vector DB
    sql_conversations = fetch_conversations()
    if sql_conversations:
        create_vector_db(sql_conversations)
        old_context = retreive_embeddings(prompt=prompt)
    else:
        old_context = ""

    # Build current session context from the uploaded document and chat history
    context = f"Document context: {st.session_state.document_text[:4000]}\n"
    context += "Chat history:\n" + "\n".join(
        [f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages[-3:]]
    )
    
    # Build the full messages list with the retrieved old context
    messages = [
        {"role": "system", "content": f"Document context: {st.session_state.document_text[:4000]}\n"},
        {"role": "system", "content": f"Relevant past conversations: {old_context}"},
        {"role": "system", "content": f"{st.session_state.chats[0]['content']}\n{context}"},
        *st.session_state.chats[1:],
        {"role": "user", "content": prompt}
    ]
    
    with st.chat_message("assistant"):
        with st.spinner("Analyzing documents and past conversations..."):
            response_text = ""
            placeholder = st.empty()
            stream = ollama.chat(
                model=chat_model,
                messages=messages,
                stream=True
            )
            for chunk in stream:
                token = chunk['message']['content']
                response_text += token
                placeholder.markdown(response_text)
            
            final_response = crop_response(response_text)
            store_conversations(prompt, final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            text_to_speech(final_response)

# --------------------
# Sidebar controls and document upload
# --------------------
with st.sidebar:
    st.header("Controls & History")
    
    # Voice input buttons
    if st.button("🎤 Speak in English"):
        st.session_state.last_voice = True
        st.session_state.voice_language = "en-IN"
    if st.button("🎤 Speak in Hindi"):
        st.session_state.last_voice = True
        st.session_state.voice_language = "hi-IN"
    
    # Previous questions from session state
    st.subheader("Question History")
    if st.session_state.messages:
        user_questions = [msg["content"] for msg in st.session_state.messages if msg["role"] == "user"]
        for i, question in enumerate(user_questions[-5:], 1):
            st.markdown(f"{i}. {question}")
    else:
        st.write("No questions yet")
    
    # Document upload
    st.subheader("Document Upload")
    uploaded_file = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf", "docx", "txt"])
    if uploaded_file:
        processed_text = process_document(uploaded_file)
        if processed_text:
            st.session_state.document_text = processed_text
            st.success("Document loaded successfully!")
            st.text_area("Document Preview", processed_text[:1000] + "\n...", height=300)

# --------------------
# Main chat interface
# --------------------
st.title("📄 Smart Document Analyst")

# Display chat messages from session state
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Handle voice input if enabled
if st.session_state.last_voice and st.session_state.voice_language:
    voice_prompt = recognize_speech(st.session_state.voice_language)
    if voice_prompt:
        st.session_state.messages.append({"role": "user", "content": voice_prompt})
        process_query(voice_prompt)

# Handle text input from the user
if prompt := st.chat_input("Type your question or Speak in Hindi/English..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    process_query(prompt)

# Optionally, re-enable voice recognition after an assistant response if last query was via voice
if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant" and st.session_state.last_voice:
    voice_prompt = recognize_speech(st.session_state.voice_language)
    if voice_prompt:
        process_query(voice_prompt)

# Clear chat history button
if st.button("🧹 Clear Chat History"):
    st.session_state.messages.clear()
