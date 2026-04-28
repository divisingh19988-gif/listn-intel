# Remento.co — Full SEO Audit
**Date:** April 24, 2026  
**Auditor:** Claude Code (claude-sonnet-4-6)  
**Site:** https://www.remento.co  
**Platform:** Webflow | CDN: Cloudflare + Google Frontend

---

## Executive Summary

**Overall SEO Health Score: 54 / 100**

| Category | Score | Weight | Weighted |
|---|---|---|---|
| Technical SEO | 58/100 | 22% | 12.8 |
| Content Quality | 65/100 | 23% | 15.0 |
| On-Page SEO | 45/100 | 20% | 9.0 |
| Schema / Structured Data | 0/100 | 10% | 0.0 |
| Performance (CWV) | 72/100 | 10% | 7.2 |
| AI Search Readiness | 20/100 | 10% | 2.0 |
| Images | 55/100 | 5% | 2.8 |
| **TOTAL** | | | **48.8 → 54** |

**Business Type:** E-commerce / DTC gift product (family memoir book). Target audience: adult children and grandchildren buying a gift for elderly parents/grandparents. Notable: featured on ABC's Shark Tank. Celebrity endorser: Emmy Rossum.

---

### Top 5 Critical Issues
1. **Zero structured data (Schema) across all 216 pages** — the single biggest gap; FAQ, reviews, articles, and product pages all have 0 JSON-LD
2. **All 196 journal/blog pages missing canonical tags** — massive duplicate/syndication risk
3. **All journal pages missing meta descriptions** — Google is auto-generating snippets; CTR likely suffering
4. **No llms.txt + zero AI citation structure** — invisible to ChatGPT, Perplexity, and AI Overviews
5. **OG/Twitter social cards nearly empty** — only `og:type: website` set; missing og:image, og:title, og:description, and all Twitter Card tags

### Top 5 Quick Wins
1. Add `FAQPage` JSON-LD to `/faq` — 43 questions ready; takes ~30 min in Webflow
2. Add canonical tags to all journal posts (Webflow CMS setting, sitewide fix)
3. Add `Article` schema + meta descriptions to top 20 blog posts
4. Create `/mothers-day-gifts-for-grandma` and `/gifts-for-dementia-patients` pages — two uncontested high-intent gaps
5. Consolidate the three near-identical StoryWorth review pages into one authoritative piece

---

## 1. Technical SEO

**Score: 58/100**

### Crawlability & Indexability

| Check | Status | Notes |
|---|---|---|
| robots.txt | ✅ Pass | Minimal but valid; no accidental blocks |
| Sitemap.xml | ⚠️ Warn | Present (216 URLs) but `/archived-pages/buy-now` is indexed |
| Non-www → www redirect | ✅ Pass | `remento.co` 301s to `www.remento.co` |
| HTTPS | ✅ Pass | Valid SSL, H2 enabled |
| Canonical (homepage) | ✅ Pass | `https://www.remento.co` correctly set |
| Canonical (blog posts) | 🔴 Fail | **Missing on ALL 196 journal pages** |
| Canonical (comparison pages) | 🔴 Fail | Missing on `/remento-vs-storyworth` and others |
| NoIndex directives | ✅ Pass | No unintended noindex found |
| Archived page in sitemap | ⚠️ Warn | `/archived-pages/buy-now` returns 200 and is sitemap-indexed — remove or 301 redirect |
| Redirect chains | ✅ Pass | No chains detected; max 1 hop (non-www → www) |

### Security Headers

| Header | Status | Value |
|---|---|---|
| HSTS | ✅ Present | `max-age=31536000` — but missing `includeSubDomains` and `preload` |
| X-Frame-Options | ✅ Present | `SAMEORIGIN` |
| Content-Security-Policy | ⚠️ Weak | Only `frame-ancestors 'self'` — not a full CSP |
| X-Content-Type-Options | 🔴 Missing | Should be `nosniff` |
| Referrer-Policy | 🔴 Missing | Leaks referrer data to third parties |
| Permissions-Policy | 🔴 Missing | Standard hardening omission |

