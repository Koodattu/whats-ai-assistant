<div align="center">

<img src="https://raw.githubusercontent.com/Koodattu/ucs-llm-voice-image-edit/main/assets/gls.png" style="height: 200px;" />
    
</div>

## Overview

Whats-AI-Assistant is an AI-powered chatbot developed as a proof of concept demo at GPT Lab Seinäjoki AI Research Initiative. It integrates with WhatsApp using the Neonize framework, leveraging OpenAI or local language models to generate responses based on chat history and web scraping. The assistant supports multiple languages and can summarize conversations for improved interaction quality.

<div align="center">

**This demo showcases AI-driven conversational interactions and automation, leveraging WhatsApp as a primary interface.**

</div>

## Features

- **WhatsApp Integration**: Uses Neonize to interact with WhatsApp users.
- **LLM Support**: Works with OpenAI API or local Ollama models.
- **Conversation Summarization**: Generates concise summaries of previous interactions.
- **Web Scraping**: Extracts and processes text from links sent in messages.
- **Persistent Storage**: Saves conversations in an SQLite database.

## Installation

### Prerequisites

- Python 3.8+
- Virtual environment (optional but recommended)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/whats-ai-assistant.git
cd whats-ai-assistant

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Environment Variables**:
   - Create a `.env` file in the root directory and add your OpenAI API key:
     ```plaintext
     OPENAI_API_KEY=your-openai-api-key
     ```

2. **Application Settings**:
   - Modify `config.py` to configure various application settings:
     - **Model Settings**: Specify the language model to use (e.g., OpenAI's GPT-3 or a local Ollama model).
     - **Database Paths**: Set the path for the SQLite database to store conversations.
     - **Language Preferences**: Define the default language for the assistant's responses.
     - **Neonize Configuration**: Configure Neonize settings to connect to your desired WhatsApp account. For detailed instructions, refer to the [Neonize documentation](https://github.com/krypton-byte/neonize).

## Usage

Start the assistant with:

```bash
python main.py
```

## File Structure

- `.env` - Stores environment variables such as API keys.
- `config.py` - Contains configuration for database paths, model selection, and language settings.
- `database.py` - Handles message storage using SQLite.
- `llm.py` - Manages interactions with OpenAI and local LLMs.
- `scraping.py` - Extracts and processes text from web links.
- `whatsapp.py` - Listens to messages, handles events, and replies using AI.
- `main.py` - Initializes and runs the WhatsApp assistant.
- `requirements.txt` - Lists the required dependencies.
- `LICENSE` - MIT license.

## Acknowledgments

This project utilizes the [Neonize](https://github.com/krypton-byte/neonize) Python library, which acts as a wrapper for [Whatsmeow](https://github.com/tulir/whatsmeow), enabling efficient WhatsApp automation.

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m "Add feature"`
4. Push to the branch: `git push origin feature-name`
5. Open a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, reach out to [Your Name] at [your-email@example.com].

