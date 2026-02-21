"""Style Recommender model - recommends visual styles for infographics."""

from ml.models.style_recommender.model import StyleRecommender
from ml.models.style_recommender.inference import StyleRecommenderInference

__all__ = [
    "StyleRecommender",
    "StyleRecommenderInference",
]
