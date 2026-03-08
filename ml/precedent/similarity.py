"""Historical precedent similarity: cosine similarity on normalized features."""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def find_similar_periods(
    features: pd.DataFrame,
    query_date: pd.Timestamp | str,
    top_k: int = 10,
    min_separation_days: int = 126,
) -> pd.DataFrame:
    """Find top-K most similar historical periods to the query date.

    Uses cosine similarity on StandardScaler-normalized feature vectors.
    Excludes periods within min_separation_days of each other to avoid
    overlapping windows.

    Args:
        features: Feature matrix (rows = dates, cols = features).
        query_date: The date to find historical matches for.
        top_k: Number of similar periods to return.
        min_separation_days: Minimum days between returned matches.

    Returns:
        DataFrame with columns: date, similarity_score, and index into features.
    """
    query_date = pd.Timestamp(query_date)

    # Only use numeric, non-NaN columns
    num_df = features.select_dtypes(include=[np.number]).dropna(axis=1, how="all")

    # Scale
    scaler = StandardScaler()
    scaled = scaler.fit_transform(num_df.fillna(0))
    scaled_df = pd.DataFrame(scaled, index=num_df.index, columns=num_df.columns)

    if query_date not in scaled_df.index:
        # Find nearest available date
        nearest = scaled_df.index[scaled_df.index.get_indexer([query_date], method="nearest")[0]]
        query_date = nearest

    query_vec = scaled_df.loc[query_date].values

    # Compute cosine similarity against all historical dates (exclude future)
    historical = scaled_df[scaled_df.index < query_date]
    if historical.empty:
        return pd.DataFrame()

    hist_matrix = historical.values
    query_norm = np.linalg.norm(query_vec)
    hist_norms = np.linalg.norm(hist_matrix, axis=1)

    # Avoid division by zero
    denom = query_norm * hist_norms
    denom = np.where(denom == 0, 1e-10, denom)
    similarities = (hist_matrix @ query_vec) / denom

    sim_series = pd.Series(similarities, index=historical.index, name="similarity")
    sim_series = sim_series.sort_values(ascending=False)

    # De-duplicate: enforce minimum separation
    selected = []
    for date, score in sim_series.items():
        too_close = any(
            abs((date - prev_date).days) < min_separation_days
            for prev_date in selected
        )
        if not too_close:
            selected.append(date)
        if len(selected) >= top_k:
            break

    result_df = pd.DataFrame({
        "date": selected,
        "similarity_score": [sim_series[d] for d in selected],
    })
    return result_df
