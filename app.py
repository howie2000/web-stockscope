import streamlit as st
import yfinance as yf
from openai import OpenAI
import os
from dotenv import load_dotenv
import requests
from PIL import Image
import base64
import io
import streamlit.components.v1 as components

# Load environment variables
load_dotenv()
client = OpenAI()  # Automatically picks up OPENAI_API_KEY from .env

# App title
st.title("📈 StockScope AI")

# User input with default value
ticker = st.text_input("Enter Stock Ticker (e.g., AAPL, TSLA)", value="MSFT")

# Chart Upload Section
st.markdown("---")
st.subheader("📊 Chart Analysis (Optional)")
st.markdown("Upload a chart screenshot for AI-powered technical analysis:")

uploaded_file = st.file_uploader(
    "Drop your chart screenshot here or click to browse",
    type=['png', 'jpg', 'jpeg'],
    help="Paste a screenshot (Ctrl+V) or drag & drop a chart image"
)

# Function to encode image for OpenAI
def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# Display uploaded image
chart_analysis_available = False
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Chart", use_container_width=True)
    chart_analysis_available = True
    st.success("Chart uploaded successfully! You can now use the Chart Analysis button.")

st.markdown("---")

# Create four columns for buttons (always visible)
col1, col2, col3, col4 = st.columns(4)

with col1:
    ai_summary_btn = st.button("🧠 Generate AI Summary")
    
with col2:
    bull_bear_btn = st.button("🐂🐻 Rate Bullishness")
    
with col3:
    news_summary_btn = st.button("📰 Show News Summary")

with col4:
    chart_analysis_btn = st.button("📊 Analyze Chart", disabled=not chart_analysis_available)

# Only process if ticker is provided
if ticker:
    try:
        # Fetch stock data
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        info = stock.info
        
        # Display basic info
        st.write(f"**Company Name:** {info.get('longName', 'N/A')}")
        st.line_chart(hist["Close"])
        
        # Button 1: AI Summary
        if ai_summary_btn:
            with st.spinner("Generating AI Summary..."):
                prompt = f"""You are a financial analyst. Summarize the recent state of stock {ticker} 
                based on the following last 5 days of data:\n{hist.tail(5)}"""

                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a helpful financial analyst."},
                        {"role": "user", "content": prompt}
                    ]
                )

                summary = response.choices[0].message.content
                st.markdown("### 💡 AI Summary")
                st.write(summary)

        # Button 2: Bull/Bear Rating
        if bull_bear_btn:
            with st.spinner("Analyzing Bull/Bear sentiment..."):
                rating_prompt = f"""You are a financial assistant. Based on the following recent stock data for {ticker}, 
                give a short answer: Is the stock more bullish, bearish, or neutral right now? Justify with 1-2 sentences:\n{hist.tail(5)}"""

                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a concise financial assistant."},
                        {"role": "user", "content": rating_prompt}
                    ]
                )

                rating = response.choices[0].message.content
                st.markdown("### 📊 Bull/Bear Rating")
                st.write(rating)

        # Button 3: News Summary
        if news_summary_btn:
            with st.spinner("Fetching news and generating summary..."):
                news_key = os.getenv("NEWSAPI_KEY")
                
                if not news_key:
                    st.error("NewsAPI key not found. Please check your .env file.")
                else:
                    company_name = info.get("longName", ticker)
                    url = f"https://newsapi.org/v2/everything?q={ticker}&sortBy=publishedAt&language=en&pageSize=5&apiKey={news_key}"
                    
                    try:
                        news_response = requests.get(url)
                        
                        if news_response.status_code == 200:
                            articles = news_response.json().get("articles", [])
                            headlines = [a["title"] for a in articles if a.get("title")]

                            if headlines:
                                st.markdown("### 📰 Recent News Headlines")
                                for h in headlines:
                                    st.write(f"- {h}")

                                # GPT news summary instead of sentiment
                                gpt_prompt = f"""Summarize the key developments and important news about {company_name} based on these recent headlines. Focus on what's happening with the company and what investors should know. Keep it concise but informative (2-3 paragraphs):\n\n"""
                                gpt_prompt += "\n".join([f"- {h}" for h in headlines])

                                gpt_news_response = client.chat.completions.create(
                                    model="gpt-4",
                                    messages=[
                                        {"role": "system", "content": "You are a financial news analyst who creates concise, informative summaries."},
                                        {"role": "user", "content": gpt_prompt}
                                    ]
                                )

                                st.markdown("### 📋 News Summary")
                                st.write(gpt_news_response.choices[0].message.content)
                            else:
                                st.warning("No recent news found for this ticker.")
                        else:
                            st.error(f"NewsAPI error: {news_response.status_code}")
                            if news_response.status_code == 401:
                                st.error("Invalid NewsAPI key. Please check your API key.")
                            elif news_response.status_code == 429:
                                st.error("NewsAPI rate limit exceeded. Please try again later.")
                    
                    except Exception as e:
                        st.error(f"Error fetching news: {str(e)}")

        # Button 4: Chart Analysis
        if chart_analysis_btn and uploaded_file is not None:
            with st.spinner("Analyzing chart for trading signals..."):
                try:
                    image = Image.open(uploaded_file)
                    base64_image = encode_image(image)
                    
                    chart_prompt = f"""Analyze this stock chart image for {ticker}. Look for:
                    
                    1. **Technical Patterns**: Support/resistance levels, trend lines, chart patterns
                    2. **Trading Signals**: Clear buy or sell signals based on technical indicators
                    3. **Price Action**: Recent price movement and momentum
                    4. **Risk Assessment**: Key levels to watch
                    
                    Provide a clear recommendation:
                    - 🟢 **BUY SIGNAL** - if you see strong bullish indicators
                    - 🔴 **SELL SIGNAL** - if you see strong bearish indicators  
                    - 🟡 **HOLD/WAIT** - if signals are mixed or unclear
                    
                    Explain your reasoning in 2-3 concise paragraphs."""

                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": chart_prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=500
                    )

                    st.markdown("### 📈 Chart Analysis & Trading Signals")
                    st.write(response.choices[0].message.content)
                    
                except Exception as e:
                    st.error(f"Error analyzing chart: {str(e)}")
                    st.info("Make sure you have uploaded a valid chart image.")
    
    except Exception as e:
        st.error(f"Error fetching stock data for {ticker}: {str(e)}")
        st.info("Please make sure you entered a valid stock ticker symbol.")

else:
    st.info("👆 Enter a stock ticker above to get started!")