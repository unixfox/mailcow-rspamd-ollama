# Mailcow Rspamd Ollama

A proxy server that enhances spam detection by integrating web search context with Ollama's AI capabilities.

## Features

- Dual-stack IPv4/IPv6 HTTP server
- Extracts domains and names from email headers
- Fetches contextual information via web search
- Integrates with Ollama API for AI-powered spam detection
- Retry logic for robust handling of network issues

## Installation

### Using Docker (Recommended)

```bash
docker-compose up -d
```

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python server.py
```

## Configuration

Set the following environment variable:

- `OLLAMA_API`: URL of the Ollama API endpoint (default: `http://127.0.0.1:11434`)

## Development

### Running Tests

Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

Run tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov --cov-report=html
```

### Running Linters

```bash
flake8 .
```

## API

The server exposes a POST endpoint that:
1. Accepts chat completion requests
2. Extracts domains and sender names from messages
3. Fetches web context for extracted entities
4. Forwards enriched messages to Ollama API
5. Returns the AI-generated response

## License

See LICENSE file for details.
