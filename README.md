# Conversational AI Bot for Credit Card Distribution

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-2.0%2B-green)](https://flask.palletsprojects.com/)
[![GitHub repo size](https://img.shields.io/github/repo-size/<your-username>/credit_card_chatbot)](https://github.com/<your-username>/credit_card_chatbot)

## Project Overview

This project implements a conversational AI chatbot to automate credit card distribution for Bank of Baroda. The chatbot handles customer queries, upselling, and data collection by integrating with external systems like Google Sheets and CRM tools, powered by advanced large language models.

The bot uses a combination of open-source and commercial LLMs to provide context-aware and personalized conversations, improving user engagement and sales effectiveness.

## Key Features

- Maintains contextual conversations and handles ambiguous queries.
- Answers FAQs and SOP-based queries using Google FLAN-T5.
- Integrates with Google Sheets API to pull user history and update customer data.
- Provides conversation summaries automatically emailed to the sales team.

## Technologies Used

- **Python** — backend development and scripting.
- **Flask** — lightweight web framework hosting the chatbot UI.
- **LangChain** — chaining LLM prompts and managing conversational flows.
- **Google FLAN-T5** — fine-tuned LLM used to answer FAQs and knowledge base queries.
- **Google Sheets API** — read/write customer data in sheets.
- **dotenv (.env)** — environment variable management for API keys and secrets.
- **Git & GitHub** — version control and remote repository hosting.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/credit_card_chatbot.git
   cd credit_card_chatbot
2. **Create and activate a virtual environment:**

  ```bash
  Copy
  Edit
  python3 -m venv venv
  source venv/bin/activate   # Mac/Linux
  venv\Scripts\activate      # Windows
  ```
3. **Install dependencies:**

  ```bash
  Copy
  Edit
  pip install -r requirements.txt
  ```

4. **Set up environment variables:**

Create a .env file in the project root and add your API keys and credentials:

  ```ini
  Copy
  Edit
  GOOGLE_SHEETS_CREDENTIALS=path/to/your/credentials.json
  FLAN_T5_API_KEY=your_flan_t5_api_key_here
```
5. **Run the Flask app:**

  ```bash
  Copy
  Edit
  python app.py
  ```
6. **Open your browser and go to:**
  http://192.168.1.3:8000

**Usage**

  1.Interact with the chatbot UI served at the above address.

  2.Ask FAQs or credit card-related queries.

  3.The bot maintains context and personalizes responses based on integrated data.

  4.After conversation, summaries are generated and emailed automatically.

7. **Folder Structure**
  ```pgsql
  Copy
  Edit
  credit_card_chatbot/
  ├── app.py
  ├── requirements.txt
  ├── .gitignore
  ├── templates/
  │   └── index.html
  ├── .env.example          # template for env variables (add this file)
  └── README.md
  ```
8. **Contributing**
Contributions are welcome! Feel free to open issues or submit pull requests for improvements.


1.Initial chatbot UI after user login, ready to accept queries.
<img width="1404" alt="image" src="https://github.com/user-attachments/assets/c09ad3ca-7368-4aaa-8c95-6f18dcb6c5ff" />

2.Chatbot responding to a user query with contextual and personalized answers
<img width="1155" alt="image" src="https://github.com/user-attachments/assets/ad37aea2-2807-4a5f-a915-42de698765ea" />

3.Updated Google Sheets showing user data captured and stored automatically by the chatbot.
<img width="1588" alt="image" src="https://github.com/user-attachments/assets/b0a27e07-97ea-49d8-9b62-3710cb17105c" />
