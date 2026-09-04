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
        name = "customer_addresses",
        indexes = {
                @Index(name = "idx_customer_addresses_user_account_id", columnList = "user_account_id"),
                @Index(name = "idx_customer_addresses_default", columnList = "user_account_id,is_default,deleted")
        }
)
public class CustomerAddress {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "user_account_id", nullable = false)
    private UserAccount userAccount;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'SHIPPING'")
    @Column(name = "address_type", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private CustomerAddressType addressType;

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

    @ColumnDefault("0")
    @Column(name = "is_default")
    private Boolean defaultAddress;

    @ColumnDefault("0")
    @Column(name = "deleted")
    private Boolean deleted;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;
}
