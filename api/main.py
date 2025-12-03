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
CSV_PATH = r"telco_with_name_phone.csv"

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
        phone_clean = phone.replace("-", "")
        result = result[result["phone_number"].astype(str).str.replace("-", "").str.contains(phone_clean, na=False)]
    
    if result.empty:
        raise HTTPException(status_code=404, detail="해당 조건에 맞는 고객이 없습니다.")
    
    # 결과를 리스트로 반환
    records = result.to_dict(orient="records")
    
    return {
        "count": len(records),
        "customers": records
    }


# ─────────────────────────────
# 6) 스프링이 호출하는 요약 엔드포인트
# ─────────────────────────────
@app.get("/summary")
def summary():
    total_customers = int(len(df))
    churn_rate = float(df["Churn"].mean())

    return {
        "total_customers": total_customers,
        "churn_rate": churn_rate
    }
