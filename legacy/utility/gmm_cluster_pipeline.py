import numpy as np
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture


def mahalanobis_distance(X_k, mean_k, cov_k):
    reg = 1e-9 * np.eye(cov_k.shape[0])
    cov_k_reg = cov_k + reg

    diff = X_k - mean_k
    inv_cov = np.linalg.inv(cov_k_reg)

    d2 = np.einsum("ij,jk,ik->i", diff, inv_cov, diff)
    d2 = np.maximum(d2, 0.0)

    return np.sqrt(d2)


def compute_interval_spike_count_pca(
    responses: np.ndarray,
    n_components: int = 3,
    verbose: bool = True,
):
    """
    Compute PCA features from interval spike-count responses.

    Args:
        responses:
            ndarray of shape (n_responses, n_channels, n_intervals)

        n_components:
            Number of PCA components.

        verbose:
            If True, print PCA diagnostics.

    Returns:
        X:
            PCA-transformed feature matrix,
            shape (n_responses, n_components)

        pca_model:
            fitted sklearn PCA model

        pca_info:
            dictionary of PCA diagnostics
    """

    responses = np.asarray(responses, dtype=np.float64)

    if responses.ndim != 3:
        raise ValueError(
            f"responses must have shape (n_responses, n_channels, n_intervals), "
            f"got {responses.shape}"
        )

    n_responses, n_channels, n_intervals = responses.shape

    if n_responses == 0:
        raise ValueError("responses contains zero responses")

    # Flatten each response into one feature vector
    # (n_responses, n_channels, n_intervals)
    # -> (n_responses, n_channels * n_intervals)
    X_in = responses.reshape(n_responses, n_channels * n_intervals)

    n_features = X_in.shape[1]

    if n_components > min(n_responses, n_features):
        raise ValueError(
            "n_components cannot exceed min(n_responses, n_channels * n_intervals)"
        )

    pca = PCA(n_components=n_components)
    X = pca.fit_transform(X_in)

    pca_info = {
        "input_shape": responses.shape,
        "pca_input_shape": X_in.shape,
        "n_responses": n_responses,
        "n_channels": n_channels,
        "n_intervals": n_intervals,
        "n_features": n_features,
        "n_components": n_components,
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "explained_variance": pca.explained_variance_,
        "singular_values": pca.singular_values_,
        "total_explained_variance_ratio": float(
            np.sum(pca.explained_variance_ratio_)
        ),
    }

    if verbose:
        print("Interval spike-count PCA completed")
        print(f"  responses: {n_responses}")
        print(f"  channels: {n_channels}")
        print(f"  intervals: {n_intervals}")
        print(f"  PCA input shape: {X_in.shape}")
        print(f"  PCA components: {n_components}")
        print("  explained variance ratio:", pca.explained_variance_ratio_)
        print(
            "  total explained variance:",
            pca_info["total_explained_variance_ratio"],
        )

    return X, pca, pca_info


def compute_spike_pca(
    waveforms: np.ndarray,
    n_components: int = 3,
    verbose: bool = True,
):
    """
    Reduce spike waveforms into PCA feature space.

    Args:
        waveforms   : Array of shape (n_spikes, n_samples). Each row is a spike waveform.
        n_components: Number of PCA components to compute.
        verbose     : If True, print basic PCA diagnostics.

    Returns:
        X           : PCA-transformed feature matrix, shape (n_spikes, n_components).
        pca_model   : Fitted sklearn PCA model.
        pca_info    : Dictionary containing PCA diagnostics.
    """

    # ---------- input validation ----------
    waveforms = np.asarray(waveforms)

    if waveforms.ndim != 2:
        raise ValueError(
            f"waveforms must have shape (n_spikes, n_samples), got {waveforms.shape}"
        )

    n_spikes, n_samples = waveforms.shape

    if n_spikes == 0:
        raise ValueError("waveforms contains zero spikes")

    if n_components > min(n_spikes, n_samples):
        raise ValueError(
            "n_components cannot exceed min(n_spikes, n_samples)"
        )

    # ---------- PCA ----------
    pca = PCA(n_components=n_components)

    X = pca.fit_transform(waveforms)

    # ---------- diagnostics ----------
    pca_info = {
        "n_spikes": n_spikes,
        "n_samples": n_samples,
        "n_components": n_components,
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "explained_variance": pca.explained_variance_,
        "singular_values": pca.singular_values_,
        "total_explained_variance_ratio": float(
            np.sum(pca.explained_variance_ratio_)
        ),
    }

    # ---------- optional printing ----------
    if verbose:
        print("PCA completed")
        print(f"  spikes: {n_spikes}")
        print(f"  samples per spike: {n_samples}")
        print(f"  PCA components: {n_components}")
        print("  explained variance ratio:", pca.explained_variance_ratio_)
        print(
            "  total explained variance:",
            pca_info["total_explained_variance_ratio"],
        )

    return X, pca, pca_info