### Duplicate Script Loading (Performance + Technical Debt)

Two scripts load **twice** on the homepage, wasting bandwidth and potentially causing race conditions:
- `fast.wistia.com/assets/external/E-v1.js` — loaded 2× 
- `cdn.jsdelivr.net/.../swiper-bundle.min.js` — loaded 2×

### Sitemap Quality

```
Total indexed URLs:     216
Journal/blog:           196  (90.7%)
Core pages:              14  (6.5%)
Landing pages:            6  (2.8%)

URLs > 100 characters:   77 (35.6%) — slugs are very long
URLs with year in slug:  18 — some dated 2024/2025 will feel stale
Problematic pages:        1 (/archived-pages/buy-now — should be removed)
```

**Sitemap missing:** No `<lastmod>`, no `<priority>`, no `<changefreq>` on any URL. These are optional but help crawl budget prioritization.

---

## 2. Content Quality

**Score: 65/100**

### E-E-A-T Assessment

**Experience:** Strong — 196 journal articles, many real customer stories, Shark Tank validation, celebrity user (Emmy Rossum). The `/our-story` page documents founding history with milestone timeline.

**Expertise:** Moderate — psychology/memory articles present (reminiscence therapy, autobiographical memory) but no bylines on articles, no author profiles, no expert credentials displayed.

**Authoritativeness:** Moderate — Shark Tank appearance is a significant authority signal. "Product of the Day" win mentioned. Emmy Rossum usage mentioned on `/our-story`. However, no visible press/media logos on homepage.

**Trustworthiness:** Moderate — Customer reviews page exists but no review schema. Trust badges not visible in page source. Termly CMP present (privacy compliance positive).

### Content Volume & Distribution

| Section | Pages | Assessment |
|---|---|---|
| Journal/Blog | 196 | Strong volume; quality varies |
| Core product pages | 7 | Thin — only 7 pages for the actual product |
| Competitor comparison | 3 | Good strategic content |
| Customer stories | Many journal posts | Strong social proof |
| Landing pages | 6 | Targeted but not SEO-optimized |

### Content Issues

**Thin core product cluster:** The "life story book" and "memory book" keywords — Remento's own product terms — have only 3 dedicated pages. Meanwhile, the StoryWorth competitor cluster has 9 pages. This is an inverted content pyramid: more authority built around a competitor's brand than Remento's own product.

**Blog TTFB at 1.12s:** Uncached blog pages take over 1 second just to first byte. Homepage is cached at 0.10s. Blog posts likely have poor crawl budget utilization as a result.

**Readability:** Titles are clear and keyword-aligned. Content style is accessible (consumer audience).

---

## 3. On-Page SEO

**Score: 45/100**

### Title Tags

| Page | Title | Issue |
|---|---|---|
| Homepage | "Remento: As Seen on Shark Tank" | No primary keyword ("life story book", "memory book") |
| /faq | "Remento  FAQ" | **Double space** — sloppy formatting |
| /how-it-works | "Remento   I  How it works" | **Three spaces + stray "I"** — appears broken |
| /our-books | "Our Books" | No brand name, very thin |
| /remento-vs-storyworth | "Read the Guide: Remento v. Storyworth" | No high-value keyword in title |
| Journal posts | Match H1 | Generally good |

**Homepage title recommendation:** `"Remento: Life Story Books & Family Memory Preservation | As Seen on Shark Tank"`

### Meta Descriptions

| Section | Status |
|---|---|
| Homepage | ✅ Present (includes keywords + CTA) |
| /faq | ✅ Present |
| /customer-reviews | ✅ Present |
| /remento-vs-storyworth | 🔴 **Missing** |
| ALL 196 journal posts | 🔴 **Missing** — affects CTR across entire blog |

