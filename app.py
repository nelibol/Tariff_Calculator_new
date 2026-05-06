import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, Union
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Tariff Scoring Calculator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Scoring configuration
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

# Initialize calculator
@st.cache_resource
def get_calculator():
    return ScoreCalculator(SCORING_CONFIG)

def create_gauge_chart(value: float, title: str, max_value: float = 10.0):
    """Create a gauge chart for score visualization"""
    # Determine color based on value
    if value >= 8:
        color = "#28a745"  # Green
    elif value >= 6:
        color = "#ffc107"  # Yellow
    elif value >= 4:
        color = "#fd7e14"  # Orange
    else:
        color = "#dc3545"  # Red

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 20}},
        delta={'reference': max_value / 2},
        gauge={
            'axis': {'range': [None, max_value], 'tickwidth': 1, 'tickcolor': "darkgray"},
            'bar': {'color': color},
            'bgcolor': "black",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, max_value * 0.4], 'color': '#ffebee'},
                {'range': [max_value * 0.4, max_value * 0.7], 'color': '#fff3e0'},
                {'range': [max_value * 0.7, max_value], 'color': '#e8f5e9'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))

    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="white",
        font={'color': "darkblue", 'family': "Arial"}
    )

    return fig

def create_breakdown_chart(details: list):
    """Create a horizontal bar chart for criterion breakdown"""
    df = pd.DataFrame(details)
    df = df.sort_values('weighted_score', ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df['display_name'],
        x=df['weighted_score'],
        orientation='h',
        marker=dict(
            color=df['weighted_score'],
            colorscale='RdYlGn',
            showscale=False,
            line=dict(color='white', width=1)
        ),
        text=df['weighted_score'].round(2),
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>' +
                      'Weighted Score: %{x:.2f}<br>' +
                      'Raw Points: %{customdata[0]}/10<br>' +
                      'Weight: %{customdata[1]}%<br>' +
                      '<extra></extra>',
        customdata=df[['raw_points', 'weight']]
    ))

    fig.update_layout(
        title="Criterion Contribution to Tarifnote",
        xaxis_title="Weighted Score",
        yaxis_title="",
        height=400,
        margin=dict(l=150, r=20, t=60, b=40),
        paper_bgcolor="white",
        plot_bgcolor="rgba(240,240,240,0.3)"
    )

    return fig

def create_points_chart(details: list):
    """Create a chart showing raw points vs weight for each criterion"""
    df = pd.DataFrame(details)

    fig = go.Figure()

    # Add raw points
    fig.add_trace(go.Bar(
        name='Raw Points',
        x=df['display_name'],
        y=df['raw_points'],
        marker_color='lightblue',
        text=df['raw_points'],
        textposition='auto',
    ))

    # Add weight as line
    fig.add_trace(go.Scatter(
        name='Weight (%)',
        x=df['display_name'],
        y=df['weight'],
        mode='lines+markers',
        marker=dict(size=10, color='red'),
        line=dict(color='red', width=2),
        yaxis='y2'
    ))

    fig.update_layout(
        title="Raw Points vs Weight by Criterion",
        xaxis=dict(title="", tickangle=-45),
        yaxis=dict(title="Raw Points (0-10)", side='left', range=[0, 10]),
        yaxis2=dict(title="Weight (%)", side='right', overlaying='y', range=[0, 30]),
        height=400,
        margin=dict(l=60, r=60, t=60, b=100),
        legend=dict(x=0.01, y=0.99),
        hovermode='x unified',
        paper_bgcolor="white",
        plot_bgcolor="rgba(240,240,240,0.3)"
    )

    return fig

def initialize_history():
    """Initialize history in session state if not present"""
    if 'score_history' not in st.session_state:
        st.session_state['score_history'] = []

