package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.CustomerProfile;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CustomerProfileRepository extends JpaRepository<CustomerProfile, Long> {
    Optional<CustomerProfile> findByUserAccount_Id(Long userAccountId);

    @EntityGraph(attributePaths = "userAccount")
    List<CustomerProfile> findByUserAccount_IdIn(Collection<Long> userAccountIds);

    boolean existsByUserAccount_Id(Long userAccountId);
}
