# Architecture and Workflow of the Project - AI Weather Chatbot with realtime data
# Chat Bot Webpage
<img width="1919" height="1027" alt="image" src="https://github.com/user-attachments/assets/65559f17-e766-4195-abc1-ae90ade12c01" />

# N8N workflow 
<img width="1919" height="1030" alt="Screenshot 2025-08-21 171131" src="https://github.com/user-attachments/assets/8d676d60-c705-4a68-967f-dc3950fd14cb" />

**Purpose:**
An interactive chatbot that answers real-time weather queries for any city in natural language.

**Tech Stack:**
- **Frontend:** Responsive HTML/CSS/JS chatbot UI (local or web)
- **Backend Integration:** n8n workflow automation platform (Dockerized)
- **LLM Parsing:** Google Gemini (Gemini 2.5) for extracting city, time, and intent from user queries
- **Weather Data:** Python MCP (Multi-Modal Command Protocol) server, fetching real data from OpenWeatherMap API
- **Orchestration:** n8n handles message parsing, API calls, and response formatting

**Workflow:**
- User types a question (e.g., “What’s the weather in Mumbai tomorrow?”) in the chat UI.
- Frontend sends the message to n8n via webhook.
- n8n uses Gemini LLM to extract structured info (city, time, request type) from the message.
- n8n calls the MCP Python server, which queries OpenWeatherMap for real-time weather.
- Weather details are formatted and returned back through n8n to the frontend for user display.

**Features:**
- Natural language understanding (thanks to LLM extraction)
- Real-time and forecast weather (OpenWeatherMap API)
- Easily extendable: add new cities, upgrade LLMs, or integrate more APIs
- Fully containerized for local development and testing

**Why this architecture?**
- Reliability: Each service is modular; problems in one do not halt the others.
- Scalability: You can host parts (n8n, MCP, UI) anywhere or together.
- Maintainability: Visual automation (n8n) and clear separation of logic.
