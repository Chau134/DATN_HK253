package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.account.AccountProfileResponse;
import com.example.serviceapiecommerce.dto.account.AccountProfileUpdateRequest;
import com.example.serviceapiecommerce.dto.account.CustomerAddressRequest;
import com.example.serviceapiecommerce.dto.account.CustomerAddressResponse;
import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.CustomerAddressType;
import com.example.serviceapiecommerce.entity.CustomerProfile;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.repository.CustomerAddressRepository;
import com.example.serviceapiecommerce.repository.CustomerProfileRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.AccountProfileService;
import com.example.serviceapiecommerce.service.CloudinaryAvatarUploadService;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.multipart.MultipartFile;

@Service
public class AccountProfileServiceImpl implements AccountProfileService {
    private static final Logger log = LoggerFactory.getLogger(AccountProfileServiceImpl.class);

    private final UserAccountRepository userAccountRepository;
    private final CustomerProfileRepository customerProfileRepository;
    private final CustomerAddressRepository customerAddressRepository;
    private final CloudinaryAvatarUploadService cloudinaryAvatarUploadService;

    public AccountProfileServiceImpl(
            UserAccountRepository userAccountRepository,
            CustomerProfileRepository customerProfileRepository,
            CustomerAddressRepository customerAddressRepository,
            CloudinaryAvatarUploadService cloudinaryAvatarUploadService
    ) {
        this.userAccountRepository = userAccountRepository;
        this.customerProfileRepository = customerProfileRepository;
        this.customerAddressRepository = customerAddressRepository;
        this.cloudinaryAvatarUploadService = cloudinaryAvatarUploadService;
    }

    @Override
    @Transactional(readOnly = true)
    public AccountProfileResponse getProfile(Long userAccountId) {
        UserAccount account = userAccount(userAccountId);
        CustomerProfile profile = customerProfileRepository.findByUserAccount_Id(userAccountId).orElse(null);
        return AccountProfileResponse.from(account, profile);
    }

    @Override
    @Transactional
    public AccountProfileResponse uploadAvatar(Long userAccountId, MultipartFile file) {
        UserAccount account = userAccount(userAccountId);
        Instant now = Instant.now();
        String avatarUrl = cloudinaryAvatarUploadService.uploadAvatar(userAccountId, file);

        CustomerProfile profile = profileForUpdate(account, now);
        profile.setAvatarUrl(avatarUrl);
        profile.setUpdatedAt(now);
        customerProfileRepository.saveAndFlush(profile);
        log.info("account_avatar_updated user_id={} avatar_url={}", userAccountId, avatarUrl);

        return AccountProfileResponse.from(account, profile);
    }

    @Override
    @Transactional
    public AccountProfileResponse deleteAvatar(Long userAccountId) {
        UserAccount account = userAccount(userAccountId);
        Instant now = Instant.now();
        CustomerProfile profile = profileForUpdate(account, now);
        profile.setAvatarUrl(null);
        profile.setUpdatedAt(now);
        customerProfileRepository.saveAndFlush(profile);
        log.info("account_avatar_deleted user_id={}", userAccountId);

        return AccountProfileResponse.from(account, profile);
    }

    @Override
    @Transactional
    public AccountProfileResponse updateProfile(Long userAccountId, AccountProfileUpdateRequest request) {
        UserAccount account = userAccount(userAccountId);
        Instant now = Instant.now();

        String email = normalizeEmail(request.email());
        if (email != null && !email.equalsIgnoreCase(account.getEmail())) {
            userAccountRepository.findByEmailIgnoreCase(email)
                    .filter(existing -> !existing.getId().equals(userAccountId))
                    .ifPresent(existing -> {
                        throw new ResponseStatusException(HttpStatus.CONFLICT, "email_already_registered");
                    });
            account.setEmail(email);
        }

        String phoneNumber = blankToNull(request.phoneNumber());
        if (phoneNumber != null && !phoneNumber.equals(account.getPhoneNumber())) {
            userAccountRepository.findByPhoneNumber(phoneNumber)
                    .filter(existing -> !existing.getId().equals(userAccountId))
                    .ifPresent(existing -> {
                        throw new ResponseStatusException(HttpStatus.CONFLICT, "phone_number_already_registered");
                    });
        }

        account.setPhoneNumber(phoneNumber);
        account.setFullName(blankToNull(request.fullName()));
        account.setDisplayName(blankToNull(request.displayName()));
        account.setUpdatedAt(now);
        userAccountRepository.save(account);

        CustomerProfile profile = profileForUpdate(account, now);
        profile.setFirstName(blankToNull(request.firstName()));
        profile.setLastName(blankToNull(request.lastName()));
        profile.setGender(blankToNull(request.gender()));
        profile.setDateOfBirth(request.dateOfBirth());
        profile.setMarketingOptIn(Boolean.TRUE.equals(request.marketingOptIn()));
        profile.setUpdatedAt(now);
        customerProfileRepository.save(profile);

        return AccountProfileResponse.from(account, profile);
    }

