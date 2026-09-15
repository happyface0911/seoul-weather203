import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────
# 기본 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="서울 100년 기온 변화",
    page_icon="🌡️",
    layout="wide",
)

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"


@st.cache_data(show_spinner="데이터를 불러오는 중입니다...")
def load_data(url: str) -> pd.DataFrame:
    """서울 기온 데이터를 불러와 연도 컬럼을 추가한다."""
    df = pd.read_csv(url, encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["연도"] = df["날짜"].dt.year
    return df


@st.cache_data(show_spinner=False)
def get_yearly_avg(df: pd.DataFrame) -> pd.DataFrame:
    """연도별 평균/최저/최고 기온을 계산한다."""
    yearly = (
        df.groupby("연도")[["평균기온", "최저기온", "최고기온"]]
        .mean()
        .reset_index()
    )
    return yearly


# ──────────────────────────────────────────────
# 데이터 로드
# ──────────────────────────────────────────────
try:
    raw_df = load_data(DATA_URL)
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

yearly_df = get_yearly_avg(raw_df)

# 데이터가 완전하지 않은 첫 해/마지막 해는 그래프 왜곡을 줄이기 위해 표시만 하고 필터링 옵션 제공
min_year = int(yearly_df["연도"].min())
max_year = int(yearly_df["연도"].max())

# ──────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────
st.title("🌡️ 서울, 100년의 기온 변화")
st.markdown(
    f"""
    서울(종로구, 관측지점 108) 일별 기온 관측 데이터를 바탕으로
    **{min_year}년부터 {max_year}년까지** 연평균 기온이 어떻게 변해왔는지 살펴봅니다.
    """
)

# ──────────────────────────────────────────────
# 사이드바 - 옵션
# ──────────────────────────────────────────────
st.sidebar.header("⚙️ 옵션")

year_range = st.sidebar.slider(
    "기간 선택",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),
)

show_minmax = st.sidebar.checkbox("최저·최고 기온도 함께 보기", value=False)
show_trend = st.sidebar.checkbox("추세선(선형 회귀) 표시", value=True)
show_ma = st.sidebar.checkbox("10년 이동평균 표시", value=True)

filtered = yearly_df[
    (yearly_df["연도"] >= year_range[0]) & (yearly_df["연도"] <= year_range[1])
].copy()

# ──────────────────────────────────────────────
# 핵심 지표
# ──────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

first_val = filtered.iloc[0]["평균기온"]
last_val = filtered.iloc[-1]["평균기온"]
diff = last_val - first_val

col1.metric(
    f"{int(filtered.iloc[0]['연도'])}년 연평균 기온",
    f"{first_val:.1f} °C",
)
col2.metric(
    f"{int(filtered.iloc[-1]['연도'])}년 연평균 기온",
    f"{last_val:.1f} °C",
)
col3.metric(
    "변화량",
    f"{diff:+.1f} °C",
    delta=f"{diff:+.1f} °C",
)

st.markdown("---")

# ──────────────────────────────────────────────
# 메인 그래프
# ──────────────────────────────────────────────
fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=filtered["연도"],
        y=filtered["평균기온"],
        mode="lines+markers",
        name="연평균 기온",
        line=dict(color="#e76f51", width=2),
        marker=dict(size=4),
    )
)

if show_ma:
    filtered["10년 이동평균"] = filtered["평균기온"].rolling(window=10, min_periods=1).mean()
    fig.add_trace(
        go.Scatter(
            x=filtered["연도"],
            y=filtered["10년 이동평균"],
            mode="lines",
            name="10년 이동평균",
            line=dict(color="#264653", width=3, dash="solid"),
        )
    )

if show_trend:
    import numpy as np

    coeffs = np.polyfit(filtered["연도"], filtered["평균기온"], 1)
    trend_y = np.polyval(coeffs, filtered["연도"])
    fig.add_trace(
        go.Scatter(
            x=filtered["연도"],
            y=trend_y,
            mode="lines",
            name=f"추세선 (연 {coeffs[0]*10:+.2f}°C/10년)",
            line=dict(color="#2a9d8f", width=2, dash="dash"),
        )
    )

if show_minmax:
    fig.add_trace(
        go.Scatter(
            x=filtered["연도"],
            y=filtered["최고기온"],
            mode="lines",
            name="연평균 최고기온",
            line=dict(color="#f4a261", width=1.5),
            opacity=0.7,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=filtered["연도"],
            y=filtered["최저기온"],
            mode="lines",
            name="연평균 최저기온",
            line=dict(color="#457b9d", width=1.5),
            opacity=0.7,
        )
    )

fig.update_layout(
    xaxis_title="연도",
    yaxis_title="기온 (°C)",
    hovermode="x unified",
    height=560,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=40, b=10),
)

st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────
# 원자료 보기
# ──────────────────────────────────────────────
with st.expander("📋 연도별 데이터 표 보기"):
    st.dataframe(
        filtered.rename(
            columns={
                "연도": "연도",
                "평균기온": "연평균 기온(°C)",
                "최저기온": "연평균 최저기온(°C)",
                "최고기온": "연평균 최고기온(°C)",
            }
        ).round(1),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "데이터 출처: 기상자료개방포털(서울, 지점번호 108) · "
    "https://github.com/greatsong/modudata"
)
