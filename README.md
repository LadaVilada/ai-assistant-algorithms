# 🧠 WellDone AI Assistant

An AI-powered **Retrieval-Augmented Generation (RAG)** assistant that helps students interact with culinary course content — including recipes, step-by-step instructions, video transcripts, and PDFs — via a conversational **Telegram bot**.

Designed with a friendly, instructional voice inspired by a well-known chef, this assistant retrieves relevant course knowledge and enhances the learning experience through smart, contextual responses.

---

## 📌 Key Features

- ⚙️ **RAG Pipeline** — built with `LangChain`, `OpenAI`, and `Pinecone`
- 🗂 **Multi-source ingestion** — supports PDFs, transcripts, structured text
- 💬 **Conversational interface with voice input support** — Telegram bot for real-time Q&A
- 🧵 **Chat context tracking** — using `DynamoDB` + `conversation_id`
- ☁️ **S3-based image delivery** — PDF previews via hosted images
- 🪝 **Modular Dependency Injection** — testable and swappable services

## 🔊 Voice Support

The WellDone AI Assistant supports voice input via Telegram using OpenAI’s latest gpt-4o-transcribe model for high-accuracy speech-to-text conversion.

✅ What It Does:
Accepts voice messages from users
Transcribes audio using gpt-4o-transcribe
Passes clean text into the RAG pipeline for context-aware answering
Returns the response in text (and optionally TTS in future)

---

## 🏗 Architecture

```bash

Telegram User
     ↓
Telegram Handler (src/ai_assistant/bots/telegram/bot.py)
     ↓
Dependency Injection (core/utils/dependency_injector.py)
     ↓
LangChain RAG Pipeline (full control)
     ├── Document Loader
     ├── Embedding Generator (OpenAI)
     ├── Vector Store (Pinecone)
     ├── Chat Store (DynamoDB)
     └── Response Formatter
     ↓
Structured Reply
```

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
poetry run src/ai_assistant/cli/welldone_main.py --ingest knowledge/books/YOUR_DATA_FOLDER

# Run tests
poetry run pytest

```

### 5. Run the AI assistant in 'telegram mode'

```bash
python src/ai_assistant/cli/welldone_main.py telegram  --token YOUR_TELEGRAM_TOKEN
```

### 6. 🧪 Example Usage (challenging question)

```bash

/start

Response:
👋 Hi, and welcome to the new season of Gastronomy!
I’m so glad you’re here 🧡

Ask me anything about meal prep, delicious solutions, and culinary beauty. Whether it’s garlic in oil, magical marinades, or a restaurant-worthy plate — I’m happy to help.

So, shall we grab our containers and create some beauty? ✨

Query:
"How do I make a seafood?"

Response:
Hi, Vlada! I noticed that the first document mentions seafood as a potential protein base for a dish. However, there isn’t a specific seafood recipe in the provided materials. Instead, I can guide you through creating your own seafood-based dish:

1. Choose seafood as the main protein.
2. Decide on the format of the dish: it could be seafood and a side cooked separately, a stew where everything is simmered together, a seafood pie, or pasta.
3. Pick a cooking technique: baking, boiling, stewing, slow cooking, or frying.
4. Choose a side that complements the dish — vegetables (fresh or cooked), grains, or legumes.
5. Select a sauce: creamy, tomato-based, or one made with broth or herbs.
6. Add spices to bring variety to the flavor.
7. Finish with plating and garnish.

It’s important to remember that cooking is a creative process, and you can always experiment and adjust recipes to your taste. Good luck in the kitchen — you’ve got this! 😊


📎 This recipe is on page 12 of the PDF. Here's a preview:
[Image from S3]
```
 ## What else user might ask during the course?

```bash

🍳 Basics & Meal Prep
“How many grams of flour do I need for the breakfast dough batch?”
“What’s a good side dish for the basic chicken prep?”
“Can I freeze roasted pumpkin purée?”

🧂 Flavor Pairing & Combinations
“What sauce goes well with a fish steak?”
“What can I pair with lentils to make it filling and tasty?”

❄️ Freezing & Batch Cooking
“Which meal preps are best to take to work?”
“How long do blanched broccoli florets last in the freezer?”

🍲 Dish Formats
“I want to make a stew — what’s a good way to build it?”
“How can I turn my prepped vegetables into a soup?”

🥣 Recipe Interpretation
“In the module it mentions ‘childhood-style purée’. Is that mashed potatoes?”
“What can I use instead of chicken if I don’t eat meat?”

👩‍🍳 Technique & Cooking Tips
“What oven mode is best for slow-roasting vegetables?”
“How do I keep chicken from drying out while baking?”

🥗 Plating & Presentation
“How can I build a Harvard-style plate using the meal preps from the module?”
“I want to plate everything beautifully — any presentation ideas?”

```



```