    @Override
    @Transactional(readOnly = true)
    public List<CustomerAddressResponse> listAddresses(Long userAccountId) {
        return customerAddressRepository
                .findByUserAccount_IdAndDeletedFalseOrderByDefaultAddressDescUpdatedAtDescIdDesc(userAccountId)
                .stream()
                .map(CustomerAddressResponse::from)
                .toList();
    }

    @Override
    @Transactional
    public CustomerAddressResponse createAddress(Long userAccountId, CustomerAddressRequest request) {
        Instant now = Instant.now();
        CustomerAddress address = new CustomerAddress();
        address.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
        applyAddress(address, request, now);
        address.setDeleted(false);
        address.setCreatedAt(now);

        if (Boolean.TRUE.equals(address.getDefaultAddress())) {
            clearDefaultAddresses(userAccountId, null, now);
        }

        return CustomerAddressResponse.from(customerAddressRepository.save(address));
    }

    @Override
    @Transactional
    public CustomerAddressResponse updateAddress(Long userAccountId, Long addressId, CustomerAddressRequest request) {
        CustomerAddress address = ownedAddress(userAccountId, addressId);
        Instant now = Instant.now();
        applyAddress(address, request, now);

        if (Boolean.TRUE.equals(address.getDefaultAddress())) {
            clearDefaultAddresses(userAccountId, addressId, now);
        }

        return CustomerAddressResponse.from(customerAddressRepository.save(address));
    }

    @Override
    @Transactional
    public void deleteAddress(Long userAccountId, Long addressId) {
        CustomerAddress address = ownedAddress(userAccountId, addressId);
        address.setDeleted(true);
        address.setDefaultAddress(false);
        address.setUpdatedAt(Instant.now());
        customerAddressRepository.save(address);
    }

    private void applyAddress(CustomerAddress address, CustomerAddressRequest request, Instant now) {
        address.setAddressType(request.addressType() == null ? CustomerAddressType.SHIPPING : request.addressType());
        address.setRecipientName(trim(request.recipientName()));
        address.setPhoneNumber(trim(request.phoneNumber()));
        address.setAddressLine1(trim(request.addressLine1()));
        address.setAddressLine2(blankToNull(request.addressLine2()));
        address.setWard(blankToNull(request.ward()));
        address.setDistrict(blankToNull(request.district()));
        address.setCity(blankToNull(request.city()));
        address.setProvince(blankToNull(request.province()));
        address.setCountryCode(blankToDefault(request.countryCode(), "VN").toUpperCase(Locale.ROOT));
        address.setPostalCode(blankToNull(request.postalCode()));
        address.setDefaultAddress(Boolean.TRUE.equals(request.defaultAddress()));
        address.setUpdatedAt(now);
    }

    private void clearDefaultAddresses(Long userAccountId, Long exceptAddressId, Instant now) {
        List<CustomerAddress> addresses = customerAddressRepository
                .findByUserAccount_IdAndDeletedFalseOrderByDefaultAddressDescUpdatedAtDescIdDesc(userAccountId);
        for (CustomerAddress address : addresses) {
            if (exceptAddressId != null && exceptAddressId.equals(address.getId())) {
                continue;
            }
            if (Boolean.TRUE.equals(address.getDefaultAddress())) {
                address.setDefaultAddress(false);
                address.setUpdatedAt(now);
            }
        }
        customerAddressRepository.saveAll(addresses);
    }

    private UserAccount userAccount(Long userAccountId) {
        return userAccountRepository.findByIdWithRoles(userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "user_not_found"));
    }

    private CustomerProfile profileForUpdate(UserAccount account, Instant now) {
        return customerProfileRepository.findByUserAccount_Id(account.getId())
                .orElseGet(() -> {
                    CustomerProfile profile = new CustomerProfile();
                    profile.setUserAccount(account);
                    profile.setLoyaltyPoints(0);
                    profile.setMarketingOptIn(false);
                    profile.setCreatedAt(now);
                    return profile;
                });
    }

    private CustomerAddress ownedAddress(Long userAccountId, Long addressId) {
        return customerAddressRepository.findByIdAndUserAccount_IdAndDeletedFalse(addressId, userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "customer_address_not_found"));
    }

    private static String normalizeEmail(String email) {
        return email == null ? null : blankToNull(email.toLowerCase(Locale.ROOT));
    }

    private static String blankToDefault(String value, String fallback) {
        String trimmed = blankToNull(value);
        return trimmed == null ? fallback : trimmed;
    }

    private static String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private static String trim(String value) {
        return value == null ? null : value.trim();
    }
}
