#!/usr/bin/env python3
"""Verify golden-set rows against the corpus page text.

Usage: python3 verify.py <csv> <text_dir> [--out report.csv]

Checks, per row:
  quote_found   every gold_quote segment occurs verbatim (whitespace-normalized) in text/<id>/pNNN.txt
  overlap       fraction of question words (len>3) that also appear in the quote; high overlap means the
                question copies the document and makes retrieval too easy. Flag at > 0.6.
  answer_ok     answer is non-empty (or "Not covered by the corpus." for type none)
Prints a summary and writes a report CSV with the flags added so a reviewer can sort by them.
"""
import csv, re, sys, os

def norm(s):
    return re.sub(r'\s+', ' ', s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"').replace('–', '-').replace('—', '-')).strip().lower()

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    src, tdir = sys.argv[1], sys.argv[2]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    cache = {}
    def page(doc, p):
        key = (doc, int(p))
        if key not in cache:
            fp = os.path.join(tdir, doc, 'p%03d.txt' % int(p))
            cache[key] = norm(open(fp, encoding='utf-8', errors='ignore').read()) if os.path.exists(fp) else None
        return cache[key]
    stop = set('what when where which does will your this that with from have about there their under than them they been were into only also than'.split())
    n_ok = n_quote_bad = n_overlap = 0
    for r in rows:
        t = (r.get('type') or '').strip()
        docs = [d.strip() for d in (r.get('gold_doc_ids') or '').split(';') if d.strip()]
        pages = [p.strip() for p in (r.get('gold_pages') or '').split(';') if p.strip()]
        quotes = [q.strip() for q in (r.get('gold_quote') or '').split('||')]
        if t == 'none':
            r['quote_found'] = 'n/a'
        else:
            found = []
            for i, q in enumerate(quotes):
                d = docs[i] if i < len(docs) else (docs[0] if docs else '')
                p = pages[i] if i < len(pages) else (pages[0] if pages else '')
                txt = page(d, p) if d and p else None
                found.append(bool(txt) and norm(q) in txt and len(q) > 20)
            r['quote_found'] = 'yes' if quotes and all(found) else 'NO'
            if r['quote_found'] == 'NO': n_quote_bad += 1
        qw = [w for w in re.findall(r"[a-z0-9']+", norm(r.get('question', ''))) if len(w) > 3 and w not in stop]
        qt = norm(' '.join(quotes))
        ov = (sum(1 for w in qw if w in qt) / len(qw)) if qw else 0
        r['overlap'] = '%.2f' % ov
        r['overlap_flag'] = 'HIGH' if ov > 0.6 else ''
        if ov > 0.6: n_overlap += 1
        a = (r.get('answer') or '').strip()
        r['answer_ok'] = 'yes' if (a and (t != 'none' or a.lower().startswith('not covered'))) else 'NO'
        if r['quote_found'] in ('yes', 'n/a') and r['answer_ok'] == 'yes' and not r['overlap_flag']:
            n_ok += 1
    print(f"rows {len(rows)}  clean {n_ok}  quote_missing {n_quote_bad}  high_overlap {n_overlap}")
    from collections import Counter
    print('types', dict(Counter(r.get('type') for r in rows)))
    print('difficulty', dict(Counter(r.get('difficulty') for r in rows)))
    print('docs covered', len({d.strip() for r in rows for d in (r.get('gold_doc_ids') or '').split(';') if d.strip()}))
    if out:
        with open(out, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        print('wrote', out)

if __name__ == '__main__':
    main()
