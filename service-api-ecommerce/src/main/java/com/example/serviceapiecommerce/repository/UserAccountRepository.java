package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserAccountStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface UserAccountRepository extends JpaRepository<UserAccount, Long> {
    Optional<UserAccount> findByEmailIgnoreCase(String email);

    boolean existsByEmailIgnoreCase(String email);

    Optional<UserAccount> findByPhoneNumber(String phoneNumber);

    boolean existsByPhoneNumber(String phoneNumber);

    List<UserAccount> findByStatusOrderByCreatedAtDesc(UserAccountStatus status);

    @Query("""
            select distinct account
            from UserAccount account
            left join fetch account.roles roles
            where account.id = :userAccountId
            """)
    Optional<UserAccount> findByIdWithRoles(@Param("userAccountId") Long userAccountId);

    @Query("""
            select distinct account
            from UserAccount account
            left join fetch account.roles roles
            where lower(account.email) = lower(:email)
            """)
    Optional<UserAccount> findByEmailWithRoles(@Param("email") String email);

    @Query("""
            select distinct account
            from UserAccount account
            join account.roles role
            left join fetch account.roles roles
            where role.name = :roleName
              and account.status = :status
            order by account.createdAt desc
            """)
    List<UserAccount> findActiveCustomersWithRoles(
            @Param("roleName") String roleName,
            @Param("status") UserAccountStatus status
    );
}
