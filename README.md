# Mnemosyne Therapeutic AI - Groq Version

A conversational therapeutic AI system for research in trauma processing and cognitive reframing, powered by Groq's fast inference API.

## Features

- **Multiple Therapeutic Modes**: Exploratory dialogue, trauma processing, CBT, narrative therapy
- **Session Management**: Full conversation history and context retention
- **AI-Generated Summaries**: Clinical session summaries
- **Cloud Deployment Ready**: Optimized for Streamlit Community Cloud
- **Free to Run**: Uses Groq's free API tier

## Quick Start (Local Testing)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Get your free Groq API key**:
   - Visit: https://console.groq.com/keys
   - Sign up and create an API key
   - Copy the key

3. **Run the app**:
   ```bash
   streamlit run mnemosyne_groq.py
   ```

4. **Enter your API key** in the sidebar and start a session!

## Deploy to Streamlit Community Cloud (FREE)

### Step 1: Prepare Your GitHub Repository

1. **Create a GitHub account** (if you don't have one): https://github.com/signup

2. **Create a new repository**:
   - Go to: https://github.com/new
   - Name: `mnemosyne-therapy-ai`
   - Select: Public
   - Click "Create repository"

3. **Upload your files** to GitHub:
   - Click "uploading an existing file"
   - Upload these 3 files:
     - `mnemosyne_groq.py`
     - `requirements.txt`
     - `README.md` (this file)
   - Click "Commit changes"

### Step 2: Deploy on Streamlit Cloud

1. **Go to Streamlit Cloud**: https://share.streamlit.io/

2. **Sign in with GitHub**

3. **Click "New app"**

4. **Fill in the details**:
   - Repository: Select your `mnemosyne-therapy-ai` repo
   - Branch: `main`
   - Main file path: `mnemosyne_groq.py`

5. **Click "Deploy"** - Your app will be live in 2-3 minutes!

6. **Get your URL**: Something like `https://your-app.streamlit.app`

### Step 3: Share With Research Participants

1. Copy your app URL
2. Share the URL with participants
3. They'll need to enter the Groq API key (you can provide them with one)

## Groq API Key Options

**Option 1: Each participant gets their own key** (recommended)
- Most secure
- Each person signs up for free Groq account
- They use their own API key

**Option 2: Shared research API key**
- You create one API key
- Share it with all participants
- Monitor usage in Groq console
- Note: Free tier has rate limits (30 req/min)

## Free Tier Limits

Groq free tier includes:
- **30 requests/minute**
- **14,400 requests/day**
- More than enough for research testing!

## Models Available

The app uses `llama-3.1-70b-versatile` by default for best therapeutic responses.

Other options you can change in the code:
- `llama-3.1-8b-instant` - Faster, less sophisticated
- `mixtral-8x7b-32768` - Alternative model

## Database

Conversations are stored in `mnemosyne_conversations.db` (SQLite).

On Streamlit Cloud, this resets when the app restarts. For persistent storage, you'd need to:
- Use Streamlit's persistent storage features
- Or connect to an external database (PostgreSQL, etc.)

## Research Ethics Notice

**IMPORTANT**: This is a research prototype. Before deploying for actual therapeutic use:

1. ✅ Obtain IRB approval (if at university)
2. ✅ Add informed consent forms
3. ✅ Include data privacy disclosures
4. ✅ Add disclaimers that this is NOT real therapy
5. ✅ Have licensed clinical oversight
6. ✅ Comply with HIPAA/GDPR if handling real patient data

## Customization

### Change the AI model:
Edit line 10 in `mnemosyne_groq.py`:
```python
MODEL_NAME = "llama-3.1-8b-instant"  # Faster option
```

### Adjust response length:
Edit the `max_tokens` parameter (currently 1000) in the `generate_ai_response` function.

### Add custom therapeutic modes:
Add new entries to the `THERAPEUTIC_SYSTEMS` dictionary with your own system prompts.

## Troubleshooting

**"API Key not configured"**
- Make sure you entered your Groq API key in the sidebar

**"Rate limit exceeded"**
- Free tier: 30 requests/minute. Wait a bit and try again
- Or upgrade to paid tier at Groq

**"Invalid API Key"**
- Double-check you copied the full key from Groq console
- Make sure there are no extra spaces

**Database errors on Streamlit Cloud**
- The database resets when app restarts (this is normal for free tier)
- For persistent storage, consider upgrading or using external database

## Support

For issues:
- Check Groq status: https://status.groq.com/
- Streamlit docs: https://docs.streamlit.io/
- Groq docs: https://console.groq.com/docs

## License

Research use only. Ensure proper licensing and supervision for clinical deployment.
