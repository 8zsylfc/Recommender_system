from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CFResult:
    movie_ids: list[int]
    scores: list[float]


@dataclass(frozen=True)
class SimilarUser:
    user_id: int
    similarity: float
    common_movies: int


def user_based_cf_recommendations(
    *,
    user_id: int,
    rating_rows: list[tuple[int, int, float]],  # (user_id, movie_id, score)
    all_movie_ids: list[int],
    top_n: int = 10,
    min_common: int = 2,
) -> CFResult:
    if not rating_rows:
        return CFResult(movie_ids=[], scores=[])

    users = sorted({u for (u, _, _) in rating_rows})
    movies = sorted({m for (_, m, _) in rating_rows})
    user_index = {u: i for i, u in enumerate(users)}
    movie_index = {m: j for j, m in enumerate(movies)}

    R = np.zeros((len(users), len(movies)), dtype=np.float32)
    mask = np.zeros_like(R, dtype=np.bool_)
    for u, m, s in rating_rows:
        i = user_index[u]
        j = movie_index[m]
        R[i, j] = float(s)
        mask[i, j] = True

    if user_id not in user_index:
        return CFResult(movie_ids=[], scores=[])

    target_i = user_index[user_id]
    target_vec = R[target_i]
    target_mask = mask[target_i]

    sims = np.zeros(len(users), dtype=np.float32)
    for i in range(len(users)):
        if i == target_i:
            continue
        common = target_mask & mask[i]
        if int(common.sum()) < min_common:
            continue
        a = target_vec[common]
        b = R[i, common]
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom <= 1e-8:
            continue
        sims[i] = float(np.dot(a, b) / denom)

    if float(np.abs(sims).sum()) <= 1e-8:
        return CFResult(movie_ids=[], scores=[])

    rated_movie_ids = {m for (u, m, _) in rating_rows if u == user_id}
    candidates = [m for m in all_movie_ids if m not in rated_movie_ids]
    if not candidates:
        return CFResult(movie_ids=[], scores=[])

    preds: list[tuple[int, float]] = []
    for movie_id in candidates:
        if movie_id not in movie_index:
            continue
        j = movie_index[movie_id]
        raters = mask[:, j]
        w = sims[raters]
        if float(np.abs(w).sum()) <= 1e-8:
            continue
        s = R[raters, j]
        pred = float(np.dot(w, s) / (np.abs(w).sum() + 1e-8))
        preds.append((movie_id, pred))

    preds.sort(key=lambda x: x[1], reverse=True)
    top = preds[:top_n]
    return CFResult(movie_ids=[m for (m, _) in top], scores=[p for (_, p) in top])


def find_similar_users(
    *,
    user_id: int,
    rating_rows: list[tuple[int, int, float]],
    top_n: int = 10,
    min_common: int = 2,
) -> list[SimilarUser]:
    if not rating_rows:
        return []

    users = sorted({u for (u, _, _) in rating_rows})
    movies = sorted({m for (_, m, _) in rating_rows})
    user_index = {u: i for i, u in enumerate(users)}
    movie_index = {m: j for j, m in enumerate(movies)}

    R = np.zeros((len(users), len(movies)), dtype=np.float32)
    mask = np.zeros_like(R, dtype=np.bool_)
    for u, m, s in rating_rows:
        i = user_index[u]
        j = movie_index[m]
        R[i, j] = float(s)
        mask[i, j] = True

    if user_id not in user_index:
        return []

    target_i = user_index[user_id]
    target_vec = R[target_i]
    target_mask = mask[target_i]

    similar_users: list[SimilarUser] = []
    for i in range(len(users)):
        if i == target_i:
            continue
        common = target_mask & mask[i]
        common_count = int(common.sum())
        if common_count < min_common:
            continue
        a = target_vec[common]
        b = R[i, common]
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom <= 1e-8:
            continue
        similarity = float(np.dot(a, b) / denom)
        similar_users.append(SimilarUser(
            user_id=users[i],
            similarity=similarity,
            common_movies=common_count,
        ))

    similar_users.sort(key=lambda x: x.similarity, reverse=True)
    return similar_users[:top_n]

