package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.admin.AdminCustomerResponse;
import com.example.serviceapiecommerce.service.AdminCustomerService;
import java.util.List;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/customers")
public class AdminCustomerController {
    private final AdminCustomerService adminCustomerService;

    public AdminCustomerController(AdminCustomerService adminCustomerService) {
        this.adminCustomerService = adminCustomerService;
    }

    @GetMapping
    public List<AdminCustomerResponse> customers() {
        return adminCustomerService.listCustomers();
    }

    @DeleteMapping("/{customerId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteCustomer(@PathVariable Long customerId) {
        adminCustomerService.deleteCustomer(customerId);
    }
}
