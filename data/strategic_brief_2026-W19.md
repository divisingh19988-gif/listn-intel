# Listn — Competitor Ad Intelligence Report

**Generated:** 2026-05-13  
**Data source:** `data/ads_scraped_latest.json`  
**Model:** `claude-sonnet-4-6`  

---

# Listn Competitive Intelligence Report
**Meta Ad Library Analysis | Fetched: 2026-05-12**

---

## A Note on the Competitive Set

Before diving in: one competitor in this dataset — **"Enna"** — returned an irrelevant result (a B2B henna/herbal powder supplier). This is a scraping artifact, not a real competitor. It has been excluded from all analysis. **"Keepsake"** in this dataset is a photo printing/framing app, not a life story product — it's directionally adjacent but not a direct competitor. It's included for CTA and longevity observations only. The meaningful competitors are: **Remento, Meminto, StoryWorth, and StoryKeeper.**

---

## 1. Messaging Themes

### Remento
Remento runs the most sophisticated and highest-volume ad operation in the set. Their messaging clusters around three consistent pillars:

| Pillar | Representative Copy |
|---|---|
| **Effortlessness / No-tech** | > "No typing. No passwords. No tech stress." |
| **The homework objection** | > "Give your parent something meaningful… not homework." / "Because writing, typing, logins, and tech make it feel like homework." |
| **Legacy as gift** | > "Make history for your family." / "His story is YOUR story too." |

**Additional observations:**
- Heavy use of the **"80% of life story books never get made"** statistic as a fear/credibility lever
- **Social proof stacking**: Shark Tank appearance, Mark Cuban quote, Tim Ferriss testimonial, and user testimonial ("My kids see their grandparents as heroes now!") all deployed as ad hooks
- The **physical book** (hardcover, QR codes, interactive) is consistently the hero product — the tangible artifact is the value proposition, not the recording experience itself
- Framing is almost always **gifter-to-recipient**: the buyer is an adult child; the storyteller is an aging parent

### Meminto
Meminto's messaging is more **discount-driven and process-forward** than emotionally sophisticated:

| Pillar | Representative Copy |
|---|---|
| **Price anchoring** | > "Give your loved ones a gift that lasts decades… now $69 (reg. $99). Save $30" |
| **Mortality/legacy lite** | > "Gift immortality" / "A gift that stays" / "Your story will stay forever" |
| **Question-driven process** | > "52 personal questions to start" / "With each answer, your book grows" |

**Additional observations:**
- Copy leans on **specific numbers** (52 questions, $69, $75 value for $9) — a conversion-optimization mindset rather than an emotional storytelling one
- "Gift immortality" is their boldest phrase but it's used casually, without being developed into a real emotional narrative
- Mothers Day promotions dominate their recent (April–May 2026) ads — they are very holiday-reactive
- The webinar ad is an outlier — Meminto appears to be testing B2B/creator acquisition alongside consumer gifting

### StoryWorth
Only one ad in the dataset (from 2023), but it establishes their foundational voice:

| Pillar | Representative Copy |
|---|---|
| **Validation / "her stories matter"** | > "Show her that her stories matter ❤️" |
| **Structured simplicity** | > "We send weekly questions. She simply replies by email with a story." |

**Additional observations:**
- The email-reply mechanic is their core differentiator — low friction for the storyteller, but it's **text-based**, which is a significant vulnerability compared to voice-first products
- Emotional framing is **warm but understated** — no urgency, no fear of loss, just quiet affirmation
- The single ad in the data suggests limited Meta spend or a much older, evergreen campaign strategy

### StoryKeeper
StoryKeeper runs a **one-message, one-line** paid ad strategy:

| Pillar | Representative Copy |
|---|---|
| **Gift occasion hook** | > "This Mother's Day, go beyond flowers!" |
| **Rhetorical legacy question** | > "What if you could give her a gift that lasts forever?" |
| **Price as CTA** | > "$99 for 1 Book & 2 Copies" |

