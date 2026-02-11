# QUICK DEPLOYMENT GUIDE

## ⚡ Fast Track to Deployment (15 minutes)

### Step 1: Get Your Groq API Key (2 minutes)
1. Go to: https://console.groq.com/keys
2. Sign up with Google/GitHub
3. Click "Create API Key"
4. **Copy the key** (starts with `gsk_...`) - you'll need this later!

### Step 2: Upload to GitHub (5 minutes)
1. Go to: https://github.com/new
2. Name: `mnemosyne-therapy-ai`
3. Keep it **Public**
4. Click "Create repository"
5. Click **"uploading an existing file"**
6. Upload ALL these files:
   - `mnemosyne_groq.py` ✓
   - `requirements.txt` ✓
   - `README.md` ✓
   - `.gitignore` ✓
   - `.streamlit/secrets.toml.example` ✓ (create folder if needed)
7. Click "Commit changes"

### Step 3: Deploy on Streamlit (5 minutes)
1. Go to: https://share.streamlit.io/
2. Click "Sign in" → "Continue with GitHub"
3. Click "New app"
4. Select your repository: `mnemosyne-therapy-ai`
5. Main file: `mnemosyne_groq.py`
6. Click "Deploy"

### Step 4: Add Your API Key Secret (3 minutes)
**CRITICAL STEP - Your app won't work without this!**

While the app is deploying:
1. Look for the **⋮ menu** (three dots) in the bottom right of the deployment page
2. Click **"Settings"**
3. Click **"Secrets"** tab on the left
4. Paste this (replace with YOUR actual key):
   ```
   GROQ_API_KEY = "gsk_your_key_here"
   ```
5. Click **"Save"**

The app will restart automatically and be ready to use!

### Step 5: Test & Share
1. Your URL: `https://mnemosyne-therapy-ai-[something].streamlit.app`
2. Open it and start a session
3. Share the URL with participants - **they don't need an API key!**

---

## 🎯 What You Should See

**On the deployed app:**
- ✅ Green checkmark: "API Key configured via Secrets"
- ✅ "Running in production mode"
- ✅ No API key input field in sidebar
- ✅ Participants can start sessions immediately

**If you see warnings:**
- ⚠️ "No secret key found" → Go back to Step 4
- ⚠️ "Invalid API Key" → Check you copied the full key from Groq

---

## 📋 Files You Need to Upload

From your computer, upload to GitHub:
```
mnemosyne-therapy-ai/
├── mnemosyne_groq.py          ← Main app
├── requirements.txt           ← Python dependencies  
├── README.md                  ← Documentation
├── .gitignore                 ← Protects secrets
└── .streamlit/
    └── secrets.toml.example   ← Example (not the real secret!)
```

**DO NOT upload:**
- ❌ `secrets.toml` (without .example) - this contains your real key
- ❌ `*.db` files - database files
- ❌ Any files with real API keys in them

---

## 🆘 Troubleshooting

**"API Key not configured"**
→ Add secrets in Streamlit Cloud Settings → Secrets

**"Rate limit exceeded"**
→ Free tier: 30 requests/min. Wait a bit or upgrade

**App keeps restarting**
→ Normal! It restarts after secret changes

**Database resets**
→ Expected on free tier. For persistent data, use paid tier or external DB

**Can't find Settings → Secrets**
→ Click the ⋮ menu (three dots) on your deployed app page

---

## 💡 Pro Tips

1. **Test locally first**: Run `python -m streamlit run mnemosyne_groq.py` before deploying
2. **Monitor usage**: Check Groq console for API usage stats
3. **Backup data**: Export session data regularly (use the Export button)
4. **Update secrets**: Can change API key anytime in Settings → Secrets

---

## 📊 Usage Limits (Groq Free Tier)

- ✅ 30 requests per minute
- ✅ 14,400 requests per day
- ✅ Free forever
- ✅ Perfect for research with 10-50 participants

Need more? Upgrade to Groq paid tier (~$0.50 per million tokens)

---

Ready to deploy? Start with Step 1! 🚀
