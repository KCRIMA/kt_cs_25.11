# conda activate kt_cs_25.11-12
# pip install fastapi uvicorn pandas

# uvicorn main:app --reload
# uvicorn main:app --host 127.0.0.1 --port 8000

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import os

app = FastAPI()

# ─────────────────────────────
# CORS 설정 (프론트엔드에서 API 호출 허용)
# ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 origin 허용 (개발용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────
# 1) 서버 시작 시 CSV 한 번만 로드
# ─────────────────────────────
CSV_PATH = r"telco_customer_data.csv"

if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}")

try:
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
except Exception:
    df = pd.read_csv(CSV_PATH, encoding="cp949")

# customerID 기준으로 바로 찾기 위해 index 설정
if "customerID" not in df.columns:
    raise ValueError("CSV에 'customerID' 컬럼이 없습니다.")

df_indexed = df.set_index("customerID")


# ─────────────────────────────
# 2) 기본 루트
# ─────────────────────────────
@app.get("/")
def root():
    return {"message": "고객 조회 API - /search/customer?name=이름&phone=전화번호"}


# ─────────────────────────────
# 3) CSV 미리보기 (확인용)
# ─────────────────────────────
@app.get("/load-csv")
def load_csv():
    preview = df.head().to_dict(orient="records")
    return {
        "filename": CSV_PATH,
        "rows": len(df),
        "cols": list(df.columns),
        "preview": preview
    }


# ─────────────────────────────
# 4) customerID로 행 조회하는 API
# ─────────────────────────────
@app.get("/customer/{customer_id}")
def get_customer(customer_id: str):
    """
    예: GET /customer/7590-VHVEG
    """
    if customer_id not in df_indexed.index:
        raise HTTPException(status_code=404, detail="해당 customerID가 없습니다.")

    row = df_indexed.loc[customer_id]

    if isinstance(row, pd.Series):
        data = row.to_dict()
        data["customerID"] = customer_id
        return data
    else:
        records = row.reset_index().to_dict(orient="records")
        return {"count": len(records), "rows": records}


# ─────────────────────────────
# 5) 고객명 + 전화번호로 검색하는 API
# ─────────────────────────────
@app.get("/search/customer")
def search_customer(
    name: str = Query(None, description="고객명"),
    phone: str = Query(None, description="전화번호")
):
    """
    고객명과 전화번호로 고객을 검색합니다.
    예: GET /search/customer?name=조하은&phone=01043033054
    """
    if not name and not phone:
        raise HTTPException(status_code=400, detail="고객명 또는 전화번호를 입력해주세요.")
    
    result = df.copy()
    
    # 고객명으로 필터링
    if name:
        result = result[result["customer_name"].str.contains(name, na=False)]
    
    # 전화번호로 필터링 (하이픈 제거 후 비교)
    if phone:
            # 1) 프론트에서 넘어온 값: 하이픈 제거
            phone_clean = phone.replace("-", "")

            # 2) 전화번호로 필터링 (맨 앞 0 제거 + 하이픈 제거 후 비교)
            phone_clean = phone_clean.lstrip("0")

            # 3) CSV 쪽도 동일한 기준으로 정규화해서 비교
            result = result[
                result["contact_number"]
                    .astype(str)
                    .str.replace("-", "")
                    .str.lstrip("0")         # 혹시 모를 0 제거
                    .str.contains(phone_clean, na=False)
            ]
    
    if result.empty:
        raise HTTPException(status_code=404, detail="해당 조건에 맞는 고객이 없습니다.")
    
    # 결과를 리스트로 반환
    records = result.to_dict(orient="records")
    
    return {
        "count": len(records),
        "customers": records
    }

# ─────────────────────────────
# 6) 연락처(랜덤 뽑는 용도)
# ─────────────────────────────
@app.get("/contact_numbers")
def get_contact_numbers():
    numbers = (
        df["contact_number"]
          .dropna()
          .astype(str)
          .str.replace(r"\D", "", regex=True)  # 숫자만 남기기(선택)
          .unique()
          .tolist()
    )
    return {"contact_numbers": numbers}

# ─────────────────────────────
# 7) 스프링이 호출하는 요약 엔드포인트
# ─────────────────────────────
@app.get("/summary")
def summary():
    total_customers = int(len(df))
    churn_rate = float(df["Actual_Churn"].mean())

    return {
        "total_customers": total_customers,
        "churn_rate": churn_rate
    }


# ═══════════════════════════════════════════════════════════════
# Admin 대시보드 API
# ═══════════════════════════════════════════════════════════════

# ─────────────────────────────
# 7) Admin 대시보드용 - 전체 고객 데이터 반환
# ─────────────────────────────
@app.get("/admin/customers")
def get_all_customers(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(100, ge=1, le=5000, description="페이지당 항목 수"),
    risk: str = Query(None, description="위험도 필터 (high/medium/low)"),
    sort_by: str = Query("Churn_Probability", description="정렬 기준"),
    order: str = Query("desc", description="정렬 순서 (asc/desc)")
):
    """관리자 대시보드용 전체 고객 데이터 (페이지네이션 지원)"""
    result = df.copy()
    
    # 위험도 필터링
    if risk == "high":
        result = result[result["Churn_Probability"] >= 0.7]
    elif risk == "medium":
        result = result[(result["Churn_Probability"] >= 0.4) & (result["Churn_Probability"] < 0.7)]
    elif risk == "low":
        result = result[result["Churn_Probability"] < 0.4]
    
    # 정렬
    if sort_by in result.columns:
        ascending = order.lower() == "asc"
        result = result.sort_values(by=sort_by, ascending=ascending)
    
    # 전체 개수
    total_count = len(result)
    
    # 페이지네이션
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated = result.iloc[start_idx:end_idx]
    
    records = paginated.to_dict(orient="records")
    
    return {
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit,
        "customers": records
    }


