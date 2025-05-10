import datetime
import requests
import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
from langchain.schema import Document
from bs4 import BeautifulSoup

def fetch_news(company_name, api_key):
    today = datetime.date.today().isoformat()
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": api_key,
        "q": f"{company_name} stock",
        "language": "en"
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            st.error(f"NewsData API error {response.status_code}: {response.text}")
            return []
        json_data = response.json()
        articles = json_data.get("results", [])
        docs = []
        for article in articles:
            pub_date = article.get("pubDate", "")[:10]
            if pub_date == today:
                content = f"{article.get('title', '')}\n{article.get('description', '')}\n{article.get('link', '')}"
                docs.append(Document(page_content=content, metadata={"source": article.get("link", "")}))
            if len(docs) >= 5:
                break
        return docs
    except Exception as e:
        st.error(f"Failed to fetch news: {e}")
        return []

def plot_stock_price(price_data):
    fig, ax = plt.subplots(figsize=(10, 6))
    for ticker, prices in price_data.items():
        if not prices.empty:
            ax.plot(prices.index, prices.values, label=ticker)
        else:
            st.warning(f"No price data found for {ticker}")
    ax.set_title("Stock Price Comparison - Last 7 Days")
    ax.set_xlabel("Date")
    ax.set_ylabel("Closing Price (in INR/USD)")
    ax.legend()
    fig.autofmt_xdate()  # Prevent overlapping dates
    st.pyplot(fig)

def get_yahoo_ticker(company_name):
    """
    Find the most probable stock ticker from Yahoo Finance search results.
    """
    search_url = f"https://finance.yahoo.com/lookup?s={company_name.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 2:
                symbol = cols[0].text.strip()
                name = cols[1].text.strip().lower()
                if company_name.lower() in name:
                    return symbol
        # Fallback: return first symbol found
        symbol_cell = soup.find("td", attrs={"data-test": "QUOTE_SYMBOL"})
        if symbol_cell:
            return symbol_cell.text.strip()
        return None
    except Exception as e:
        st.error(f"Error fetching ticker for {company_name}: {e}")
        return None

def summarize_news(news_docs, llm=None):
    """
    Summarizes each news article.
    If an LLM is provided, use it; otherwise, use the first two lines as a summary.
    Returns a list of (summary, source_url) tuples.
    """
    summaries = []
    for doc in news_docs:
        content = doc.page_content
        if llm:
            prompt = f"Summarize this news article in 1-2 sentences:\n{content}"
            summary = llm(prompt)
        else:
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            summary = " ".join(lines[:2]) if lines else ""
        source_url = doc.metadata.get("source", "")
        summaries.append((summary, source_url))
    return summaries

def conclude_from_news(news_summaries, company_name):
    """
    Given a list of (summary, url) tuples for a company,
    returns a formatted conclusion string.
    Handles the case where no news articles are found.
    """
    if not news_summaries:
        return f"**{company_name}:**\n_No recent news articles found for this stock. Please check back later or consider other sources._"

    # Simple sentiment analysis: count positive/negative words
    pos_keywords = ["growth", "profit", "gain", "strong", "beat", "record", "increase", "up", "surge", "improve"]
    neg_keywords = ["loss", "decline", "drop", "fall", "down", "weak", "scandal", "cut", "negative", "decrease"]

    pos_count = 0
    neg_count = 0
    for summary, _ in news_summaries:
        s = summary.lower()
        if any(word in s for word in pos_keywords):
            pos_count += 1
        if any(word in s for word in neg_keywords):
            neg_count += 1

    if pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count:
        sentiment = "negative"
    else:
        sentiment = "mixed or neutral"

    # Format bullet-pointed news and sources
    news_points = "\n".join([f"- {summary}" for summary, url in news_summaries])
    sources = "\n".join([f"- [Source {i+1}]({url})" for i, (_, url) in enumerate(news_summaries) if url])

    conclusion = (
        f"**{company_name}:**\n"
        f"**News sentiment:** {sentiment.capitalize()}.\n\n"
        f"**Key News Points:**\n{news_points}\n\n"
        f"**Sources:**\n{sources if sources else '_No sources available_'}"
    )
    return conclusion