def select_gmm_cluster_number(
    X: np.ndarray,
    k_min: int = 1,
    k_max: int = 6,
    covariance_type: str = "full",
    random_state: int = 0,
    verbose: bool = True,
):
    """
    Determine the best number of GMM clusters using BIC/AIC model selection.

    Args:
        X               : PCA feature matrix, shape (n_spikes, n_features)
        k_min           : Minimum candidate cluster number
        k_max           : Maximum candidate cluster number
        covariance_type : GMM covariance type ("full", "diag", "tied", "spherical")
        random_state    : Random seed for reproducibility
        verbose         : Print model selection diagnostics

    Returns:
        best_k      : Cluster number selected using BIC
        score_table : Dict containing model selection results:
            {
                "candidate_k": [...],
                "bic": [...],
                "aic": [...],
                "best_k": ...
            }
    """
    # ---------- input validation ----------
    X = np.asarray(X)
    n_samples, n_features = X.shape
    if X.ndim != 2:
        raise ValueError("X must have shape (n_samples, n_features)")
    if n_samples == 0:
        raise ValueError("X contains zero samples")
    if k_min < 1:
        raise ValueError("k_min must be >= 1")
    if k_max < k_min:
        raise ValueError("k_max must be >= k_min")

    # Prevent invalid cluster counts
    k_max = min(k_max, n_samples)

    candidate_k = list(range(k_min, k_max + 1))

    bic_scores = []
    aic_scores = []

    # ---------- model selection loop ----------
    for k in candidate_k:

        gmm = GaussianMixture(
            n_components=k,
            covariance_type=covariance_type,
            random_state=random_state,
        )

        gmm.fit(X)

        bic = gmm.bic(X)
        aic = gmm.aic(X)

        bic_scores.append(bic)
        aic_scores.append(aic)

    bic_scores = np.array(bic_scores)
    aic_scores = np.array(aic_scores)

    # ---------- select best model ----------
    best_idx = np.argmin(bic_scores)
    best_k = candidate_k[best_idx]

    # ---------- diagnostics ----------
    score_table = {
        "candidate_k": candidate_k,
        "bic": bic_scores,
        "aic": aic_scores,
        "best_k": best_k,
    }

    # ---------- optional printing ----------
    if verbose:
        print("GMM cluster number selection")
        print(f"  samples: {n_samples}")
        print(f"  feature dimension: {n_features}")
        print()
        print("  k | BIC | AIC")
        print("  ------------------------")

        for i, k in enumerate(candidate_k):
            print(f"  {k:2d} | {bic_scores[i]:.2f} | {aic_scores[i]:.2f}")

        print()
        print(f"  Selected cluster number (BIC): {best_k}")

    return best_k, score_table


def fit_gmm_clusters(
    X: np.ndarray,
    n_clusters: int,
    covariance_type: str = "full",
    random_state: int = 0,
    verbose: bool = True,
):
    """
    Fit a Gaussian Mixture Model and assign provisional cluster labels.

    Args:
        X               : PCA feature matrix, shape (n_spikes, n_features)
        n_clusters      : Number of GMM clusters
        covariance_type : GMM covariance type ("full", "diag", "tied", "spherical")
        random_state    : Random seed for reproducibility
        verbose         : If True, print cluster size summary

    Returns:
        provisional_labels  : Initial cluster labels assigned by the GMM, shape (n_spikes,)
        gmm_model           : Fitted GaussianMixture object
        fit_info            : Dictionary containing GMM diagnostics
    """

    # ---------- input validation ----------
    X = np.asarray(X)

    if X.ndim != 2:
        raise ValueError("X must have shape (n_samples, n_features)")

    n_samples, n_features = X.shape

    if n_samples == 0:
        raise ValueError("X contains zero samples")

    if n_clusters < 1:
        raise ValueError("n_clusters must be >= 1")

    if n_clusters > n_samples:
        raise ValueError("n_clusters cannot exceed number of samples")

    # ---------- fit GMM ----------
    gmm = GaussianMixture(
        n_components=n_clusters,
        covariance_type=covariance_type,
        random_state=random_state,
    )

    gmm.fit(X)

    provisional_labels = gmm.predict(X)

    # ---------- cluster size summary ----------
    cluster_sizes = {
        int(k): int(np.sum(provisional_labels == k))
        for k in range(n_clusters)
    }

    # ---------- diagnostics ----------
    fit_info = {
        "n_clusters": n_clusters,
        "n_samples": n_samples,
        "n_features": n_features,
        "weights": gmm.weights_,
        "means": gmm.means_,
        "covariances": gmm.covariances_,
        "converged": gmm.converged_,
        "n_iter": gmm.n_iter_,
        "lower_bound": gmm.lower_bound_,
        "cluster_sizes": cluster_sizes,
    }

    # ---------- optional printing ----------
    if verbose:
        print("GMM clustering completed")
        print(f"  clusters: {n_clusters}")
        print(f"  samples: {n_samples}")
        print()

        print("  cluster sizes:")
        for k in range(n_clusters):
            print(f"    cluster {k}: {cluster_sizes[k]}")

        print()

        if not gmm.converged_:
            print("WARNING: GMM did not converge")

    return provisional_labels, gmm, fit_info


