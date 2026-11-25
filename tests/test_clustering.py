import numpy as np

from bgllog.clustering import (choose_best_deep, event_count_matrix, external_metrics, fit_kmeans,
                               stratified_sample_indices)


def test_event_count_matrix_ignores_pad_and_unknown_and_normalizes_rows():
    windows = np.array([[0, 1, 2, 2], [3, 3, 3, 1]], dtype=np.int16)

    counts = event_count_matrix(windows, vocab_size=4).toarray()

    assert counts.shape == (2, 4)
    assert counts[0, 0] == 0
    assert counts[0, 1] == 0
    assert np.isclose(np.linalg.norm(counts[0]), 1.0)
    assert np.isclose(counts[1, 3], 1.0)


def test_kmeans_recovers_clear_groups_and_external_scores():
    rng = np.random.default_rng(42)
    first = rng.normal(loc=-4, scale=0.15, size=(40, 2))
    second = rng.normal(loc=4, scale=0.15, size=(40, 2))
    features = np.vstack((first, second))
    expected = np.array([False] * len(first) + [True] * len(second))

    model = fit_kmeans(features, k=2, seed=42)
    scores = external_metrics(model.labels_, expected, np.where(expected, "ALERT", "NONE"))

    assert scores["nmi_alert"] > 0.95
    assert scores["purity_alert"] > 0.95


def test_best_deep_representation_uses_nmi_when_silhouettes_are_close():
    validation = {
        "lstm": {"silhouette": 0.6686, "nmi_alert_tag": 0.1409},
        "gru": {"silhouette": 0.6728, "nmi_alert_tag": 0.1288},
    }

    assert choose_best_deep(validation) == "lstm"


def test_stratified_sample_preserves_class_proportions_and_is_reproducible():
    strata = np.array([False] * 90 + [True] * 10)

    first = stratified_sample_indices(strata, sample_size=50, seed=42)
    second = stratified_sample_indices(strata, sample_size=50, seed=42)

    assert np.array_equal(first, second)
    assert len(first) == 50
    assert np.count_nonzero(strata[first]) == 5
