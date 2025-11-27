package com.kt_cs.kt_cs_2511.service;

import com.kt_cs.kt_cs_2511.config.AdminApiProperties;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Service
@RequiredArgsConstructor
public class AdminService {

    private final RestTemplate restTemplate;
    private final AdminApiProperties adminProperties;

    public Map<String, Object> getAdminSummary() {

        // host 설정 누락 방지
        if (adminProperties.getHost() == null) {
            throw new IllegalStateException("admin.api.host 값이 없습니다! application-local.yml 확인하세요.");
        }

        String url = adminProperties.getHost() + "/summary";
        return restTemplate.getForObject(url, Map.class);
    }
}
