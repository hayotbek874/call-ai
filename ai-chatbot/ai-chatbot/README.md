# STRATIX AI CHAT BOT

Multi-channel AI-powered chatbot system for Uzbekistan market, supporting phone calls, Telegram, Instagram DM, and web widget.

## Features

- **Multi-Channel Support**
  - Telegram Bot integration
  - Instagram DM via Graph API
  - Web Widget (REST API)
  - Voice calls via Asterisk (ARI)

- **AI-Powered Conversations**
  - Intent detection using OpenAI GPT
  - Context-aware response generation
  - Multilingual support (Uzbek, Russian, English)
  - Automatic language detection

- **Voice Capabilities**
  - Speech-to-Text (Whisper API)
  - Text-to-Speech (ElevenLabs)
  - Call recording and transcription

- **Order Management**
  - Order creation and tracking
  - Status updates with notifications
  - Payment integration (Click, Payme)

- **CRM Integration**
  - Contact synchronization
  - Deal/opportunity tracking
  - Activity logging

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async)
- **Cache**: Redis
- **Task Queue**: Celery
- **AI**: OpenAI GPT, ElevenLabs, Whisper
- **Voice**: Asterisk ARI
- **Container**: Docker, Docker Compose

## Project Structure

```
STRATIX_AI_CHAT_BOT/
├── src/
│   ├── api/                    # API layer
│   │   ├── deps.py             # Dependencies & auth
│   │   ├── router.py           # Main router
│   │   └── routes/             # Route handlers
│   │       ├── chat.py         # Chat endpoints
│   │       ├── orders.py       # Order endpoints
│   │       ├── products.py     # Product endpoints
│   │       ├── voice.py        # Voice endpoints
│   │       ├── webhooks.py     # Webhook handlers
│   │       ├── payments.py     # Payment callbacks
│   │       └── admin.py        # Admin endpoints
│   ├── core/                   # Core configuration
│   │   ├── config.py           # Settings
│   │   ├── security.py         # JWT & auth
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── logging.py          # Logging config
│   ├── db/                     # Database layer
│   │   ├── base.py             # Base model
│   │   ├── session.py          # DB session
│   │   └── redis.py            # Redis client
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── repositories/           # Data access layer
│   ├── services/               # Business logic
│   │   ├── ai/                 # AI services
│   │   └── voice/              # Voice services
│   ├── clients/                # External API clients
│   ├── workers/                # Celery tasks
│   ├── middleware/             # FastAPI middleware
│   ├── utils/                  # Utilities
│   └── main.py                 # Application entry
├── tests/                      # Test suite
├── alembic/                    # Database migrations
├── scripts/                    # Utility scripts
├── docker/                     # Docker configs
├── .env.example                # Environment template
├── pyproject.toml              # Project config
├── Dockerfile                  # Container build
└── docker-compose.yml          # Local development
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/stratix-ai-chat-bot.git
   cd stratix-ai-chat-bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   .\venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Seed initial data**
   ```bash
   python scripts/seed_db.py
   ```

7. **Start the application**
   ```bash
   uvicorn src.main:app --reload
   ```

### Docker Setup

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection URL | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `SECRET_KEY` | JWT secret key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | For voice |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | For Telegram |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram Graph API token | For Instagram |
| `CLICK_MERCHANT_ID` | Click payment merchant ID | For payments |
| `PAYME_MERCHANT_ID` | Payme merchant ID | For payments |

See `.env.example` for full list.

## API Documentation

Once running, access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI spec: `http://localhost:8000/openapi.json`

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/
```

### Code Quality

```bash
# Format code
ruff format src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Background Tasks

```bash
# Start Celery worker
celery -A src.workers.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A src.workers.celery_app beat --loglevel=info

# Combined (development)
celery -A src.workers.celery_app worker --beat --loglevel=info
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure proper database credentials
- [ ] Set up SSL/TLS
- [ ] Configure webhook URLs
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Configure rate limiting
- [ ] Set up backup strategy

### Docker Production

```bash
docker compose -f docker-compose.prod.yml up -d
```

### GitHub Actions CI/CD (GHCR build + server deploy)

Bu loyiha uchun CI/CD oqimi 2 ta alohida workflow bilan yozilgan:

- `.github/workflows/ci.yml`:
   - `main` ga push bo'lganda GitHub ichida build qiladi
   - image'larni GHCR ga push qiladi:
      - `ghcr.io/<owner>/<repo>/api`
      - `ghcr.io/<owner>/<repo>/worker`
      - `ghcr.io/<owner>/<repo>/telegram-bot`
- `.github/workflows/cd.yml`:
   - CI muvaffaqiyatli tugagandan keyin serverga SSH qiladi
   - serverda `git pull` + `docker compose pull` + `up -d` bajaradi

#### GitHub repository secrets

`Settings -> Secrets and variables -> Actions` ichiga quyidagilarni kiriting:

- `DEPLOY_HOST` — masalan: `198.163.207.189`
- `DEPLOY_USER` — masalan: `uz-user`
- `DEPLOY_PASSWORD` — server SSH paroli
- `DEPLOY_PORT` — odatda `22`
- `APP_DIR` — serverdagi repo papkasi (masalan `/opt/ai-chatbot`)
- `DEPLOY_BRANCH` — odatda `main`

`GHCR` uchun alohida secret shart emas — CD workflow GitHub job token (`GITHUB_TOKEN`) bilan login qiladi.

#### Server tarafida bir martalik tayyorlash

```bash
sudo mkdir -p /opt/ai-chatbot
cd /opt
git clone <YOUR_REPO_URL> ai-chatbot
cd /opt/ai-chatbot
cp .env.example .env
# .env ichida GHCR_REPOSITORY ni owner/repository formatida to'g'rilang
```

`docker-compose.prod.yml` ichida app servislar build qilinmaydi, tayyor image pull qilinadi.

### Nginx (WebSocket / WSS-ready)

- Nginx reverse-proxy konfiguratsiyasi: `nginx/conf.d/default.conf`
- WebSocket upgrade yo'li: `/ws/`
- `docker-compose.prod.yml` ichida `nginx` servisi API oldida ishlaydi
- To'liq `wss://` uchun SSL terminatsiya (masalan Cloudflare yoki serverda TLS cert) talab qilinadi

## Architecture

### Clean Architecture

```
Routes → Services → Repositories → Models
           ↓
       Clients (External APIs)
```

### Request Flow

1. Request → FastAPI Router
2. Authentication middleware
3. Rate limiting check
4. Route handler
5. Service layer (business logic)
6. Repository layer (database)
7. Response

### Multi-Channel Flow

```
Telegram/Instagram/Web/Voice
            ↓
       Webhook Handler
            ↓
       Chat Service
            ↓
     Intent Detection (AI)
            ↓
    Response Generation (AI)
            ↓
       Send Response
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is proprietary software. All rights reserved.

## Support

For support, contact: support@stratix.uz