def investment_recommendation_from_news(all_summaries, input_names):
    """
    Given all_summaries: dict of {company_name: [(summary, url), ...]}
    and input_names: list of company names,
    returns a short, actionable investment recommendation.
    """
    # Define keywords for hype/growth and stability
    growth_keywords = ["record", "growth", "soared", "profit", "surge", "beat", "increase", "expanding", "momentum", "innovation", "revenue", "up", "jump", "strong", "supremacy"]
    stable_keywords = ["steady", "stable", "diversified", "consistent", "reliable", "long-term", "core", "retail", "telecom", "industrial", "operations"]
    risk_keywords = ["volatile", "risk", "loss", "decline", "uncertain", "high expectations", "priced in", "sell-off"]

    scores = {}
    notes = {}

    for name in input_names:
        summaries = all_summaries.get(name, [])
        if not summaries:
            scores[name] = 0
            notes[name] = "No recent news."
            continue

        text = " ".join(summary for summary, _ in summaries).lower()
        growth = sum(text.count(word) for word in growth_keywords)
        stable = sum(text.count(word) for word in stable_keywords)
        risk = sum(text.count(word) for word in risk_keywords)
        score = growth + 0.5 * stable - risk
        scores[name] = score
        notes[name] = f"Growth: {growth}, Stability: {stable}, Risk: {risk}"

    # Find best and second-best
    sorted_stocks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_stock, best_score = sorted_stocks[0]
    second_stock, second_score = sorted_stocks[1] if len(sorted_stocks) > 1 else (None, None)

    # Compose recommendation
    if best_score == 0:
        return "No actionable investment recommendation can be made due to lack of recent news."

    recommendation = f"**Investment Recommendation:**\n\n"
    recommendation += f"- **{best_stock}** shows the strongest positive signals in recent news ({notes[best_stock]}). "
    if second_stock:
        recommendation += f"\n- **{second_stock}** is also mentioned, but with less positive momentum ({notes[second_stock]})."
    recommendation += "\n\n*If you seek high growth and can tolerate volatility, consider the top pick. For lower risk and steady performance, consider the alternative. Always match your choice to your risk tolerance and investment goals.*"
    return recommendation


# import datetime
# import requests
# import streamlit as st
# import yfinance as yf
# import matplotlib.pyplot as plt
# from langchain.schema import Document
# from bs4 import BeautifulSoup

# def fetch_news(company_name, api_key):
#     today = datetime.date.today().isoformat()
#     url = "https://newsdata.io/api/1/news"
#     params = {
#         "apikey": api_key,
#         "q": f"{company_name} stock",
#         "language": "en"
#     }
#     try:
#         response = requests.get(url, params=params)
#         if response.status_code != 200:
#             st.error(f"NewsData API error {response.status_code}: {response.text}")
#             return []
#         json_data = response.json()
#         articles = json_data.get("results", [])
#         docs = []
#         for article in articles:
#             pub_date = article.get("pubDate", "")[:10]
#             if pub_date == today:
#                 content = f"{article.get('title', '')}\n{article.get('description', '')}\n{article.get('link', '')}"
#                 docs.append(Document(page_content=content, metadata={"source": article.get("link", "")}))
#             if len(docs) >= 5:
#                 break
#         return docs
#     except Exception as e:
#         st.error(f"Failed to fetch news: {e}")
#         return []

# def plot_stock_price(price_data):
#     fig, ax = plt.subplots(figsize=(10, 6))
#     for ticker, prices in price_data.items():
#         if not prices.empty:
#             ax.plot(prices.index, prices.values, label=ticker)
#         else:
#             st.warning(f"No price data found for {ticker}")
#     ax.set_title("Stock Price Comparison - Last 7 Days")
#     ax.set_xlabel("Date")
#     ax.set_ylabel("Closing Price (in INR/USD)")
#     ax.legend()
#     fig.autofmt_xdate()  # Prevent overlapping dates
#     st.pyplot(fig)

# def get_yahoo_ticker(company_name):
#     """
#     Find the most probable stock ticker from Yahoo Finance search results.
#     """
#     search_url = f"https://finance.yahoo.com/lookup?s={company_name.replace(' ', '+')}"
#     headers = {"User-Agent": "Mozilla/5.0"}
#     try:
#         response = requests.get(search_url, headers=headers, timeout=10)
#         soup = BeautifulSoup(response.text, "html.parser")
#         for row in soup.find_all("tr"):
#             cols = row.find_all("td")
#             if len(cols) >= 2:
#                 symbol = cols[0].text.strip()
#                 name = cols[1].text.strip().lower()
#                 if company_name.lower() in name:
#                     return symbol
#         # Fallback: return first symbol found
#         symbol_cell = soup.find("td", attrs={"data-test": "QUOTE_SYMBOL"})
#         if symbol_cell:
#             return symbol_cell.text.strip()
#         return None
#     except Exception as e:
#         st.error(f"Error fetching ticker for {company_name}: {e}")
#         return None

