package com.kt_cs.kt_cs_2511.service;

import com.kt_cs.kt_cs_2511.config.DashApiProperties;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Service
public class DashService {

    private final DashApiProperties dashApiProperties;
    private final RestTemplate restTemplate;

    public DashService(DashApiProperties dashApiProperties,
                       RestTemplate restTemplate) {
        this.dashApiProperties = dashApiProperties;
        this.restTemplate = restTemplate;
    }

    public Map<String, Object> getDashSummary() {
        String url = dashApiProperties.getHost() + "/summary"; // 예: http://127.0.0.1:8000/summary
        // FastAPI가 JSON을 반환한다고 가정
        return restTemplate.getForObject(url, Map.class);
    }
}
