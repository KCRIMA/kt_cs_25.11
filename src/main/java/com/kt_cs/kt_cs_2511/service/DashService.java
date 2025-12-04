package com.kt_cs.kt_cs_2511.service;

import com.kt_cs.kt_cs_2511.config.DashApiProperties;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.List;
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

    /** FastAPI → /customer/{customer_id} (기존 기능) */
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

    /** ★★ FastAPI → /contact/{contact_number} (추가된 기능: 전화번호로 조회) */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getCustomerByContact(String contactNumber) {
        String url = dashApiProperties.getHost() + "/contact/" + contactNumber;

        try {
            // FastAPI /contact 는 [ { ... }, { ... } ] 형태의 리스트를 반환하도록 만들었으므로
            List<Map<String, Object>> list =
                    restTemplate.getForObject(url, List.class);

            if (list == null || list.isEmpty()) {
                return null;   // 컨트롤러에서 hasCustomer=false 처리
            }
            return list.get(0); // 첫 번째 결과만 사용

        } catch (HttpClientErrorException e) {
            if (e.getStatusCode() == HttpStatus.NOT_FOUND) {
                // 전화번호로 조회된 고객이 없는 경우 → null 반환
                return null;
            }
            throw e;
        }
    }
}