def add_to_history(inputs: Dict, price_rank: int, total_tariffs: int, 
                   tarifnote: float, preisnote: float, overall_score: float, tarif_result: Dict):
    """Add a score calculation to history with full config"""
    history_entry = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'inputs': inputs.copy(),
        'price_rank': price_rank,
        'total_tariffs': total_tariffs,
        'tarifnote': tarifnote,
        'preisnote': preisnote,
        'overall_score': overall_score,
        'config_details': tarif_result['details']  # Store full config details
    }
    st.session_state['score_history'].append(history_entry)

def get_history_dataframe():
    """Convert history to a displayable dataframe"""
    if not st.session_state['score_history']:
        return None
    
    history_data = []
    for idx, entry in enumerate(st.session_state['score_history']):
        row = {
            '#': idx + 1,
            'Timestamp': entry['timestamp'],
            'Tarifnote': entry['tarifnote'],
            'Preisnote': entry['preisnote'],
            'Overall Score': entry['overall_score'],
            'Price Rank': entry['price_rank'],
            'Total Tariffs': entry['total_tariffs']
        }
        history_data.append(row)
    
    return pd.DataFrame(history_data)

def display_config_details(entry: Dict, entry_index: int):
    """Display detailed config for a specific history entry"""
    st.subheader(f"📋 Configuration Details - Calculation #{entry_index + 1}")
    st.markdown(f"**Timestamp:** {entry['timestamp']}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tarifnote", entry['tarifnote'])
    with col2:
        st.metric("Preisnote", entry['preisnote'])
    with col3:
        st.metric("Overall Score", entry['overall_score'])
    with col4:
        st.metric("Price Rank", f"{entry['price_rank']}/{entry['total_tariffs']}")
    
    st.markdown("---")
    st.markdown("### Input Values")
    
    # Display input values
    input_cols = st.columns(2)
    col_idx = 0
    for criterion_name, value in entry['inputs'].items():
        with input_cols[col_idx % 2]:
            st.write(f"**{criterion_name}:** {value}")
        col_idx += 1
    
    st.markdown("---")
    st.markdown("### Scoring Details")
    
    # Create detailed table
    df_config = pd.DataFrame(entry['config_details'])
    df_config_display = df_config[['display_name', 'value', 'raw_points', 'weight', 'weighted_score', 'max_weighted_score']].copy()
    df_config_display.columns = ['Criterion', 'Value', 'Raw Points', 'Weight (%)', 'Weighted Score', 'Max Score']
    df_config_display['Efficiency %'] = ((df_config_display['Weighted Score'] / df_config_display['Max Score']) * 100).round(1)
    
    st.dataframe(
        df_config_display.style.format({
            'Raw Points': '{:.0f}',
            'Weight (%)': '{:.0f}',
            'Weighted Score': '{:.2f}',
            'Max Score': '{:.2f}',
            'Efficiency %': '{:.1f}%'
        }).background_gradient(subset=['Efficiency %'], cmap='RdYlGn', vmin=0, vmax=100),
        use_container_width=True
    )

