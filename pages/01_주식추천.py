import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# ==========================================
# 1. 페이지 설정 및 제목
# ==========================================
st.set_page_config(page_title="삼성전자 집중 분석기", layout="wide")
st.title("📱 삼성전자(005930.KS) 주가 & 거래량 분석")
st.write("삼성전자의 과거 주가 추이와 이동평균선, 거래량 흐름을 실시간으로 분석합니다.")

# ==========================================
# 2. 사이드바 설정 (분석 기간 선택)
# ==========================================
st.sidebar.header("📅 분석 기간 설정")
start_date = st.sidebar.date_input("시작일", datetime.date(2023, 1, 1))
end_date = st.sidebar.date_input("종료일", datetime.date.today())

# ==========================================
# 3. 데이터 로드 함수 (캐싱 적용)
# ==========================================
ticker_code = "005930.KS"

@st.cache_data
def get_stock_data(start, end):
    # 안정적인 주가 데이터만 다운로드 (종가, 거래량 등)
    df_raw = yf.download(ticker_code, start=start, end=end)
    return df_raw

# 데이터 불러오기
df = get_stock_data(start_date, end_date)

# ==========================================
# 4. 데이터 시각화 및 분석
# ==========================================
if not df.empty:
    # yfinance 버전에 따라 컬럼이 MultiIndex로 오는 경우를 대비해 단일 인덱스로 변환
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 이동평균선(MA) 계산
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()

    # 상단 대시보드용 주요 지표 계산 (가장 최근 영업일 기준)
    latest_close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2])
    price_change = latest_close - prev_close
    price_change_pct = (price_change / prev_close) * 100
    max_price = float(df['High'].max())

    # 최상단 메트릭 카드 배치 (현재가, 전일대비, 최고가)
    col1, col2, col3 = st.columns(3)
    col1.metric(label="현재가 (종가 기준)", value=f"{int(latest_close):,} 원")
    col2.metric(label="전일 대비", value=f"{int(price_change):,} 원", delta=f"{price_change_pct:.2f}%")
    col3.metric(label="분석 기간 최고가", value=f"{int(max_price):,} 원")

    st.markdown("---")

    # 탭 메뉴 구성 (에러 유발하는 재무 탭 제거)
    tab1, tab2, tab3 = st.tabs(["📉 주가 및 이동평균선", "📊 거래량 분석", "💾 데이터 원본"])

    # [탭 1] 주가 및 이동평균선 차트
    with tab1:
        st.subheader("주가 추이 및 이동평균선 (20일, 60일, 120일)")
        st.caption("이동평균선(MA)을 통해 주가의 단기/장기 흐름을 파악할 수 있습니다.")
