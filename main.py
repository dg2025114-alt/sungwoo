
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date, timedelta

# -----------------------------
# 유틸 함수
# -----------------------------
@st.cache_data(show_spinner=False)
def load_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """
    yfinance로 종가(Adj Close) 데이터 로드 후, 열을 티커명으로 하는 DataFrame 반환.
    시간대/공휴일 차이를 고려해 outer join 후 정렬하고, 전일가로 결측 채움.
    """
    if not tickers:
        return pd.DataFrame()

    data = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        group_by='ticker',
        threads=True
    )

    # yfinance가 단일/복수 티커에서 반환 형태가 달라서 정규화
    if isinstance(data.columns, pd.MultiIndex):
        # ('AAPL', 'Adj Close') 형태 -> 열: AAPL, 값: Adj Close
        adj = {}
        for t in tickers:
            if (t, 'Adj Close') in data.columns:
                adj[t] = data[(t, 'Adj Close')]
            elif (t, 'Close') in data.columns:
                adj[t] = data[(t, 'Close')]
        df = pd.DataFrame(adj)
    else:
        # 단일 티커: 열이 'Adj Close' 또는 'Close'
        if 'Adj Close' in data.columns:
            df = data[['Adj Close']].rename(columns={'Adj Close': tickers[0]})
        else:
            df = data[['Close']].rename(columns={'Close': tickers[0]})

    df = df.sort_index()
    # 휴장일/미싱값을 전일 값으로 보간(리턴 계산의 안정성)
    df = df.ffill()
    # 전부 NaN인 열 제거(티커 오류 방지)
    df = df.dropna(axis=1, how='all')
    return df


def compute_metrics(price_df: pd.DataFrame, freq: str = 'D'):
    """
    - 일간 수익률, 연율화 수익률/변동성, 최대낙폭 계산
    freq: 'D' 기준으로 252거래일 가정
    """
    if price_df.empty or price_df.shape[0] < 2:
        return None

    ret = price_df.pct_change().dropna(how='all')
    ann_factor = 252 if freq.upper() == 'D' else 52

    cum = (1 + ret).cumprod() - 1
    mean_daily = ret.mean()
    std_daily = ret.std()

    ann_return = (1 + mean_daily) ** ann_factor - 1
    ann_vol = std_daily * np.sqrt(ann_factor)
    sharpe = ann_return / ann_vol.replace(0, np.nan)

    # 최대낙폭
    rolling_max = price_df.cummax()
    drawdown = price_df / rolling_max - 1
    mdd = drawdown.min()

    metrics = pd.DataFrame({
        'Ann. Return': ann_return,
        'Ann. Vol': ann_vol,
        'Sharpe (R=0)': sharpe,
        'Max Drawdown': mdd
    }).sort_values('Ann. Return', ascending=False)
    return ret, cum, drawdown, metrics


def normalize_to_base(df: pd.DataFrame, base: pd.Timestamp | None):
    """
    기준일(base) 가격 = 100으로 정규화. base가 None이면 첫 날짜 사용.
    """
    if df.empty:
        return df

    if base is None or base not in df.index:
        base = df.index[0]
    base_vals = df.loc[base]
    # 0 또는 NaN 방지
    base_vals = base_vals.replace(0, np.nan)
    norm = df.divide(base_vals) * 100
    return norm


# -----------------------------
# UI 설정
# -----------------------------
st.set_page_config(page_title="글로벌 주식 비교 대시보드", page_icon="📈", layout="wide")

st.title("📈 한국/미국 주요 주식 비교 대시보드")
st.caption("yfinance 기반 | 수익률·차트·리스크 지표를 한 화면에서 비교")

# 기본 티커 (KR: 종가 KRW 환산, US: USD)
# 한국 종목은 yfinance 표기: '005930.KS' (삼성전자), '000660.KS'(SK하이닉스) 등
default_kr = ["005930.KS", "000660.KS", "035420.KS"]  # 삼성전자, SK하이닉스, NAVER
default_us = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]

