"""
stats.py - the statistics the paper reports, standard library only.

  mean_ci        mean with a percentile bootstrap confidence interval
  diff_ci        difference of two group means with a bootstrap CI
  perm_test      two-sided permutation test for a difference in means
  wilson         Wilson score interval for a proportion
  holm           Holm-Bonferroni adjustment for a family of p-values
  cohen_kappa    agreement between two coders (e.g. automated judge vs human)

All resampling is seeded so the numbers in the paper reproduce exactly.
"""
import math
import random
from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

B = 10000
SEED = 20261104


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def sd(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _pct(sorted_xs: List[float], q: float) -> float:
    if not sorted_xs:
        return float("nan")
    k = (len(sorted_xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (k - lo)


def mean_ci(xs: Sequence[float], alpha: float = 0.05, b: int = B, seed: int = SEED) -> Tuple[float, float, float]:
    xs = list(xs)
    if not xs:
        return (float("nan"),) * 3
    if len(xs) == 1:
        return xs[0], float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(xs)
    boots = sorted(mean([xs[rng.randrange(n)] for _ in range(n)]) for _ in range(b))
    return mean(xs), _pct(boots, alpha / 2), _pct(boots, 1 - alpha / 2)


def diff_ci(a: Sequence[float], b_: Sequence[float], alpha: float = 0.05, b: int = B,
            seed: int = SEED) -> Tuple[float, float, float]:
    """mean(a) - mean(b_), resampling each group independently."""
    a, b_ = list(a), list(b_)
    if not a or not b_:
        return (float("nan"),) * 3
    rng = random.Random(seed)
    na, nb = len(a), len(b_)
    boots = sorted(mean([a[rng.randrange(na)] for _ in range(na)]) - mean([b_[rng.randrange(nb)] for _ in range(nb)])
                   for _ in range(b))
    return mean(a) - mean(b_), _pct(boots, alpha / 2), _pct(boots, 1 - alpha / 2)


def perm_test(a: Sequence[float], b_: Sequence[float], b: int = B, seed: int = SEED) -> float:
    a, b_ = list(a), list(b_)
    if len(a) < 2 or len(b_) < 2:
        return float("nan")
    obs = abs(mean(a) - mean(b_))
    pooled = a + b_
    na = len(a)
    rng = random.Random(seed)
    hits = 0
    for _ in range(b):
        rng.shuffle(pooled)
        if abs(mean(pooled[:na]) - mean(pooled[na:])) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (b + 1)


def wilson(k: int, n: int, z: float = 1.959964) -> Tuple[float, float, float]:
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def holm(pvals: Dict[str, float]) -> Dict[str, float]:
    items = sorted(((p, k) for k, p in pvals.items() if not math.isnan(p)))
    m = len(items)
    out, running = {}, 0.0
    for i, (p, k) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    for k, p in pvals.items():
        out.setdefault(k, float("nan"))
    return out


def cohen_kappa(x: Sequence[str], y: Sequence[str]) -> float:
    if len(x) != len(y) or not x:
        return float("nan")
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    cx, cy = Counter(x), Counter(y)
    pe = sum(cx[c] * cy[c] for c in set(cx) | set(cy)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def fmt_ci(m: float, lo: float, hi: float, digits: int = 1) -> str:
    if math.isnan(m):
        return "n/a"
    if math.isnan(lo):
        return f"{m:.{digits}f}"
    return f"{m:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"


def fmt_p(p: Optional[float]) -> str:
    if p is None or math.isnan(p):
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.3f}"
