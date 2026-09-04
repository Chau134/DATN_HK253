package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.account.AccountProfileResponse;
import com.example.serviceapiecommerce.dto.account.AccountProfileUpdateRequest;
import com.example.serviceapiecommerce.dto.account.CustomerAddressRequest;
import com.example.serviceapiecommerce.dto.account.CustomerAddressResponse;
import java.util.List;
import org.springframework.web.multipart.MultipartFile;

public interface AccountProfileService {
    AccountProfileResponse getProfile(Long userAccountId);

    AccountProfileResponse updateProfile(Long userAccountId, AccountProfileUpdateRequest request);

    AccountProfileResponse uploadAvatar(Long userAccountId, MultipartFile file);

    AccountProfileResponse deleteAvatar(Long userAccountId);

    List<CustomerAddressResponse> listAddresses(Long userAccountId);

    CustomerAddressResponse createAddress(Long userAccountId, CustomerAddressRequest request);

    CustomerAddressResponse updateAddress(Long userAccountId, Long addressId, CustomerAddressRequest request);

    void deleteAddress(Long userAccountId, Long addressId);
}