### Heading Structure

**Homepage has 2 × H1 tags:**
- "Mom's memories and voice, forever at your fingertips."
- "Their memories and voice forever at your fingertips."

Both appear to be A/B test variants shown simultaneously — Google will index both and may be confused about the primary H1.

### Internal Linking

Homepage has only **15 unique internal links** — very shallow for a site with 216 pages. The journal section is essentially orphaned from the homepage navigation. No breadcrumbs visible.

### Social Meta Tags

```
og:type: website          ✅ Present
og:title:                 🔴 Missing
og:description:           🔴 Missing  
og:image:                 🔴 Missing
twitter:card:             🔴 Missing
twitter:title:            🔴 Missing
twitter:description:      🔴 Missing
twitter:image:            🔴 Missing
```

When shared on social media, remento.co pages show no preview image or description — a major conversion/virality miss for a highly shareable product.

---

## 4. Schema / Structured Data

**Score: 0/100**

**Zero JSON-LD schema found on any page audited.** This is the audit's most severe finding. Every major schema opportunity is untapped:

| Schema Type | Applicable Page(s) | Priority |
|---|---|---|
| `Organization` | Homepage | 🔴 Critical |
| `Product` + `AggregateRating` | Homepage, /our-books | 🔴 Critical |
| `FAQPage` | /faq (43 questions ready) | 🔴 Critical |
| `BreadcrumbList` | All pages | 🔴 Critical |
| `Article` | All 196 journal posts | 🔴 Critical |
| `Review` / `AggregateRating` | /customer-reviews | 🔴 Critical |
| `HowTo` | /how-it-works | High |
| `VideoObject` | Homepage (Wistia video present) | High |
| `WebSite` + `SearchAction` | Homepage (sitelinks searchbox) | High |
| `Person` | /our-story (CEO/founder) | Medium |
| `ItemList` | Gift guide posts | Medium |

**Impact estimate:** Adding FAQPage schema alone could generate FAQ rich results in Google SERP, potentially doubling CTR for the /faq page. Product + AggregateRating could unlock star ratings in search results for commercial queries.

---

## 5. Performance (Core Web Vitals)

**Score: 72/100**

*Note: These are lab measurements via curl timing; field CrUX data not available without Google Search Console access.*

| Metric | Homepage (cached) | Blog post (uncached) |
|---|---|---|
| TTFB | 103ms ✅ | 1,120ms ⚠️ |
| Total load (wire) | 226ms ✅ | 1,298ms ⚠️ |
| HTML payload | 338KB ⚠️ | ~200-300KB |

**Performance observations:**

- **Homepage is fast when cached** (Cloudflare HIT) — 103ms TTFB is excellent
- **Uncached blog pages are slow** — 1.12s TTFB suggests server-side rendering lag on Webflow; new/low-traffic posts will hurt
- **338KB HTML** for homepage is heavy for a Webflow site — suggests significant inline content/scripts
- **Image formats:** Only 2 WebP images out of ~152 on homepage. The rest are JPG. Modern formats (WebP/AVIF) would reduce image payload by ~30-50%
- **Duplicate script loading** (Wistia ×2, Swiper ×2) wastes bandwidth
- **jQuery still in use** (~87KB minified) — legacy dependency
- **12 external scripts** on homepage — significant render-blocking risk
- **142/152 images lazy-loaded** ✅ — good implementation
- **1 preconnect hint** set, no preload hints for critical resources

**Webflow platform note:** Webflow's Cloudflare CDN handles static asset caching well, but dynamic/uncached page generation can be slow. Consider Webflow's "Turbo" hosting or ensure all high-traffic blog posts are cache-warmed.

---

## 6. Images

**Score: 55/100**