def pretrim_cluster_points(
    X: np.ndarray,
    labels: np.ndarray,
    gmm_model,
    trim_mode: str = "mahalanobis",
    trim_percentile: float = 97.5,
    min_points_after_trim: int = 10,
    verbose: bool = True,
):
    """
    Lightly trim extreme points within each provisional cluster before
    evaluating cluster validity.

    Purpose:
        This step is only for obtaining more stable cluster validity metrics.
        It does not modify labels and is not the final rejection step.

    Args:
        X                       : PCA feature matrix, shape (n_spikes, n_features)
        labels                  : Provisional cluster labels, shape (n_spikes,)
        gmm_model               : Fitted GaussianMixture model
        trim_mode               : Currently only supports "mahalanobis"
        trim_percentile         : Percentile threshold used within each cluster
        min_points_after_trim   : Minimum number of points to retain in a cluster after pre-trim
        verbose                 : If True, print pre-trim summary

    Returns:
        trimmed_mask    : Boolean mask of shape (n_spikes,)
            True = retained for cluster validity evaluation
            False = temporarily trimmed for metric estimation

        pretrim_info    : Dictionary containing per-cluster trim diagnostics
    """

    # ---------- input validation ----------
    X = np.asarray(X)
    labels = np.asarray(labels)

    if X.ndim != 2:
        raise ValueError("X must have shape (n_samples, n_features)")

    if labels.ndim != 1:
        raise ValueError("labels must have shape (n_samples,)")

    if X.shape[0] != labels.shape[0]:
        raise ValueError("X and labels must have the same number of samples")

    if trim_mode != "mahalanobis":
        raise ValueError("Currently only trim_mode='mahalanobis' is supported")

    if not (0 < trim_percentile < 100):
        raise ValueError("trim_percentile must be between 0 and 100")

    if min_points_after_trim < 1:
        raise ValueError("min_points_after_trim must be >= 1")

    n_samples, n_features = X.shape
    n_clusters = gmm_model.n_components

    trimmed_mask = np.ones(n_samples, dtype=bool)
    cluster_stats = {}

    # ---------- helper: Mahalanobis distance ----------
    def mahalanobis_distance_to_component(X_k, mean_k, cov_k):
        """
        Compute Mahalanobis distance from points X_k to one Gaussian component.
        """
        # Small regularization for numerical stability
        reg = 1e-9 * np.eye(cov_k.shape[0])
        cov_k_reg = cov_k + reg

        diff = X_k - mean_k
        inv_cov = np.linalg.inv(cov_k_reg)

        # Squared Mahalanobis distance for each row
        d2 = np.einsum("ij,jk,ik->i", diff, inv_cov, diff)

        # Numerical guard against tiny negative values from precision
        d2 = np.maximum(d2, 0.0)

        return np.sqrt(d2)

    # ---------- pre-trim per cluster ----------
    for k in range(n_clusters):
        cluster_mask = labels == k
        idx_k = np.where(cluster_mask)[0]
        n_before = idx_k.size

        if n_before == 0:
            cluster_stats[int(k)] = {
                "n_before": 0,
                "n_after": 0,
                "n_trimmed": 0,
                "trim_percentile": trim_percentile,
                "distance_threshold": np.nan,
            }
            continue

        X_k = X[cluster_mask]
        mean_k = gmm_model.means_[k]

        if gmm_model.covariance_type == "full":
            cov_k = gmm_model.covariances_[k]
        elif gmm_model.covariance_type == "diag":
            cov_k = np.diag(gmm_model.covariances_[k])
        elif gmm_model.covariance_type == "tied":
            cov_k = gmm_model.covariances_
        elif gmm_model.covariance_type == "spherical":
            cov_k = np.eye(n_features) * gmm_model.covariances_[k]
        else:
            raise ValueError(f"Unsupported covariance_type: {gmm_model.covariance_type}")

        distances = mahalanobis_distance_to_component(X_k, mean_k, cov_k)

        threshold = np.percentile(distances, trim_percentile)
        keep_local = distances <= threshold

        # Prevent over-trimming small clusters
        n_keep = int(np.sum(keep_local))
        if n_keep < min_points_after_trim:
            order = np.argsort(distances)
            keep_local = np.zeros_like(distances, dtype=bool)
            keep_local[order[:min(min_points_after_trim, n_before)]] = True

        trimmed_mask[idx_k] = keep_local

        n_after = int(np.sum(keep_local))
        n_trimmed = n_before - n_after

        cluster_stats[int(k)] = {
            "n_before": int(n_before),
            "n_after": int(n_after),
            "n_trimmed": int(n_trimmed),
            "trim_percentile": float(trim_percentile),
            "distance_threshold": float(threshold),
        }

    pretrim_info = {
        "trim_mode": trim_mode,
        "trimmed_mask": trimmed_mask,
        "cluster_stats": cluster_stats,
    }

    # ---------- optional printing ----------
    if verbose:
        print("Pre-trim completed")
        print(f"  mode: {trim_mode}")
        print(f"  trim_percentile: {trim_percentile}")
        print(f"  min_points_after_trim: {min_points_after_trim}")
        print()

        print("  cluster pre-trim summary:")
        for k in range(n_clusters):
            s = cluster_stats[int(k)]
            print(
                f"    cluster {k}: "
                f"before={s['n_before']}, "
                f"after={s['n_after']}, "
                f"trimmed={s['n_trimmed']}, "
                f"threshold={s['distance_threshold']:.4f}"
            )

    return trimmed_mask, pretrim_info