with st.sidebar:
    st.header("설정")
    st.subheader("티커 선택")
    kr_tickers = st.text_area(
        "한국(KRX) 티커(.KS/.KQ 포함, 쉼표로 구분)",
        value=", ".join(default_kr),
        height=80,
        placeholder="예) 005930.KS, 000660.KS"
    )
    us_tickers = st.text_area(
        "미국(US) 티커(쉼표로 구분)",
        value=", ".join(default_us),
        height=80,
        placeholder="예) AAPL, MSFT"
    )

    st.subheader("기간")
    today = date.today()
    start_date = st.date_input("시작일", today - timedelta(days=365))
    end_date = st.date_input("종료일", today)

    st.subheader("정규화 기준일")
    norm_mode = st.radio(
        "차트 기준",
        options=["첫 거래일(자동)", "사용자 지정"],
        horizontal=True
    )
    norm_base = None
    if norm_mode == "사용자 지정":
        norm_base = st.date_input("정규화 기준일 선택")

    st.subheader("표시 옵션")
    show_kr = st.checkbox("한국 주식 보기", value=True)
    show_us = st.checkbox("미국 주식 보기", value=True)
    show_table = st.checkbox("수익률 표 보기", value=True)
    show_drawdown = st.checkbox("최대낙폭(드로우다운) 차트", value=False)

# 입력 파싱
def parse_tickers(s: str):
    return [t.strip() for t in s.split(",") if t.strip()]

kr_list = parse_tickers(kr_tickers) if show_kr else []
us_list = parse_tickers(us_tickers) if show_us else []
tickers = kr_list + us_list

# 데이터 로드
if not tickers:
    st.warning("왼쪽 사이드바에서 티커를 입력/선택하세요.")
    st.stop()

if start_date >= end_date:
    st.error("시작일은 종료일보다 이전이어야 합니다.")
    st.stop()

with st.spinner("데이터 불러오는 중..."):
    price = load_prices(tickers, str(start_date), str(end_date + timedelta(days=1)))  # yfinance end-exclusive 보정

if price.empty:
    st.error("데이터를 불러오지 못했습니다. 티커 표기 또는 기간을 확인하세요.")
    st.stop()

# 공휴일/상장일 차이로 인해 티커별 시작점이 다를 수 있어, 전부 NaN인 행 제거
price = price.dropna(how='all')

# 메트릭 계산
calc = compute_metrics(price, freq='D')
if calc is None:
    st.error("계산할 데이터가 충분하지 않습니다.")
    st.stop()

ret, cum, dd, metrics = calc

# 정규화(=100 기준) 라인차트
norm_base_ts = None
if norm_base is not None:
    try:
        norm_base_ts = pd.Timestamp(norm_base)
    except Exception:
        norm_base_ts = None

norm_price = normalize_to_base(price, norm_base_ts)
st.subheader("정규화 가격(=100) 비교")
st.line_chart(norm_price)

# 요약 메트릭(상위 5 기준 수익률)
st.subheader("핵심 지표")
st.dataframe(
    (metrics * 100).round(2).rename(columns={
        'Ann. Return': 'Ann. Return (%)',
        'Ann. Vol': 'Ann. Vol (%)',
        'Sharpe (R=0)': 'Sharpe',
        'Max Drawdown': 'Max DD (%)'
    }),
    use_container_width=True
)

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 누적 수익률")
    st.line_chart((cum * 100).round(2))

with col2:
    st.markdown("### 일간 수익률 분포(간단 보기)")
    # 간단 요약: 최근 252일 평균/표준편차
    recent = ret.tail(252)
    desc = pd.DataFrame({
        'Mean(%)': (recent.mean() * 100).round(3),
        'Std(%)': (recent.std() * 100).round(3),
        'Skew': recent.skew().round(3),
        'Kurt': recent.kurt().round(3)
    }).sort_values('Mean(%)', ascending=False)
    st.dataframe(desc, use_container_width=True)

if show_drawdown:
    st.subheader("드로우다운(최대낙폭) 경로")
    st.line_chart((dd * 100).round(2))

if show_table:
    st.subheader("원시 가격 데이터 미리보기")
    st.dataframe(price.tail(20).round(2), use_container_width=True)

st.markdown("---")
st.caption(
    "참고: 한국(.KS/.KQ)과 미국 시장은 거래일이 달라 결측이 있을 수 있습니다. "
    "본 앱은 전일가로 결측을 채워 비교 가능한 시계열로 정렬합니다. "
    "수수료/세금/환율 변동 미반영. 투자 판단의 책임은 투자자 본인에게 있습니다."
)