# def summarize_news(news_docs, llm=None):
#     """
#     Summarizes each news article.
#     If an LLM is provided, use it; otherwise, use the first two lines as a summary.
#     Returns a list of (summary, source_url) tuples.
#     """
#     summaries = []
#     for doc in news_docs:
#         content = doc.page_content
#         if llm:
#             prompt = f"Summarize this news article in 1-2 sentences:\n{content}"
#             summary = llm(prompt)
#         else:
#             lines = [line.strip() for line in content.split('\n') if line.strip()]
#             summary = " ".join(lines[:2]) if lines else ""
#         source_url = doc.metadata.get("source", "")
#         summaries.append((summary, source_url))
#     return summaries

# def display_news_summaries_and_sources(st, all_summaries):
#     """
#     Displays news summaries and sources in a clean, aligned format in Streamlit.
#     all_summaries: dict {company_name: [(summary, url), ...]}
#     """
#     st.header("📰 News Summaries")
#     for company, summaries in all_summaries.items():
#         if summaries:
#             st.markdown(f"### {company}")
#             st.markdown("**Key News Points:**")
#             for i, (summary, url) in enumerate(summaries, 1):
#                 st.markdown(f"{i}. {summary}")
#             st.markdown("**Sources:**")
#             for i, (summary, url) in enumerate(summaries, 1):
#                 st.markdown(f"- [Source {i}]({url})")
#             st.markdown("---")
#         else:
#             st.markdown(f"### {company}")
#             st.markdown("_No recent news found._")
#             st.markdown("---")

# def conclude_from_news(news_summaries, company_name):
#     """
#     Given a list of (summary, url) tuples for a company,
#     returns a formatted conclusion string.
#     Handles the case where no news articles are found.
#     """
#     if not news_summaries:
#         return f"**{company_name}:**\n_No recent news articles found for this stock. Please check back later or consider other sources._"

#     # Simple sentiment analysis: count positive/negative words
#     pos_keywords = ["growth", "profit", "gain", "strong", "beat", "record", "increase", "up", "surge", "improve"]
#     neg_keywords = ["loss", "decline", "drop", "fall", "down", "weak", "scandal", "cut", "negative", "decrease"]

#     pos_count = 0
#     neg_count = 0
#     for summary, _ in news_summaries:
#         s = summary.lower()
#         if any(word in s for word in pos_keywords):
#             pos_count += 1
#         if any(word in s for word in neg_keywords):
#             neg_count += 1

#     if pos_count > neg_count:
#         sentiment = "positive"
#     elif neg_count > pos_count:
#         sentiment = "negative"
#     else:
#         sentiment = "mixed or neutral"

#     # Format bullet-pointed news and sources
#     news_points = "\n".join([f"- {summary}" for summary, url in news_summaries])
#     sources = "\n".join([f"- [Source {i+1}]({url})" for i, (_, url) in enumerate(news_summaries) if url])

#     conclusion = (
#         f"**{company_name}:**\n"
#         f"**News sentiment:** {sentiment.capitalize()}.\n\n"
#         f"**Key News Points:**\n{news_points}\n\n"
#         f"**Sources:**\n{sources if sources else '_No sources available_'}"
#     )
#     return conclusion

# def analyze_news_sentiment(news_summaries):
#     """
#     Simple keyword-based sentiment: 'positive', 'negative', or 'mixed'
#     """
#     if not news_summaries:
#         return "no news"
#     pos_keywords = ["profit", "growth", "expansion", "record", "strong", "beat", "increase", "surge", "rise", "up"]
#     neg_keywords = ["loss", "decline", "drop", "fall", "decrease", "scandal", "weak", "down", "plunge", "cut"]
#     pos, neg = 0, 0
#     for summary, _ in news_summaries:
#         s = summary.lower()
#         if any(word in s for word in pos_keywords):
#             pos += 1
#         if any(word in s for word in neg_keywords):
#             neg += 1
#     if pos > neg:
#         return "positive"
#     elif neg > pos:
#         return "negative"
#     else:
#         return "mixed"
    
    