# ─────────────────────────────
# 8) Admin 대시보드용 - KPI 통계
# ─────────────────────────────
@app.get("/admin/stats")
def get_admin_stats():
    """KPI 카드용 통계"""
    total_customers = len(df)
    risk_customers = len(df[df["Churn_Probability"] >= 0.7])
    avg_wait_time = df["wait_time_sec"].mean()
    repeat_rate = (df["repeat_contacts_7d"] > 0).mean() * 100
    avg_call_duration = df["call_duration_sec"].mean()
    actual_churn_count = int(df["Actual_Churn"].sum())
    
    return {
        "total_customers": int(total_customers),
        "risk_customers": int(risk_customers),
        "avg_wait_time": round(avg_wait_time, 1),
        "repeat_rate": round(repeat_rate, 1),
        "avg_call_duration": round(avg_call_duration, 1),
        "actual_churn_count": actual_churn_count
    }


# ─────────────────────────────
# 9) Admin 대시보드용 - 모든 차트 데이터
# ─────────────────────────────
@app.get("/admin/charts")
def get_chart_data():
    """모든 차트 데이터 한 번에 반환"""
    import numpy as np
    
    # 1. 문의 카테고리 분포
    category_counts = df["issue_category"].value_counts().to_dict()
    
    # 2. 이탈 확률 분포 (10% 구간별)
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    labels = ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%", "50-60%", "60-70%", "70-80%", "80-90%", "90-100%"]
    churn_dist = pd.cut(df["Churn_Probability"], bins=bins, labels=labels, include_lowest=True).value_counts().sort_index()
    churn_histogram = {str(k): int(v) for k, v in churn_dist.items()}
    
    # 3. 계약유형별 이탈률
    contract_stats = df.groupby("Contract").agg({
        "Churn_Probability": "mean",
        "Actual_Churn": "mean",
        "customerID": "count"
    }).rename(columns={"customerID": "count"})
    contract_churn = {}
    for contract_type in contract_stats.index:
        contract_churn[contract_type] = {
            "avg_churn_probability": round(float(contract_stats.loc[contract_type, "Churn_Probability"]) * 100, 1),
            "actual_churn_rate": round(float(contract_stats.loc[contract_type, "Actual_Churn"]) * 100, 1),
            "count": int(contract_stats.loc[contract_type, "count"])
        }
    
    # 4. 대기 시간 분포 (초 단위)
    wait_bins = [0, 30, 60, 90, 120, 150, 180, float("inf")]
    wait_labels = ["0-30초", "30-60초", "60-90초", "90-120초", "120-150초", "150-180초", "180초+"]
    wait_dist = pd.cut(df["wait_time_sec"], bins=wait_bins, labels=wait_labels, include_lowest=True).value_counts().sort_index()
    wait_time = {str(k): int(v) for k, v in wait_dist.items()}
    
    # 5. 통화 시간 분포 (분 단위)
    call_duration_min = df["call_duration_sec"] / 60
    call_bins = [0, 2, 5, 10, 15, 20, float("inf")]
    call_labels = ["0-2분", "2-5분", "5-10분", "10-15분", "15-20분", "20분+"]
    call_dist = pd.cut(call_duration_min, bins=call_bins, labels=call_labels, include_lowest=True).value_counts().sort_index()
    call_duration = {str(k): int(v) for k, v in call_dist.items()}
    
    # 6. 반복 문의 vs 이탈 확률 (산점도용 데이터)
    scatter_data = df[["repeat_contacts_7d", "Churn_Probability", "issue_category"]].to_dict(orient="records")
    
    return {
        "category": category_counts,
        "churn_histogram": churn_histogram,
        "contract_churn": contract_churn,
        "wait_time": wait_time,
        "call_duration": call_duration,
        "scatter_data": scatter_data
    }


# ─────────────────────────────
# 10) Admin 대시보드용 - 고위험 고객 리스트
# ─────────────────────────────
@app.get("/admin/high-risk-customers")
def get_high_risk_customers(limit: int = Query(20, ge=1, le=100)):
    """이탈 확률 높은 순으로 고위험 고객 리스트"""
    high_risk = df[df["Churn_Probability"] >= 0.7].sort_values(
        by="Churn_Probability", ascending=False
    ).head(limit)
    
    # 필요한 컬럼만 선택
    columns = [
        "customerID", "customer_name", "Churn_Probability", 
        "issue_category", "repeat_contacts_7d", "wait_time_sec",
        "call_duration_sec", "Contract", "MonthlyCharges"
    ]
    result = high_risk[columns].to_dict(orient="records")
    
    return {
        "count": len(result),
        "customers": result
    }
