package com.kt_cs.kt_cs_2511.service;

import com.kt_cs.kt_cs_2511.config.DashApiProperties;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
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

    /** FastAPI → /summary */
    public Map<String, Object> getDashSummary() {
        String url = dashApiProperties.getHost() + "/summary";
        return restTemplate.getForObject(url, Map.class);
    }

    /** ★ FastAPI → /customer/{customer_id} */
    public Map<String, Object> getCustomerById(String customerId) {
        String url = dashApiProperties.getHost() + "/customer/" + customerId;

        try {
            return restTemplate.getForObject(url, Map.class);
        } catch (HttpClientErrorException e) {
            // FastAPI가 404를 던지면 그대로 던져서 Controller가 처리함
            if (e.getStatusCode() == HttpStatus.NOT_FOUND) {
                throw e;
            }
            // 그 외 오류도 다시 던짐
            throw e;
        }
    }
}
