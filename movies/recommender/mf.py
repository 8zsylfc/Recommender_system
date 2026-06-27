from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MFModel:
    user_ids: list[int]
    movie_ids: list[int]
    P: np.ndarray  # users x k
    Q: np.ndarray  # movies x k
    bu: np.ndarray  # users
    bi: np.ndarray  # movies
    mu: float


def train_mf_sgd(
    *,
    rating_rows: list[tuple[int, int, float]],  # (user_id, movie_id, score)
    k: int = 20,
    steps: int = 30,
    lr: float = 0.01,
    reg: float = 0.02,
    seed: int = 42,
) -> MFModel | None:
    if not rating_rows:
        return None

    rng = np.random.default_rng(seed)
    user_ids = sorted({u for (u, _, _) in rating_rows})
    movie_ids = sorted({m for (_, m, _) in rating_rows})
    u_index = {u: i for i, u in enumerate(user_ids)}
    m_index = {m: j for j, m in enumerate(movie_ids)}

    n_u, n_m = len(user_ids), len(movie_ids)
    P = rng.normal(0, 0.1, size=(n_u, k)).astype(np.float32)
    Q = rng.normal(0, 0.1, size=(n_m, k)).astype(np.float32)
    bu = np.zeros(n_u, dtype=np.float32)
    bi = np.zeros(n_m, dtype=np.float32)

    y = np.array([s for (_, _, s) in rating_rows], dtype=np.float32)
    mu = float(y.mean()) if len(y) else 0.0

    samples = np.array([(u_index[u], m_index[m], float(s)) for (u, m, s) in rating_rows], dtype=np.float32)

    for _ in range(steps):
        rng.shuffle(samples)
        for i_f, j_f, r in samples:
            i = int(i_f)
            j = int(j_f)
            pred = mu + float(bu[i]) + float(bi[j]) + float(np.dot(P[i], Q[j]))
            e = float(r - pred)
            bu[i] += lr * (e - reg * float(bu[i]))
            bi[j] += lr * (e - reg * float(bi[j]))
            Pi = P[i].copy()
            P[i] += lr * (e * Q[j] - reg * P[i])
            Q[j] += lr * (e * Pi - reg * Q[j])

    return MFModel(user_ids=user_ids, movie_ids=movie_ids, P=P, Q=Q, bu=bu, bi=bi, mu=mu)


def mf_recommendations_for_user(
    *,
    model: MFModel,
    user_id: int,
    rated_movie_ids: set[int],
    top_n: int = 10,
) -> list[tuple[int, float]]:
    user_to_idx = {uid: idx for idx, uid in enumerate(model.user_ids)}
    if user_id not in user_to_idx:
        return []

    u = user_to_idx[user_id]
    base = model.mu + float(model.bu[u])
    scores = base + model.bi + (model.Q @ model.P[u])
    preds: list[tuple[int, float]] = []
    for j, movie_id in enumerate(model.movie_ids):
        if movie_id in rated_movie_ids:
            continue
        preds.append((movie_id, float(scores[j])))
    preds.sort(key=lambda x: x[1], reverse=True)
    return preds[:top_n]

