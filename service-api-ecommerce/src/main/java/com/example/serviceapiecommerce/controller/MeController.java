package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.account.AccountProfileResponse;
import com.example.serviceapiecommerce.dto.account.AccountProfileUpdateRequest;
import com.example.serviceapiecommerce.dto.account.CustomerAddressRequest;
import com.example.serviceapiecommerce.dto.account.CustomerAddressResponse;
import com.example.serviceapiecommerce.dto.auth.AuthUserResponse;
import com.example.serviceapiecommerce.dto.auth.ChangePasswordRequest;
import com.example.serviceapiecommerce.dto.auth.PasswordResetConfirmRequest;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.AccountProfileService;
import com.example.serviceapiecommerce.service.AuthService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/me")
public class MeController {
    private final AuthService authService;
    private final AccountProfileService accountProfileService;

    public MeController(AuthService authService, AccountProfileService accountProfileService) {
        this.authService = authService;
        this.accountProfileService = accountProfileService;
    }

    @GetMapping
    public AuthUserResponse me(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return authService.currentUser(currentUser.id());
    }

    @PostMapping("/change-password")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void changePassword(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody ChangePasswordRequest request
    ) {
        authService.changePassword(currentUser.id(), request);
    }

    @PostMapping("/create-password")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void createPassword(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody PasswordResetConfirmRequest request
    ) {
        authService.createPassword(currentUser.id(), request);
    }

    @GetMapping("/profile")
    public AccountProfileResponse profile(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return accountProfileService.getProfile(currentUser.id());
    }

    @PatchMapping("/profile")
    public AccountProfileResponse updateProfile(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody AccountProfileUpdateRequest request
    ) {
        return accountProfileService.updateProfile(currentUser.id(), request);
    }

    @PostMapping(value = "/avatar", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public AccountProfileResponse uploadAvatar(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @RequestPart("file") MultipartFile file
    ) {
        return accountProfileService.uploadAvatar(currentUser.id(), file);
    }

    @DeleteMapping("/avatar")
    public AccountProfileResponse deleteAvatar(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return accountProfileService.deleteAvatar(currentUser.id());
    }

    @GetMapping("/addresses")
    public List<CustomerAddressResponse> addresses(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return accountProfileService.listAddresses(currentUser.id());
    }

    @PostMapping("/addresses")
    @ResponseStatus(HttpStatus.CREATED)
    public CustomerAddressResponse createAddress(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody CustomerAddressRequest request
    ) {
        return accountProfileService.createAddress(currentUser.id(), request);
    }

    @PatchMapping("/addresses/{addressId}")
    public CustomerAddressResponse updateAddress(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long addressId,
            @Valid @RequestBody CustomerAddressRequest request
    ) {
        return accountProfileService.updateAddress(currentUser.id(), addressId, request);
    }

    @DeleteMapping("/addresses/{addressId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteAddress(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long addressId
    ) {
        accountProfileService.deleteAddress(currentUser.id(), addressId);
    }
}
