# pip install fastapi uvicorn pandas

# uvicorn main:app --reload
# uvicorn main:app --host 127.0.0.1 --port 8000

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import os, re, json

BASE_DIR = Path(__file__).resolve().parents[6]
# ↑ api/main.py 기준
# api → kt_cs_2511 → kt_cs → com → java → main → src → [프로젝트 루트]

ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 .env에 없습니다.")
if not OPENAI_VECTOR_STORE_ID:
    raise RuntimeError("OPENAI_VECTOR_STORE_ID가 .env에 없습니다. setup_vector_store.py 실행 후 .env에 추가하세요.")

client = OpenAI(api_key=OPENAI_API_KEY)

class RAGRequest(BaseModel):
    # ✅ 둘 중 하나만 오면 됨: customer_id or contact_number
    customer_id: Optional[str] = None
    contact_number: Optional[str] = None

    # ✅ 아래는 “직접 입력 안 해도” 됨(서버가 CSV에서 채움)
    customer_name: Optional[str] = ""
    issue_category: Optional[str] = "해당없음"  # 요금/해지/품질/장애/해당없음
    repeat_contacts_7d: Optional[int] = 0
    billing_issue_flag: Optional[bool] = False
    usage_change_score: Optional[float] = 0.0
    summary_text: Optional[str] = ""

app = FastAPI()

# ─────────────────────────────
# CORS 설정 (프론트엔드에서 API 호출 허용)
# ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────
# 1) 서버 시작 시 CSV 한 번만 로드
# ─────────────────────────────
CSV_PATH = r"12.09_telco_customer_data_final.csv"
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

    # 전화번호로 필터링 (맨 앞 0 제거 + 하이픈 제거 후 비교)
    if phone:
        # 1) 프론트에서 넘어온 값: 하이픈 제거
        phone_clean = phone.replace("-", "")

        # 2) 맨 앞 '0'들 제거 (010... -> 10..., 0010... -> 10...)
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

# ─────────────────────────────
# 8) 관리자용 고객 리스트 (대시보드)
# ─────────────────────────────
@app.get("/admin/customers")
def admin_customers(limit: int = 1500):
    """
    대시보드 테이블용 고객 리스트.
    프론트에서 필요한 컬럼만 추려서 내려줌.
    """
    # limit 개수만 사용 (너무 많으면 테이블 무거워지니까)
    sub = df.head(limit).copy()

    # 필요한 컬럼만 선택 (CSV 컬럼명에 맞게 조정 필요)
    cols = [
        "customerID",
        "customer_name",
        "Churn_Probability",
        "issue_category",
        "repeat_contacts_7d",
        "wait_time_sec",
        "call_duration_sec",
        "Contract",
        "MonthlyCharges",
    ]

    # 혹시 일부 컬럼이 없으면 에러 대신 가능한 것만 내려주고 싶다면:
    existing_cols = [c for c in cols if c in sub.columns]
    sub = sub[existing_cols]

    return {
        "count": int(len(sub)),
        "customers": sub.to_dict(orient="records"),
    }

# ─────────────────────────────
# 9) 관리자용 KPI 통계
# ─────────────────────────────
@app.get("/admin/stats")
def admin_stats():
    """
    대시보드 KPI 카드용 집계.
    """
    total_customers = int(len(df))

    # 이탈 위험 고객: Churn_Probability >= 0.7 기준 (프론트 로직과 맞춤)
    if "Churn_Probability" in df.columns:
        risk_customers = int((df["Churn_Probability"] >= 0.7).sum())
    else:
        risk_customers = 0

    # 평균 대기시간
    if "wait_time_sec" in df.columns:
        avg_wait_time = float(df["wait_time_sec"].mean())
        avg_wait_time = round(avg_wait_time, 1)
    else:
        avg_wait_time = 0.0

    # 반복 문의율: repeat_contacts_7d > 0 인 비율 (%)
    if "repeat_contacts_7d" in df.columns:
        repeat_rate = float((df["repeat_contacts_7d"] > 0).mean() * 100)
        repeat_rate = round(repeat_rate, 1)
    else:
        repeat_rate = 0.0

    return {
        "total_customers": total_customers,
        "risk_customers": risk_customers,
        "avg_wait_time": avg_wait_time,
        "repeat_rate": repeat_rate,
    }
# ─────────────────────────────
# ✅ 헬퍼: 전화번호 정규화
# ─────────────────────────────
def normalize_phone(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"\D", "", s)     # 숫자만
    s = s.lstrip("0")            # 앞 0 제거
    return s

# ─────────────────────────────
# ✅ 헬퍼: contact_number로 고객 찾기 (1명만 반환)
# ─────────────────────────────
def find_customer_by_phone(phone: str) -> dict:
    phone_clean = normalize_phone(phone)
    if not phone_clean:
        raise HTTPException(status_code=400, detail="contact_number가 비어있습니다.")

    tmp = df.copy()
    if "contact_number" not in tmp.columns:
        raise HTTPException(status_code=500, detail="CSV에 contact_number 컬럼이 없습니다.")

    tmp["_phone_norm"] = tmp["contact_number"].astype(str).apply(normalize_phone)

    matched = tmp[tmp["_phone_norm"].str.contains(phone_clean, na=False)]
    if matched.empty:
        raise HTTPException(status_code=404, detail="해당 연락처로 고객을 찾을 수 없습니다.")

    # 여러 명이면 첫 번째로 (원하면 최신/위험도 기준 정렬로 바꿀 수 있음)
    row = matched.iloc[0].drop(labels=["_phone_norm"], errors="ignore")
    return row.to_dict()

