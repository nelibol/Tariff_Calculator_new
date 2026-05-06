import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from typing import Dict, Any, Union

st.set_page_config(page_title="Tariff Scoring Calculator", layout="wide")

# ---------------- CONFIG ----------------
SCORING_CONFIG = {
    "scoring_config": {
        "contract_duration_months": {
            "type": "numeric",
            "unit": "Monate",
            "display_name": "Vertragslaufzeit",
            "weight": 25,
            "buckets": [
                {"threshold": 0.0, "points": 10, "description": "0 Monate"},
                {"threshold": 1.0, "points": 10, "description": "1 Monat"},
                {"threshold": 2.0, "points": 10, "description": "2-6 Monate"},
                {"threshold": 7.0, "points": 10, "description": "7-12 Monate"},
                {"threshold": 13.0, "points": 3, "description": "13-24 Monate"}
            ],
            "threshold_range": [0, 36]
        },
        "price_guarantee_months": {
            "type": "numeric",
            "unit": "Monate",
            "display_name": "Dauer Preisgarantie",
            "weight": 20,
            "buckets": [
                {"threshold": 0.0, "points": 0, "description": "0 Monate"},
                {"threshold": 1.0, "points": 1, "description": "1-6 Monate"},
                {"threshold": 7.0, "points": 7, "description": "7-12 Monate"},
                {"threshold": 13.0, "points": 9, "description": "13-24 Monate"},
                {"threshold": 25.0, "points": 10, "description": "Ab 25 Monate"}
            ],
            "threshold_range": [0, 36]
        },
        "price_guarantee_kind": {
            "type": "categorical",
            "display_name": "Art der Preisgarantie",
            "weight": 10,
            "buckets": [
                {"label": "Keine Preisgarantie", "points": 0},
                {"label": "Energiepreisgarantie", "points": 3},
                {"label": "eingeschränkte Preisgarantie", "points": 8},
                {"label": "Preisgarantie", "points": 10},
                {"label": "Unbekannt", "points": 0}
            ]
        },
        "eco_tariff": {
            "type": "categorical",
            "display_name": "Ökostrom",
            "weight": 5,
            "buckets": [
                {"label": "Nein", "points": 8},
                {"label": "Ja", "points": 10}
            ]
        },
        "is_eco_plus": {
            "type": "categorical",
            "display_name": "Gütesiegel",
            "weight": 0,
            "buckets": [
                {"label": "Nein", "points": 8},
                {"label": "Ja", "points": 10}
            ]
        },
        "cancellation_rate": {
            "type": "percentage",
            "unit": "%",
            "display_name": "Stornoquote",
            "weight": 20,
            "buckets": [
                {"threshold": 0.0, "points": 10, "description": "0-4.99%"},
                {"threshold": 0.05, "points": 8, "description": "5-9.99%"},
                {"threshold": 0.1, "points": 6, "description": "10-14.99%"},
                {"threshold": 0.15, "points": 4, "description": "15-19.99%"},
                {"threshold": 0.2, "points": 0, "description": "Ab 20%"}
            ],
            "threshold_range": [0, 0.5]
        },
        "Rating_50_50": {
            "type": "numeric",
            "unit": "Rating",
            "display_name": "Anbieterbewertung",
            "weight": 10,
            "buckets": [
                {"threshold": 0.0, "points": 0, "description": "0-3.60"},
                {"threshold": 3.61, "points": 4, "description": "3.61-4.00"},
                {"threshold": 4.01, "points": 6, "description": "4.01-4.40"},
                {"threshold": 4.41, "points": 8, "description": "4.41-4.80"},
                {"threshold": 4.81, "points": 10, "description": "Ab 4.81"}
            ],
            "threshold_range": [0, 5]
        },
        "dynamic_tariff": {
            "type": "categorical",
            "display_name": "Dynamischer Tarif",
            "weight": 5,
            "buckets": [
                {"label": "Nein", "points": 10},
                {"label": "Ja", "points": 0}
            ]
        },
        "switching_status": {
            "type": "categorical",
            "display_name": "Switching Status",
            "weight": 5,
            "buckets": [
                {"label": "Nein", "points": 0},
                {"label": "Ja", "points": 10}
            ]
        }
    },
    "overall_weights": {
        "tarifnote": 40,
        "preisnote": 60
    },
    "price_score_max": 10.0,
    "price_score_step": 0.15
}
# ---------------- CALCULATOR ----------------
class ScoreCalculator:
    """Calculator for tariff scoring based on configuration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scoring_config = config['scoring_config']
        self.overall_weights = config['overall_weights']
        self.price_score_max = config['price_score_max']
        self.price_score_step = config['price_score_step']
    
    def calculate_numeric_score(self, value: float, criterion_config: Dict) -> int:
        """Calculate score for numeric/percentage type criteria"""
        buckets = criterion_config['buckets']
        sorted_buckets = sorted(buckets, key=lambda x: x['threshold'], reverse=True)
        
        for bucket in sorted_buckets:
            if value >= bucket['threshold']:
                return bucket['points']
        
        return 0
    
    def calculate_categorical_score(self, label: str, criterion_config: Dict) -> int:
        """Calculate score for categorical type criteria"""
        buckets = criterion_config['buckets']
        
        for bucket in buckets:
            if bucket['label'] == label:
                return bucket['points']
        
        return 0
    
    def calculate_criterion_score(self, criterion_name: str, value: Union[str, float]) -> Dict[str, Any]:
        """Calculate weighted score for a single criterion"""
        if criterion_name not in self.scoring_config:
            raise ValueError(f"Unknown criterion: {criterion_name}")
        
        criterion_config = self.scoring_config[criterion_name]
        criterion_type = criterion_config['type']
        weight = criterion_config['weight']
        
        if criterion_type in ['numeric', 'percentage']:
            raw_points = self.calculate_numeric_score(value, criterion_config)
        elif criterion_type == 'categorical':
            raw_points = self.calculate_categorical_score(value, criterion_config)
        else:
            raise ValueError(f"Unknown criterion type: {criterion_type}")
        
        weighted_score = (raw_points / 10.0) * weight
        
        return {
            'criterion': criterion_name,
            'display_name': criterion_config['display_name'],
            'value': value,
            'raw_points': raw_points,
            'weight': weight,
            'weighted_score': weighted_score,
            'max_weighted_score': weight
        }
    
    def calculate_tarifnote(self, inputs: Dict[str, Union[str, float]]) -> Dict[str, Any]:
        """Calculate the Tarifnote (tariff score) from all criteria"""
        results = []
        total_score = 0
        total_weight = 0
        
        for criterion_name, value in inputs.items():
            if criterion_name in self.scoring_config:
                result = self.calculate_criterion_score(criterion_name, value)
                results.append(result)
                total_score += result['weighted_score']
                total_weight += result['weight']
        
        if total_weight > 0:
            tarifnote = (total_score / total_weight) * 10
        else:
            tarifnote = 0
        
        return {
            'tarifnote': round(tarifnote, 2),
            'total_weighted_score': round(total_score, 2),
            'total_weight': total_weight,
            'details': results
        }
    
    def calculate_preisnote(self, price_rank: int, total_tariffs: int) -> float:
        """Calculate price score based on ranking"""
        if price_rank < 1 or total_tariffs < 1:
            return 0
        
        score = self.price_score_max - (price_rank - 1) * self.price_score_step
        return max(0, round(score, 2))
    
    def calculate_overall_score(self, tarifnote: float, preisnote: float) -> float:
        """Calculate the overall score combining tarifnote and preisnote"""
        tarif_weight = self.overall_weights['tarifnote']
        preis_weight = self.overall_weights['preisnote']
        
        overall = (tarifnote * tarif_weight + preisnote * preis_weight) / 100
        return round(overall, 2)

# ---------------- CHART ----------------
def gauge(val, title):
    return go.Figure(go.Indicator(mode="gauge+number",value=val,title={'text':title}))

# ---------------- MAIN ----------------
def main():
    calc = get_calc()

    # INIT HISTORY
    if "history" not in st.session_state:
        st.session_state["history"] = []

    st.title("⚡ Tariff Calculator")

    # SIDEBAR INPUTS
    inputs = {}
    with st.sidebar:
        st.header("Inputs")
        inputs["contract_duration_months"] = st.slider("Contract Duration",0,36,12)
        inputs["price_guarantee_months"] = st.slider("Price Guarantee",0,36,12)
        inputs["eco_tariff"] = st.selectbox("Eco Tariff",["Nein","Ja"])
        rank = st.number_input("Price Rank",1,100,1)

        if st.button("Calculate"):
            t = calc.calc_tarifnote(inputs)
            p = calc.calc_preisnote(rank)
            o = calc.calc_overall(t,p)

            # SAVE HISTORY
            st.session_state["history"].append({
                "tarifnote":t,
                "preisnote":p,
                "overall":o
            })

    # SHOW CURRENT
    if st.session_state["history"]:
        current = st.session_state["history"][-1]

        st.subheader("Current Score")
        c1,c2,c3 = st.columns(3)
        c1.plotly_chart(gauge(current["tarifnote"],"Tarifnote"),use_container_width=True)
        c2.plotly_chart(gauge(current["preisnote"],"Preisnote"),use_container_width=True)
        c3.plotly_chart(gauge(current["overall"],"Overall"),use_container_width=True)

        # HISTORY
        st.subheader("Previous Results")

        if len(st.session_state["history"]) > 1:
            for i, r in enumerate(st.session_state["history"][:-1][::-1],1):
                st.markdown(f"Run {i}")
                col1,col2,col3 = st.columns(3)
                col1.metric("Tarifnote",r["tarifnote"])
                col2.metric("Preisnote",r["preisnote"])
                col3.metric("Overall",r["overall"])
        else:
            st.info("No previous runs")

    # CLEAR BUTTON
    if st.sidebar.button("Clear History"):
        st.session_state["history"] = []

if __name__ == "__main__":
    main()
