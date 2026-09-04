package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.CustomerAddressType;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CustomerAddressRepository extends JpaRepository<CustomerAddress, Long> {
    List<CustomerAddress> findByUserAccount_IdAndDeletedFalseOrderByDefaultAddressDescUpdatedAtDescIdDesc(
            Long userAccountId
    );

    List<CustomerAddress> findByUserAccount_IdAndAddressTypeAndDeletedFalseOrderByDefaultAddressDescUpdatedAtDescIdDesc(
            Long userAccountId,
            CustomerAddressType addressType
    );

    Optional<CustomerAddress> findByIdAndUserAccount_IdAndDeletedFalse(Long id, Long userAccountId);

    Optional<CustomerAddress> findFirstByUserAccount_IdAndDefaultAddressTrueAndDeletedFalseOrderByUpdatedAtDescIdDesc(
            Long userAccountId
    );
}
