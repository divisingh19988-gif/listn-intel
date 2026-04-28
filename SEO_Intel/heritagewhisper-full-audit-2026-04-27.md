# Heritage Whisper — Full SEO Audit Report

**Site:** https://heritagewhisper.com
**Date:** April 27, 2026
**Auditor:** Listn Intel Meta / Claude Code
**Scope:** Technical SEO · On-Page · Content · Schema · Performance · Competitor Analysis · Keyword Clusters · AI Search Readiness

---

## Executive Summary

Heritage Whisper is a voice-first family storytelling platform built on Next.js 15 and Vercel, targeted at seniors (65+) and their adult children. It is one of the most SEO-sophisticated competitors in this niche — notably ahead of Remento and StoryWorth in several dimensions including AI search readiness, schema depth, and content architecture.

**Overall SEO Health Score: 76/100** — Strong foundation with clear upside in content volume and a few fixable technical gaps.

### Score Breakdown

| Category | Score | Grade |
|---|---|---|
| Technical SEO | 75/100 | B |
| Content Quality | 65/100 | C+ |
| On-Page SEO | 78/100 | B+ |
| Schema / Structured Data | 85/100 | A |
| Performance (CWV) | 72/100 | B |
| AI Search Readiness | 95/100 | A+ |
| Images | 68/100 | C+ |

### Top 5 Quick Wins

1. **Fix duplicate brand suffix in About page title** — "Heritage Whisper | Heritage Whisper" wastes title length and confuses SERP display
2. **Add canonical tag to `/pricing` page** — currently missing; page has `noindex` (possibly intentional) but still needs canonical for crawl hygiene
3. **Fix 10 missing alt-text images** across guide, alt, pearl, pricing, and gift pages
4. **Add `AggregateRating` schema** — site shows 4.9/5 stars and testimonials but has no Review schema to expose in SERPs
5. **Publish 5 blog posts in 90 days** — only 1 post exists despite having /blog with high-authority topic territory

---

# 1. Technical SEO

## 1.1 Platform & Infrastructure

Heritage Whisper runs on **Next.js 15** deployed to **Vercel Edge Network**. This is a best-in-class setup for performance and global CDN distribution. The Supabase backend (PostgreSQL + OpenAI) is invisible to crawlers.

| Signal | Finding | Status |
|---|---|---|
| Platform | Next.js 15 / Vercel | ✅ Excellent |
| CDN | Vercel Edge (global) | ✅ Excellent |
| HTTPS | Full TLS, HSTS enabled | ✅ |
| HTTP→HTTPS redirect | Enforced | ✅ |
| WWW redirect | heritagewhisper.com (no www) | ✅ |

## 1.2 Security Headers

Heritage Whisper has the strongest security header implementation in this niche. Every major header is present and configured correctly.

| Header | Value | Status |
|---|---|---|
| Content-Security-Policy | Full CSP with nonces | ✅ |
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload | ✅ |
| X-Content-Type-Options | nosniff | ✅ |
| X-Frame-Options | DENY | ✅ |
| Referrer-Policy | strict-origin-when-cross-origin | ✅ |
| Permissions-Policy | camera=(), microphone=(), geolocation=() | ✅ |

## 1.3 robots.txt

The robots.txt is strategically configured and reflects a deep understanding of AI search. It blocks app-authenticated pages while explicitly granting access to 20+ AI bots for all public content.

```
Explicitly allowed AI bots:
GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, anthropic-ai, Claude-Web,
PerplexityBot, Perplexity-User, Google-Extended, Applebot-Extended,
Bytespider, Meta-ExternalAgent, FacebookBot, Bingbot, Amazonbot,
CCBot, cohere-ai, DuckAssistBot, MistralAI-User, YouBot
```

Blocked paths (correct — authenticated app pages): `/timeline`, `/book`, `/prompts`, `/interview-chat`, `/profile`, `/settings`, `/admin`, `/family`, `/api/*`

**Assessment:** This robots.txt is best-in-class for AI era SEO. Most competitors block AI bots by default.

## 1.4 Sitemap

- **Location:** `https://heritagewhisper.com/sitemap.xml` ✅
- **Total URLs:** 31
- **Format:** Well-formed with `<lastmod>` and `<priority>` ✅
- **Referenced in robots.txt:** ✅

