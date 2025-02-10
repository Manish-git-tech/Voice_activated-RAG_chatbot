# Voice_activated-RAG_chatbot

Voice_activated-RAG_chatbot is a long-term communication chatbot with persistent memory and document question-answering capabilities. Users can interact with the chatbot using either voice or text, and the system is bilingual—it understands both Hindi and English. The chatbot leverages Retrieval-Augmented Generation (RAG) to analyze user-uploaded documents along with past conversations, providing contextually relevant and coherent responses.

## Features

- **Bilingual Communication:**  
  Understands both Hindi and English spoken or typed input.
  
- **Voice Activation:**  
  Users can interact via voice commands using built-in speech recognition and text-to-speech.
  
- **Document Analysis:**  
  Upload documents (PDF, DOCX, or TXT) to have the chatbot extract and analyze their content.
  
- **Persistent Memory:**  
  Past conversations are stored in a MySQL database. A vector database (Chromadb) is used for semantic search across stored conversations to provide relevant context.
  
- **Retrieval-Augmented Generation (RAG):**  
  Uses an embedding model (e.g. `mxbai-embed-large`) and a local chat model (e.g. `gemma2` via Ollama) to semantically search through and incorporate historical conversation data.
  
- **Long-Term Communication:**  
  Maintains context over extended interactions for a natural, coherent dialogue experience.

## Architecture & Technologies

- **Streamlit:**  
  Provides the web-based user interface for chat, document upload, and controls.

- **Ollama:**  
  Runs local AI models for both chat generation and embedding creation.

- **MySQL:**  
  Stores conversation history persistently.

- **Chromadb:**  
  An in-memory vector database used to build and query embeddings for past conversations.

- **SpeechRecognition & Pyttsx3:**  
  Enable voice input and text-to-speech functionalities.

- **Document Processing:**  
  Utilizes PyPDF2 for PDFs, docx2txt for DOCX files, and standard decoding for TXT files.

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/Manish-git-tech/Voice_activated-RAG_chatbot.git
    cd Voice_activated-RAG_chatbot
    ```

2. **Set up a virtual environment (optional but recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate      # For Linux/MacOS
    .\venv\Scripts\activate       # For Windows
    ```

3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up MySQL:**

    - Ensure you have a MySQL server running.
    - Create a database named `AI_db3`.
    - Create a table called `conversations` with at least the following columns:  
      `id` (INT, primary key, auto-increment), `prompt` (TEXT), `response` (TEXT).

5. **Configure Ollama:**

    - Install and run [Ollama](https://ollama.com) locally.
    - Pull the required models:  
      - For embeddings: `ollama pull mxbai-embed-large`
      - For chat: `ollama pull gemma2`
    - Verify that Ollama is running (typically on port 11434).

## Usage

1. **Run the Streamlit App:**

    ```bash
    streamlit run GUI_chatBOT.py
    ```

2. **Using the Chatbot:**

    - **Document Upload:**  
      Use the sidebar to upload a PDF, DOCX, or TXT file. The document’s text will be extracted and used as context for answering questions.
    
    - **Voice or Text Input:**  
      Ask your question by typing it in the chat input or by using the voice buttons (for English or Hindi).
    
    - **Persistent Memory:**  
      Past conversations are stored in the MySQL database and incorporated via Chromadb’s semantic search, so the chatbot can recall and use previous interactions to provide better answers.

## Contributing

Contributions are welcome! If you have suggestions, bug fixes, or enhancements, please open an issue or submit a pull request.


## Acknowledgements

- Thanks to the developers of Streamlit, Ollama, Chromadb, MySQL Connector, and other libraries used in this project.
- Credits to the GDSC club of IIT Indore for giving such a good project.