def assess_cluster_validity(
    X: np.ndarray,
    labels: np.ndarray,
    trimmed_mask: np.ndarray,
    gmm_model,
    min_cluster_size: int = 20,
    max_cluster_spread: float | None = None,
    verbose: bool = True,
):
    """
    Evaluate whether each cluster is valid after light pre-trim.

    Args:
        X                   : PCA feature matrix (n_spikes, n_features)
        labels              : Provisional cluster labels from GMM
        trimmed_mask        : Boolean mask indicating points retained for cluster metric estimation (from pretrim step)
        gmm_model           : Fitted GaussianMixture model
        min_cluster_size    : Minimum number of trimmed points required for a valid cluster
        max_cluster_spread  : Optional upper threshold on cluster spread
        verbose             : Print summary of cluster validity

    Returns:
        valid_clusters      : List of cluster ids that passed validity rules
        invalid_clusters    : List of rejected cluster ids
        cluster_metrics     : Dict containing per-cluster metrics
    """

    # ---------- input validation ----------
    X = np.asarray(X)
    labels = np.asarray(labels)
    trimmed_mask = np.asarray(trimmed_mask)

    if X.ndim != 2:
        raise ValueError("X must have shape (n_samples, n_features)")

    if labels.ndim != 1:
        raise ValueError("labels must have shape (n_samples,)")

    if trimmed_mask.ndim != 1:
        raise ValueError("trimmed_mask must have shape (n_samples,)")

    if not (X.shape[0] == labels.shape[0] == trimmed_mask.shape[0]):
        raise ValueError("X, labels, and trimmed_mask must have same length")

    n_samples, n_features = X.shape
    n_clusters = gmm_model.n_components

    valid_clusters = []
    invalid_clusters = []
    cluster_metrics = {}

    # ---------- evaluate clusters ----------
    for k in range(n_clusters):

        raw_mask = labels == k
        trimmed_cluster_mask = raw_mask & trimmed_mask

        n_raw = int(np.sum(raw_mask))
        n_trimmed = int(np.sum(trimmed_cluster_mask))

        rejection_reasons = []

        # ---------- size check ----------
        if n_trimmed < min_cluster_size:
            rejection_reasons.append("size_below_min")

        # ---------- compute spread ----------
        spread = np.nan

        if n_trimmed > 0:

            X_k = X[trimmed_cluster_mask]
            mean_k = gmm_model.means_[k]

            if gmm_model.covariance_type == "full":
                cov_k = gmm_model.covariances_[k]

            elif gmm_model.covariance_type == "diag":
                cov_k = np.diag(gmm_model.covariances_[k])

            elif gmm_model.covariance_type == "tied":
                cov_k = gmm_model.covariances_

            elif gmm_model.covariance_type == "spherical":
                cov_k = np.eye(n_features) * gmm_model.covariances_[k]

            else:
                raise ValueError("Unsupported covariance_type")

            d = mahalanobis_distance(X_k, mean_k, cov_k)
            spread = float(np.mean(d))

        # ---------- spread check ----------
        if max_cluster_spread is not None:
            if not np.isnan(spread) and spread > max_cluster_spread:
                rejection_reasons.append("spread_above_max")

        # ---------- final validity ----------
        is_valid = len(rejection_reasons) == 0

        if is_valid:
            valid_clusters.append(int(k))
        else:
            invalid_clusters.append(int(k))

        cluster_metrics[int(k)] = {
            "n_points_raw": int(n_raw),
            "n_points_trimmed": int(n_trimmed),
            "spread": float(spread),
            "is_valid": bool(is_valid),
            "rejection_reasons": rejection_reasons,
        }

    # ---------- printing ----------
    if verbose:
        print("Cluster validity assessment")
        print(f"  min_cluster_size: {min_cluster_size}")
        print(f"  max_cluster_spread: {max_cluster_spread}")
        print()

        for k in range(n_clusters):

            m = cluster_metrics[k]

            print(
                f"  cluster {k}: "
                f"raw={m['n_points_raw']}, "
                f"trimmed={m['n_points_trimmed']}, "
                f"spread={m['spread']:.3f}, "
                f"valid={m['is_valid']}"
            )

            if not m["is_valid"]:
                print(f"    rejection reasons: {m['rejection_reasons']}")

        print()

    return valid_clusters, invalid_clusters, cluster_metrics


