from ..base_module import SEOModule
from .weights import DEFAULT_WEIGHTS
from .util import add_score as _add_score
from .on_page import score_on_page
from .technical import score_technical
from .content import score_content


class ScoringModule(SEOModule):
    def __init__(self, config=None):
        super().__init__(config=config)
        self.scoring_config = self.config.get(self.module_name, {})
        # Start with defaults and let user override
        self.default_weights = {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_WEIGHTS.items()}
        for key, value in self.scoring_config.get("weights", {}).items():
            if key in self.default_weights:
                if isinstance(self.default_weights[key], dict) and isinstance(value, dict):
                    self.default_weights[key].update(value)
                else:
                    self.default_weights[key] = value
        if "category_weights" in self.scoring_config:
            self.default_weights["category_weights"].update(self.scoring_config["category_weights"])

    def analyze(self, url: str, full_report_data: dict = None) -> dict:
        if not full_report_data:
            return {self.module_name: {"scoring_status": "error", "error_message": "No report data."}}

        on_page_data = full_report_data.get("OnPageAnalyzer", {})
        tech_data = full_report_data.get("TechnicalSEOAnalyzer", {})
        content_data = full_report_data.get("ContentAnalyzer", {})

        scores = {
            "on_page": {"earned_points": 0, "max_points": 0, "issues": [], "successes": []},
            "technical": {"earned_points": 0, "max_points": 0, "issues": [], "successes": []},
            "content": {"earned_points": 0, "max_points": 0, "issues": [], "successes": []},
        }

        score_on_page(on_page_data, scores["on_page"], self.default_weights, _add_score)
        score_technical(tech_data, scores["technical"], self.default_weights, _add_score)
        score_content(content_data, scores["content"], self.default_weights, _add_score)

        final_scores = {}
        for category, data in scores.items():
            cat_score = (data["earned_points"] / data["max_points"] * 100) if data["max_points"] > 0 else 0
            final_scores[f"{category}_score_percent"] = round(max(0, min(cat_score, 100)), 1)
            final_scores[f"{category}_issues"] = data["issues"]
            final_scores[f"{category}_successes"] = data["successes"]

        overall_score = 0; total_weight = 0
        cat_weights = self.default_weights["category_weights"]
        for cat_name, weight in cat_weights.items():
            score_key = f"{cat_name.lower()}_score_percent"
            if score_key in final_scores and final_scores[score_key] is not None:
                overall_score += final_scores[score_key] * weight
                total_weight += weight
        final_scores["overall_seo_score_percent"] = round(overall_score / total_weight, 1) if total_weight > 0 else 0
        final_scores["scoring_status"] = "completed"
        return {self.module_name: final_scores}