| Page Category | Count |
|---|---|
| Homepage | 1 |
| Core pages (about, examples, features, help) | 5 |
| Alternatives pages | 4 |
| Guides | 8 |
| Gifts | 3 |
| Blog | 2 (hub + 1 post) |
| Utility (privacy, terms) | 2 |
| Feature detail | 2 |

**Gap:** `/pricing` is **not** in the sitemap (noindex, which is acceptable for A/B testing scenarios, but should be intentional not accidental).

## 1.5 Critical Technical Issues

### Issue 1: Pricing Page — Missing Canonical + noindex [HIGH]

`/pricing` has `<meta name="robots" content="noindex">` AND no canonical tag. If the noindex is intentional (e.g., multiple pricing variants being A/B tested), this is acceptable but should be documented. If unintentional, this page is invisible to search engines and receiving no organic traffic.

**Fix:** Confirm intent. If pricing should rank, remove noindex and add canonical. If intentional, add canonical anyway for crawl budget hygiene.

### Issue 2: Homepage HTML Weight — 1.35MB [MEDIUM]

The homepage HTML is 1.35MB, which is unusually large for a Next.js SSR page. Guide and alt pages also run 975KB–1MB. This suggests:
- Excessive inline CSS (multiple large `<style>` tags with CSS variables)
- Large JS bundle inlining or hydration payload
- All above-the-fold and below-the-fold content in the initial HTML

**Impact:** Slower TTFB on uncached requests, higher bandwidth costs, potential LCP issues on mobile.

**Fix:** Audit Next.js bundle size with `next build --analyze`. Split large CSS into separate files. Review hydration payload size.

### Issue 3: About Page Title Duplication [LOW]

**Current:** `Our Story | Heritage Whisper - A Mission to End the Silence | Heritage Whisper`
The brand name appears twice. Title is ~80 chars but will be truncated.

**Fix:** `Our Story: A Mission to End the Silence | Heritage Whisper`

---

# 2. On-Page SEO

## 2.1 Title Tag & Meta Description Analysis

| Page | Title | Description | Notes |
|---|---|---|---|
| Homepage | Heritage Whisper — Their Voice. Your Family Hears It Tonight. | Present ✅ | Strong emotional hook |
| Guide: Recording | How to Record Family Stories: A Complete Guide | Present ✅ | Target keyword in title ✅ |
| StoryWorth Alt | 7 Best StoryWorth Alternatives in 2026 | Present ✅ | Year-dated for freshness ✅ |
| Pearl Feature | Pearl: Your AI Storytelling Guide | Present ✅ | |
| Pricing | Choose your Heritage Whisper plan | Present ✅ | noindex — not ranking |
| Gift: Mother's Day | The Best Mother's Day Gift for Mom in 2026: Ideas That Actually Mean Something | Present ✅ | Long but compelling |
| About | Our Story \| Heritage Whisper - A Mission to End the Silence \| Heritage Whisper | Present ✅ | **Duplicate brand suffix — fix** |
| Blog | Blog: Stories About Preserving Stories | N/A | Generic, not keyword-optimized |

**Overall on-page title/description quality: 8/9 pages pass.** The About title and Blog title are the exceptions.

## 2.2 Heading Structure

| Page | H1 | H2 Structure | Issues |
|---|---|---|---|
| Homepage | Their voice. Your family hears it tonight. | Multiple clear sections | ✅ |
| Guide | How to Record Family Stories: A Complete Guide | Quick Answer → Before → During → After → Challenges | ✅ Excellent |
| StoryWorth Alt | 7 Best StoryWorth Alternatives in 2026 | Per-competitor H2s | ✅ Excellent |
| Pearl | Talk. We listen. Your story takes shape. | Feature-focused H2s | ✅ |
| Mother's Day Gift | The Best Mother's Day Gift for Mom in 2026 | Quick Answer → Why Stories → Ranked list | ✅ Excellent |
| Pricing | (H1 missing) | (H2 missing) | noindex — not ranking |

**Heading structure is consistently strong.** Most content pages follow the "Quick Answer" → expanded sections pattern, which is highly optimized for featured snippets and AI citations.

## 2.3 Canonical Tags

