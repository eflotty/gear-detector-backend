# Gear Detector - Data Source Strategy

## Scraper Accuracy Ranking (Highest to Lowest)

### 🥇 Tier 1: High Accuracy, Specific Data
1. **YouTube** (`youtube_scraper.py`)
   - **Why:** Rig rundown videos, gear demos, and tutorial videos explicitly discuss equipment
   - **Sources:**
     - Video titles and descriptions (direct gear lists)
     - Top comments (fans and artists discussing specific models)
     - Searches: "Artist rig rundown", "Artist song guitar tone", "Artist guitar gear"
   - **Coverage:** Excellent for popular artists (2010s+), moderate for older artists
   - **Confidence:** 80-95%
   - **API Cost:** ~105 quota units per song (within free tier: 95 songs/day)

2. **Reddit** (`reddit_scraper.py`)
   - **Why:** Dedicated music/gear communities with detailed discussions
   - **Subreddits:**
     - r/Guitar, r/guitarlessons, r/guitarpedals
     - r/WeAreTheMusicMakers, r/audioengineering
     - Artist-specific subreddits (e.g., r/JohnMayer)
   - **Coverage:** Excellent for well-discussed artists and songs
   - **Confidence:** 75-90%
   - **API Cost:** Free (60 requests/minute rate limit)

3. **Equipboard** (`equipboard_scraper.py`)
   - **Why:** Crowdsourced database specifically for musician gear
   - **Coverage:** Very good for popular artists, limited for obscure artists
   - **Confidence:** 80-90% (user-submitted, moderated)
   - **API Cost:** Free (web scraping)

### 🥈 Tier 2: Moderate Accuracy, Broader Coverage
4. **Gearspace (formerly Gearslutz)** (`gearspace_scraper.py`)
   - **Why:** Pro audio forum with recording engineers discussing gear
   - **Coverage:** Good for studio gear, mixing/mastering equipment
   - **Confidence:** 70-85%
   - **API Cost:** Free (web scraping)

5. **Web Search (SerpAPI/Google)** (`web_search_scraper.py`)
   - **Why:** Aggregates blog posts, interviews, and gear articles
   - **Coverage:** Broad - catches sources not covered by other scrapers
   - **Confidence:** 60-80% (varies by source quality)
   - **API Cost:** Free tier (100 searches/month), then $50/month

### 🥉 Tier 3: Contextual Info (Not Gear-Specific)
6. **Artist Metadata** (`artist_metadata_scraper.py`)
   - **Why:** Provides context for inference (genre, era, known preferences)
   - **Sources:** Wikipedia, MusicBrainz, Discogs
   - **Usage:** Helps Claude infer likely gear when explicit data is missing
   - **Confidence:** N/A (used for inference, not direct gear data)
   - **API Cost:** Free

---

## Expected Data Quality by Artist Popularity

### Popular Artists (Post-2000)
- **YouTube:** ✅ Excellent (multiple rig rundowns, gear demos)
- **Reddit:** ✅ Excellent (active fan discussions)
- **Equipboard:** ✅ Very Good (comprehensive user-submitted data)
- **Expected Result:** 90-95% complete gear list

### Mid-Tier Artists (2000-2020)
- **YouTube:** ✅ Good (some gear videos, live footage)
- **Reddit:** ✅ Good (moderate discussion)
- **Equipboard:** ⚠️ Moderate (partial data)
- **Expected Result:** 70-80% complete gear list

### Older/Obscure Artists (Pre-2000)
- **YouTube:** ⚠️ Limited (fewer rig rundowns, rely on historical content)
- **Reddit:** ⚠️ Limited (less active discussion)
- **Web Search:** ✅ Better (more likely to find magazine interviews, old articles)
- **Expected Result:** 50-70% complete gear list, more inference needed

---

## Quota Management & Cost Estimates

### Daily Limits (Free Tier)
- **YouTube:** 10,000 units/day = ~95 searches
- **Reddit:** 60 requests/minute = ~86,400 requests/day (functionally unlimited)
- **SerpAPI:** 100 searches/month = ~3 searches/day

### Recommended Strategy
1. **Development:** Use all scrapers with real API keys to build confidence data
2. **Production:**
   - Cache aggressively (90-day TTL for songs)
   - Prioritize YouTube + Reddit for new searches
   - Use SerpAPI sparingly for high-value searches
   - Consider upgrading SerpAPI after initial user traction

### Cost at Scale (1000 searches/day)
- **YouTube:** Free (under 10k quota/day)
- **Reddit:** Free
- **SerpAPI:** $50-150/month (depending on tier)
- **Claude API:** ~$20-50/day (depends on prompt length and response)
- **Estimated Total:** ~$2,000-3,500/month at 1k searches/day

---

## Implementation Status

| Scraper | Status | API Key Required | Currently Returns Data |
|---------|--------|------------------|------------------------|
| YouTube | ✅ Enhanced with comments | Yes | Mock (key needed) |
| Reddit | ✅ Implemented | Yes | Mock (key needed) |
| Equipboard | ✅ Implemented | No | Mock (scraping blocked?) |
| Gearspace | ✅ Implemented | No | Mock (scraping blocked?) |
| Web Search | ✅ Implemented | Yes (SerpAPI) | Mock (key needed) |
| Artist Metadata | ✅ Implemented | No (Wikipedia/MusicBrainz) | Mock |

---

## Next Steps to Enable Real Data

1. **Set up YouTube API key** (Highest priority - best coverage)
   - Go to https://console.cloud.google.com/
   - Create project → Enable YouTube Data API v3 → Create API key
   - Add to `.env`: `YOUTUBE_API_KEY=your_key_here`

2. **Set up Reddit API credentials** (High priority - free and high quality)
   - Go to https://www.reddit.com/prefs/apps
   - Create app (script type) → Copy client ID and secret
   - Add to `.env`: `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`

3. **Optional: Set up SerpAPI** (Lower priority - cost vs. benefit)
   - Go to https://serpapi.com/dashboard
   - Sign up for free tier (100 searches/month)
   - Add to `.env`: `SCRAPER_API_KEY=your_key_here`

4. **Test with real API keys**
   - Search for a well-known artist (e.g., "John Mayer - Gravity")
   - Verify data quality in Claude's synthesis
   - Adjust scraper confidence scores based on results

5. **Monitor quota usage**
   - YouTube: Check https://console.cloud.google.com/apis/dashboard
   - Reddit: Generally won't hit limits with normal usage
   - SerpAPI: Check dashboard for usage stats
