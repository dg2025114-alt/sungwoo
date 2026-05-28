import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# ==========================================
# 1. 페이지 설정 및 제목
# ==========================================
st.set_page_config(page_title="삼성전자 집중 분석기", layout="wide")
st.title("📱 삼성전자(005930.KS) 주가 & 재무 집중 분석")
st.write("삼성전자의 과거 주가 추이, 기술적 지표, 그리고 최신 재무 상태를 분석합니다.")

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
    # 지정된 기간 동안의 주가 데이터 다운로드
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

    # 최상단 메트릭 카드 배치
    col1, col2, col3 = st.columns(3)
    col1.metric(label="현재가 (종가 기준)", value=f"{int(latest_close):,} 원")
    col2.metric(label="전일 대비", value=f"{int(price_change):,} 원", delta=f"{price_change_pct:.2f}%")
    col3.metric(label="분석 기간 최고가", value=f"{int(max_price):,} 원")

    st.markdown("---")

    # 탭 메뉴 구성
    tab1, tab2, tab3 = st.tabs(["📉 주가 및 이동평균선", "📊 거래량 분석", "📑 기업 재무 정보"])

    # [탭 1] 주가 및 이동평균선 차트
    with tab1:
        st.subheader("주가 추이 및 이동평균선 (20일, 60일, 120일)")
        st.caption("이동평균선(MA)을 통해 주가의 단기/장기 흐름을 파악할 수 있습니다.")
        
        # 차트 표기용 데이터프레임 분리 및 한글 이름 매핑
        chart_data = df[['Close', 'MA20', 'MA60', 'MA120']].rename(
            columns={'Close': '종가', 'MA20': '20일선', 'MA60': '60일선', 'MA120': '120일선'}
        )
        st.line_chart(chart_data)

    # [탭 2] 거래량 바 차트
    with tab2:
        st.subheader("일별 거래량(Volume) 추이")
        st.caption("주가 변동 시 거래량이 동반되었는지 확인하는 지표입니다.")
        st.bar_chart(df['Volume'])

    # [탭 3] 야후 파이낸스 기업 재무 정보
    with tab3:
        st.subheader("삼성전자 주요 재무 및 투자 지표")
        
        # Ticker 객체를 통해 재무 데이터 추출
        samsung_ticker = yf.Ticker(ticker_code)
        
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.write("**기업 기본 투자 정보**")
            info = samsung_ticker.info
            
            # 정보가 없을 경우를 대비해 .get() 연산자 사용
            market_cap = info.get('marketCap', 'N/A')
            per = info.get('trailingPE', 'N/A')
            pbr = info.get('priceToBook', 'N/A')
            div_yield = info.get('dividendYield')
            
            # 단위 및 포맷팅 처리
            if isinstance(market_cap, (int, float)):
                st.write(f"- **시가총액:** 약 {market_cap:,} 원")
            else:
                st.write(f"- **시가총액:** {market_cap}")
                
            st.write(f"- **PER (주가수익비율):** {per}")
            st.write(f"- **PBR (주가순자산비율):** {pbr}")
            
            if isinstance(div_yield, float):
                st.write(f"- **배당수익률:** {div_yield * 100:.2f}%")
            else:
                st.write(f"- **배당수익률:** {div_yield}")

        with col_info2:
            st.write("**최근 연간 실적 (결산)**")
            try:
                financials = samsung_ticker.financials
                if not financials.empty:
                    # 주요 항목(매출, 영업이익, 순이익)만 필터링하여 출력
                    target_rows = ['Total Revenue', 'Operating Income', 'Net Income']
                    exist_rows = [r for r in target_rows if r in financials.index]
                    st.dataframe(financials.loc[exist_rows].style.format("{:,.0f}"))
                else:
                    st.info("연간 재무제표 데이터를 불러올 수 없습니다.")
            except Exception:
                st.info("현재 재무제표 데이터를 가져오는 중 일시적인 오류가 발생했습니다.")

else:
    st.error("데이터를 불러오지 못했습니다. 사이드바의 날짜 설정을 확인해 주세요.")
