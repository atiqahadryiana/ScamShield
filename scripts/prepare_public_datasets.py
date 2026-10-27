"""Normalize the five documented public datasets without merging label semantics.

Raw files are never modified. Exact normalized duplicates are collapsed; every text
whose duplicates disagree on a label is excluded and counted in the manifest.
URLs are parsed locally only and are never resolved or fetched.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'datasets' / 'raw'
OUT = ROOT / 'datasets' / 'processed'
sys.path.insert(0, str(ROOT / 'backend'))


def normalized(value: str) -> str:
    import re
    import unicodedata
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', value).casefold()).strip()


def write_text_dataset(name, records, source, doi, license_name='CC BY 4.0'):
    grouped = defaultdict(set)
    original = {}
    for text, label in records:
        key = normalized(text)
        if key:
            grouped[key].add(label.strip().casefold())
            original.setdefault(key, text.strip())
    conflicts = {key for key, labels in grouped.items() if len(labels) != 1}
    clean = [(original[key], next(iter(labels))) for key, labels in grouped.items() if key not in conflicts]
    destination = OUT / f'{name}.csv'
    with destination.open('w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['text', 'label'])
        writer.writerows(clean)
    return {
        'name': name, 'task': 'text_classification', 'source': source, 'doi': doi,
        'license': license_name, 'download_date': str(date.today()),
        'raw_rows': len(records), 'processed_rows': len(clean),
        'excluded_conflicting_normalized_texts': len(conflicts),
        'class_distribution': dict(Counter(label for _, label in clean)),
        'processed_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'processed_file': destination.name,
        'permission_basis': f'Public dataset released under {license_name}; attribution required.',
        'labeling_method': 'Labels supplied by dataset authors; conflicting exact normalized duplicates excluded.',
    }


def csv_records(path, encoding, text_column, label_column):
    with path.open(encoding=encoding, newline='') as file:
        return [(row[text_column], row[label_column]) for row in csv.DictReader(file)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifests = []
    manifests.append(write_text_dataset(
        'sms_phishing', csv_records(RAW / 'sms_phishing' / 'Dataset_5971.csv', 'cp1252', 'TEXT', 'LABEL'),
        'Mishra & Soni, SMS PHISHING DATASET FOR MACHINE LEARNING AND PATTERN RECOGNITION, version 1',
        '10.17632/f45bkkt8pr.1'))
    manifests.append(write_text_dataset(
        'balanced_spam_smishing', csv_records(RAW / 'balanced_spam_smishing.csv', 'utf-8-sig', 'TEXT', 'LABEL'),
        'Munoz & Islam, A Balanced Dataset for Spam and Smishing Detection using LLMs, version 1',
        '10.17632/vmg875v4xs.1'))
    uci = []
    with (RAW / 'uci_sms_spam' / 'SMSSpamCollection').open(encoding='utf-8', errors='replace') as file:
        for line in file:
            label, text = line.rstrip('\n').split('\t', 1)
            uci.append((text, label))
    manifests.append(write_text_dataset(
        'uci_sms_spam', uci, 'Almeida & Hidalgo, SMS Spam Collection', '10.24432/C5CC84'))
    manifests.append(write_text_dataset(
        'financial_scams', csv_records(RAW / 'financial_scams.csv', 'utf-8-sig', 'message', 'label'),
        'Ahmed & Islam, Financial scams detection dataset, version 2', '10.17632/znsk27yk3h.2'))

    url_source = RAW / 'legitphish.csv'
    from app.ml.url_features import parse_url
    urls, excluded, malformed = [], 0, 0
    with url_source.open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file):
            label = row['ClassLabel'].strip()
            if label not in {'0', '1'}:
                excluded += 1
                continue
            try:
                parse_url(row['URL'])
            except ValueError:
                malformed += 1
                continue
            # Source labels: 1 legitimate, 0 phishing. Runtime labels: 0 legitimate, 1 phishing.
            urls.append((row['URL'].strip(), 1 if label == '0' else 0))
    deduplicated = {}
    conflicts = set()
    for url, label in urls:
        key = url.casefold()
        if key in deduplicated and deduplicated[key][1] != label:
            conflicts.add(key)
        deduplicated[key] = (url, label)
    clean_urls = [value for key, value in deduplicated.items() if key not in conflicts]
    url_destination = OUT / 'legitphish.csv'
    with url_destination.open('w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['url', 'label'])
        writer.writerows(clean_urls)
    manifests.append({
        'name': 'legitphish', 'task': 'url_classification',
        'source': 'Potpelwar, Kulkarni & Waghmare, LegitPhish Dataset, version 2',
        'doi': '10.17632/hx4m73v2sf.2', 'license': 'CC BY 4.0', 'download_date': str(date.today()),
        'raw_rows': len(urls) + excluded + malformed, 'processed_rows': len(clean_urls),
        'excluded_unlabeled_rows': excluded, 'excluded_malformed_urls': malformed, 'excluded_conflicting_urls': len(conflicts),
        'class_distribution': dict(Counter(str(label) for _, label in clean_urls)),
        'processed_sha256': hashlib.sha256(url_destination.read_bytes()).hexdigest(),
        'processed_file': url_destination.name,
        'permission_basis': 'Public dataset released under CC BY 4.0; attribution required.',
        'labeling_method': 'Labels supplied by dataset authors; source labels inverted to 0 legitimate / 1 phishing.',
    })
    for manifest in manifests:
        (OUT / f"{manifest['name']}.provenance.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT / 'manifest.json').write_text(json.dumps({'datasets': manifests}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'datasets': manifests}, indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
