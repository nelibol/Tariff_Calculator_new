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
            "type": "numeric","display_name": "Vertragslaufzeit","weight": 25,
            "buckets":[{"threshold":0,"points":10},{"threshold":13,"points":3}],
            "threshold_range":[0,36]
        },
        "price_guarantee_months": {
            "type": "numeric","display_name": "Preisgarantie","weight": 20,
            "buckets":[{"threshold":0,"points":0},{"threshold":25,"points":10}],
            "threshold_range":[0,36]
        },
        "eco_tariff": {
            "type": "categorical","display_name": "Ökostrom","weight": 5,
            "buckets":[{"label":"Nein","points":8},{"label":"Ja","points":10}]
        }
    },
    "overall_weights": {"tarifnote":40,"preisnote":60},
    "price_score_max":10.0,
    "price_score_step":0.15
}

# ---------------- CALCULATOR ----------------
class ScoreCalculator:
    def __init__(self, config):
        self.config = config
        self.scoring_config = config['scoring_config']
        self.overall_weights = config['overall_weights']
        self.price_score_max = config['price_score_max']
        self.price_score_step = config['price_score_step']

    def calc_numeric(self, value, cfg):
        for b in sorted(cfg['buckets'], key=lambda x: x['threshold'], reverse=True):
            if value >= b['threshold']:
                return b['points']
        return 0

    def calc_categorical(self, value, cfg):
        for b in cfg['buckets']:
            if b['label'] == value:
                return b['points']
        return 0

    def calc_tarifnote(self, inputs):
        total = 0
        weight_sum = 0
        for k,v in inputs.items():
            cfg = self.scoring_config[k]
            if cfg['type']=="numeric":
                pts = self.calc_numeric(v,cfg)
            else:
                pts = self.calc_categorical(v,cfg)
            total += (pts/10)*cfg['weight']
            weight_sum += cfg['weight']
        return round((total/weight_sum)*10,2)

    def calc_preisnote(self, rank):
        return max(0, round(self.price_score_max-(rank-1)*self.price_score_step,2))

    def calc_overall(self, t,p):
        return round((t*40+p*60)/100,2)

@st.cache_resource
def get_calc():
    return ScoreCalculator(SCORING_CONFIG)

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
