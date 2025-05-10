import streamlit as st
import os
import yfinance as yf
from dotenv import load_dotenv

from utils import (
    fetch_news,
    plot_stock_price,
    get_yahoo_ticker,
    summarize_news,
    conclude_from_news,
    investment_recommendation_from_news,
)

load_dotenv()

st.set_page_config(page_title="📊 Stock News Comparison Tool", layout="wide")
st.title("📈 Stock News Comparison Tool")
st.markdown("Compare up to 4 stocks using today's latest news and price trends.")

API_KEY = os.getenv("NEWSDATA_API_KEY")

input_names = []
for i in range(4):
    ticker_input = st.sidebar.text_input(f"Stock {i+1} Name (e.g., HDFC Bank, D-Wave Quantum Inc)", key=f"ticker_{i}")
    if ticker_input:
        input_names.append(ticker_input.strip())

if st.sidebar.button("🔍 Compare Stocks") and input_names:
    # --- Ticker detection using Yahoo Finance ---
    tickers = []
    for name in input_names:
        ticker = get_yahoo_ticker(name)
        if ticker:
            tickers.append(ticker)
        else:
            st.warning(f"Could not find ticker for {name}")
            tickers.append(name.upper())  # fallback

    # --- Fetch news and summarize ---
    all_docs = []
    all_summaries = {}
    with st.spinner("Fetching latest news articles..."):
        for company_name in input_names:
            news_docs = fetch_news(company_name, API_KEY)
            if news_docs:
                st.success(f"✅ Fetched {len(news_docs)} articles for {company_name}")
                summaries = summarize_news(news_docs)
                all_summaries[company_name] = summaries
                all_docs.extend(news_docs)
            else:
                st.warning(f"⚠️ No recent news found for {company_name}")
                all_summaries[company_name] = []

    # --- Show news summaries and sources ---
    st.header("📰 News Summaries")
    for company_name in input_names:
        summaries = all_summaries.get(company_name, [])
        if summaries:
            st.markdown(f"**{company_name}:**")
            for summary, url in summaries:
                st.markdown(f"- {summary} [Source]({url})")
        else:
            st.markdown(f"- No recent news found for {company_name}")

    # --- Fetch and plot stock prices ---
    st.subheader("📉 Stock Price Graphs (7-day)")
    price_data = {}
    for ticker in tickers:
        try:
            close_prices = yf.download(ticker, period="7d", interval="1d")["Close"]
            price_data[ticker] = close_prices
        except Exception as e:
            st.warning(f"Error fetching price for {ticker}: {e}")

    plot_stock_price(price_data)
    
    # --- News-based conclusions ---
    # st.header("📰 News-Based Conclusions")
    # for company_name in input_names:
    #     summaries = all_summaries.get(company_name, [])
    #     st.markdown(conclude_from_news(summaries, company_name))
    #     st.markdown("---")
        
    st.header("💡 Investment Recommendation")
    st.markdown(investment_recommendation_from_news(all_summaries, input_names))


# import streamlit as st
# import os
# import yfinance as yf
# from dotenv import load_dotenv

# from utils import (
#     fetch_news,
#     plot_stock_price,
#     get_yahoo_ticker,
#     display_news_summaries_and_sources, 
#     conclude_from_news,
# )

# load_dotenv()

# st.set_page_config(page_title="📊 Stock News Comparison Tool", layout="wide")
# st.title("📈 Stock News Comparison Tool")
# st.markdown("Compare up to 4 stocks using today's latest news and price trends.")

# API_KEY = os.getenv("NEWSDATA_API_KEY")

# input_names = []
# for i in range(4):
#     ticker_input = st.sidebar.text_input(f"Stock {i+1} Name (e.g., HDFC Bank, D-Wave Quantum Inc)", key=f"ticker_{i}")
#     if ticker_input:
#         input_names.append(ticker_input.strip())

# if st.sidebar.button("🔍 Compare Stocks") and input_names:
#     # --- Ticker detection using Yahoo Finance ---
#     tickers = []
#     for name in input_names:
#         ticker = get_yahoo_ticker(name)
#         if ticker:
#             tickers.append(ticker)
#         else:
#             st.warning(f"Could not find ticker for {name}")
#             tickers.append(name.upper())  # fallback

#     # --- Fetch news and summarize ---
#     all_docs = []
#     all_summaries = {}
#     with st.spinner("Fetching latest news articles..."):
#         for company_name in input_names:
#             news_docs = fetch_news(company_name, API_KEY)
#             if news_docs:
#                 st.success(f"✅ Fetched {len(news_docs)} articles for {company_name}")
#                 summaries = display_news_summaries_and_sources(news_docs, llm=None)
#                 all_summaries[company_name] = summaries
#                 all_docs.extend(news_docs)
#             else:
#                 st.warning(f"⚠️ No recent news found for {company_name}")

#     # --- Show news summaries and sources ---
#     st.header("📰 News Summaries")
#     for company_name in input_names:
#         summaries = all_summaries.get(company_name, [])
#         if summaries:
#             st.markdown(f"**{company_name}:**")
#             for summary, url in summaries:
#                 st.markdown(f"- {summary} [Source]({url})")
#         else:
#             st.markdown(f"- No recent news found for {company_name}")

#     # --- Fetch and plot stock prices ---
#     st.subheader("📉 Stock Price Graphs (7-day)")
#     price_data = {}
#     for ticker in tickers:
#         try:
#             close_prices = yf.download(ticker, period="7d", interval="1d")["Close"]
#             price_data[ticker] = close_prices
#         except Exception as e:
#             st.warning(f"Error fetching price for {ticker}: {e}")

#     plot_stock_price(price_data)
    
#     st.header("📰 News-Based Conclusions")
#     for company_name in input_names:
#         summaries = all_summaries.get(company_name, [])
#         st.markdown(conclude_from_news(summaries, company_name))
#         st.markdown("---")
