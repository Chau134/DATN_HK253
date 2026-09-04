package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.admin.AdminCustomerResponse;
import java.util.List;

public interface AdminCustomerService {
    List<AdminCustomerResponse> listCustomers();

    void deleteCustomer(Long customerId);
}
