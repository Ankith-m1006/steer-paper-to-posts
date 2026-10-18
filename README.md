# Paper in, posts out: Steer's research-to-Instagram pipeline

Built for the Steer Club Hackathon, Problem Statement 2 ("From research paper to Instagram, automated").

One command takes a research paper (a PDF or a link) and produces, in Steer's voice and brand:
a carousel, a static post (4:5 and 1:1), an AI-voiced reel in English and in Hindi, a caption with
hashtags, a Hinglish caption, and a review page where a Steer doctor sees every line next to the exact
sentence and page of the paper it came from. Nothing is scheduled until the doctor approves it.

```
python run.py --batch papers.txt     # 3 papers in, a week of content out
# doctor opens out/<paper>/review.html, ticks, saves approvals.json
python publish.py out/*/approvals.json   # schedules only approved posts
```

## Architecture

```
paper (PDF or link)
  │  ingest.py   PDF -> text per page (pypdf) | link -> Europe PMC open-access full text, per section paragraph
  ▼
located chunks  ("p. 2", "Results, para 3")
  │  extract.py  Gemini proposes 8-14 claims, each with a verbatim quote + location
  │              CODE VERIFIER: keeps a claim only if its quote is really in the paper (exact after
  │              normalising, or >= 0.92 fuzzy) and every number in the claim is in the quote
  ▼
verified claims (+ a list of rejected ones, with the reason)
  │  write.py    Gemini writes carousel / static / reel / captions / Hinglish / Hindi reel in Steer's voice,
  │              every slide and scene citing claim ids
  │              CODE CHECKS: cited ids exist; every number (and number words like "two-thirds") is in the
  │              cited claims; no drug or brand names; no promises of kilos or timelines; no ALL CAPS
  │              DOCTOR-JUDGE: a second Gemini pass checks each line against only the claims it cites
  │              -> one automatic rewrite; anything still wrong is flagged for the doctor
  ▼
checked copy
  │  render.py   Pillow renders in the Steer brand pack (cream, rust serif with italics, Inter body,
  │              Caveat field-note accents); source + page printed on every slide that makes a claim
  │  reel.py     edge-tts neural voices (en-IN Neerja, hi-IN Swara) per scene, ffmpeg slow-zoom motion,
  │              story progress bars, burned-in subtitles (Inter / Noto Sans Devanagari)
  ▼
out/<paper>/ carousel/*.png  static.png  static_square.png  reel_en.mp4  reel_hi.mp4  caption.txt  content.json
  │  review.py   review.html: every line, the quote it rests on, its page, flags; approve boxes -> approvals.json
  ▼
publish.py      schedule.csv (Meta Business Suite / Buffer) for approved posts only + canva_bulk.csv
```

## Why the science survives the trip

1. **Quotes are checked by code, not trusted.** A claim the model paraphrased into a quote, or a number it added, is thrown out and shown in the review page under "Thrown out by the verifier". In the first run on the STEP 1 extension paper, the model added "52 weeks" to a finding; the verifier rejected it.
2. **Every number in a post must exist in the claim it cites**, including numbers written as words.
3. **A doctor-judge pass reads each line against only its cited claims.** It flagged "Without ongoing support, two-thirds of lost weight returned" because in the trial both the medicine and the lifestyle programme stopped. That line goes to the doctor with the suggested fix instead of being published.
4. **The doctor approves line by line**, with the quote and the page beside each line. The publish step refuses anything not approved.

## Steer voice and brand, enforced

The writer prompt carries the voice guide (doctor-led, warm, made for India, habits over quick fixes; "Before you start, hear it from a doctor, not a reel."), and code rejects drug or brand names, weight-loss promises, miracle words and ALL CAPS. Renders use the brand palette (#F5EBDF cream, #C04E2A rust, #661414 maroon, #351D1D ink, #B58777 clay, #E6CBBD blush, #F8F2EB paper), an elegant serif mixing upright and italic, a clean sans, lowercase "steer" and steerclub.com.

## Papers used (all CC BY, open access)

| | Paper | Input |
|---|---|---|
| A | Wilding JPH et al. Weight regain and cardiometabolic effects after withdrawal of semaglutide: the STEP 1 trial extension. *Diabetes Obes Metab* 2022. doi:10.1111/dom.14725 | PDF |
| B | Mechanick JI et al. Strategies for minimizing muscle loss during use of incretin-mimetic drugs for treatment of obesity. *Obes Rev* 2025. doi:10.1111/obr.13841 | link (PMC11611443) |
| C | McLaren J et al. Weight gain leads to greater adverse metabolic responses in South Asian compared with white European men. *Nat Metab* 2024. doi:10.1038/s42255-024-01101-z | link (PMC11349579) |

## Human time per paper

Machine time per paper is printed on each review page (about 3-5 minutes: extraction ~30 s, writing and checks ~1-2 min, images a few seconds, two reels ~1-2 min). Human time is the doctor's review: reading the flagged lines and spot-checking the quotes on one page, about 10 minutes per paper. A week of content (3 papers) is about 30 minutes of a doctor's time.

## Bonus items

- Hindi reel (Devanagari voice and subtitles) and Hinglish caption for every paper.
- Auto-resize: static post in 4:5 and 1:1.
- Batch mode: `--batch papers.txt`.
- Scheduling: `schedule.csv` with dates, times, files and captions for approved posts.
- Canva: `canva_bulk.csv` (one row per slide) for Canva Bulk Create, to restyle the same copy in a Canva template.

## Tools

Python, pypdf, Pillow, Europe PMC REST API, Google Gemini (gemini-3.5-flash through AI Studio) for extraction, writing and the judge pass, edge-tts neural voices, ffmpeg. Fonts: Instrument Serif, Inter, Caveat, Noto Sans Devanagari (SIL Open Font License). Claude (Anthropic) was used as an AI coding assistant to build the pipeline. Solo build by Ankith M.
