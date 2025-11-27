package com.kt_cs.kt_cs_2511.controller;

import com.kt_cs.kt_cs_2511.service.AdminService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
@RequiredArgsConstructor
public class AdminController {

    private final AdminService adminService;

    @GetMapping("/admin")
    public String admin(Model model) {
        model.addAttribute("adminSummary", adminService.getAdminSummary());
        return "admin/admin";   // templates/admin/admin.mustache
    }
}
