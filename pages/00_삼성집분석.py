import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# 1. 페이지 설정
st.set_page_config(page_title="삼성전자 집중 분석기", layout="wide")
st.title("📱 삼성전자(005930.KS) 주가 & 재무 집중 분석")
st.write("삼성전자의 과거 주가 추이, 기술적 지표, 그리고 최신 재무 상태를 분석합니다.")

# 2. 데이터 가져오기
ticker_code = "005930.KS"
samsung = yf.Ticker(ticker_code)

# 사이드바 설정 (기간 선택)
st.sidebar.header("📅 분석 기간 설정")
start_date = st.sidebar.date_input("시작일", datetime.date(2023, 1, 1))
end_date = st.sidebar.date_input("종료일", datetime.date.today())

# 주가 데이터 로드
@st.cache_data
def get_stock_data(start, end):
    df = yf.download(ticker_code, start=start, end=end)
    return df

df = get_stock_data(start_date, end_date)

# 3. 데이터가 있을 경우 분석 시작
if not df.empty:
    # 2차원 컬럼 구조(MultiIndex) 풀기 (yfinance 버전에 따른 호환성 확보)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 기술적 지표 계산 (이동평균선)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()

    # 상단 요약 카드 (현재가, 전일대비 등)
    latest_close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2])
    price_change = latest_close - prev_close
    price_change_pct = (price_change / prev_close) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric(label="현재가 (종가 기준)", value=f"{int(latest_close):,} 원")
    col2.metric(label="전일 대비", value=f"{int(price_change):,} 원", delta=f"{price_change_pct:.2f}%")
    col3.metric(label="분석 기간 최고가", value=f"{int(df['High'].max()):,} 원")

    st.markdown("---")

    # 탭 구성 (주가/지표 분석 vs 재무제표)
    tab1, tab2, tab3 = st.tabs(["📉 주가 및 이동평균선", "📊 거래량 분석", "📑 기업 재무 정보"])

    with tab1:
        st.subheader("주가 추이 및 이동평균선 (20일, 60일, 120일)")
        st.caption("이동평균선(MA)을 통해 주가의 단기/장기 흐름을 파악할 수 있습니다.")
        
        # 차트용 데이터 가공
        chart_data = df[['Close', 'MA20', 'MA60', 'MA120']].rename(
            columns={'Close': '종가', 'MA20': '20일선', 'MA60': '60일선', 'MA120': '120일선'}
        )
        st.line_chart(chart_data)

    with tab2:
        st.subheader("일별 거래량(Volume) 추이")
        st.caption("주가 상승/하락 시 거래량이 동반되었는지 확인해 보세요.")
        st.bar_chart(df['Volume'])

    with tab3:
        st.subheader("삼성전자 주요 재무 지표")
        st.write("야후 파이낸스에서 제공하는 삼성전자의 연간/분기 실적 요약입니다.")
        
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.write("**기업 기본 정보**")
            info = samsung.info
            # 주요 정보 안전하게 가져오기
            market_cap = info.get('marketCap', 'N/A')
            per = info.get('trailingPE', 'N/A')
            pbr = info.get('priceToBook', 'N/A')
            dividend_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 'N/A'
            
            st.write(f"- **시가총액:** 약 {market_cap:,} 원" if isinstance(market_cap, (int, float)) else f"- **시가총액:** {market_cap}")
            st.write(f"- **PER (주가수익비율):** {per}")
            st.write(f"- **PBR (주가순자산비율):** {pbr}")
            st.write(f"- **배당수익률:** {dividend_yield:.2f}%" if isinstance(dividend_yield, float) else f"- **배당수익률:** {dividend_yield}")

        with col_info2:
            st.write("**최근 연간 실적 (결산)**")
            try:
                # 연간 재무제표
                financials = samsung.financials
                if not financials.empty:
                    # 상위 몇 개 항목만 추출 (매출, 영업이익, 순이익 등)
                    target_rows = ['Total Revenue', 'Operating Income', 'Net Income']
                    exist_rows =