def reject_invalid_clusters(
    labels: np.ndarray,
    invalid_clusters: list,
    invalid_label: int = -1,
):
    """
    Convert all points belonging to invalid clusters into invalid_label.

    Args:
        labels          : Cluster labels, shape (n_spikes,)
        invalid_clusters: List of cluster ids to reject completely
        invalid_label   : Label assigned to rejected points

    Returns:
        labels_after_cluster_filter:
            Updated labels with invalid clusters mapped to invalid_label
    """

    labels = np.asarray(labels)

    if labels.ndim != 1:
        raise ValueError("labels must have shape (n_samples,)")

    labels_after_cluster_filter = labels.copy()

    if len(invalid_clusters) == 0:
        return labels_after_cluster_filter

    invalid_clusters = np.asarray(invalid_clusters)

    reject_mask = np.isin(labels_after_cluster_filter, invalid_clusters)
    labels_after_cluster_filter[reject_mask] = invalid_label

    return labels_after_cluster_filter


def reject_marginal_points(
    X: np.ndarray,
    labels: np.ndarray,
    gmm_model,
    valid_clusters: list,
    method: str = "mahalanobis",
    mahalanobis_percentile: float = 99.0,
    invalid_label: int = -2,
    verbose: bool = True,
):
    """
    Perform final point-level rejection within valid clusters.

    Args:
        X                   : PCA feature matrix, shape (n_spikes, n_features)
        labels              : Labels after cluster filtering
        gmm_model           : Fitted GaussianMixture model
        valid_clusters      : List of cluster ids considered valid
        method              : Currently supports "mahalanobis"
        mahalanobis_percentile: Percentile threshold used for marginal-point rejection
        invalid_label       : Label assigned to rejected marginal points
        verbose             : Print summary of point rejection

    Returns:
        final_labels        : Labels after point-level rejection

        point_filter_info   : Dict containing rejection diagnostics
    """

    # ---------- input validation ----------
    X = np.asarray(X)
    labels = np.asarray(labels)

    if X.ndim != 2:
        raise ValueError("X must have shape (n_samples, n_features)")

    if labels.ndim != 1:
        raise ValueError("labels must have shape (n_samples,)")

    if X.shape[0] != labels.shape[0]:
        raise ValueError("X and labels must have same number of samples")

    if method != "mahalanobis":
        raise ValueError("Currently only method='mahalanobis' is supported")

    n_samples, n_features = X.shape
    n_clusters = gmm_model.n_components

    final_labels = labels.copy()

    cluster_stats = {}

    # ---------- iterate clusters ----------
    for k in valid_clusters:

        cluster_mask = final_labels == k
        idx_k = np.where(cluster_mask)[0]

        n_input = idx_k.size

        if n_input == 0:

            cluster_stats[int(k)] = {
                "n_input": 0,
                "n_retained": 0,
                "n_rejected": 0,
                "threshold": np.nan,
            }

            continue

        X_k = X[cluster_mask]
        mean_k = gmm_model.means_[k]

        if gmm_model.covariance_type == "full":
            cov_k = gmm_model.covariances_[k]

        elif gmm_model.covariance_type == "diag":
            cov_k = np.diag(gmm_model.covariances_[k])

        elif gmm_model.covariance_type == "tied":
            cov_k = gmm_model.covariances_

        elif gmm_model.covariance_type == "spherical":
            cov_k = np.eye(n_features) * gmm_model.covariances_[k]

        else:
            raise ValueError("Unsupported covariance_type")

        distances = mahalanobis_distance(X_k, mean_k, cov_k)

        threshold = np.percentile(distances, mahalanobis_percentile)

        reject_local = distances > threshold

        reject_idx = idx_k[reject_local]

        final_labels[reject_idx] = invalid_label

        n_rejected = int(np.sum(reject_local))
        n_retained = n_input - n_rejected

        cluster_stats[int(k)] = {
            "n_input": int(n_input),
            "n_retained": int(n_retained),
            "n_rejected": int(n_rejected),
            "threshold": float(threshold),
        }

    point_filter_info = {
        "method": method,
        "cluster_stats": cluster_stats,
    }

    # ---------- optional printing ----------
    if verbose:
        print("Marginal point rejection")
        print(f"  method: {method}")
        print(f"  mahalanobis_percentile: {mahalanobis_percentile}")
        print()

        for k in valid_clusters:

            s = cluster_stats[k]

            print(
                f"  cluster {k}: "
                f"input={s['n_input']}, "
                f"retained={s['n_retained']}, "
                f"rejected={s['n_rejected']}, "
                f"threshold={s['threshold']:.4f}"
            )

        print()

    return final_labels, point_filter_info


