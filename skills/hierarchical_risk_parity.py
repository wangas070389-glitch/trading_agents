"""
Hierarchical Risk Parity (HRP) Portfolio Allocator

Implements De Prado's Hierarchical Risk Parity (HRP) algorithm:
1. Distance Matrix Computation: d_ij = sqrt(2 * (1 - corr_ij))
2. Single-linkage Hierarchical Tree Clustering
3. Quasi-Diagonalization of Covariance Matrix
4. Recursive Bisection Portfolio Weight Allocation

Used for stable multi-asset portfolio optimization (S15, S25).
"""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, leaves_list


def calculate_hrp_weights(cov_matrix: pd.DataFrame) -> pd.Series:
    """
    Calculates Hierarchical Risk Parity (HRP) portfolio weights given an asset covariance matrix.
    
    cov_matrix: pandas DataFrame representing NxN asset returns covariance.
    returns: pandas Series of portfolio weights summing to 1.0.
    """
    if cov_matrix.empty or cov_matrix.shape[0] != cov_matrix.shape[1]:
        raise ValueError("Input covariance matrix must be square and non-empty.")

    labels = cov_matrix.columns.tolist()
    n = len(labels)

    if n == 1:
        return pd.Series([1.0], index=labels)

    # 1. Compute Correlation and Distance Matrix
    std_diag = np.sqrt(np.diag(cov_matrix.values))
    std_diag[std_diag == 0] = 1e-8
    corr_matrix = cov_matrix.values / np.outer(std_diag, std_diag)
    np.fill_diagonal(corr_matrix, 1.0)
    corr_matrix = np.clip(corr_matrix, -1.0, 1.0)

    dist_matrix = np.sqrt(np.clip(2.0 * (1.0 - corr_matrix), 0.0, None))

    # 2. Hierarchical Clustering (Single-linkage)
    # Convert square distance matrix to condensed form for scipy linkage
    condensed_dist = []
    for i in range(n):
        for j in range(i + 1, n):
            condensed_dist.append(dist_matrix[i, j])
    condensed_dist = np.array(condensed_dist)

    link = linkage(condensed_dist, method='single')

    # 3. Quasi-Diagonalization (Rearrange indices by dendrogram leaf order)
    sort_ix = leaves_list(link).tolist()

    # 4. Recursive Bisection Allocation
    weights = pd.Series(1.0, index=sort_ix, dtype=np.float64)
    clusters = [sort_ix]

    while len(clusters) > 0:
        clusters = [c[i:j] for c in clusters for i, j in ((0, len(c) // 2), (len(c) // 2, len(c))) if len(c) > 1]
        for i in range(0, len(clusters), 2):
            c_left = clusters[i]
            c_right = clusters[i + 1]

            # Calculate cluster variances
            cov_left = cov_matrix.values[np.ix_(c_left, c_left)]
            cov_right = cov_matrix.values[np.ix_(c_right, c_right)]

            w_left_ivp = 1.0 / np.diag(cov_left)
            w_left_ivp /= np.sum(w_left_ivp)
            var_left = np.dot(w_left_ivp, np.dot(cov_left, w_left_ivp))

            w_right_ivp = 1.0 / np.diag(cov_right)
            w_right_ivp /= np.sum(w_right_ivp)
            var_right = np.dot(w_right_ivp, np.dot(cov_right, w_right_ivp))

            alloc_factor = 1.0 - var_left / (var_left + var_right)

            weights[c_left] *= alloc_factor
            weights[c_right] *= (1.0 - alloc_factor)

    # Re-index weights to original asset labels
    hrp_weights = pd.Series(0.0, index=labels, dtype=np.float64)
    for ix, w in weights.items():
        hrp_weights.iloc[ix] = w

    return hrp_weights