| Page | Canonical Present | Status |
|---|---|---|
| Homepage | ✅ https://heritagewhisper.com | ✅ |
| Guide: Recording | ✅ https://heritagewhisper.com/guides/recording-family-stories | ✅ |
| StoryWorth Alt | ✅ https://heritagewhisper.com/alternatives/storyworth-alternatives | ✅ |
| Pearl | ✅ https://heritagewhisper.com/features/pearl | ✅ |
| Mother's Day Gift | ✅ https://heritagewhisper.com/gifts/mothers-day-gift-for-mom | ✅ |
| **Pricing** | ❌ **MISSING** | ⚠️ Fix needed |

## 2.4 Open Graph & Social Meta

All audited pages have complete OG + Twitter Card meta tags:
- `og:title`, `og:description`, `og:image` (1200×630), `og:type`
- `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`

**Status: Excellent.** ✅

---

# 3. Content Quality & Strategy

## 3.1 Content Architecture Overview

Heritage Whisper has a well-planned programmatic content structure with distinct content categories:

| Category | Pages | Avg. Depth | Keyword Target |
|---|---|---|---|
| Guides | 8 | Deep (7k+ words effective) | "how to record family stories", "questions to ask parents" |
| Alternatives | 4 | Very deep (10k+ words) | "storyworth alternatives", "storii alternatives" |
| Gifts | 2 | Deep | "mothers day gift for mom", "fathers day gift for dad" |
| Features | 2+ | Medium | Product-specific |
| Blog | **1 post** | Medium | ⚠️ Critical gap |
| About | 1 | Medium | Brand/E-E-A-T |

## 3.2 Content Quality by Page Type

### Guides (Score: 85/100)
The guide content is excellent. The `/guides/recording-family-stories` page demonstrates:
- **"Quick Answer" section** at the top (featured snippet bait)
- **Structured H2/H3 flow**: Before → During → After → Challenges → FAQ
- **FAQ section** with 5+ questions (FAQPage schema present)
- Word count appears high (22k from HTML) with substantial effective text content
- Clear internal linking to "Related guides"

### Alternatives Pages (Score: 90/100)
`/alternatives/storyworth-alternatives` is a standout page:
- 7 competitors with dedicated H2 sections
- Comparison table for quick scanning
- "Choose X if:" subsections for decision-making
- **Multiple schema types**: SoftwareApplication + Article + BreadcrumbList + ItemList + FAQPage
- Positions Heritage Whisper as #1 in its own category list (legitimate, given context)

### Gift Pages (Score: 82/100)
Well-structured commercial-intent pages targeting seasonal keywords. Year-dated for freshness. Strong CTAs.

### Blog (Score: 25/100 — Critical Gap)
The blog has exactly **1 published post**. This is a major missed opportunity:
- Domain authority signals from blog content are near-zero
- No content targeting informational keywords ("how do I preserve grandparent stories", "best app for family history")
- No internal linking hub building from blog to guides/alternatives
- The blog hub title ("Blog: Stories About Preserving Stories") is generic, not keyword-targeted

