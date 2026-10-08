"""
Anomaly detection and short-range forecasting over the scores the app already stores.

Anomaly: a source's latest trust or quality score drops well below its own recent history:
  >= 3 prior points: latest < mean - max(2 * stdev, 5)       (a 2-sigma drop, at least 5 points)
  1-2 prior points:  latest < previous - 10                   (not enough history for a stdev)
Forecast: least-squares slope of a daily series, applied from the latest value `horizon` days ahead.
"""
from dataclasses import dataclass
from statistics import StatisticsError, linear_regression, mean, stdev

HISTORY = 10          # prior points used as the baseline
MIN_DROP = 5.0        # ignore drops smaller than this many points, however unusual
FALLBACK_DROP = 10.0  # drop that counts when there's too little history for a stdev


@dataclass
class Anomaly:
    source: str
    measure: str        # 'trust score' | 'data quality'
    latest: float
    baseline: float     # mean of the prior points
    threshold: float    # latest had to fall below this

    @property
    def drop(self):
        return round(self.baseline - self.latest, 1)

    def to_dict(self):
        return {'source': self.source, 'measure': self.measure, 'latest': round(self.latest, 1),
                'baseline': round(self.baseline, 1), 'drop': self.drop, 'threshold': round(self.threshold, 1)}


def check_drop(values):
    """values: oldest -> newest. Returns (baseline, threshold) if the newest is an anomalous drop, else None."""
    if len(values) < 2:
        return None
    *prior, latest = values
    prior = prior[-HISTORY:]
    baseline = mean(prior)
    if len(prior) >= 3:
        threshold = baseline - max(2 * stdev(prior), MIN_DROP)
    else:
        threshold = prior[-1] - FALLBACK_DROP
    return (baseline, threshold) if latest < threshold else None


def detect_anomalies():
    from core.models import DataSource
    found = []
    for source in DataSource.objects.filter(is_active=True).order_by('name'):
        series = {
            'trust score': list(source.trust_scores.order_by('-calculated_at')
                                .values_list('overall_score', flat=True)[:HISTORY + 1])[::-1],
            'data quality': list(source.validations.order_by('-timestamp')
                                 .values_list('quality_score', flat=True)[:HISTORY + 1])[::-1],
        }
        for measure, values in series.items():
            hit = check_drop(values)
            if hit:
                found.append(Anomaly(source.name, measure, values[-1], *hit))
    return found


def forecast(dates, values, horizon=7):
    """Project a daily series `horizon` days past its last point. None if fewer than 3 points or no spread."""
    points = [(d, v) for d, v in zip(dates, values) if v is not None]
    if len(points) < 3:
        return None
    origin = points[0][0]
    xs = [(d - origin).days for d, _ in points]
    ys = [v for _, v in points]
    try:
        slope, _ = linear_regression(xs, ys)
    except StatisticsError:  # all points on the same day
        return None
    projected = min(100.0, max(0.0, ys[-1] + slope * horizon))
    return {'latest': round(ys[-1], 1), 'projected': round(projected, 1), 'slope_per_day': round(slope, 2),
            'horizon_days': horizon, 'points': len(points)}