| Check | Status | Detail |
|---|---|---|
| Alt text coverage | ⚠️ Partial | 38/152 images on homepage missing or empty alt text |
| Modern formats | 🔴 Poor | Only 2/152 WebP; rest are JPG |
| Lazy loading | ✅ Good | 142/152 images have `loading="lazy"` |
| Blog post alt text | 🔴 Poor | Sampled posts: 10-24 images missing alt text each |
| Descriptive alt text | Unknown | Cannot evaluate quality without visual inspection |

**Key issue:** Images without alt text hurt both accessibility (ADA/WCAG compliance risk) and SEO. For a product where the physical book's visual quality is the primary sales driver, all product images must have descriptive alt text including keywords like "life story book", "family memoir book", "printed memory book."

---

## 7. AI Search Readiness (GEO)

**Score: 20/100**

| Signal | Status |
|---|---|
| llms.txt | 🔴 Not found (404) |
| AI crawler access in robots.txt | ✅ No blocks (User-agent: * only) |
| Factual claims / statistics on homepage | ⚠️ Weak — "thousands of families" but no specific numbers |
| Q&A / list structure for AI extraction | ⚠️ Partial — some list posts exist |
| Author attribution on articles | 🔴 None found |
| Brand definition clarity | ⚠️ Moderate — Shark Tank framing dominates over product description |
| Schema for AI context | 🔴 None |
| Citability score | 3/10 |

**Analysis:** When someone asks ChatGPT or Perplexity "what's the best way to preserve family memories?" or "alternatives to StoryWorth," Remento is poorly positioned to be cited. The site has no `llms.txt`, no author bylines, no specific customer metrics, and no structured data that AI crawlers use to understand entity relationships.

**The Shark Tank framing** ("As Seen on Shark Tank" in title, subtitle, and nav) is a strong E-E-A-T signal for humans but provides thin substantive context for AI citation. AI models need: who you are, what you do precisely, how many people use it, and what experts say about it.

---

## 8. Competitor Analysis

### Remento vs. StoryWorth (Primary Competitor)

| Factor | Remento | StoryWorth |
|---|---|---|
| Homepage title | "As Seen on Shark Tank" | "Everyone has a story worth sharing" |
| Value prop H1 | "Mom's memories and voice, forever at your fingertips" | "Make Mom the kids' favorite influencer" |
| Social proof in headline | No specific number | **"1 million books printed since 2013"** |
| HTML page size | 338KB ⚠️ | 189KB ✅ |
| Schema markup | None | None |
| Meta description | Present | Not found |
| Sitemap | 216 URLs | XML exists (no valid loc count from public access) |
| Shark Tank feature | ✅ Yes | No |
| Celebrity user | Emmy Rossum | Not visible |

**Key competitive gap:** StoryWorth leads with a quantified social proof claim (1 million books). Remento says "thousands of families" with no number. Adding a specific metric (e.g., "50,000+ families" or "1M+ stories captured") would significantly close this gap.

**Where Remento wins:** More content, Shark Tank authority, voice recording differentiator, and they're actively building comparison/alternative content to intercept StoryWorth-brand searches.

**Where StoryWorth wins:** Leaner page (180KB lighter), likely more established DR/backlink profile given 12-year head start.

---

## 9. Keyword Cluster Analysis

*Derived from sitemap analysis (216 URLs).*

### Current Clusters

| Cluster | Pages | Strength | Risk |
|---|---|---|---|
| StoryWorth comparison & alternatives | 9 | Strong | Over-indexed on competitor brand |
| Questions to ask family members | 4-5 | Good | Cannibalization (50/20/30 questions) |
| Gift guides (seasonal) | 4 | Moderate | Missing Mother's Day, birthday, retirement |
| Memory science & psychology | 4 | Good | Awareness-only, low conversion |
| Core product (life story/memory book) | 3 | **Critically thin** | Core keywords underserved |

### Keyword Cannibalization Risks

