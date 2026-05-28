import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# 1. 페이지 설정
st.set_page_config(page_title="한/미 주요 주식 비교 분석기", layout="wide")
st.title("📈 한/미 주요 주식 수익률 & 차트 비교")
st.write("한국과 미국 주요 주식의 수익률과 주가 추이를 한눈에 비교해 보세요.")

# 2. 사이드바 - 조건 선택
st.sidebar.header("🔍 설정")

# 비교할 주식 매핑 (이름: 티커)
STOCK_DICT = {
    # 미국 주식
    "Apple (AAPL)": "AAPL",
    "Microsoft (MSFT)": "MSFT",
    "NVIDIA (NVDA)": "NVDA",
    "Tesla (TSLA)": "TSLA",
    # 한국 주식 (yfinance는 .KS 또는 .KQ 필요)
    "삼성전자 (005930)": "005930.KS",
    "SK하이닉스 (000660)": "000660.KS",
    "현대차 (005380)": "005380.KS",
    "NAVER (035420)": "035420.KS"
}

# 주식 선택 (기본값으로 애플과 삼성전자 선택)
selected_stocks = st.sidebar.multiselect(
    "비교할 주식을 선택하세요 (복수 선택 가능)",
    options=list(STOCK_DICT.keys()),
    default=["Apple (AAPL)", "삼성전자 (005930)"]
)

# 날짜 선택
start_date = st.sidebar.date_input("시작일", datetime.date(2023, 1, 1))
end_date = st.sidebar.date_input("종료일", datetime.date.today())

# 3. 데이터 로드 및 처리
if selected_stocks:
    tickers = [STOCK_DICT[stock] for stock in selected_stocks]
    
    # 데이터 가져오기 (종가 기준)
    @st.cache_data # 데이터를 캐싱하여 앱 속도 향상
    def load_data(ticker_list, start, end):
        data = yf.download(ticker_list, start=start, end=end)['Close']
        # 주식이 1개만 선택되었을 때 Series가 반환되는 것을 방지하기 위해 DataFrame 변환
        if isinstance(data, pd.Series):
            data = data.to_frame(name=ticker_list[0])
        return data

    with st.spinner('데이터를 불러오는 중입니다...'):
        df_price = load_data(tickers, start_date, end_date)
    
    # 역이름 매핑 (티커 코드를 다시 보기 좋은 이름으로 변경)
    inv_stock_dict = {v: k for k, v in STOCK_DICT.items()}
    df_price = df_price.rename(columns=inv_stock_dict)

    # 4. 레이아웃 구성
    tab1, tab2, tab3 = st.tabs(["📊 누적 수익률 비교", "📉 주가 추이 (원시 데이터)", "💾 데이터 확인"])

    with tab1:
        st.subheader("선택 기간 누적 수익률 (%)")
        st.caption("시작일의 주가를 100(%)으로 기준으로 잡은 상대적 수익률 추이입니다.")
        
        # 누적 수익률 계산: (현재 가격 / 시작 가격) - 1
        # 첫 날 가격이 NaN인 경우를 대비해 bfill() 후 첫 행 사용
        initial_prices = df_price.bfill().iloc[0]
        df_return = (df_price / initial_prices - 1) * 100
        
        # 선차트 그리기
        st.line_chart(df_return)

    with tab2:
        st.subheader("주가 추이 비교 (각국 통화 기준)")
        st.caption("미국 주식은 USD($), 한국 주식은 KRW(원) 기준 종가입니다.")
        
        # 주가 원본 차트 (단, 스케일이 다르면 보기 힘들 수 있어 탭을 분리함)
        st.line_chart(df_price)

    with tab3:
        st.subheader("최근 데이터 보기")
        st.dataframe(df_price.tail(10))

else:
    st.warning("⚠️ 사이드바에서 비교할 주식을 하나 이상 선택해 주세요.")
