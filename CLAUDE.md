# Listn Intel Meta — Competitive Intelligence Platform

## Project Overview

**Listn Intel Meta** is a competitive intelligence platform that analyzes Meta (Facebook) ads from competitors in the voice-first memory preservation space. The platform helps Listn (a voice-first memory app for older adults) understand competitor messaging, identify market gaps, and optimize their own advertising strategy.

### Core Capabilities

- **Ad Scraping**: Automated scraping of competitor ads from Meta's Ad Library using Playwright
- **AI Analysis**: Claude-powered analysis of competitor ad strategies, messaging themes, and emotional positioning
- **Dashboard**: Streamlit-based visualization of competitive insights and KPIs
- **Reporting**: Automated weekly email reports with PDF attachments
- **SEO Intelligence**: Integrated SEO analysis tools for broader competitive research

### Target Competitors

- Remento
- Meminto
- StoryWorth
- Storykeeper
- Tell me
- Keepsake
- HereAfter AI
- No Story Lost

---

## Tech Stack

- **Language**: Python 3.8+
- **Web Scraping**: Playwright (headless Chromium)
- **AI Analysis**: Anthropic Claude API
- **Dashboard**: Streamlit
- **Data Processing**: Pandas
- **Visualization**: Plotly
- **PDF Generation**: ReportLab
- **Email**: SMTP (Gmail)
- **Environment**: `.env` file for API keys

### Key Dependencies

```
streamlit==1.50.0      # Dashboard framework
anthropic==0.96.0      # Claude AI client
playwright==1.x.x      # Web scraping
pandas==2.3.3          # Data analysis
plotly==5.24.1         # Data visualization
reportlab==4.4.10      # PDF generation
```

---

## Project Structure

```
├── analyze_ads.py          # Claude AI analysis of scraped ad data
├── dashboard.py            # Streamlit dashboard for insights
├── scrape_ads.py           # Playwright scraper for Meta Ad Library
├── fetch_ads.py            # Meta Graph API client (alternative to scraping)
├── weekly_email.py         # Automated email reporting system
├── inspect_page.py         # Ad Library page inspection utilities
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys)
├── .claude/               # Spartan AI Toolkit configuration
│   ├── CLAUDE.md          # Toolkit documentation
│   ├── rules/             # Project-specific coding rules
│   └── skills/            # Custom AI skills
├── sample_data/           # Sample datasets for testing
├── SEO_Intel/             # SEO analysis tools and reports
└── claude-seo/            # SEO toolkit (separate project)
```

### Data Flow

1. **Collection**: `scrape_ads.py` or `fetch_ads.py` pulls competitor ads
2. **Analysis**: `analyze_ads.py` uses Claude to analyze messaging and strategies
3. **Visualization**: `dashboard.py` displays insights and KPIs
4. **Reporting**: `weekly_email.py` generates and sends PDF reports

---

## Getting Started

### 1. Environment Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### 2. Required API Keys

```bash
# .env file
ANTHROPIC_API_KEY=your_claude_key
META_TOKEN=your_meta_access_token  # For Graph API access
GMAIL_APP_PASSWORD=your_gmail_app_password  # For email reports
```

### 3. Running the Dashboard

```bash
streamlit run dashboard.py
```

### 4. Scraping Ads

```bash
# Scrape competitor ads (no API key needed)
python scrape_ads.py

# Or use Meta Graph API (requires token)
python fetch_ads.py
```

### 5. Generate Analysis

```bash
python analyze_ads.py
```

### 6. Send Weekly Report

```bash
python weekly_email.py
```

---

## Development Workflows

### Adding a New Competitor

1. Add competitor name to `COMPETITORS` list in both `scrape_ads.py` and `fetch_ads.py`
2. Add page filter keywords to `COMPETITOR_PAGE_FILTER`
3. Add search plan to `COMPETITOR_SEARCH_PLAN`
4. Test scraping: `python scrape_ads.py`
5. Update dashboard filters if needed

### Modifying Analysis Prompts

Edit the `SYSTEM_PROMPT` in `analyze_ads.py` to change analysis focus:

- Messaging themes
- Longevity analysis
- CTA landscape
- Emotional tone
- Strategic recommendations
- Market gaps

### Dashboard Customization

The dashboard uses a dark purple theme. Key customization points:

- **Colors**: Edit CSS variables in `dashboard.py`
- **KPIs**: Modify the KPI calculation logic
- **Charts**: Update Plotly configurations
- **Layout**: Adjust Streamlit column layouts

### Email Report Customization

Edit `weekly_email.py` to customize:

- Report structure and sections
- PDF styling and layout
- Email subject and body
- Recipient list

---

## Data Formats

### Scraped Ad Data (`ads_scraped_*.json`)

```json
{
  "competitor_name": {
    "ads": [
      {
        "id": "ad_id",
        "page_name": "Competitor Page",
        "ad_creative_body": "Ad copy text...",
        "ad_creative_link_caption": "Learn More",
        "days_running": 45,
        "impressions": "10K-50K",
        "spend": "$100-500"
      }
    ],
    "total_ads": 25,
    "date_scraped": "2026-04-23"
  }
}
```

### Analysis Output (`competitor_analysis.md`)

Structured markdown with sections:
- Messaging Themes
- Longevity Analysis
- CTA Landscape
- Emotional Tone
- Strategic Recommendations
- Market Gaps

---

## Common Issues & Solutions

### Meta Ad Library Blocking

**Problem**: Meta blocks automated scraping
**Solution**: Use different user agents, add delays, or switch to Graph API

### Claude API Rate Limits

**Problem**: Analysis hits token limits
**Solution**: Break analysis into smaller chunks, add retry logic

### Email Delivery Issues

**Problem**: Gmail blocks automated emails
**Solution**: Use App Passwords, check spam folder, verify SMTP settings

### Streamlit Performance

**Problem**: Dashboard slow with large datasets
**Solution**: Implement data caching, pagination, or sampling

---

## Deployment

### Local Development

```bash
# Run dashboard locally
streamlit run dashboard.py --server.port 8501

# Run with hot reload
streamlit run dashboard.py --server.headless true
```

### Production Deployment

Consider deploying to:
- **Streamlit Cloud**: Direct deployment from GitHub
- **Heroku**: Containerized deployment
- **AWS/GCP**: Full infrastructure for scaling

### Scheduled Jobs

Set up cron jobs for:
- Daily ad scraping
- Weekly analysis generation
- Weekly email reports

---

## Contributing

### Code Style

- Use type hints for function parameters
- Add docstrings to all public functions
- Follow PEP 8 formatting
- Use descriptive variable names
- Handle errors gracefully

### Testing

- Test scraping with sample data
- Validate API responses
- Check email delivery
- Test dashboard interactions

### Documentation

- Update this CLAUDE.md for new features
- Document API key setup process
- Include troubleshooting steps
- Add examples for common use cases

---

## Related Projects

- **claude-seo/**: SEO analysis toolkit with additional competitive intelligence features
- **SEO_Intel/**: Broader SEO intelligence tools that complement ad analysis

---

## Contact & Support

For questions about this codebase or the competitive intelligence strategy, refer to the analysis reports and dashboard insights.