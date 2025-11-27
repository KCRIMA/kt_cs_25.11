package com.kt_cs.kt_cs_2511.controller;

import com.kt_cs.kt_cs_2511.service.DashService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.Map;

@Controller
public class DashController {

    private final DashService dashService;

    public DashController(DashService dashService) {
        this.dashService = dashService;
    }

    @GetMapping("/dashboard")
    public String dashboard(Model model) {
        // 1) FastAPI 호출해서 데이터 가져오기
        Map<String, Object> summary = dashService.getDashSummary();

        // 2) Mustache에 넘길 attribute 세팅
        model.addAttribute("summary", summary);
        // 예시로 개별값도 뽑아서 쓰고 싶으면:
        model.addAttribute("totalCustomers", summary.get("total_customers"));
        model.addAttribute("churnRate", summary.get("churn_rate"));

        // 3) templates/main/admin.mustache 를 렌더링
        return "main/dashboard";
    }

    @GetMapping("/")
    public String root() {
        // 루트로 들어오면 /dashboard로 리다이렉트
        return "redirect:/dashboard";
    }

}