def display_history():
    """Display the score history"""
    st.subheader("📜 Score History")
    
    if not st.session_state['score_history']:
        st.info("No score calculations yet. Complete a calculation to see history.")
        return
    
    df_history = get_history_dataframe()
    
    # Display table
    st.dataframe(
        df_history.style.format({
            'Tarifnote': '{:.2f}',
            'Preisnote': '{:.2f}',
            'Overall Score': '{:.2f}'
        }).background_gradient(subset=['Overall Score'], cmap='RdYlGn', vmin=0, vmax=10),
        use_container_width=True,
        height=300
    )
    
    # Show statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Calculations", len(st.session_state['score_history']))
    with col2:
        avg_overall = df_history['Overall Score'].mean()
        st.metric("Avg Overall Score", f"{avg_overall:.2f}")
    with col3:
        max_overall = df_history['Overall Score'].max()
        st.metric("Best Overall Score", f"{max_overall:.2f}")
    with col4:
        min_overall = df_history['Overall Score'].min()
        st.metric("Worst Overall Score", f"{min_overall:.2f}")
    
    st.markdown("---")
    st.markdown("### View Detailed Configuration")
    
    # Create selectbox to view specific calculation details
    calculation_options = [f"Calculation #{i+1} ({entry['timestamp']})" 
                          for i, entry in enumerate(st.session_state['score_history'])]
    selected_calc = st.selectbox("Select a calculation to view details:", calculation_options)
    
    if selected_calc:
        selected_idx = int(selected_calc.split('#')[1].split()[0]) - 1
        display_config_details(st.session_state['score_history'][selected_idx], selected_idx)
    
    st.markdown("---")
    
    # Show history visualization
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_history['#'],
            y=df_history['Overall Score'],
            mode='lines+markers',
            name='Overall Score',
            line=dict(color='blue', width=2),
            marker=dict(size=8)
        ))
        fig.update_layout(
            title="Overall Score Trend",
            xaxis_title="Calculation #",
            yaxis_title="Score",
            height=300,
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_history['#'],
            y=df_history['Tarifnote'],
            mode='lines+markers',
            name='Tarifnote',
            line=dict(color='green', width=2),
            marker=dict(size=8)
        ))
        fig.add_trace(go.Scatter(
            x=df_history['#'],
            y=df_history['Preisnote'],
            mode='lines+markers',
            name='Preisnote',
            line=dict(color='orange', width=2),
            marker=dict(size=8)
        ))
        fig.update_layout(
            title="Tarifnote vs Preisnote Trend",
            xaxis_title="Calculation #",
            yaxis_title="Score",
            height=300,
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### Export History")
    
    # Export history
    col1, col2 = st.columns(2)
    with col1:
        csv = df_history.to_csv(index=False)
        st.download_button(
            label="📥 Download History (CSV)",
            data=csv,
            file_name="scoring_history.csv",
            mime="text/csv"
        )
    
    with col2:
        json_data = json.dumps(st.session_state['score_history'], indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Download History (JSON)",
            data=json_data,
            file_name="scoring_history.json",
            mime="application/json"
        )

def main():
    calculator = get_calculator()
    initialize_history()

    # Header
    st.title("⚡ Tariff Scoring Calculator Dashboard")
    st.markdown("---")

    # Sidebar for inputs
    with st.sidebar:
        st.header("📝 Input Parameters")
        st.markdown("Enter tariff details below:")

        inputs = {}

        # Create input fields for each criterion
        for criterion_name, config in calculator.scoring_config.items():
            st.markdown(f"**{config['display_name']}**")

            if config['type'] == 'categorical':
                labels = [b['label'] for b in config['buckets']]
                inputs[criterion_name] = st.selectbox(
                    f"{criterion_name}_select",
                    options=labels,
                    key=criterion_name,
                    label_visibility="collapsed"
                )
            elif config['type'] in ['numeric', 'percentage']:
                unit = config.get('unit', '')
                ranges = config.get('threshold_range', [0, 100])

                if config['type'] == 'percentage':
                    # For percentage, show as percentage but store as decimal
                    value = st.slider(
                        f"{criterion_name}_slider",
                        min_value=float(ranges[0]),
                        max_value=float(ranges[1]),
                        value=float(ranges[0]),
                        step=0.01,
                        format=f"%.2f",
                        key=criterion_name,
                        label_visibility="collapsed"
                    )
                    inputs[criterion_name] = value
                else:
                    # Use slider for numeric types (Vertragslaufzeit, Dauer Preisgarantie, Anbieterbewertung)
                    if criterion_name == 'Rating_50_50':
                        step = 0.01
                        value_default = 4.5
                    else:
                        step = 1.0
                        value_default = float((ranges[0] + ranges[1]) / 2)

                    inputs[criterion_name] = st.slider(
                        f"{criterion_name}_slider",
                        min_value=float(ranges[0]),
                        max_value=float(ranges[1]),
                        value=value_default,
                        step=step,
                        format=f"%.2f" if criterion_name == 'Rating_50_50' else "%.0f",
                        key=criterion_name,
                        label_visibility="collapsed"
                    )

            st.markdown("")

        st.markdown("---")
        st.markdown("**💰 Price Information**")
        price_rank = st.number_input(
            "Price Rank (1 = cheapest)",
            min_value=1,
            value=1,
            step=1
        )
        total_tariffs = st.number_input(
            "Total Number of Tariffs",
            min_value=1,
            value=100,
            step=1
        )

        calculate_button = st.button("🔄 Calculate Scores", type="primary", use_container_width=True)

    # Main content area
    if calculate_button or 'calculated' not in st.session_state:
        # Calculate scores
        tarif_result = calculator.calculate_tarifnote(inputs)
        preisnote = calculator.calculate_preisnote(price_rank, total_tariffs)
        overall_score = calculator.calculate_overall_score(tarif_result['tarifnote'], preisnote)

        # Add to history (passing tarif_result for full config details)
        add_to_history(inputs, price_rank, total_tariffs, tarif_result['tarifnote'], preisnote, overall_score, tarif_result)

        # Store in session state
        st.session_state['calculated'] = True
        st.session_state['tarif_result'] = tarif_result
        st.session_state['preisnote'] = preisnote
        st.session_state['overall_score'] = overall_score
        st.session_state['inputs'] = inputs
        st.session_state['price_rank'] = price_rank
        st.session_state['total_tariffs'] = total_tariffs

    if 'calculated' in st.session_state:
        tarif_result = st.session_state['tarif_result']
        preisnote = st.session_state['preisnote']
        overall_score = st.session_state['overall_score']
        price_rank = st.session_state['price_rank']
        total_tariffs = st.session_state['total_tariffs']

        # Display key metrics
        st.subheader("🎯 Score Summary")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.plotly_chart(
                create_gauge_chart(tarif_result['tarifnote'], "Tarifnote"),
                use_container_width=True
            )
        with col2:
            st.plotly_chart(
                create_gauge_chart(preisnote, "Preisnote"),
                use_container_width=True
            )
        with col3:
            st.plotly_chart(
                create_gauge_chart(overall_score, "Overall Score"),
                use_container_width=True
            )

        st.markdown("---")

        # Detailed breakdown
        st.subheader("📊 Detailed Breakdown")

        # Create tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Weighted Scores", "📉 Points & Weights", "📋 Data Table", "⚙️ Configuration", "📜 History"])

        with tab1:
            st.plotly_chart(create_breakdown_chart(tarif_result['details']), use_container_width=True)

            # Score composition pie chart
            col1, col2 = st.columns(2)

            with col1:
                fig = go.Figure(data=[go.Pie(
                    labels=['Tarifnote (40%)', 'Preisnote (60%)'],
                    values=[tarif_result['tarifnote'] * 0.4, preisnote * 0.6],
                    hole=.3,
                    marker=dict(colors=['#4CAF50', '#2196F3'])
                )])
                fig.update_layout(title="Overall Score Composition", height=300)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Create weight distribution chart
                df_weights = pd.DataFrame(tarif_result['details'])
                fig = go.Figure(data=[go.Pie(
                    labels=df_weights['display_name'],
                    values=df_weights['weight'],
                    hole=.3
                )])
                fig.update_layout(title="Criterion Weights Distribution", height=300)
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.plotly_chart(create_points_chart(tarif_result['details']), use_container_width=True)

            # Show efficiency (raw points vs weighted score)
            st.markdown("### Scoring Efficiency")
            df_details = pd.DataFrame(tarif_result['details'])
            df_details['efficiency'] = (df_details['weighted_score'] / df_details['max_weighted_score'] * 100).round(1)

            fig = go.Figure(data=[go.Bar(
                x=df_details['display_name'],
                y=df_details['efficiency'],
                marker=dict(
                    color=df_details['efficiency'],
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="Efficiency %")
                ),
                text=df_details['efficiency'].astype(str) + '%',
                textposition='auto'
            )])
            fig.update_layout(
                title="Criterion Efficiency (Achieved / Maximum Possible)",
                xaxis=dict(title="", tickangle=-45),
                yaxis=dict(title="Efficiency (%)", range=[0, 100]),
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.markdown("### Detailed Scores Table")
            df_table = pd.DataFrame(tarif_result['details'])
            df_table = df_table[['display_name', 'value', 'raw_points', 'weight', 'weighted_score', 'max_weighted_score']]
            df_table.columns = ['Criterion', 'Value', 'Raw Points', 'Weight (%)', 'Weighted Score', 'Max Weighted Score']
            df_table['Efficiency %'] = ((df_table['Weighted Score'] / df_table['Max Weighted Score']) * 100).round(1)

            st.dataframe(
                df_table.style.format({
                    'Raw Points': '{:.0f}',
                    'Weight (%)': '{:.0f}',
                    'Weighted Score': '{:.2f}',
                    'Max Weighted Score': '{:.2f}',
                    'Efficiency %': '{:.1f}%'
                }).background_gradient(subset=['Efficiency %'], cmap='RdYlGn', vmin=0, vmax=100),
                use_container_width=True,
                height=400
            )

            # Summary statistics
            st.markdown("### Summary Statistics")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Weighted Score", f"{tarif_result['total_weighted_score']:.2f}")
            with col2:
                st.metric("Total Weight", f"{tarif_result['total_weight']}%")
            with col3:
                avg_efficiency = df_table['Efficiency %'].mean()
                st.metric("Average Efficiency", f"{avg_efficiency:.1f}%")
            with col4:
                criteria_at_max = (df_table['Efficiency %'] == 100).sum()
                st.metric("Criteria at Max", f"{criteria_at_max}/{len(df_table)}")

        with tab4:
            st.markdown("### Scoring Configuration")

            # Show bucket information for each criterion
            for criterion_name, config in calculator.scoring_config.items():
                with st.expander(f"📌 {config['display_name']} ({criterion_name})"):
                    st.markdown(f"**Type:** {config['type']}")
                    st.markdown(f"**Weight:** {config['weight']}%")

                    if config['type'] == 'categorical':
                        df_buckets = pd.DataFrame(config['buckets'])
                        st.dataframe(df_buckets, use_container_width=True)
                    else:
                        df_buckets = pd.DataFrame(config['buckets'])
                        st.dataframe(df_buckets, use_container_width=True)

            st.markdown("### Overall Weights")
            st.json(calculator.overall_weights)

            st.markdown("### Price Score Configuration")
            st.json({
                "max_score": calculator.price_score_max,
                "step_per_rank": calculator.price_score_step
            })

        with tab5:
            display_history()

        st.markdown("---")

        # Export options
        st.subheader("💾 Export Results")
        col1, col2, col3 = st.columns(3)

        with col1:
            # Export as JSON
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "inputs": st.session_state['inputs'],
                "price_rank": st.session_state['price_rank'],
                "total_tariffs": st.session_state['total_tariffs'],
                "results": {
                    "tarifnote": tarif_result['tarifnote'],
                    "preisnote": preisnote,
                    "overall_score": overall_score,
                    "details": tarif_result['details']
                }
            }
            st.download_button(
                label="📥 Download Results (JSON)",
                data=json.dumps(export_data, indent=2, ensure_ascii=False),
                file_name="tariff_scoring_results.json",
                mime="application/json"
            )

        with col2:
            # Export as CSV
            df_export = pd.DataFrame(tarif_result['details'])
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download Details (CSV)",
                data=csv,
                file_name="tariff_scoring_details.csv",
                mime="text/csv"
            )

        with col3:
            # Clear history button
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state['score_history'] = []
                st.rerun()

    else:
        st.info("👈 Please enter parameters in the sidebar and click 'Calculate Scores' to see results.")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            <p>Tariff Scoring Calculator Dashboard v2.1</p>
            <p>Formula: Overall Score = (Tarifnote × 40% + Preisnote × 60%)</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
