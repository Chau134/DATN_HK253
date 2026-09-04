package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.OrderAddress;
import com.example.serviceapiecommerce.entity.OrderAddressType;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderAddressRepository extends JpaRepository<OrderAddress, Long> {
    List<OrderAddress> findByOrder_IdOrderByAddressTypeAscIdAsc(Long orderId);

    Optional<OrderAddress> findFirstByOrder_IdAndAddressType(Long orderId, OrderAddressType addressType);
}
