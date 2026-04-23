# LuminaScrape 🕸️🤖

LuminaScrape is a production-grade, autonomous **"Browser-as-an-Agent"** system designed to navigate complex web structures, bypass anti-bot measures, and extract structured data using multimodal LLMs.

Powered by **LangGraph**, **Playwright**, and **LiteLLM**, it uses a multi-agent orchestration to "think" like a human user while scraping.

## 🚀 Key Features

- **Autonomous Navigation**: Uses a Pilot-Extractor-Overseer agent architecture to handle multi-page flows and complex interactions.
- **Multimodal Intelligence**: Combines visual screenshots with Accessibility Tree (AXTree) snapshots for superior structural reasoning.
- **Anti-Bot Arsenal**: 
  - `playwright-stealth` integration.
  - Automatic Cloudflare challenge resolution.
  - ReCaptcha & HCaptcha solving via CapSolver/2Captcha.
  - Proxy rotation and custom user-agent spoofing.
- **Model Agnostic**: Seamlessly switch between local models (Ollama/Llama 3.2) and remote APIs (OpenAI, Anthropic, Gemini) via a simple YAML config.
- **Crawl4AI Integration**: High-speed, clean Markdown extraction for efficient LLM processing.
- **Production Ready**: Built-in FastAPI backend for task monitoring and configuration management.

## 📁 Directory Structure

```text
LuminaScrape/
├── api/                    # FastAPI Backend & Routes
├── core/                   # Core engine (Browser, LLM, State)
├── agents/                 # Agent logic (Pilot, Extractor, Overseer)
├── tools/                  # 16+ specialized interaction & bypass tools
├── schemas/                # Pydantic models & settings logic
├── config/                 # YAML-based model & system configuration
├── tests/                  # Unit and integration tests
└── main.py                 # Application entry point
```

## 🛠️ Toolset

The system includes a suite of specialized tools, including:
- **Interaction**: `visit_url`, `click_element`, `type_text`, `scroll_page`, `accept_cookies`.
- **Observation**: `take_screenshot`, `get_accessibility_tree`, `crawl_page`, `get_robots_txt`, `parse_sitemap`.
- **Bypass**: `bypass_cloudflare`, `solve_recaptcha`, `solve_hcaptcha`.
- **Utility**: `clean_dom`, `check_platform`.

## 🚦 Getting Started

### Prerequisites
- Python 3.10+
- Playwright (`playwright install`)
- Ollama (optional, for local models)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/abrarshahh/LuminaScrape.git
   cd LuminaScrape
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Add your API keys and proxy settings
   ```

### Running the API
```bash
uvicorn api.main:app --reload
```

## ⚙️ Configuration

Manage your models in `config/models.yaml`:
```yaml
agents:
  pilot:
    model: "ollama/llama3.2-vision"
    temperature: 0.0
```

## 📜 License
MIT License. See [LICENSE](LICENSE) for details.
