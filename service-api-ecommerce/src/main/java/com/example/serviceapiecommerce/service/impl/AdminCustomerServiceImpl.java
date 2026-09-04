package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.admin.AdminCustomerResponse;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserAccountStatus;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.AdminCustomerService;
import java.time.Instant;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AdminCustomerServiceImpl implements AdminCustomerService {
    private static final String ROLE_CUSTOMER = "CUSTOMER";

    private final UserAccountRepository userAccountRepository;

    public AdminCustomerServiceImpl(UserAccountRepository userAccountRepository) {
        this.userAccountRepository = userAccountRepository;
    }

    @Override
    @Transactional(readOnly = true)
    public List<AdminCustomerResponse> listCustomers() {
        return userAccountRepository.findActiveCustomersWithRoles(ROLE_CUSTOMER, UserAccountStatus.ACTIVE)
                .stream()
                .map(AdminCustomerResponse::from)
                .toList();
    }

    @Override
    @Transactional
    public void deleteCustomer(Long customerId) {
        UserAccount account = userAccountRepository.findByIdWithRoles(customerId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "customer_not_found"));
        boolean isCustomer = account.getRoles().stream().anyMatch(role -> ROLE_CUSTOMER.equals(role.getName()));
        if (!isCustomer) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "customer_not_found");
        }

        account.setStatus(UserAccountStatus.DISABLED);
        account.setUpdatedAt(Instant.now());
        userAccountRepository.save(account);
    }
}