**Additional observations:**
- Virtually zero creative variation — the same three sentences run across 14+ ads simultaneously, differentiated only by headlines and video vs. static
- No product explanation, no process, no testimonials, no emotional depth beyond the one rhetorical question
- The "go beyond flowers" framing is clichéd and extremely common in the gifting category
- A second, unrelated "StoryKeeper: Family Book Log" page appeared in the data — a children's reading tracker with no connection to life stories. This suggests namespace confusion that dilutes their brand

---

## 2. Longevity Analysis

> **Methodology note:** Days running is calculated from `start_date` to `stop_date`. Ads still active at fetch date (2026-05-12) without a stop_date are calculated from start to fetch date.

| Ad ID | Brand | Days Running | Core Creative Theme |
|---|---|---|---|
| 763892383471439 | Remento | **136** | "Autobiography that talks back" + $99 price |
| 712538008277944 | Remento | **135** | Same as above (A/B variant) |
| 1797082684484054 | Keepsake Frames | **357** | Photo printing app (not core competitor) |
| 725689447110382 | Remento | 51 | "Make history for your family" |
| 1288732889525790 | Remento | 49 | "Make history for your family" |
| 854656737028819 | Remento | 45 | "Easy as conversation / QR code" explainer |

### Why the 135–136 Day Remento Ads Keep Working

These are the **clear winners** in the dataset and deserve close attention. The winning ad copy:

> "Introducing the autobiography that talks back! Family can scan each page to hear your recording! 80% of life story books never get made, because the process requires so much writing & typing. So get Remento and actually make history for your family. 'My kids see their grandparents as heroes now!' — Karen L."
> **Headline: "The AI Biographer & Book are only $99!"**

Three reasons this creative has exceptional staying power:

1. **"Autobiography that talks back"** — a single, memorable, novel concept phrase that requires no explanation. It is descriptive, surprising, and immediately differentiating. This is a genuine hook, not a category descriptor.

2. **The $99 price point is stated in the headline** — it pre-qualifies buyers, reduces friction from price-shock at checkout, and signals accessibility. Most competitors bury price or treat it as a discount anchor.

3. **Social proof is woven into the body copy** — the Karen L. testimonial appears inside the ad narrative, not as a separate element. "My kids see their grandparents as heroes now" is emotionally resonant proof at the *outcome* level, not just satisfaction-level.

The 51 and 49-day "Make history" ads are straightforward longevity performers — broad enough to not fatigue, gift-framed enough to work across occasions.

**Key insight for Listn:** Long-running ads in this space share a formula: **novel concept phrase + specific price or outcome + embedded social proof**. None of Listn's competitors are running emotionally deep, voice-specific creative that lasts. The longevity gap is in *depth*, not just duration.

---

## 3. CTA Landscape

### What's Dominant

| CTA | Frequency | Brands Using It |
|---|---|---|
| **"Learn More"** | Most common (explicit in Remento) | Remento |
| **"Shop Now"** | Occasional | Meminto |
| **"Install Now"** | Keepsake Frames only | Keepsake |
| **Implicit / no CTA tagged** | Majority of ads | Remento, StoryKeeper, Meminto, StoryWorth |

**The uncomfortable truth:** Most ads in this category have **no differentiated CTA**. "Learn More" is the universal default. StoryKeeper essentially uses the price point ("$99 for 1 Book & 2 Copies") as a de facto CTA. Meminto uses discount urgency ("Save $30 and start making unforgettable memories today!") but buries it in body copy.

### Most Distinctive CTAs in the Set
- Remento's **"Make history for your family"** — functions as both CTA and brand tagline, which is unusual and smart
- Meminto's **"Gift immortality"** — conceptually bold but tonally mismatched to the warm gifting category; feels more like a headline than an action prompt
- StoryKeeper's implicit **"go beyond flowers"** — contrarian positioning but not technically a CTA

### What's Missing
No competitor is using:
- Urgency CTAs tied to **life stage** ("Before it's too late" — though this may be too dark for paid social)
- **Curiosity CTAs** ("Hear what your dad would say")
- **Experience-first CTAs** ("Start your first conversation free")
- Any CTA that puts the **voice/audio** at the center of the action

---

## 4. Emotional Tone