# ─────────────────────────────
# ✅ Vector Store 검색 함수
# ─────────────────────────────
def vector_store_search(query: str, k: int = 5) -> str:
    vs_api = getattr(client, "vector_stores", None)
    if vs_api is None:
        vs_api = client.beta.vector_stores

    result = vs_api.search(
        vector_store_id=OPENAI_VECTOR_STORE_ID,
        query=query,
        max_num_results=k,
    )

    texts = []
    for item in getattr(result, "data", []) or []:
        if hasattr(item, "content") and item.content:
            texts.append(str(item.content))
        elif isinstance(item, dict) and "content" in item:
            texts.append(str(item["content"]))
        else:
            texts.append(str(item))

    return "\n\n".join(texts)

# ─────────────────────────────
# ✅ 핵심: 연락처만 보내도 자동 채움 + query 멀티라인 검색
# ─────────────────────────────
@app.post("/churn/rag")
def churn_rag(req: RAGRequest):
    # 1) 고객 찾기: customer_id 우선, 없으면 contact_number로
    cust = None

    if req.customer_id:
        if req.customer_id not in df_indexed.index:
            raise HTTPException(status_code=404, detail="해당 customerID가 없습니다.")
        row = df_indexed.loc[req.customer_id]
        cust = row.to_dict() if isinstance(row, pd.Series) else row.iloc[0].to_dict()
    else:
        if not req.contact_number:
            raise HTTPException(status_code=400, detail="customer_id 또는 contact_number 중 하나는 필요합니다.")
        cust = find_customer_by_phone(req.contact_number)
        req.customer_id = cust.get("customerID") or cust.get("customer_id") or req.customer_id

    # 2) ✅ CSV 값으로 자동 채우기 (프론트가 안 보내도 됨)
    #    프론트 값이 비어있으면 CSV를 우선 사용
    issue_category = (req.issue_category or "").strip()
    if not issue_category or issue_category == "해당없음":
        issue_category = str(cust.get("issue_category") or "해당없음").strip()

    summary_text = (req.summary_text or "").strip()
    if not summary_text:
        summary_text = str(cust.get("summary_text") or "").strip()

    repeat_contacts_7d = req.repeat_contacts_7d
    if repeat_contacts_7d is None or repeat_contacts_7d == 0:
        try:
            repeat_contacts_7d = int(cust.get("repeat_contacts_7d") or 0)
        except:
            repeat_contacts_7d = 0

    billing_issue_flag = req.billing_issue_flag
    if billing_issue_flag is None:
        billing_issue_flag = bool(cust.get("billing_issue_flag") or False)

    usage_change_score = req.usage_change_score
    if usage_change_score is None or usage_change_score == 0.0:
        try:
            usage_change_score = float(cust.get("usage_change_score") or 0.0)
        except:
            usage_change_score = 0.0

    customer_name = (req.customer_name or "").strip()
    if not customer_name:
        customer_name = str(cust.get("customer_name") or "").strip()

    # 3) ✅ 너가 원하는 멀티라인 query로 검색 (자동 구성)
    query = f"""
이슈카테고리: {issue_category}
상담요약: {summary_text}
반복문의: {repeat_contacts_7d}
요금이슈: {billing_issue_flag}
사용량변화: {usage_change_score}
""".strip()

    # 4) Retrieval
    try:
        retrieved_text = vector_store_search(query=query, k=5)
        if not retrieved_text.strip():
            retrieved_text = "(검색 결과 없음)"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector Store 검색 실패: {e}")

    # 5) Generation (LLM)
    system_msg = (
        "당신은 고객센터 상담 지원 AI입니다. "
        "아래 [참고문서] 내용에 근거해 답하세요. "
        "문서에 없는 보상/정책은 추측하지 말고 '확인 필요'라고 말하세요. "
        "항상 한국어 존댓말로 작성하세요. "
        "반드시 JSON만 출력하세요(설명/코드블록 금지)."
    )

    user_msg = f"""
[고객 정보]
- 고객ID: {req.customer_id}
- 고객명: {customer_name}
- 계약유형(Contract): {cust.get("Contract")}
- 가입기간(tenure): {cust.get("tenure")}
- 월요금(MonthlyCharges): {cust.get("MonthlyCharges")}
- 대기시간(wait_time_sec): {cust.get("wait_time_sec")}
- 콜시간(call_duration_sec): {cust.get("call_duration_sec")}

[상담 입력]
- issue_category: {issue_category}
- summary_text: {summary_text}
- repeat_contacts_7d: {repeat_contacts_7d}
- billing_issue_flag: {billing_issue_flag}
- usage_change_score: {usage_change_score}

[참고문서(매뉴얼 검색 결과)]
{retrieved_text}

[출력 JSON 형식(반드시 이 형식만)]
{{
  "main_causes": ["원인1","원인2","원인3"],
  "strategies": ["전략1","전략2","전략3"],
  "recommended_script": "6~10문장 (인사→공감→확인질문→안내→대안/후속→마무리)"
}}
""".strip()

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        text = resp.choices[0].message.content.strip()

        try:
            result = json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not m:
                raise ValueError(f"JSON 파싱 실패. 원문:\n{text}")
            result = json.loads(m.group(0))

        result["meta"] = {
            "customer_id": req.customer_id,
            "customer_name": customer_name,
            "issue_category": issue_category,
            "query_used_for_retrieval": query,  # ✅ 확인용(원하면 제거)
            "vector_store_id": OPENAI_VECTOR_STORE_ID,
        }
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI 생성 실패: {e}")
