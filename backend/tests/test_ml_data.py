import pytest
from app.ml.train import load_dataset


def test_training_data_deduplicates_normalized_text(tmp_path):
    data = tmp_path / 'fictional.csv'
    data.write_text('text,label,language\nHELLO project meeting,0,en\nhello  project meeting,0,en\nBayar dahulu untuk hadiah,1,ms\n', encoding='utf-8')
    texts, labels, languages = load_dataset(data)
    assert len(texts) == 2
    assert labels == [0, 1]
    assert languages == ['en', 'ms']


def test_training_data_rejects_conflicting_labels(tmp_path):
    data = tmp_path / 'fictional.csv'
    data.write_text('text,label,language\nSame message,0,en\nsame message,1,en\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Conflicting'):
        load_dataset(data)