def build_clustering_diagnostics(
    X: np.ndarray,
    pca_info: dict,
    best_k: int,
    score_table: dict,
    fit_info: dict,
    provisional_labels: np.ndarray,
    labels_after_cluster_filter: np.ndarray,
    final_labels: np.ndarray,
    pretrim_info: dict,
    valid_clusters: list,
    invalid_clusters: list,
    cluster_metrics: dict,
    point_filter_info: dict,
    invalid_label_cluster: int = -1,
    invalid_label_point: int = -2,
    pipeline_params: dict | None = None,
):
    """
    Gather all intermediate and final clustering results into one
    diagnostics dictionary.

    Args:
        X                   : PCA feature matrix, shape (n_spikes, n_features)
        pca_info            : Dictionary returned by compute_spike_pca
        best_k              : Selected number of GMM clusters
        score_table         : Dictionary returned by select_gmm_cluster_number
        fit_info            : Dictionary returned by fit_gmm_clusters
        provisional_labels  : Initial hard labels from GMM
        labels_after_cluster_filter: Labels after rejecting invalid clusters
        final_labels        : Labels after final marginal-point rejection
        pretrim_info        : Dictionary returned by pretrim_cluster_points
        valid_clusters      : List of valid cluster ids
        invalid_clusters    : List of invalid cluster ids
        cluster_metrics     : Dictionary returned by assess_cluster_validity
        point_filter_info   : Dictionary returned by reject_marginal_points
        invalid_label_cluster: Label used for cluster-level rejection
        invalid_label_point : Label used for point-level rejection
        pipeline_params     : Optional dictionary of pipeline runtime parameters

    Returns:
        diagnostics         : Dictionary containing all intermediate results and summaries
    """

    # ---------- input normalization ----------
    X = np.asarray(X)
    provisional_labels = np.asarray(provisional_labels)
    labels_after_cluster_filter = np.asarray(labels_after_cluster_filter)
    final_labels = np.asarray(final_labels)

    if X.ndim != 2:
        raise ValueError("X must have shape (n_spikes, n_features)")

    if provisional_labels.ndim != 1:
        raise ValueError("provisional_labels must have shape (n_spikes,)")

    if labels_after_cluster_filter.ndim != 1:
        raise ValueError("labels_after_cluster_filter must have shape (n_spikes,)")

    if final_labels.ndim != 1:
        raise ValueError("final_labels must have shape (n_spikes,)")

    n_spikes = X.shape[0]

    if not (
        provisional_labels.shape[0] == n_spikes
        and labels_after_cluster_filter.shape[0] == n_spikes
        and final_labels.shape[0] == n_spikes
    ):
        raise ValueError("All label arrays must have the same length as X")

    # ---------- summary counts ----------
    n_spikes_cluster_rejected = int(np.sum(labels_after_cluster_filter == invalid_label_cluster))
    n_spikes_point_rejected = int(np.sum(final_labels == invalid_label_point))
    n_spikes_final_valid = int(
        np.sum(
            (final_labels != invalid_label_cluster) &
            (final_labels != invalid_label_point)
        )
    )

    unique_labels, unique_counts = np.unique(final_labels, return_counts=True)
    final_label_counts = {
        int(label): int(count)
        for label, count in zip(unique_labels, unique_counts)
    }

    # ---------- diagnostics dict ----------
    diagnostics = {
        "pipeline_params": {} if pipeline_params is None else pipeline_params,

        "summary": {
            "n_spikes_total": int(n_spikes),
            "n_spikes_cluster_rejected": int(n_spikes_cluster_rejected),
            "n_spikes_point_rejected": int(n_spikes_point_rejected),
            "n_spikes_final_valid": int(n_spikes_final_valid),
            "best_k": int(best_k),
            "valid_clusters": [int(k) for k in valid_clusters],
            "invalid_clusters": [int(k) for k in invalid_clusters],
            "final_label_counts": final_label_counts,
        },

        "pca": {
            "X": X,
            "n_spikes": int(pca_info["n_spikes"]),
            "n_samples": int(pca_info["n_samples"]),
            "n_components": int(pca_info["n_components"]),
            "explained_variance_ratio": np.asarray(pca_info["explained_variance_ratio"]),
            "explained_variance": np.asarray(pca_info["explained_variance"]),
            "singular_values": np.asarray(pca_info["singular_values"]),
            "total_explained_variance_ratio": float(pca_info["total_explained_variance_ratio"]),
        },

        "model_selection": {
            "criterion_used": "BIC",
            "candidate_k": list(score_table["candidate_k"]),
            "bic": np.asarray(score_table["bic"]),
            "aic": np.asarray(score_table["aic"]),
            "best_k": int(score_table["best_k"]),
        },

        "gmm": {
            "n_clusters": int(fit_info["n_clusters"]),
            "n_samples": int(fit_info["n_samples"]),
            "n_features": int(fit_info["n_features"]),
            "weights": np.asarray(fit_info["weights"]),
            "means": np.asarray(fit_info["means"]),
            "covariances": np.asarray(fit_info["covariances"]),
            "converged": bool(fit_info["converged"]),
            "n_iter": int(fit_info["n_iter"]),
            "lower_bound": float(fit_info["lower_bound"]),
            "cluster_sizes": dict(fit_info["cluster_sizes"]),
        },

        "labels": {
            "provisional": provisional_labels,
            "after_cluster_filter": labels_after_cluster_filter,
            "final": final_labels,
        },

        "pretrim": {
            "trim_mode": pretrim_info["trim_mode"],
            "trimmed_mask": np.asarray(pretrim_info["trimmed_mask"]),
            "cluster_stats": pretrim_info["cluster_stats"],
        },

        "cluster_metrics": cluster_metrics,

        "point_filter": point_filter_info,
    }

    return diagnostics