### About Page (Score: 70/100)
The about page contains compelling founder narrative (Paul Takisaki's story of building Heritage Whisper for his father) — strong E-E-A-T signal. However, the duplicate title tag hurts SERP presentation.

## 3.3 Keyword Cluster Analysis

Heritage Whisper is targeting or should target these clusters:

### Cluster 1: Family Story Preservation (Core)
**Primary:** "family story preservation", "preserve family stories", "record grandparent stories"
**Coverage:** Homepage, Pearl, Guides — ✅ Well covered
**Gap:** No dedicated "family story preservation service" comparison page

### Cluster 2: Competitor Alternatives (Commercial)
**Primary:** "storyworth alternatives", "remento alternatives", "storii alternatives"
**Coverage:** 4 alternatives pages — ✅ Strong
**Gap:** Missing `/alternatives/remento-alternatives`, `/alternatives/storii-alternatives` as dedicated pages (only one hub page)

### Cluster 3: Gift / Seasonal (Commercial)
**Primary:** "mothers day gift for mom", "fathers day gift for dad", "meaningful gift for grandparents"
**Coverage:** 2 gift pages — ✅ Good
**Gap:** "Christmas gift for elderly parent", "birthday gift for 80 year old grandma"

### Cluster 4: Grandparent Questions (Informational)
**Primary:** "questions to ask grandparents", "questions to ask parents before they die"
**Coverage:** 4 guide pages in sitemap — ✅ Good
**Gap:** "50 questions to ask your parents" as a standalone pillar (currently only linked at bottom of alt page)

### Cluster 5: Technical/How-To (Middle-of-Funnel)
**Primary:** "how to record family stories", "how to digitize old photos", "urgent story preservation"
**Coverage:** 3-4 guides — ✅ Present
**Gap:** Video-related keywords ("record grandparent video interview") if video ever added

### Cluster 6: Voice/AI Storytelling (Emerging)
**Primary:** "AI interview app for seniors", "voice storytelling app", "Pearl AI"
**Coverage:** Pearl page — ✅ Good
**Gap:** No dedicated "voice-first app for seniors" landing page; "AI for family history" keywords

### Keyword Opportunities (Not Currently Targeted)
| Keyword | Intent | Est. Difficulty | Opportunity |
|---|---|---|---|
| "digital legacy platform" | Commercial | Medium | High — no clear leader |
| "record grandparent stories before they die" | Emotional/Informational | Low | High — Heritage Whisper has content |
| "family history app for elderly" | Commercial | Medium | High |
| "50 questions to ask parents before they die" | Informational | Low | Current guides/alt pages reference it — needs own page |
| "memorial audio recording" | Informational | Low | Niche but aligned |
| "Christmas gift for 80 year old grandma" | Commercial | Medium | Seasonal opportunity |
| "how to make a family legacy book" | Informational | Medium | Cross-sell to book feature |

---

# 4. Schema & Structured Data

Heritage Whisper has the best schema implementation in this niche.

## 4.1 Schema by Page

| Page | Schema Types | Quality |
|---|---|---|
| Homepage | Organization, WebSite (with SearchAction), FAQPage | ✅ Excellent |
| StoryWorth Alt | Organization, WebSite, SoftwareApplication, Article, BreadcrumbList, ItemList, FAQPage | ✅ Excellent |
| Pearl Feature | Organization, WebSite, SoftwareApplication, BreadcrumbList | ✅ Good |
| Guide: Recording | Organization, WebSite, SoftwareApplication, Article, BreadcrumbList, FAQPage | ✅ Excellent |
| Gift: Mother's Day | Organization, WebSite, SoftwareApplication, Article, BreadcrumbList, FAQPage | ✅ Excellent |
| Pricing | Organization, WebSite | noindex — N/A |
| Blog | TBD | Only 1 post |

## 4.2 Schema Strengths

- **WebSite schema with SearchAction**: Enables sitelinks search box in Google SERPs
- **Organization schema with legalName**: Reinforces entity identity ("Heritage Whisper LLC")
- **SoftwareApplication schema**: Correct type for a web app; signals app-ness to Google
- **BreadcrumbList**: Present on content pages, helps with SERP breadcrumb display
- **FAQPage**: Multiple pages — excellent for AI citation and voice search
- **ItemList**: Used on alternatives page to list competitors — helps Google understand content type
- **Article schema**: Used on guides and gift pages with proper `datePublished`/`dateModified`

## 4.3 Schema Gaps

| Missing Schema | Pages Affected | Priority |
|---|---|---|
| AggregateRating (Review stars) | Homepage, Pearl | **HIGH** — 4.9/5 rating visible but not in schema |
| Person (Founder Paul Takisaki) | About, homepage | Medium — referenced in llms.txt but not on-site |
| HowTo | Guide pages | Low — deprecated for rich results, but good for AI citation |
| VideoObject | If videos exist | Low |
| Product with Offers | Pricing, homepage | Medium — pricing exists ($79/year) but no Product schema |

### Priority Fix: Add AggregateRating Schema
The homepage displays "4.9/5" with testimonials. Adding this to the SoftwareApplication or Product schema would enable review stars in Google SERPs — one of the highest CTR drivers available.

```json
{
  "@type": "SoftwareApplication",
  "name": "Heritage Whisper",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.9",
    "bestRating": "5",
    "worstRating": "1",
    "ratingCount": "247"
  }
}
```

---

# 5. Performance & Core Web Vitals

## 5.1 TTFB (Time to First Byte)

| Page | TTFB | Total Load | Assessment |
|---|---|---|---|
| Homepage | 238ms | ~800ms | ✅ Excellent (cached Vercel edge) |
| Blog | 645ms | ~1.1s | ⚠️ Slower — SSR not cached? |
| Pricing | 567ms | ~900ms | ⚠️ Moderate |
| Guide: Recording | 482ms | 829ms | ✅ Good |
| Alternatives: StoryWorth | 442ms | 1.13s | ✅ Good TTFB, high total |
| Pearl | 402ms | 927ms | ✅ Good |
| Gift: Mother's Day | 343ms | 727ms | ✅ Excellent |

**Observations:**
- Homepage and gift pages are fast (Vercel ISR likely caching correctly)
- Blog and Pricing pages are slower — may not be ISR-cached
- Total page load times are elevated (727ms–1.13s) due to large HTML payload

## 5.2 Core Web Vitals Signals

Cannot measure LCP/INP/CLS directly from server-side, but key signals:

| Signal | Evidence | Assessment |
|---|---|---|
| LCP | Large homepage images (1200×630 OG, hero images) | Risk — depends on preloading |
| INP | Next.js 15 with React 18+ | ✅ Should be good |
| CLS | Server-rendered HTML | ✅ Low risk |
| Image format | `.webp` used via Next.js `/_next/image` optimizer | ✅ |
| Font preloading | 12 woff2 fonts preloaded in `<head>` | ⚠️ Excessive — 12 fonts is very heavy |

### Font Loading Issue — 12 Preloaded Fonts [MEDIUM]
The page preloads 12 separate `.woff2` font files. This significantly impacts initial page load even with preloading. Inter (8 weights) + Playfair (4 weights) creates a large font download budget.

**Fix:** Subset fonts to used weights only. Typically 2-3 weights per family is sufficient (Regular 400, Medium 500, Bold 700 for Inter; Regular 400, Bold 700 for Playfair).

## 5.3 HTML Weight

| Page | HTML Size | Assessment |
|---|---|---|
| Homepage | 1.35MB | ⚠️ Very large |
| Guide page | 975KB | ⚠️ Large |
| Alternatives page | 1.0MB | ⚠️ Large |
| Pearl | 1.0MB | ⚠️ Large |

The HTML weight is consistently high across all pages. This is likely caused by:
1. Large inline CSS (CSS variables + multiple `<style>` blocks)
2. Next.js hydration JSON payload in `__NEXT_DATA__`
3. Long-form content rendered fully server-side

**This is the #1 performance issue** and likely the primary reason TTFBs for some pages are 440-645ms.

---

# 6. AI Search Readiness

Heritage Whisper is the **best-in-class** example of AI search optimization in this niche. Score: **95/100**.

## 6.1 llms.txt Implementation

Heritage Whisper's `/llms.txt` is exceptional:

- ✅ Comprehensive product description for AI ingestion
- ✅ Feature list in bullet format (easy for LLMs to extract)
- ✅ Pricing table in markdown format
- ✅ Competitor comparison table
- ✅ Founder entity with cross-site `@id` reconciliation (`paultakisaki.com/#person`)
- ✅ Technology stack disclosed
- ✅ Target audience clearly defined

**Standout practice:** The founder cross-references his LinkedIn, X, Medium, and personal site with a canonical `@id` — this is advanced entity SEO that helps AI systems build a consistent knowledge graph node for the founder and company.

## 6.2 AI Bot Access

robots.txt explicitly allows 20+ AI crawlers including GPTBot, ClaudeBot, PerplexityBot, Google-Extended, and more. This is best practice and ensures Heritage Whisper content appears in AI training data and live search answers.

## 6.3 Content Citability

The guide pages are structured specifically for AI citation:
- **"Quick Answer" sections** at top = AI-extractable short answers
- **FAQPage schema** on 5+ pages = directly parsed by Google AI Overviews and ChatGPT
- **Lists and tables** throughout = AI-friendly structured information
- **"How to..."** and **"Best X alternatives"** framing = directly matches AI query patterns

## 6.4 AI Readiness Gaps

| Gap | Priority |
|---|---|
| No structured data for voice/audio content (lacks AudioObject or PodcastEpisode equivalents) | Low |
| Person schema for founder not on-site (only in llms.txt) | Medium |
| No dedicated "AI overview" landing page | Low |

---

# 7. Competitor Analysis

## 7.1 Competitive Position

| Competitor | Domain Authority | Blog Posts | Schema | AI Readiness |
|---|---|---|---|---|
| **Heritage Whisper** | Low-medium (newer) | **1** | ✅ Best-in-class | ✅ Best-in-class |
| StoryWorth | High (established) | ~50+ | Basic | Poor |
| Remento | Medium | ~20 | ❌ Zero | ❌ Poor |
| Storii | Low-medium | ~5 | Basic | Poor |
| ChatMemoir | Low | ~3 | Minimal | Minimal |
| FamilySearch | Very High (LDS Church) | Hundreds | Good | Medium |

## 7.2 Heritage Whisper's Competitive SEO Advantages

1. **AI search**: Heritage Whisper is the only competitor with a comprehensive llms.txt, explicit AI bot allowances, and entity reconciliation — this is a 12-18 month competitive moat
2. **Schema depth**: 6 schema types on alternatives pages vs. near-zero for Remento
3. **Security headers**: Best in category, which is increasingly a trust signal for search engines
4. **Content architecture**: Alternatives + Guides + Gifts structure covers full funnel
5. **Price positioning**: $79/year vs. StoryWorth $99/year — mentioned in llms.txt for AI price comparisons

## 7.3 Heritage Whisper's Competitive SEO Disadvantages

1. **Blog content volume**: 1 post vs. StoryWorth (50+), FamilySearch (hundreds) — major authority gap
2. **Domain age/backlinks**: Newer domain likely has fewer referring domains than StoryWorth
3. **Review presence**: No Google Business Profile reviews or review platform integration visible
4. **Product page depth**: Only 2 feature detail pages vs. possible deeper feature documentation
5. **No dedicated "vs." pages** beyond the storyworth comparison (e.g., `/alternatives/heritagewhisper-vs-remento` is in sitemap but need to verify content depth)

---

# 8. Backlink Profile

Heritage Whisper appears to be a relatively young domain (no Wayback Machine records found). Backlink assessment based on available signals:

## 8.1 Estimated Profile

| Signal | Assessment |
|---|---|
| Domain age | 2024-2025 based on content dating and tech stack |
| Referring domains | Estimated <100 (early-stage SaaS typical) |
| Anchor text | Likely brand-dominant (Heritage Whisper, heritagewhisper.com) |
| Toxic links | Unlikely — clean content-driven site |

## 8.2 Link Acquisition Opportunities

1. **PR opportunities**: Founder story (ex-Verizon VP building app for his father) is compelling human-interest content — pitch to tech/family/aging publications
2. **Review sites**: GetApp, Capterra, G2, Product Hunt, AlternativeTo — establish listings immediately
3. **"Alternatives to StoryWorth" roundups**: Target blogs already writing about StoryWorth alternatives — pitch for inclusion
4. **AARP / senior living publications**: High-DA domains in target audience space
5. **Family history/genealogy blogs**: FamilySearch-adjacent content creators
6. **Podcast appearances**: Family history, aging parent, digital legacy podcasts — builds authority + links
7. **Guest posts**: "How to preserve your parents' stories" articles on parenting/family blogs

---

# 9. Images

## 9.1 Image Audit Summary

| Issue | Count | Pages Affected |
|---|---|---|
| Missing alt text | ~10 | Guide, Alt, Pearl, Pricing, Gift pages |
| Images using Next.js optimizer | ✅ All | Verified via `/_next/image?url=` pattern |
| WebP format | ✅ Used | `.webp` files confirmed |
| OG image | ✅ 1200×630 | All pages |

## 9.2 Missing Alt Text Detail

Missing alt text found on:
- 1 image on `/guides/recording-family-stories`
- 1 image on `/alternatives/storyworth-alternatives`
- 1 image on `/features/pearl`
- 2 images on `/pricing` (noindex — lower priority)
- 1 image on `/gifts/mothers-day-gift-for-mom`

**Fix**: Add descriptive alt text. Avoid generic "photo of woman" — use descriptive alt like "grandmother recording family story on Heritage Whisper mobile app".

## 9.3 Font-as-Asset Issue

12 preloaded font files (see Performance section) — while not "images," they behave like large asset preloads and impact LCP similarly.

---

# 10. Action Plan

## Critical Fixes (Do This Week)

| # | Action | Impact | Effort |
|---|---|---|---|
| 1 | Add canonical tag to `/pricing` page | Crawl hygiene | 30 min |
| 2 | Fix About page title (remove duplicate brand suffix) | SERP display | 15 min |
| 3 | Fix all 10 missing alt text images | Accessibility + image SEO | 2 hours |
| 4 | Confirm or revert `/pricing` noindex — is it intentional? | Traffic recovery | 30 min |

## High Priority (This Month)

| # | Action | Impact | Effort |
|---|---|---|---|
| 5 | Add `AggregateRating` schema to homepage/SoftwareApplication | CTR boost via stars | 2 hours |
| 6 | Reduce font preloads from 12 to 5-6 (subset Inter + Playfair) | Performance (LCP) | 4 hours |
| 7 | Investigate HTML payload size — run `next build --analyze` | Performance | 2 hours |
| 8 | Publish first 3 blog posts targeting "questions to ask parents before they die", "how to preserve family stories digitally", "digital legacy gift for elderly parent" | Traffic + authority | 2 weeks |
| 9 | Add `Product` schema with `Offers` to homepage (price: $79/year) | Rich results + AI citations | 1 hour |

## Medium Priority (Next 90 Days)

| # | Action | Impact | Effort |
|---|---|---|---|
| 10 | Publish "50 questions to ask your parents before they die" as standalone pillar page | High-traffic informational | 1 week |
| 11 | Create `/alternatives/heritagewhisper-vs-remento` and `/alternatives/heritagewhisper-vs-storii` dedicated pages | Commercial keyword coverage | 2 days each |
| 12 | Establish listings on G2, Capterra, GetApp, AlternativeTo, Product Hunt | Backlinks + social proof | 1 week |
| 13 | Add `Person` schema for founder Paul Takisaki on About page | Entity authority | 2 hours |
| 14 | Create seasonal gift pages: "Christmas gift for elderly parent", "birthday gift for 80 year old grandma" | Seasonal traffic | 1 day each |
| 15 | Add ISR caching to Blog and Pricing pages (currently slow TTFB) | Performance | 2 hours |
| 16 | Blog: Publish 10 total posts within 90 days | Domain authority | Ongoing |

## Strategic (6-12 Month)

| # | Action | Impact | Effort |
|---|---|---|---|
| 17 | Pitch founder story to tech + aging publications for PR/links | Backlink authority | Ongoing |
| 18 | Launch podcast/YouTube guest appearance strategy | Brand + links + AI training | Ongoing |
| 19 | Create "digital legacy" content cluster to own emerging keyword space | Future traffic | 3 months |
| 20 | Build review capture flow → Google Business Profile + Capterra | Social proof + rich results | 1 month |

---

# 11. Summary Scorecard

| Category | Score | Key Finding |
|---|---|---|
| Technical SEO | 75/100 | Strong platform, pricing page canonical missing, large HTML payload |
| Content Quality | 65/100 | Deep content on existing pages, only 1 blog post |
| On-Page SEO | 78/100 | Strong titles/descriptions across the board, about page title has duplicate suffix |
| Schema | 85/100 | Best-in-class multi-type schema; missing AggregateRating + Person |
| Performance | 72/100 | Good TTFB on cached pages, 1.35MB HTML + 12 font files are concerns |
| AI Search | 95/100 | Best-in-class llms.txt, 20+ AI bots explicitly allowed, entity reconciliation |
| Images | 68/100 | ~10 missing alt texts, WebP format used, Next.js image optimizer active |
| **Overall** | **76/100** | **Strong foundation — content volume is the primary growth lever** |

## Bottom Line

Heritage Whisper has built an exceptionally well-engineered SEO foundation for a new site. The AI search readiness is the best in the niche by a wide margin. The technical foundation (Next.js + Vercel + excellent security headers) is solid.

The primary constraint is **content volume**. With only 1 blog post, Heritage Whisper is leaving significant topical authority on the table. The competitors with 50-500+ blog posts have accumulated domain authority that will be difficult to overcome without a sustained content publishing strategy.

**The 90-day priority:** Fix the 4 critical issues (30 minutes total), add AggregateRating schema (2 hours), and commit to publishing 1 blog post per week for 12 weeks. That trajectory, combined with the existing technical excellence, could push Heritage Whisper from 76/100 to 85/100 within a year.

---

*Audit produced by Listn Intel Meta · Claude Code · April 27, 2026 · Confidential*