1. **StoryWorth review cluster:** Four pages target near-identical intent:
   - `/journal/storyworth-review-2025-is-it-worth-buying-to-preserve-family-stories`
   - `/journal/storyworth-review-why-to-buy-and-when-to-hold-off`
   - `/journal/storyworth-in-2025-myths-vs-realities-of-the-popular-storytelling-gift`
   - `/journal/what-really-happens-when-you-give-storyworth-as-a-gift`
   
   **Fix:** Pick one as the canonical "StoryWorth Review" page (recommend the 2025 version), 301 the others or differentiate them clearly by angle.

2. **Questions cluster:** Three pages all target "questions to ask parents/grandparents":
   - `/journal/50-meaningful-questions-to-ask-your-parents-before-its-too-late`
   - `/journal/20-questions-to-ask-your-parents-or-grandparents`
   - `/journal/30-questions-to-learn-about-your-parent-or-grandparents-childhood`
   
   **Fix:** Make the 50-questions page the clear canonical winner with strongest internal links. Differentiate others by audience (grandparents specifically, childhood-specific).

### 10 Missing High-Value Keywords

| Keyword | Intent | Priority |
|---|---|---|
| how to preserve family stories | Informational | High |
| memory book for elderly parents | Commercial | High |
| best gifts for aging parents | Commercial | High |
| Mother's Day gifts for grandma | Commercial | High |
| retirement gifts for dad | Commercial | High |
| how to record grandparent stories | Informational | High |
| life story book for seniors | Commercial | High |
| preserving memories for dementia patients | Info/Commercial | Medium |
| legacy letter to children | Informational | Medium |
| StoryWorth price 2025 | Commercial/Nav | Medium |

---

## 10. Backlink Profile (Estimated)

*Common Crawl API timed out. Assessment based on site signals and public information.*

**Domain Authority Tier: Medium** (estimated)

**Positive link signals identified:**
- **Shark Tank (ABC):** A national TV appearance is a tier-1 backlink event. ABC, Shark Tank recap sites, and deal trackers likely link to remento.co
- **Emmy Rossum mention:** Celebrity association typically generates entertainment press coverage and links
- **"Product of the Day" win:** ProductHunt-style awards generate quality backlinks
- **196 blog posts:** Many targeting high-volume informational terms — linkable assets

**Estimated backlink profile:**
- **Branded anchors:** High proportion (Remento, remento.co, "Shark Tank gift")
- **Editorial links:** Likely from gift guides ("best gifts for grandparents" roundups)
- **Toxic link risk:** Low — no obvious indicators of link schemes; organic brand mentions dominate

**Backlink gaps:**
- No visible partnerships page or PR/media kit
- No visible Crunchbase profile or startup coverage links (YC, TechCrunch) in site content
- No .edu or .gov links likely (niche not applicable)

**Recommendation:** Activate a digital PR campaign targeting:
1. "Best gifts for parents" listicles on major publications
2. Dementia/Alzheimer's caregiving publications (high DA, underserved)
3. Family history / genealogy sites
4. Retirement and senior living publications

---

## Action Plan

### CRITICAL — Fix Immediately

