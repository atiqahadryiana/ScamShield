"""Synthetic pipeline smoke test ONLY; no model/dataset is shipped or validated."""
import csv
import json
import sys
import pytest


def test_candidate_pipeline_is_unvalidated_and_hash_gated(tmp_path, monkeypatch):
    pytest.importorskip('sklearn')
    pytest.importorskip('skops')
    from app.ml.train import main
    from app.ml.inference import ValidatedModel
    data = tmp_path / 'synthetic_test_only.csv'
    with data.open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['text', 'label', 'language'])
        for lang in ['en', 'ms']:
            for label in [0, 1]:
                for n in range(60):
                    # Deliberately trivial fixtures test software plumbing, not validity.
                    writer.writerow([f'SYNTHETIC TEST ONLY {lang} class{label} fictional sample {n}', label, lang])
    provenance = tmp_path / 'provenance.json'
    provenance.write_text(json.dumps({'source': 'synthetic unit test fixtures', 'license': 'test-only original text', 'permission_basis': 'created exclusively for software smoke tests', 'labeling_method': 'artificial class marker; not real-world labels'}), encoding='utf-8')
    output = tmp_path / 'candidate'
    monkeypatch.setattr(sys, 'argv', ['train', '--csv', str(data), '--provenance', str(provenance), '--output', str(output)])
    main()
    report = json.loads((output / 'evaluation.json').read_text())
    assert report['validated'] is False
    assert report['unique_rows'] == 240
    assert report['heldout_rows'] == 48
    assert set(report['languages']) == {'en', 'ms'}
    assert len(report['model_metrics']['confusion_matrix']) == 2
    with pytest.raises(ValueError, match='human-reviewed'):
        ValidatedModel(str(output / 'model.skops'), str(output / 'evaluation.json'))


def test_message_experiment_runner_compares_three_candidates(tmp_path, monkeypatch):
    pytest.importorskip('sklearn')
    pytest.importorskip('skops')
    from app.ml.train_message import main
    data = tmp_path / 'messages.csv'
    with data.open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['text', 'label', 'language'])
        for language in ('en', 'ms'):
            for label in (0, 1):
                for number in range(55):
                    marker = 'urgent fictional otp request' if label else 'ordinary fictional meeting'
                    writer.writerow([f'{language} {marker} sample {number}', label, language])
    source = tmp_path / 'provenance.json'
    source.write_text(json.dumps({'source': 'synthetic test', 'license': 'test only', 'permission_basis': 'generated fixture', 'labeling_method': 'class marker'}), encoding='utf-8')
    output = tmp_path / 'message-output'
    monkeypatch.setattr(sys, 'argv', ['train_message', '--csv', str(data), '--provenance', str(source), '--output', str(output)])
    main()
    report = json.loads((output / 'evaluation.json').read_text())
    assert report['validated'] is False
    assert report['model_kind'] == 'message'
    assert len(report['experiments']) == 3
    assert (output / 'message_model.skops').exists()


def test_url_experiment_runner_compares_two_candidates(tmp_path, monkeypatch):
    pytest.importorskip('sklearn')
    pytest.importorskip('skops')
    from app.ml.train_url import main
    data = tmp_path / 'urls.csv'
    with data.open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['url', 'label'])
        for label in (0, 1):
            for number in range(110):
                host = f'secure-login-{number}.phish-example.test' if label else f'service-{number}.example.com'
                path = '/verify-account' if label else '/information'
                writer.writerow([f'https://{host}{path}', label])
    source = tmp_path / 'provenance.json'
    source.write_text(json.dumps({'source': 'synthetic test', 'license': 'test only', 'permission_basis': 'generated fixture', 'labeling_method': 'class marker'}), encoding='utf-8')
    output = tmp_path / 'url-output'
    monkeypatch.setattr(sys, 'argv', ['train_url', '--csv', str(data), '--provenance', str(source), '--output', str(output)])
    main()
    report = json.loads((output / 'evaluation.json').read_text())
    assert report['validated'] is False
    assert report['model_kind'] == 'url'
    assert len(report['experiments']) == 2
    assert (output / 'url_model.skops').exists()
