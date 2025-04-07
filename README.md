# 🧠 WellDone AI Assistant

An AI-powered **Retrieval-Augmented Generation (RAG)** assistant that helps students interact with culinary course content — including recipes, step-by-step instructions, video transcripts, and PDFs — via a conversational **Telegram bot**.

Designed with a friendly, instructional voice inspired by a well-known chef, this assistant retrieves relevant course knowledge and enhances the learning experience through smart, contextual responses.

---

## 📌 Key Features

- ⚙️ **RAG Pipeline** — built with `LangChain`, `OpenAI`, and `Pinecone`
- 🗂 **Multi-source ingestion** — supports PDFs, transcripts, structured text
- 💬 **Conversational interface** — Telegram bot for real-time Q&A
- 🧵 **Chat context tracking** — using `DynamoDB` + `conversation_id`
- ☁️ **S3-based image delivery** — PDF previews via hosted images
- 🪝 **Modular Dependency Injection** — testable and swappable services
- 🔐 **Pluggable access control (Planned)** — for multi-tier content delivery

---

## 🚀 Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/welldone-ai-assistant.git
cd welldone-ai-assistant
```

### 2. Create a .env file 

```bash 
 With the following values:

OPENAI_API_KEY=your-openai-key
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENV=your-pinecone-environment
PINECONE_INDEX=welldone-index
S3_BUCKET=welldone-pdf-assets
DYNAMODB_TABLE=welldone-chat-history
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```


### 3. Install python virtual environment

```bash
cd path_to_your_project    # Change to your project directory
source venv/bin/activate   # Activate the virtual environment
poetry --version           # Now Poetry should work
poetry install --no-root

OR

pip install -r requirements.txt

```

### 🧩 4. Ingest Content

``` bash 

This one-time setup indexes all source materials for RAG retrieval.
# Ingest your documents from knowledge/books
poetry run python main.py --ingest knowledge/books/YOUR_DATA_FOLDER

# Run tests
poetry run pytest

```

### 5. Run the Telegram assistant

```bash
python src/ai_assistant/cli/welldone_main.py telegram  --token YOUR_TELEGRAM_TOKEN

```


