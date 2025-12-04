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

        // 3) 검색 여부
        boolean hasSearched = !searchKeyword.isEmpty();
        boolean hasCustomer = false;

        // ─────────────────────────────
        // 🔹 이탈 위험도 관련 기본값 세팅 (항상 필요)
        //    - 검색 안 했을 때 / 못 찾았을 때도 Mustache가 변수 찾을 수 있게
        // ─────────────────────────────
        double circumference = 2 * Math.PI * 36; // r=36 → 약 226.19
        model.addAttribute("gaugeOffset", circumference); // 0%로 보이게
        model.addAttribute("negProb", 0.0);
        model.addAttribute("negProbPercent", "-");
        model.addAttribute("riskLabel", "-");
        model.addAttribute("riskColor", "green");

        // 4) 검색을 한 경우에만 FastAPI 호출
        if (hasSearched) {
            try {
                Map<String, Object> customerInfo;

                // 숫자 8~12자리면 전화번호로 간주 (예: 01013317181)
                boolean looksLikePhone = searchKeyword.matches("^[0-9]{8,12}$");

                if (looksLikePhone) {
                    // FastAPI: GET /contact/{contact_number}
                    customerInfo = dashService.getCustomerByContact(searchKeyword);
                } else {
                    // FastAPI: GET /customer/{customer_id}
                    customerInfo = dashService.getCustomerById(searchKeyword);
                }

                if (customerInfo != null && !customerInfo.isEmpty()) {
                    hasCustomer = true;

                    // ID 영역에 보여줄 값
                    Object idFromApi = customerInfo.get("customerID");
                    model.addAttribute("customer_id",
                            idFromApi != null ? idFromApi.toString() : searchKeyword);

                    // 전체 고객 정보
                    model.addAttribute("customer", customerInfo);

                    // tenure
                    Object tenure = customerInfo.get("tenure");
                    model.addAttribute("tenure", tenure);

                    // PaymentMethod
                    model.addAttribute("paymentMethod", customerInfo.get("PaymentMethod"));

                    // ─────────────────────────────
                    // 🔥 Churn_Probability 기반 이탈 위험도 계산
                    // ─────────────────────────────
                    Object probObj = customerInfo.get("Churn_Probability");
                    double churnProb = 0.0;
                    if (probObj != null) {
                        try {
                            churnProb = Double.parseDouble(probObj.toString());
                        } catch (NumberFormatException ignored) {}
                    }

                    int probPercent = (int) Math.round(churnProb * 100);

                    String riskLabel;
                    String riskColor;
                    if (churnProb <= 0.50) {
                        riskLabel = "LOW RISK";
                        riskColor = "green";
                    } else if (churnProb <= 0.70) {
                        riskLabel = "MIDDLE RISK";
                        riskColor = "orange";
                    } else {
                        riskLabel = "HIGH RISK";
                        riskColor = "red";
                    }

                    double gaugeOffsetValue = circumference * (1 - churnProb);

                    // 뷰로 전달 (템플릿 변수 이름은 기존 그대로)
                    model.addAttribute("negProb", churnProb);
                    model.addAttribute("negProbPercent", probPercent + "%");
                    model.addAttribute("riskLabel", riskLabel);
                    model.addAttribute("riskColor", riskColor);
                    model.addAttribute("gaugeOffset", gaugeOffsetValue);
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


}
