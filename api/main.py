# conda activate kt_cs_25.11-12
# pip install flask

# uvicorn main:app --reload
# uvicorn app:app --host 127.0.0.1 --port 8000


from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import os

app = FastAPI()

# ─────────────────────────────
# 1) 서버 시작 시 CSV 한 번만 로드
# ─────────────────────────────
CSV_PATH = r"11.29_lgb_chan.csv"

if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}")

try:
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
except Exception:
    df = pd.read_csv(CSV_PATH, encoding="cp949")

# customerID 기준으로 바로 찾기 위해 index 설정
if "customerID" not in df.columns:
    raise ValueError("CSV에 'customerID' 컬럼이 없습니다.")

df = df.set_index("customerID")


# ─────────────────────────────
# 2) 기본 루트
# ─────────────────────────────
@app.get("/")
def root():
    return {"message": "CSV 미리보기는 /load-csv, 고객 조회는 /customer/{customer_id} 를 사용하세요."}


# ─────────────────────────────
# 3) CSV 미리보기 (그냥 확인용)
# ─────────────────────────────
@app.get("/load-csv")
def load_csv():
    preview = df.reset_index().head().to_dict(orient="records")
    return {
        "filename": CSV_PATH,
        "rows": len(df),
        "cols": list(df.reset_index().columns),
        "preview": preview
    }


# ─────────────────────────────
# 4) 핵심: customerID로 행 조회하는 API
# ─────────────────────────────
@app.get("/customer/{customer_id}")
def get_customer(customer_id: str):
    """
    예: GET /customer/1113-IUJYX
    """
    if customer_id not in df.index:
        # 없는 ID면 404
        raise HTTPException(status_code=404, detail="해당 customerID가 없습니다.")

    row = df.loc[customer_id]

    # 중복 없이 unique하면 row는 Series, 중복이면 DataFrame이 될 수 있음
    if isinstance(row, pd.Series):
        data = row.to_dict()
        data["customerID"] = customer_id
        return data
    else:
        # 혹시 같은 customerID가 여러 개면 리스트로 반환
        records = row.reset_index().to_dict(orient="records")
        return {"count": len(records), "rows": records}

# 스프링이 호출하는 엔드포인트
@app.get("/summary")
def summary():
    # 전체 고객 수
    total_customers = int(len(df))

    # 이탈률(Churn 컬럼이 0/1이니까 mean() == 이탈 비율)
    churn_rate = float(df["Churn"].mean())

    return {
        "total_customers": total_customers,
        "churn_rate": churn_rate
    }