| Brand | Primary Emotional Register | Secondary Register | What's Absent |
|---|---|---|---|
| **Remento** | Warm legacy + mild urgency | Social proof / credibility | Grief, genuine vulnerability, the older adult's own perspective |
| **Meminto** | Transactional warmth | Discount urgency | Depth, storytelling, any actual story |
| **StoryWorth** | Quiet affirmation | Simplicity | Urgency, specificity, voice/audio dimension |
| **StoryKeeper** | Aspirational gifting | Price value | Personality, differentiation, emotion beyond the rhetorical question |

### Deeper Read

**Remento** operates in the warmest, most sophisticated emotional space of the set — but it is still fundamentally **gifter-centric**. The emotion is about what *you* give, not what *they* feel when telling their stories. The older adult's own experience of being heard and honored is almost entirely absent from the ad copy.

**Meminto** gestures at legacy ("immortality," "forever") but undercuts it immediately with discount mechanics. The emotional register is confused — you cannot credibly sell immortality and a Black Friday coupon in the same sentence.

**StoryWorth** is the gentlest — the "her stories matter" framing is emotionally honest but thin. One ad is insufficient to read a full strategy, but the email-reply mechanic suggests a product designed for the *gifter's* convenience, not the storyteller's joy.

**StoryKeeper** has essentially no emotional architecture. "What if you could give her a gift that lasts forever?" is the kind of rhetorical question that appears on every Mother's Day ad for every product category. It does no differentiation work.

**The category-wide emotional gap:** No competitor is speaking to the **fear of loss as a present-tense reality** — the moment when you realize your parent's stories are already fading and you haven't captured them yet. They gesture at legacy as a positive aspiration, but they don't sit with the specific, low-grade grief of not yet having done this. That emotional territory is unoccupied.

---

## 5. Three Things Listn Should Do Differently

### 1. Make the Voice the Hero, Not the Book

Every competitor frames the **printed/physical book** as the destination and the voice recording as merely the input mechanism. Remento's breakthrough creative is "the autobiography that talks back" — and even that frames the talking as a feature of the *book*, not the core experience.

Listn's product IS the voice. The conversation IS the gift. The audio IS irreplaceable.

**What to do:** Lead ads with the experience of *hearing* a loved one's voice — not what you'll do with it afterward. A creative angle no competitor is touching:

> *"Your dad's laugh when he tells the story about the night he met your mom. That sound exists right now. Listn helps you keep it."*

No competitor is saying this. None of them are making the **sound of a specific person's voice** the emotional object. This is Listn's native advantage — use it.

### 2. Speak to the Storyteller, Not Just the Gifter

Every competitor targets the **adult child** buying a gift for an aging parent. The older adult — the person whose life is being documented — never appears as the audience. They are the subject, not the protagonist.

This creates an enormous creative and audience gap. Older adults are on Facebook. Many of them *want* to tell their stories. They just don't want to feel like a project.

**What to do:** Run a separate creative track addressed to the storyteller directly:

> *"You've lived through things your grandchildren will study in history books. Listn wants to hear them — in your voice, on your schedule, whenever you're ready."*

This opens a self-purchase acquisition path that competitors have completely abandoned — every competitor assumes the older adult cannot or will not buy for themselves.

### 3. Use Specificity Over Sentiment

Competitors default to abstract legacy language: "forever," "timeless," "immortality," "a gift that lasts decades." This language is category wallpaper. Everyone says it. Nobody believes it because it doesn't feel real.

Listn should ground every ad in **specific, concrete, sensory moments** that make the value feel immediate and personal — not aspirational and vague.

**What to do:** Build creative around named story types:

> *"The summer your dad spent hitchhiking across the country. The job he almost took in another city. The person who believed in him before anyone else did. Those stories exist right now. Listn captures them in his own voice before they're gone."*

This is specific enough to create recognition ("that's MY dad") and urgency without being morbid. No competitor is writing at this level of narrative specificity.

---

## 6. Gaps Listn Can Own

### Gap 1: The Urgency That Doesn't Feel Like a Threat

Competitors either ignore urgency entirely (StoryWorth, StoryKeeper) or use holiday deadlines ("until Mother's Day!") as their urgency mechanism. No one is building urgency around the actual, present-tense stakes: cognitive decline, physical decline, the simple passage of time.

