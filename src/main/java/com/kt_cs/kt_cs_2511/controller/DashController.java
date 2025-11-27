package com.kt_cs.kt_cs_2511.controller;

import com.kt_cs.kt_cs_2511.service.DashService;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.client.HttpClientErrorException;

import java.util.Map;

@Controller
public class DashController {

    private final DashService dashService;

    public DashController(DashService dashService) {
        this.dashService = dashService;
    }

    @GetMapping("/dashboard")
    public String dashboard(
            @RequestParam(value = "customer_id", required = false) String customerId,
            Model model) {

        // 1) FastAPI 요약 데이터 (/summary)
        Map<String, Object> summary = dashService.getDashSummary();
        model.addAttribute("summary", summary);
        model.addAttribute("totalCustomers", summary.get("total_customers"));
        model.addAttribute("churnRate", summary.get("churn_rate"));

        // 2) 검색창에 그대로 남겨줄 값
        String searchKeyword = (customerId == null) ? "" : customerId.trim();
        model.addAttribute("searchKeyword", searchKeyword);

        // 3) 검색을 했는지?
        boolean hasSearched = !searchKeyword.isEmpty();
        boolean hasCustomer = false;

        // 4) FastAPI 에서 /customer/{id} 조회
        if (hasSearched) {
            try {
                // FastAPI: GET http://127.0.0.1:8000/customer/{customer_id}
                Map<String, Object> customerInfo = dashService.getCustomerById(searchKeyword);

                if (customerInfo != null && !customerInfo.isEmpty()) {
                    hasCustomer = true;

                    // ID 영역에 보여줄 값
                    Object idFromApi = customerInfo.get("customerID");
                    model.addAttribute("customer_id",
                            idFromApi != null ? idFromApi.toString() : searchKeyword);

                    // 전체 고객 정보
                    model.addAttribute("customer", customerInfo);

                    // tenure
                    Object tenure = customerInfo.get("tenure");   // CSV에 컬럼명이 tenure 라고 가정
                    model.addAttribute("tenure", tenure);

                    // PaymentMethod
                    model.addAttribute("paymentMethod", customerInfo.get("PaymentMethod"));

                    // =========================
                    // 🔥 neg_prob 기반 이탈 위험도 추가 -> 변수 변경예정
                    // =========================
                    Object npObj = customerInfo.get("neg_prob");  // CSV 컬럼명 neg_prob
                    double negProb = 0.0;
                    if (npObj != null) {
                        try {
                            negProb = Double.parseDouble(npObj.toString());
                        } catch (NumberFormatException ignored) {}
                    }

                    // 0~1 -> 0~100%
                    int negProbPercent = (int) Math.round(negProb * 100);

                    // 위험 레벨 / 색상 결정
                    String riskLabel;
                    String riskColor;   // green / orange / red

                    if (negProb <= 0.50) {
                        riskLabel = "LOW RISK";
                        riskColor = "green";
                    } else if (negProb <= 0.70) {
                        riskLabel = "MIDDLE RISK";
                        riskColor = "orange";
                    } else {
                        riskLabel = "HIGH RISK";
                        riskColor = "red";
                    }

                    // 게이지 stroke-dashoffset 계산
                    double circumference = 2 * Math.PI * 36;  // r=36 이니까 약 226.19
                    double gaugeOffset = circumference * (1 - negProb);

                    // 뷰로 전달
                    model.addAttribute("negProb", negProb);                      // 필요하면 원래 값
                    model.addAttribute("negProbPercent", negProbPercent + "%");  // "92%"
                    model.addAttribute("riskLabel", riskLabel);                  // HIGH RISK 등
                    model.addAttribute("riskColor", riskColor);                  // green/orange/red
                    model.addAttribute("gaugeOffset", gaugeOffset);              // 게이지용
                    // =========================

                }
            } catch (HttpClientErrorException e) {
                if (e.getStatusCode() == HttpStatus.NOT_FOUND) {
                    hasCustomer = false;
                } else {
                    throw e;
                }
            } catch (Exception e) {
                hasCustomer = false;
                e.printStackTrace();
            }
        }


        model.addAttribute("hasSearched", hasSearched);
        model.addAttribute("hasCustomer", hasCustomer);

        // templates/main/dashboard.mustache
        return "main/dashboard";
    }

    @GetMapping("/")
    public String root() {
        return "redirect:/dashboard";
    }
}
