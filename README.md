# Guitar Gear Detector - Backend API

FastAPI backend for the Guitar Gear Detector app. Aggregates gear information from multiple sources and uses Claude AI to synthesize comprehensive gear setups with intelligent inference.

## Features

- **Multi-Source Data Aggregation**: Scrapes gear info from Equipboard, Reddit, YouTube, Gearspace, and web search
- **Intelligent AI Inference**: Uses Claude AI to synthesize data and infer missing information based on artist signature sound, genre, and era
- **Artist Context Enrichment**: Gathers artist metadata from Wikipedia and MusicBrainz for better inference
- **Complete Gear Details**: Always returns amp settings, signal chain, and confidence scores
- **Caching System**: PostgreSQL-based caching with 90-day TTL
- **RESTful API**: Clean FastAPI endpoints with OpenAPI documentation

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy (async)
- **AI**: Anthropic Claude API (Sonnet 4.5)
- **Scraping**: aiohttp, BeautifulSoup4, PRAW (Reddit)
- **Deployment**: Render (auto-deploy from GitHub)

## Architecture

```
Backend/
├── src/
│   ├── api/              # API routes and request/response models
│   │   ├── routes/       # Endpoint handlers
│   │   └── models/       # Pydantic models
│   ├── services/         # Business logic
│   │   ├── aggregator.py       # Coordinates all scrapers
│   │   ├── claude_service.py   # AI synthesis
│   │   └── context_service.py  # Artist metadata enrichment
│   ├── scrapers/         # Data source scrapers
│   │   ├── base_scraper.py
│   │   ├── equipboard_scraper.py
│   │   ├── reddit_scraper.py
│   │   ├── youtube_scraper.py
│   │   ├── gearspace_scraper.py
│   │   ├── web_search_scraper.py
│   │   └── artist_metadata_scraper.py
│   ├── database/         # Database models and connection
│   └── config.py         # Configuration management
└── main.py               # Application entry point
```

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+ (local or cloud)
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/eflotty/gear-detector-backend.git
   cd gear-detector-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Set up PostgreSQL database**
   ```bash
   createdb geardetector
   # Update DATABASE_URL in .env
   ```

6. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

7. **Start the development server**
   ```bash
   uvicorn main:app --reload
   ```

   API will be available at `http://localhost:8000`

### API Keys Required

See `.env.example` for detailed instructions on obtaining each key.

#### Essential (for full functionality):
- **Anthropic Claude API** - Required for gear synthesis
  - Get from: https://console.anthropic.com/
  - Cost: Pay-as-you-go

#### Optional (improves data quality):
- **Reddit API** - For gear discussions
  - Get from: https://www.reddit.com/prefs/apps
  - Cost: Free (rate limited)

- **YouTube Data API** - For rig rundowns
  - Get from: https://console.cloud.google.com/
  - Cost: Free tier (10,000 queries/day)

- **SerpAPI** - For web search
  - Get from: https://serpapi.com/
  - Cost: Free tier (100 searches/month)

**Note**: The app works without optional API keys by using mock data for testing.

## Deployment

### Render (Recommended)

1. **Connect GitHub repository**
   - Go to https://render.com
   - Create new Web Service
   - Connect your GitHub repo

2. **Configure service**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3.11

3. **Add environment variables**
   - Add all API keys from `.env.example`
   - Render provides `DATABASE_URL` automatically if you add PostgreSQL

4. **Deploy**
   - Push to `main` branch
   - Render auto-deploys on every push

### Other Platforms

The app is compatible with any platform supporting Python ASGI apps:
- Heroku
- Railway
- Google Cloud Run
- AWS Elastic Beanstalk
- DigitalOcean App Platform

## API Documentation

### Endpoints

#### POST /api/v1/search
Search for guitar gear used in a specific song.

**Request:**
```json
{
  "artist": "John Mayer",
  "song": "Gravity",
  "year": 2006
}
```

**Response:**
```json
{
  "search_id": "uuid",
  "status": "complete",
  "artist": "John Mayer",
  "song": "Gravity",
  "year": 2006,
  "result": {
    "guitars": [
      {
        "make": "Fender",
        "model": "Stratocaster",
        "year": 1964,
        "notes": "Sunburst finish",
        "confidence": 95.0,
        "sources": ["equipboard", "youtube"]
      }
    ],
    "amps": [...],
    "pedals": [...],
    "signal_chain": [
      {"type": "guitar", "item": "Fender Stratocaster (1964)"},
      {"type": "pedal", "item": "Ibanez TS808"},
      {"type": "amp", "item": "Dumble Overdrive Special"}
    ],
    "amp_settings": {
      "gain": "Medium (5-6)",
      "treble": "7",
      "middle": "5",
      "bass": "6",
      "presence": "5",
      "notes": "Clean headroom with slight breakup"
    },
    "context": "...",
    "confidence_score": 85.0
  }
}
```

#### GET /api/v1/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### Interactive Docs

Visit `/docs` for Swagger UI or `/redoc` for ReDoc documentation.

## How It Works

### 1. Data Aggregation
When a search is performed:
- 6 scrapers run in parallel (30s timeout each)
- Equipboard, Reddit, YouTube, Gearspace, Web Search, Artist Metadata
- Results are collected and passed to Claude

### 2. AI Synthesis
Claude AI analyzes all data and:
- Cross-references sources for accuracy
- Assigns confidence scores (Confirmed 90-100%, Likely 70-89%, Inferred 50-69%)
- Infers missing data based on:
  - Artist's signature sound and known gear
  - Album/era production characteristics
  - Genre conventions
  - Similar songs from same period
- **Always** generates complete amp settings and signal chain

### 3. Context Enrichment
Artist metadata scraper provides:
- Genre and musical style
- Era characteristics
- Active years and career timeline
- Background information for better inference

### 4. Caching
- Search results are cached in PostgreSQL for 90 days
- Cache key: MD5 hash of `artist:song:year`
- Reduces API costs and improves response time

## Confidence Levels

- **Confirmed (90-100%)**: Direct evidence from sources (rig rundowns, interviews, photos)
- **Likely (70-89%)**: Strong circumstantial evidence or artist's known signature gear
- **Inferred (50-69%)**: Educated inference based on tone, genre, artist style

## Development

### Running Tests
```bash
pytest
```

### Code Style
```bash
black .
flake8 .
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Performance

- **Average response time**: 5-15 seconds
- **Concurrent requests**: Supports multiple via async/await
- **Cache hit rate**: ~70% for popular searches
- **Claude API cost**: ~$0.01-0.05 per search (depending on prompt length)

## Troubleshooting

### "No scraper results" warning
- Check that API keys are configured
- Verify network connectivity
- App will return mock data for testing

### Database connection errors
- Verify `DATABASE_URL` is correct
- Ensure PostgreSQL is running
- Check firewall rules for production DB

### Claude API errors
- Verify `ANTHROPIC_API_KEY` is valid
- Check API quota/billing
- Review logs for specific error messages

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT

## Contact

For issues and questions:
- GitHub Issues: https://github.com/eflotty/gear-detector-backend/issues
- Email: contact@geardetector.com

---

Built with Claude Sonnet 4.5