This is a gap, not because the fear angle is absent, but because **no one has found the warm, non-morbid version of that urgency.** There is a version of "do this now" that doesn't feel like a funeral ad — it sounds like:

> *"He still remembers everything. That window is a gift. Listn helps you use it."*

That line isn't scary. It's honest. And it creates urgency from a place of love rather than fear. No competitor has cracked this. Listn can own it.

### Gap 2: The Multigenerational Audience — Grandchildren as the End Beneficiary

Every competitor frames this as a parent-child gift transaction. But the people who will treasure these stories most — statistically, emotionally, across time — are **grandchildren and great-grandchildren** who may never meet the storyteller at full capacity.

No ad in this entire dataset mentions grandchildren as the *primary emotional beneficiary*. Remento's best testimonial gestures at it ("My kids see their grandparents as heroes now") but doesn't lead with it.

Listn can claim the frame:

> *"Someday your kids will want to know who their grandmother really was — not just what she cooked on holidays, but what she believed, what she fought for, what made her laugh. Listn makes sure they'll know."*

This reframes the product from "gift for mom" to "inheritance for your children" — a profoundly more emotionally durable value proposition.

### Gap 3: The Self-Documenter — Older Adults Who Want Agency

The entire category markets to a passive subject (the older adult) being gifted something by an active gifter (the adult child). This implicitly positions older adults as **objects of documentation** rather than agents of their own narrative.

There is a large, underserved audience of older adults — particularly 65–80, active, digitally capable, with strong narrative identities — who want to tell their stories **on their own terms**, not as someone else's gift project.

This is a positioning Listn can own cleanly: **"Tell your own story. In your own voice. While you still have everything to say."**

This also speaks to a powerful purchasing dynamic: self-gifters and self-buyers have higher LTV, higher intent, and require less persuasion about the product's value — they already feel the need.

### Gap 4: The Caregiver Channel

No competitor is targeting **professional caregivers, memory care staff, hospice workers, or elder care coordinators** as acquisition channels. These are people who:
- Have daily relationships with the exact population Listn serves
- Understand acutely the value of captured memories
- Can become institutional partners and bulk buyers

This is a B2B2C channel that competitors are entirely ignoring in their paid social creative. Meminto ran one webinar ad that hints at a professional track, but it was a single-day flight with no apparent follow-through.

A Listn ad aimed at this audience:

> *"You see what families miss. You know which stories are still there to capture. Listn partners with memory care facilities to help families preserve what matters most — before the window closes."*

### Gap 5: The "Already Happened" Story — Post-Loss Capture

Not addressed by any competitor: the audience of people who have **already lost a loved one** and are haunted by the stories they didn't capture. This is a grief-adjacent audience that is enormous, emotionally activated, and motivated to ensure the same thing doesn't happen with other family members still living.

The positioning for this audience isn't morbid — it's **redemptive**:

> *"You couldn't capture your dad's stories. But your mom's are still there, waiting. Listn."*

This is a high-intent retargeting and lookalike audience that competitors are leaving completely untouched.

---

## Summary Table

| Dimension | Competitor Consensus | Listn Opportunity |
|---|---|---|
| **Target audience** | Adult child buying a gift | Older adult as self-buyer; caregivers; post-loss families |
| **Product hero** | The printed book | The voice itself — the sound of someone you love |
| **Emotional register** | Warm but abstract legacy | Specific, present-tense urgency rooted in love |
| **CTA style** | "Learn More" / holiday deadlines | Experience-first / curiosity-led |
| **Key differentiator claimed** | No writing / no tech | Voice-first intimacy — no competitor has claimed this |
| **Urgency mechanism** | Holiday gifting seasons | The present-tense reality of a window that exists right now |
| **Beneficiary framing** | The gifter's generosity | The grandchildren who will inherit these stories |

---

*Report prepared for Listn growth strategy. Based on Meta Ad Library data scraped 2026-05-12. Analysis excludes Enna (irrelevant brand match) and treats Keepsake Frames as tangential/non-competitive.*