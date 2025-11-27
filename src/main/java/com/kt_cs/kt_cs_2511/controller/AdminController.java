package com.kt_cs.kt_cs_2511.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class AdminController {

    @GetMapping("/admin")
    public String adminPage() {
        // => src/main/resources/templates/admin/admin.mustache
        return "admin/admin";
    }
}