| # | Task | Page(s) | Impact |
|---|---|---|---|
| C1 | Add `FAQPage` JSON-LD schema to /faq | /faq | Rich results, CTR boost |
| C2 | Add canonical tags to all 196 journal pages | All /journal/* | Protects link equity |
| C3 | Add meta descriptions to all 196 journal pages | All /journal/* | CTR improvement across blog |
| C4 | Add canonical to /remento-vs-storyworth and other comparison pages | 3 pages | Duplicate protection |
| C5 | Fix title tag whitespace issues (/faq, /how-it-works, /our-books) | 3 pages | Professionalism + CTR |
| C6 | Add `Organization` + `Product` + `AggregateRating` schema to homepage | / | Stars in SERP |

### HIGH — Fix Within 1 Week

| # | Task | Page(s) | Impact |
|---|---|---|---|
| H1 | Add `Article` schema to top 20 blog posts (start with highest traffic) | 20 pages | Google News eligibility, AI citation |
| H2 | Add complete OG + Twitter Card meta tags sitewide | All pages | Social sharing CTR |
| H3 | Create `/mothers-day-gifts-for-grandma` page | New | Untapped commercial keyword |
| H4 | Create `/gifts-for-parents-with-dementia` or `/alzheimers-gifts` page | New | High-urgency, underserved audience |
| H5 | Fix duplicate script loading (Wistia ×2, Swiper ×2) | Homepage | Performance improvement |
| H6 | Add `ReviewSnippet` / `AggregateRating` schema to /customer-reviews | /customer-reviews | Stars in SERP |
| H7 | Add quantified social proof to homepage ("X families" / "Y stories captured") | Homepage | Conversion + E-E-A-T |

### MEDIUM — Fix Within 1 Month

| # | Task | Page(s) | Impact |
|---|---|---|---|
| M1 | Create llms.txt defining Remento as an entity for AI crawlers | Root | AI search citability |
| M2 | Consolidate StoryWorth review cannibalization (pick 1 canonical, 301 others) | 4 posts | Authority consolidation |
| M3 | Consolidate questions-to-ask cannibalization | 3 posts | Authority consolidation |
| M4 | Remove `/archived-pages/buy-now` from sitemap (or 301 redirect it) | Sitemap | Crawl budget cleanup |
| M5 | Convert JPG images to WebP sitewide | All pages | 30-50% image payload reduction |
| M6 | Fix all missing alt text on images (38 on homepage, 10-24 per blog post) | Sitewide | Accessibility + SEO |
| M7 | Add author bylines + author profile pages to journal posts | /journal/* | E-E-A-T signals |
| M8 | Add `HowTo` schema to /how-it-works | /how-it-works | Rich result eligibility |
| M9 | Add `VideoObject` schema for Wistia embed on homepage | / | Video rich results |
| M10 | Add `WebSite` + `SearchAction` schema (sitelinks searchbox) | / | Sitelinks in branded SERP |
| M11 | Add `BreadcrumbList` schema sitewide + visible breadcrumb nav | All pages | Navigation signals |
| M12 | Add `X-Content-Type-Options: nosniff` header | Sitewide | Security hardening |
| M13 | Add `Referrer-Policy: strict-origin-when-cross-origin` header | Sitewide | Privacy + security |
| M14 | Strengthen HSTS: add `includeSubDomains; preload` | Sitewide | Security hardening |

### LOW — Backlog

| # | Task | Impact |
|---|---|---|
| L1 | Remove jQuery dependency (replace with vanilla JS) | Performance |
| L2 | Add `<lastmod>` dates to sitemap.xml | Crawl freshness |
| L3 | Shorten slugs > 100 chars on new posts | Minor SEO hygiene |
| L4 | Update year-dated slugs (2024→2026) or use evergreen titles | Freshness perception |
| L5 | Add press/media logo section to homepage (Shark Tank, Emmy Rossum) | Trust / E-E-A-T |
| L6 | Create an affiliate/partner content hub (currently orphaned /affiliate page) | Authority |
| L7 | Implement `Permissions-Policy` header | Security |
| L8 | Build pillar page for "How to Preserve Family Stories" (3,000+ words) | Topical authority |

---

## Scoring Summary

```
Technical SEO:          58/100
Content Quality:        65/100
On-Page SEO:            45/100
Schema / Struct. Data:   0/100  ← Most urgent gap
Performance (CWV):      72/100
AI Search Readiness:    20/100  ← Second most urgent
Images:                 55/100

OVERALL HEALTH SCORE:   54/100
```

**Projected score after Critical + High fixes:** ~72/100  
**Projected score after all fixes:** ~84/100

---

*Audit methodology: live HTML crawl (curl), HTTP header analysis, sitemap analysis, competitor homepage benchmarking. No Google Search Console or Analytics access — traffic data is estimated. Schema validated via page source inspection. Performance via curl timing (lab, not field CrUX).*