def cluster_spikes_gmm_pipeline(
    waveforms: np.ndarray,
    n_pca_components: int = 3,
    k_min: int = 1,
    k_max: int = 6,
    covariance_type: str = "full",
    pretrim_percentile: float = 97.5,
    min_points_after_trim: int = 10,
    min_cluster_size: int = 20,
    max_cluster_spread: float | None = None,
    mahalanobis_percentile: float = 95.0,
    invalid_label_cluster: int = -1,
    invalid_label_point: int = -2,
    random_state: int = 0,
    verbose: bool = True,
):
    """
    Full spike clustering pipeline using PCA + GMM + cluster/point filtering.

    Pipeline:
        1. Compute PCA features
        2. Select cluster number using GMM BIC model selection
        3. Fit provisional GMM clusters
        4. Light pre-trim within each cluster for stable metric estimation
        5. Assess cluster validity
        6. Reject invalid clusters entirely
        7. Reject marginal points within valid clusters
        8. Build diagnostics object

    Args:
        waveforms           : Array of shape (n_spikes, n_samples)
        n_pca_components    : Number of PCA components used for clustering
        k_min               : Minimum candidate cluster count for model selection
        k_max               : Maximum candidate cluster count for model selection
        covariance_type     : GMM covariance type
        pretrim_percentile  : Percentile used for temporary pre-trim before cluster validity assessment
        min_points_after_trim: Minimum points to retain per cluster during pre-trim
        min_cluster_size    : Minimum trimmed cluster size required to keep a cluster valid
        max_cluster_spread  : Optional maximum allowed mean Mahalanobis distance for a valid cluster
        mahalanobis_percentile: Percentile threshold for final marginal-point rejection
        invalid_label_cluster: Label assigned to spikes rejected because their cluster is invalid
        invalid_label_point : Label assigned to spikes rejected as marginal points
        random_state        : Random seed for reproducibility
        verbose             : If True, print progress at each stage

    Returns:
        final_labels:
            Final labels after all filtering, shape (n_spikes,)

        X:
            PCA feature matrix, shape (n_spikes, n_pca_components)

        diagnostics:
            Dictionary containing intermediate and final diagnostics
    """

    if invalid_label_cluster == invalid_label_point:
        raise ValueError("invalid_label_cluster and invalid_label_point must be different")

    pipeline_params = {
        "n_pca_components": int(n_pca_components),
        "k_min": int(k_min),
        "k_max": int(k_max),
        "covariance_type": covariance_type,
        "pretrim_percentile": float(pretrim_percentile),
        "min_points_after_trim": int(min_points_after_trim),
        "min_cluster_size": int(min_cluster_size),
        "max_cluster_spread": max_cluster_spread,
        "mahalanobis_percentile": float(mahalanobis_percentile),
        "invalid_label_cluster": int(invalid_label_cluster),
        "invalid_label_point": int(invalid_label_point),
        "random_state": int(random_state),
    }

    # ---------- 1. PCA ----------
    if verbose:
        print("=" * 60)
        print("Step 1/8: PCA")
        print("=" * 60)

    X, pca_model, pca_info = compute_spike_pca(
        waveforms=waveforms,
        n_components=n_pca_components,
        verbose=verbose,
    )

    # ---------- 2. Select cluster number ----------
    if verbose:
        print("=" * 60)
        print("Step 2/8: Select GMM cluster number")
        print("=" * 60)

    best_k, score_table = select_gmm_cluster_number(
        X=X,
        k_min=k_min,
        k_max=k_max,
        covariance_type=covariance_type,
        random_state=random_state,
        verbose=verbose,
    )

    # ---------- 3. Fit GMM ----------
    if verbose:
        print("=" * 60)
        print("Step 3/8: Fit GMM clusters")
        print("=" * 60)

    provisional_labels, gmm_model, fit_info = fit_gmm_clusters(
        X=X,
        n_clusters=best_k,
        covariance_type=covariance_type,
        random_state=random_state,
        verbose=verbose,
    )

    # ---------- 4. Pre-trim ----------
    if verbose:
        print("=" * 60)
        print("Step 4/8: Pre-trim cluster tails")
        print("=" * 60)

    trimmed_mask, pretrim_info = pretrim_cluster_points(
        X=X,
        labels=provisional_labels,
        gmm_model=gmm_model,
        trim_mode="mahalanobis",
        trim_percentile=pretrim_percentile,
        min_points_after_trim=min_points_after_trim,
        verbose=verbose,
    )

    # ---------- 5. Assess cluster validity ----------
    if verbose:
        print("=" * 60)
        print("Step 5/8: Assess cluster validity")
        print("=" * 60)

    valid_clusters, invalid_clusters, cluster_metrics = assess_cluster_validity(
        X=X,
        labels=provisional_labels,
        trimmed_mask=trimmed_mask,
        gmm_model=gmm_model,
        min_cluster_size=min_cluster_size,
        max_cluster_spread=max_cluster_spread,
        verbose=verbose,
    )

    # ---------- 6. Reject invalid clusters ----------
    if verbose:
        print("=" * 60)
        print("Step 6/8: Reject invalid clusters")
        print("=" * 60)
        print(f"  invalid clusters: {invalid_clusters}")
        print(f"  invalid_label_cluster: {invalid_label_cluster}")
        print()

    labels_after_cluster_filter = reject_invalid_clusters(
        labels=provisional_labels,
        invalid_clusters=invalid_clusters,
        invalid_label=invalid_label_cluster,
    )

    # ---------- 7. Reject marginal points ----------
    if verbose:
        print("=" * 60)
        print("Step 7/8: Reject marginal points")
        print("=" * 60)

    final_labels, point_filter_info = reject_marginal_points(
        X=X,
        labels=labels_after_cluster_filter,
        gmm_model=gmm_model,
        valid_clusters=valid_clusters,
        method="mahalanobis",
        mahalanobis_percentile=mahalanobis_percentile,
        invalid_label=invalid_label_point,
        verbose=verbose,
    )

    # ---------- 8. Build diagnostics ----------
    if verbose:
        print("=" * 60)
        print("Step 8/8: Build diagnostics")
        print("=" * 60)

    diagnostics = build_clustering_diagnostics(
        X=X,
        pca_info=pca_info,
        best_k=best_k,
        score_table=score_table,
        fit_info=fit_info,
        provisional_labels=provisional_labels,
        labels_after_cluster_filter=labels_after_cluster_filter,
        final_labels=final_labels,
        pretrim_info=pretrim_info,
        valid_clusters=valid_clusters,
        invalid_clusters=invalid_clusters,
        cluster_metrics=cluster_metrics,
        point_filter_info=point_filter_info,
        invalid_label_cluster=invalid_label_cluster,
        invalid_label_point=invalid_label_point,
        pipeline_params=pipeline_params,
    )

    if verbose:
        summary = diagnostics["summary"]

        print("=" * 60)
        print("Pipeline complete")
        print("=" * 60)
        print(f"  total spikes: {summary['n_spikes_total']}")
        print(f"  best_k: {summary['best_k']}")
        print(f"  valid clusters: {summary['valid_clusters']}")
        print(f"  invalid clusters: {summary['invalid_clusters']}")
        print(f"  cluster-rejected spikes ({invalid_label_cluster}): {summary['n_spikes_cluster_rejected']}")
        print(f"  marginal-rejected spikes ({invalid_label_point}): {summary['n_spikes_point_rejected']}")
        print(f"  final valid spikes: {summary['n_spikes_final_valid']}")
        print(f"  final label counts: {summary['final_label_counts']}")
        print()

    return final_labels, X, diagnostics