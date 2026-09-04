package com.example.serviceapiecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

@Getter
@Setter
@Entity
@Table(
        name = "order_addresses",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_order_addresses_order_type",
                columnNames = {"order_id", "address_type"}
        ),
        indexes = {
                @Index(name = "idx_order_addresses_order_id", columnList = "order_id"),
                @Index(name = "idx_order_addresses_source_address_id", columnList = "source_customer_address_id")
        }
)
public class OrderAddress {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "source_customer_address_id")
    private CustomerAddress sourceCustomerAddress;

    @Enumerated(EnumType.STRING)
    @Column(name = "address_type", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private OrderAddressType addressType;

    @Column(name = "recipient_name", nullable = false, length = 150)
    private String recipientName;

    @Column(name = "phone_number", nullable = false, length = 30)
    private String phoneNumber;

    @Column(name = "address_line1", nullable = false)
    private String addressLine1;

    @Column(name = "address_line2")
    private String addressLine2;

    @Column(name = "ward", length = 150)
    private String ward;

    @Column(name = "district", length = 150)
    private String district;

    @Column(name = "city", length = 150)
    private String city;

    @Column(name = "province", length = 150)
    private String province;

    @ColumnDefault("'VN'")
    @Column(name = "country_code", nullable = false, length = 2)
    private String countryCode;

    @Column(name = "postal_code", length = 20)
    private String postalCode;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;
}
