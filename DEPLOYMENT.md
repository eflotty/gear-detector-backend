# Deploying to Render

## Prerequisites
- Render account (sign up at https://render.com)
- GitHub account (to push your code)

## Step 1: Push to GitHub

```bash
cd /Users/eddieflottemesch/Experiment/Backend

# Add all files
git add .

# Commit
git commit -m "Initial Gear Detector backend"

# Create GitHub repo and push
# (Go to github.com and create a new repository called 'gear-detector-backend')
git remote add origin https://github.com/YOUR_USERNAME/gear-detector-backend.git
git branch -M main
git push -u origin main
```

## Step 2: Create Render Services

1. Go to https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: geardetector-api
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`

## Step 3: Add PostgreSQL Database

1. In Render dashboard: "New +" → "PostgreSQL"
2. **Name**: geardetector-db
3. **Plan**: Free
4. Copy the **Internal Database URL** after creation

## Step 4: Add Redis

1. In Render dashboard: "New +" → "Redis"
2. **Name**: geardetector-redis
3. **Plan**: Free
4. Copy the **Internal Redis URL** after creation

## Step 5: Set Environment Variables

In your web service settings → Environment:

```
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY
DATABASE_URL=<paste Internal Database URL from Step 3>
REDIS_URL=<paste Internal Redis URL from Step 4>
ENVIRONMENT=production
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=4000
```

Optional (add if you have these):
```
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret
YOUTUBE_API_KEY=your_youtube_key
```

## Step 6: Deploy

Click "Manual Deploy" → "Deploy latest commit"

Your API will be available at: `https://geardetector-api.onrender.com`

## Step 7: Update iOS App

Update the API base URL in your iOS app:

```swift
// In GearDetectorAPI.swift
init(baseURL: String = "https://geardetector-api.onrender.com/api/v1") {
    ...
}
```

## Cost

- Web Service (Free tier): $0
- PostgreSQL (Free tier): $0
- Redis (Free tier): $0
- **Total: FREE** for first month

After free tier limits, upgrade to Starter ($7/month for web service).
