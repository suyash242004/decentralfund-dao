"""
DecentralFund DAO - Main Streamlit Dashboard
Interactive web interface for the world's first decentralized autonomous mutual fund
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import asyncio
import json
import time
from typing import Dict, List, Optional
import numpy as np

# Configure Streamlit page
st.set_page_config(
    page_title="DecentralFund DAO",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = "http://localhost:8000/api"

# Initialize session state
if 'user_wallet' not in st.session_state:
    st.session_state.user_wallet = None
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'portfolio_data' not in st.session_state:
    st.session_state.portfolio_data = None

# Helper Functions
@st.cache_data(ttl=30)  # Cache for 30 seconds
def fetch_platform_stats():
    """Fetch platform-wide statistics"""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Failed to fetch platform stats: {str(e)}")
        return None

@st.cache_data(ttl=60)  # Cache for 1 minute
def fetch_market_data():
    """Fetch current market data"""
    try:
        response = requests.get(f"{API_BASE_URL}/market-data", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Failed to fetch market data: {str(e)}")
        return None

def fetch_user_portfolio(wallet_address: str):
    """Fetch user portfolio data"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/portfolio/user/{wallet_address}",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Failed to fetch portfolio: {str(e)}")
        return None

def fetch_active_proposals():
    """Fetch active governance proposals"""
    try:
        response = requests.get(f"{API_BASE_URL}/governance/proposals/active", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Failed to fetch proposals: {str(e)}")
        return []

# Main App
def main():
    # Header
    st.markdown('<h1 class="main-header">🏛️ DecentralFund DAO</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; font-size: 1.2rem; color: #666;">World\'s First Decentralized Autonomous Mutual Fund</p>',
        unsafe_allow_html=True
    )
    
    # Sidebar for user authentication
    with st.sidebar:
        st.header("🔐 Connect Wallet")
        
        # Mock wallet connection (in production, integrate with Web3 wallets)
        wallet_address = st.text_input(
            "Wallet Address",
            placeholder="0x742d35Cc6634C0532925a3b8D",
            help="Enter your Ethereum wallet address"
        )
        
        if st.button("Connect Wallet", type="primary"):
            if wallet_address and len(wallet_address) == 42 and wallet_address.startswith("0x"):
                st.session_state.user_wallet = wallet_address
                st.success("✅ Wallet connected successfully!")
                st.rerun()
            else:
                st.error("❌ Please enter a valid Ethereum address")
        
        if st.session_state.user_wallet:
            st.success(f"Connected: {st.session_state.user_wallet[:6]}...{st.session_state.user_wallet[-4:]}")
            
            if st.button("Disconnect"):
                st.session_state.user_wallet = None
                st.session_state.user_data = None
                st.session_state.portfolio_data = None
                st.rerun()
    
    # Main dashboard tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", 
        "💰 SIP Investment", 
        "🗳️ Governance", 
        "📈 Portfolio", 
        "🤖 AI Insights"
    ])
    
    # Tab 1: Dashboard
    with tab1:
        st.header("Platform Overview")
        
        # Fetch platform statistics
        stats = fetch_platform_stats()
        if stats:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Total Users",
                    value=f"{stats['total_users']:,}",
                    delta="+12% vs last month"
                )
            
            with col2:
                st.metric(
                    label="Assets Under Management",
                    value=f"${stats['total_aum_usd']:,.0f}",
                    delta="+8.5% vs last month"
                )
            
            with col3:
                st.metric(
                    label="Active SIPs",
                    value=f"{stats['active_sips']:,}",
                    delta="+15 new this week"
                )
            
            with col4:
                st.metric(
                    label="Active Proposals",
                    value=f"{stats['active_proposals']}",
                    delta="2 ending soon"
                )
        
        # Market performance chart
        st.subheader("📈 Fund Performance vs Benchmarks")
        
        # Generate sample performance data
        dates = pd.date_range(start='2024-01-01', end='2024-09-20', freq='D')
        np_random = np.random.RandomState(42)
        
        performance_data = pd.DataFrame({
            'Date': dates,
            'DecentralFund': np_random.normal(0.0008, 0.02, len(dates)).cumsum() * 100 + 100,
            'S&P 500': np_random.normal(0.0005, 0.015, len(dates)).cumsum() * 100 + 100,
            'BTC': np_random.normal(0.001, 0.04, len(dates)).cumsum() * 100 + 100,
        })
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=performance_data['Date'],
            y=performance_data['DecentralFund'],
            name='DecentralFund DAO',
            line=dict(color='#1f77b4', width=3)
        ))
        fig.add_trace(go.Scatter(
            x=performance_data['Date'],
            y=performance_data['S&P 500'],
            name='S&P 500',
            line=dict(color='#ff7f0e', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=performance_data['Date'],
            y=performance_data['BTC'],
            name='Bitcoin',
            line=dict(color='#2ca02c', width=2)
        ))
        
        fig.update_layout(
            title="Cumulative Returns (YTD)",
            xaxis_title="Date",
            yaxis_title="Value ($)",
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Top performing assets
        if stats and stats.get('top_performing_assets'):
            st.subheader("🏆 Top Performing Assets (30 Days)")
            
            assets_df = pd.DataFrame(stats['top_performing_assets'])
            fig_assets = px.bar(
                assets_df,
                x='symbol',
                y='return_30d',
                title="30-Day Returns by Asset",
                color='return_30d',
                color_continuous_scale='RdYlGn'
            )
            fig_assets.update_layout(height=400)
            st.plotly_chart(fig_assets, use_container_width=True)
        
        # Recent activity feed
        st.subheader("🔄 Recent Activity")
        
        # Mock activity data
        activities = [
            {"time": "2 minutes ago", "action": "New proposal created", "details": "Increase BTC allocation to 15%", "user": "0x742d...8D"},
            {"time": "5 minutes ago", "action": "SIP payment processed", "details": "$500 invested by 0x8a3f...2C", "user": "0x8a3f...2C"},
            {"time": "12 minutes ago", "action": "Vote cast", "details": "Voted 'Yes' on Proposal #47", "user": "0x1b4e...9F"},
            {"time": "18 minutes ago", "action": "Fund rebalanced", "details": "Portfolio automatically rebalanced", "user": "System"},
            {"time": "25 minutes ago", "action": "New user joined", "details": "Started $100 monthly SIP", "user": "0x9c7a...4B"},
        ]
        
        for activity in activities:
            with st.container():
                col1, col2, col3 = st.columns([2, 4, 2])
                with col1:
                    st.text(activity["time"])
                with col2:
                    st.write(f"**{activity['action']}**: {activity['details']}")
                with col3:
                    st.text(activity["user"])
                st.divider()
    
    # Tab 2: SIP Investment
    with tab2:
        st.header("💰 Systematic Investment Plan (SIP)")
        
        if not st.session_state.user_wallet:
            st.warning("⚠️ Please connect your wallet to access SIP features")
            return
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🎯 Start New SIP")
            
            with st.form("sip_form"):
                amount = st.number_input(
                    "Investment Amount (USD)",
                    min_value=10,
                    max_value=10000,
                    value=100,
                    step=10,
                    help="Minimum $10, Maximum $10,000 per SIP"
                )
                
                frequency = st.selectbox(
                    "Investment Frequency",
                    ["Daily", "Weekly", "Monthly"],
                    index=2,
                    help="How often you want to invest"
                )
                
                duration = st.selectbox(
                    "Investment Duration",
                    ["3 months", "6 months", "1 year", "2 years", "5 years", "Unlimited"],
                    index=2,
                    help="How long you want to continue the SIP"
                )
                
                auto_compound = st.checkbox(
                    "Auto-compound returns",
                    value=True,
                    help="Automatically reinvest returns for compound growth"
                )
                
                if st.form_submit_button("🚀 Start SIP", type="primary"):
                    # Calculate projected returns
                    annual_return = 12  # Assumed 12% annual return
                    
                    if frequency == "Monthly":
                        freq_multiplier = 12
                    elif frequency == "Weekly":
                        freq_multiplier = 52
                    else:  # Daily
                        freq_multiplier = 365
                    
                    years = 1 if duration == "1 year" else (2 if duration == "2 years" else 0.5)
                    total_periods = int(freq_multiplier * years)
                    
                    # SIP future value calculation
                    monthly_rate = annual_return / 100 / freq_multiplier
                    future_value = amount * (((1 + monthly_rate) ** total_periods - 1) / monthly_rate) * (1 + monthly_rate)
                    total_invested = amount * total_periods
                    profit = future_value - total_invested
                    
                    st.success("✅ SIP Created Successfully!")
                    st.info(f"""
                    **SIP Summary:**
                    - Investment: ${amount} {frequency.lower()}
                    - Duration: {duration}
                    - Total Investment: ${total_invested:,.2f}
                    - Projected Value: ${future_value:,.2f}
                    - Projected Profit: ${profit:,.2f}
                    - Estimated Return: {(profit/total_invested)*100:.1f}%
                    """)
                    
                    # Mock API call to create SIP
                    with st.spinner("Creating SIP on blockchain..."):
                        time.sleep(2)  # Simulate blockchain transaction
                    
                    st.success("🎉 Your SIP is now active and will start investing automatically!")
        
        with col2:
            st.subheader("📊 Your Active SIPs")
            
            # Mock user SIPs
            sips = [
                {
                    "id": "SIP-001",
                    "amount": 500,
                    "frequency": "Monthly",
                    "start_date": "2024-01-15",
                    "total_invested": 4000,
                    "current_value": 4320,
                    "return": 8.0,
                    "status": "Active"
                },
                {
                    "id": "SIP-002", 
                    "amount": 100,
                    "frequency": "Weekly",
                    "start_date": "2024-06-01",
                    "total_invested": 1600,
                    "current_value": 1728,
                    "return": 8.0,
                    "status": "Active"
                }
            ]
            
            for sip in sips:
                with st.container():
                    st.markdown(f"**{sip['id']}** - {sip['status']}")
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.metric("Invested", f"${sip['total_invested']:,}")
                    with col_b:
                        st.metric("Current Value", f"${sip['current_value']:,}")
                    with col_c:
                        profit = sip['current_value'] - sip['total_invested']
                        st.metric("Profit/Loss", f"${profit:,}", f"{sip['return']}%")
                    
                    if st.button(f"Manage {sip['id']}", key=f"manage_{sip['id']}"):
                        st.info(f"Managing {sip['id']} - Feature coming soon!")
                    
                    st.divider()
            
            # SIP calculator
            st.subheader("🧮 SIP Calculator")
            calc_amount = st.slider("Monthly Investment ($)", 50, 2000, 500)
            calc_years = st.slider("Investment Period (Years)", 1, 10, 5)
            calc_return = st.slider("Expected Annual Return (%)", 5, 20, 12)
            
            # Calculate SIP returns
            monthly_rate = calc_return / 100 / 12
            total_months = calc_years * 12
            future_value = calc_amount * (((1 + monthly_rate) ** total_months - 1) / monthly_rate) * (1 + monthly_rate)
            total_invested = calc_amount * total_months
            
            st.metric("Total Investment", f"${total_invested:,.0f}")
            st.metric("Projected Value", f"${future_value:,.0f}")
            st.metric("Projected Profit", f"${future_value - total_invested:,.0f}")
    
    # Tab 3: Governance
    with tab3:
        st.header("🗳️ DAO Governance")
        
        if not st.session_state.user_wallet:
            st.warning("⚠️ Please connect your wallet to participate in governance")
            return
        
        # User's voting power
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Your Tokens", "1,250 FUND", "+50 this month")
        with col2:
            st.metric("Voting Power", "35.36", "√1,250 tokens")
        with col3:
            st.metric("Proposals Voted", "12", "100% participation")
        
        st.divider()
        
        # Create new proposal
        with st.expander("📝 Create New Proposal"):
            proposal_type = st.selectbox(
                "Proposal Type",
                [
                    "Portfolio Allocation Change",
                    "Fund Manager Election", 
                    "Fee Structure Adjustment",
                    "New Asset Addition",
                    "Risk Parameter Update"
                ]
            )
            
            proposal_title = st.text_input("Proposal Title")
            proposal_description = st.text_area("Detailed Description", height=100)
            
            if proposal_type == "Portfolio Allocation Change":
                st.subheader("Allocation Changes")
                
                assets = ["Bitcoin (BTC)", "Ethereum (ETH)", "S&P 500 (SPY)", "Gold (GLD)", "Bonds (TLT)"]
                for asset in assets:
                    current_allocation = st.slider(
                        f"{asset} allocation %",
                        0, 30, 10,
                        key=f"allocation_{asset}"
                    )
            
            elif proposal_type == "New Asset Addition":
                new_asset = st.text_input("Asset Symbol (e.g., SOL, AAPL)")
                max_allocation = st.slider("Maximum Allocation %", 1, 20, 5)
                rationale = st.text_area("Why should this asset be added?")
            
            voting_duration = st.selectbox("Voting Duration", ["3 days", "7 days", "14 days"], index=1)
            
            if st.button("🚀 Submit Proposal", type="primary"):
                if proposal_title and proposal_description:
                    st.success("✅ Proposal submitted successfully!")
                    st.info("Your proposal will be reviewed and made available for voting within 24 hours.")
                else:
                    st.error("Please fill in all required fields")
        
        st.subheader("🔥 Active Proposals")
        
        # Mock active proposals
        proposals = [
            {
                "id": "PROP-047",
                "title": "Increase Bitcoin Allocation from 10% to 15%",
                "description": "Given the recent market conditions and Bitcoin's strong performance...",
                "type": "Portfolio Change",
                "creator": "0x742d...8D",
                "created": "2 days ago",
                "voting_ends": "5 days",
                "total_votes": 2847,
                "options": {
                    "Yes (15% BTC)": 1823,
                    "No (Keep 10%)": 724,
                    "Alternative (12%)": 300
                },
                "status": "Active",
                "quorum": "✅ Met (2847/1000)"
            },
            {
                "id": "PROP-048", 
                "title": "Add Solana (SOL) to Portfolio - Max 5% Allocation",
                "description": "Solana has shown strong fundamentals and growing ecosystem...",
                "type": "New Asset",
                "creator": "0x8a3f...2C",
                "created": "1 day ago", 
                "voting_ends": "6 days",
                "total_votes": 1456,
                "options": {
                    "Yes (Add SOL)": 987,
                    "No (Don't Add)": 469
                },
                "status": "Active",
                "quorum": "✅ Met (1456/1000)"
            },
            {
                "id": "PROP-049",
                "title": "Elect New Fund Manager: Sarah Chen",
                "description": "Sarah has 15 years experience in portfolio management...",
                "type": "Manager Election",
                "creator": "0x1b4e...9F",
                "created": "6 hours ago",
                "voting_ends": "6 days",
                "total_votes": 234,
                "options": {
                    "Approve Sarah": 156,
                    "Reject": 78
                },
                "status": "Active",
                "quorum": "❌ Not Met (234/1000)"
            }
        ]
        
        for prop in proposals:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**{prop['id']}: {prop['title']}**")
                    st.text(f"Type: {prop['type']} | Creator: {prop['creator']} | Created: {prop['created']}")
                    st.write(prop['description'][:100] + "...")
                    
                    # Voting options with progress bars
                    total_votes = prop['total_votes']
                    for option, votes in prop['options'].items():
                        percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                        st.progress(percentage / 100, text=f"{option}: {votes:,} votes ({percentage:.1f}%)")
                
                with col2:
                    st.metric("Total Votes", f"{prop['total_votes']:,}")
                    st.text(f"Ends in: {prop['voting_ends']}")
                    st.text(f"Quorum: {prop['quorum']}")
                    
                    if prop['status'] == 'Active':
                        if st.button(f"Vote on {prop['id']}", key=f"vote_{prop['id']}"):
                            # Vote modal
                            with st.form(f"vote_form_{prop['id']}"):
                                st.write(f"**Voting on:** {prop['title']}")
                                
                                selected_option = st.radio(
                                    "Select your vote:",
                                    list(prop['options'].keys()),
                                    key=f"option_{prop['id']}"
                                )
                                
                                voting_power = st.number_input(
                                    "Voting power to use:",
                                    min_value=1,
                                    max_value=35,
                                    value=35,
                                    help="You have 35.36 voting power available"
                                )
                                
                                if st.form_submit_button("Cast Vote", type="primary"):
                                    with st.spinner("Submitting vote to blockchain..."):
                                        time.sleep(2)
                                    st.success(f"✅ Vote cast for '{selected_option}'!")
                                    st.info("Your vote has been recorded on the blockchain.")
                                    st.rerun()
                
                st.divider()
        
        # Historical proposals
        st.subheader("📜 Recent Decisions")
        
        completed_proposals = [
            {
                "id": "PROP-045",
                "title": "Reduce Management Fee from 1.2% to 1.0%",
                "result": "✅ PASSED",
                "votes": "3,247 votes (73% yes)",
                "executed": "3 days ago"
            },
            {
                "id": "PROP-044",
                "title": "Add Real Estate ETF (VNQ) - 8% allocation", 
                "result": "❌ REJECTED",
                "votes": "2,156 votes (52% no)",
                "executed": "1 week ago"
            }
        ]
        
        for prop in completed_proposals:
            st.text(f"{prop['id']}: {prop['title']} - {prop['result']}")
            st.text(f"   {prop['votes']} | Executed: {prop['executed']}")
    
    # Tab 4: Portfolio
    with tab4:
        st.header("📈 Portfolio Management")
        
        if not st.session_state.user_wallet:
            st.warning("⚠️ Please connect your wallet to view your portfolio")
            return
        
        # Portfolio overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Portfolio Value", "$5,720", "+$320 (5.9%)")
        with col2:
            st.metric("Total Invested", "$5,400", "Via 2 SIPs")
        with col3:
            st.metric("Unrealized P&L", "+$320", "+5.9%")
        with col4:
            st.metric("24h Change", "+$45", "+0.8%")
        
        # Portfolio allocation pie chart
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🥧 Current Allocation")
            
            allocation_data = {
                'Asset': ['Bitcoin (BTC)', 'Ethereum (ETH)', 'S&P 500 (SPY)', 'Gold (GLD)', 'Bonds (TLT)', 'Cash'],
                'Allocation': [15, 12, 35, 10, 18, 10],
                'Value': [858, 686, 2002, 572, 1030, 572],
                'Target': [15, 12, 35, 10, 18, 10]
            }
            
            fig_pie = px.pie(
                allocation_data,
                values='Allocation',
                names='Asset',
                title="Portfolio Allocation",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.subheader("📊 Asset Details")
            
            df_allocation = pd.DataFrame(allocation_data)
            
            for _, row in df_allocation.iterrows():
                if row['Asset'] != 'Cash':
                    with st.container():
                        st.write(f"**{row['Asset']}**")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.text(f"${row['Value']:,}")
                        with col_b:
                            st.text(f"{row['Allocation']}%")
                        
                        # Show if rebalancing is needed
                        if abs(row['Allocation'] - row['Target']) > 2:
                            st.warning("⚖️ Rebalancing needed")
                        
                        st.divider()
        
        # Performance chart
        st.subheader("📈 Portfolio Performance")
        
        # Generate sample portfolio performance data
        perf_dates = pd.date_range(start='2024-01-01', end='2024-09-20', freq='D')
        np.random.seed(42)
        
        portfolio_performance = pd.DataFrame({
            'Date': perf_dates,
            'Portfolio_Value': np.random.normal(0.0008, 0.02, len(perf_dates)).cumsum() * 1000 + 5000,
            'Invested_Amount': np.linspace(3000, 5400, len(perf_dates))
        })
        
        fig_perf = go.Figure()
        
        fig_perf.add_trace(go.Scatter(
            x=portfolio_performance['Date'],
            y=portfolio_performance['Portfolio_Value'],
            name='Portfolio Value',
            line=dict(color='#1f77b4', width=3),
            fill='tonexty'
        ))
        
        fig_perf.add_trace(go.Scatter(
            x=portfolio_performance['Date'],
            y=portfolio_performance['Invested_Amount'],
            name='Total Invested',
            line=dict(color='#ff7f0e', width=2, dash='dash')
        ))
        
        fig_perf.update_layout(
            title="Portfolio Value vs Investment Over Time",
            xaxis_title="Date",
            yaxis_title="Value ($)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_perf, use_container_width=True)
        
        # Rebalancing recommendations
        st.subheader("⚖️ Rebalancing Recommendations")
        
        rebalancing = [
            {"action": "Sell", "asset": "S&P 500 (SPY)", "amount": "$200", "reason": "Overweight by 2%"},
            {"action": "Buy", "asset": "Bitcoin (BTC)", "amount": "$100", "reason": "Underweight by 1%"}, 
            {"action": "Buy", "asset": "Bonds (TLT)", "amount": "$100", "reason": "Underweight by 1%"}
        ]
        
        if rebalancing:
            st.info("🤖 AI-powered rebalancing recommendations based on target allocation:")
            
            for rec in rebalancing:
                col1, col2, col3, col4 = st.columns([1, 2, 2, 3])
                with col1:
                    color = "🔴" if rec["action"] == "Sell" else "🟢"
                    st.write(f"{color} {rec['action']}")
                with col2:
                    st.write(rec["asset"])
                with col3:
                    st.write(rec["amount"])
                with col4:
                    st.write(rec["reason"])
            
            if st.button("Execute Rebalancing", type="primary"):
                with st.spinner("Executing rebalancing trades..."):
                    time.sleep(3)
                st.success("✅ Portfolio rebalanced successfully!")
                st.info("All trades have been executed according to community-approved allocation targets.")
        else:
            st.success("✅ Your portfolio is perfectly balanced according to target allocation!")
        
        # Transaction history
        st.subheader("📋 Recent Transactions")
        
        transactions = [
            {"date": "2024-09-20", "type": "SIP Investment", "asset": "Mixed Portfolio", "amount": "+$500", "status": "✅"},
            {"date": "2024-09-18", "type": "Rebalancing", "asset": "BTC → ETH", "amount": "$120", "status": "✅"},
            {"date": "2024-09-15", "type": "SIP Investment", "asset": "Mixed Portfolio", "amount": "+$100", "status": "✅"},
            {"date": "2024-09-12", "type": "Dividend", "asset": "SPY", "amount": "+$12.50", "status": "✅"},
            {"date": "2024-09-10", "type": "Rebalancing", "asset": "GOLD → BTC", "amount": "$80", "status": "✅"}
        ]
        
        df_transactions = pd.DataFrame(transactions)
        st.dataframe(df_transactions, use_container_width=True, hide_index=True)
    
    # Tab 5: AI Insights
    with tab5:
        st.header("🤖 AI-Powered Insights")
        
        # AI sentiment analysis
        st.subheader("📊 Community Sentiment Analysis")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overall Sentiment", "Bullish", "↗️ +5% vs last week")
        with col2:
            st.metric("Confidence Score", "87%", "High confidence")
        with col3:
            st.metric("Active Discussions", "1,247", "+15% vs last week")
        
        # Sentiment chart
        sentiment_data = pd.DataFrame({
            'Date': pd.date_range('2024-09-01', '2024-09-20', freq='D'),
            'Bullish': np.random.uniform(30, 70, 20),
            'Neutral': np.random.uniform(15, 35, 20),
            'Bearish': np.random.uniform(5, 25, 20)
        })
        
        fig_sentiment = px.line(
            sentiment_data,
            x='Date',
            y=['Bullish', 'Neutral', 'Bearish'],
            title='Community Sentiment Trends',
            color_discrete_map={'Bullish': 'green', 'Neutral': 'gray', 'Bearish': 'red'}
        )
        fig_sentiment.update_layout(height=300)
        st.plotly_chart(fig_sentiment, use_container_width=True)
        
        # AI recommendations
        st.subheader("🎯 AI Portfolio Recommendations")
        
        recommendations = [
            {
                "title": "Increase DeFi Exposure",
                "confidence": "92%",
                "rationale": "DeFi protocols showing strong fundamentals and growing TVL",
                "suggested_allocation": "Add 5% to DeFi tokens",
                "impact": "Expected to increase portfolio yield by 1.2%"
            },
            {
                "title": "Reduce Bond Allocation", 
                "confidence": "85%",
                "rationale": "Rising interest rates making current bonds less attractive",
                "suggested_allocation": "Reduce from 18% to 15%",
                "impact": "Reduce interest rate risk"
            },
            {
                "title": "Geographic Diversification",
                "confidence": "78%", 
                "rationale": "Overexposure to US markets, emerging markets showing opportunity",
                "suggested_allocation": "Add 3% emerging market ETF",
                "impact": "Better diversification and risk-adjusted returns"
            }
        ]
        
        for rec in recommendations:
            with st.expander(f"💡 {rec['title']} (Confidence: {rec['confidence']})"):
                st.write(f"**Rationale:** {rec['rationale']}")
                st.write(f"**Suggested Action:** {rec['suggested_allocation']}")
                st.write(f"**Expected Impact:** {rec['impact']}")
                
                if st.button(f"Create Proposal for {rec['title']}", key=f"ai_rec_{rec['title']}"):
                    st.success("✅ Proposal draft created! Review and submit in the Governance tab.")
        
        # Market analysis
        st.subheader("📈 AI Market Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔍 Technical Analysis**")
            technical_signals = {
                "Bitcoin (BTC)": {"signal": "Buy", "strength": "Strong", "price_target": "$32,000"},
                "Ethereum (ETH)": {"signal": "Hold", "strength": "Moderate", "price_target": "$2,100"},
                "S&P 500 (SPY)": {"signal": "Buy", "strength": "Weak", "price_target": "$450"},
                "Gold (GLD)": {"signal": "Sell", "strength": "Moderate", "price_target": "$180"}
            }
            
            for asset, signal in technical_signals.items():
                color = "🟢" if signal["signal"] == "Buy" else ("🟡" if signal["signal"] == "Hold" else "🔴")
                st.write(f"{color} **{asset}**: {signal['signal']} ({signal['strength']}) - Target: {signal['price_target']}")
        
        with col2:
            st.markdown("**📰 News Impact Analysis**")
            news_impact = [
                {"news": "Federal Reserve hints at rate cuts", "impact": "Positive", "affected_assets": "Bonds, REITs"},
                {"news": "Bitcoin ETF approval speculation", "impact": "Very Positive", "affected_assets": "BTC, Crypto"},
                {"news": "Inflation data lower than expected", "impact": "Positive", "affected_assets": "Stocks, Gold"},
                {"news": "Geopolitical tensions rising", "impact": "Negative", "affected_assets": "Risk Assets"}
            ]
            
            for news in news_impact:
                impact_color = "🟢" if "Positive" in news["impact"] else "🔴"
                st.write(f"{impact_color} **{news['impact']}**: {news['news']}")
                st.text(f"   Affects: {news['affected_assets']}")
        
        # AI chat interface
        st.subheader("💬 Ask AI Assistant")
        
        user_question = st.text_input(
            "Ask anything about your portfolio or market conditions:",
            placeholder="e.g., 'Should I increase my crypto allocation?'"
        )
        
        if st.button("Ask AI") and user_question:
            with st.spinner("AI analyzing your question..."):
                time.sleep(2)
            
            # Mock AI response
            ai_responses = [
                "Based on current market conditions and your risk profile, I recommend maintaining your current crypto allocation at 27%. The market shows mixed signals with high volatility expected in the short term.",
                "Your portfolio is well-diversified. However, consider the upcoming Fed meeting on interest rates which could impact your bond holdings. I suggest reviewing your fixed-income allocation.",
                "The technical indicators suggest a potential correction in tech stocks. Your S&P 500 exposure might benefit from some profit-taking if we see a 5% pullback."
            ]
            
            import random
            response = random.choice(ai_responses)
            
            st.success("🤖 AI Assistant Response:")
            st.write(response)
            st.info("💡 This analysis is based on real-time market data, your portfolio composition, and current community sentiment.")

if __name__ == "__main__":
    main()