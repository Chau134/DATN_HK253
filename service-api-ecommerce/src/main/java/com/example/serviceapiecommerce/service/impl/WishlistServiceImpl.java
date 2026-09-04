package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.wishlist.WishlistCreateRequest;
import com.example.serviceapiecommerce.dto.wishlist.WishlistItemRequest;
import com.example.serviceapiecommerce.dto.wishlist.WishlistItemResponse;
import com.example.serviceapiecommerce.dto.wishlist.WishlistResponse;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.entity.Wishlist;
import com.example.serviceapiecommerce.entity.WishlistItem;
import com.example.serviceapiecommerce.entity.WishlistStatus;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.repository.WishlistItemRepository;
import com.example.serviceapiecommerce.repository.WishlistRepository;
import com.example.serviceapiecommerce.service.WishlistService;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class WishlistServiceImpl implements WishlistService {
    private static final String DEFAULT_WISHLIST_NAME = "Default";

    private final WishlistRepository wishlistRepository;
    private final WishlistItemRepository wishlistItemRepository;
    private final ProductRepository productRepository;
    private final ProductVariantRepository productVariantRepository;
    private final UserAccountRepository userAccountRepository;

    public WishlistServiceImpl(
            WishlistRepository wishlistRepository,
            WishlistItemRepository wishlistItemRepository,
            ProductRepository productRepository,
            ProductVariantRepository productVariantRepository,
            UserAccountRepository userAccountRepository
    ) {
        this.wishlistRepository = wishlistRepository;
        this.wishlistItemRepository = wishlistItemRepository;
        this.productRepository = productRepository;
        this.productVariantRepository = productVariantRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @Override
    @Transactional(readOnly = true)
    public List<WishlistResponse> listWishlists(Long userAccountId) {
        List<Wishlist> wishlists = wishlistRepository
                .findByUserAccount_IdAndStatusOrderByUpdatedAtDescIdDesc(userAccountId, WishlistStatus.ACTIVE);
        if (wishlists.isEmpty()) {
            return List.of();
        }
        Map<Long, List<WishlistItem>> itemsByWishlistId = new LinkedHashMap<>();
        List<Long> wishlistIds = wishlists.stream().map(Wishlist::getId).toList();
        for (WishlistItem item : wishlistItemRepository.findByWishlist_IdInOrderByCreatedAtDescIdDesc(wishlistIds)) {
            itemsByWishlistId.computeIfAbsent(item.getWishlist().getId(), ignored -> new ArrayList<>()).add(item);
        }
        return wishlists.stream()
                .map(wishlist -> toResponse(wishlist, itemsByWishlistId.getOrDefault(wishlist.getId(), List.of())))
                .toList();
    }

    @Override
    @Transactional
    public WishlistResponse getDefaultWishlist(Long userAccountId) {
        return toResponse(ensureDefaultWishlist(userAccountId));
    }

    @Override
    @Transactional
    public WishlistResponse createWishlist(Long userAccountId, WishlistCreateRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "wishlist_request_required");
        }
        String name = blankToNull(request.name());
        if (name == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "wishlist_name_required");
        }
        if (DEFAULT_WISHLIST_NAME.equalsIgnoreCase(name)) {
            return getDefaultWishlist(userAccountId);
        }
        if (wishlistRepository.existsByUserAccount_IdAndName(userAccountId, name)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "wishlist_name_exists");
        }

        Instant now = Instant.now();
        Wishlist wishlist = new Wishlist();
        wishlist.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
        wishlist.setName(name);
        wishlist.setDefaultWishlist(false);
        wishlist.setStatus(WishlistStatus.ACTIVE);
        wishlist.setCreatedAt(now);
        wishlist.setUpdatedAt(now);
        return toResponse(wishlistRepository.save(wishlist));
    }

    @Override
    @Transactional
    public WishlistResponse addItemToDefaultWishlist(Long userAccountId, WishlistItemRequest request) {
        return addItemToWishlist(ensureDefaultWishlist(userAccountId), request);
    }

    @Override
    @Transactional
    public WishlistResponse addItem(Long userAccountId, Long wishlistId, WishlistItemRequest request) {
        return addItemToWishlist(wishlist(userAccountId, wishlistId), request);
    }

    @Override
    @Transactional
    public WishlistResponse removeItem(Long userAccountId, Long wishlistItemId) {
        if (wishlistItemId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "wishlist_item_id_required");
        }
        WishlistItem item = wishlistItemRepository.findByIdAndWishlist_UserAccount_Id(wishlistItemId, userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "wishlist_item_not_found"));
        Wishlist wishlist = item.getWishlist();
        wishlistItemRepository.delete(item);
        wishlist.setUpdatedAt(Instant.now());
        wishlistRepository.save(wishlist);
        return toResponse(wishlist);
    }

    @Override
    @Transactional
    public WishlistResponse removeProductFromDefaultWishlist(Long userAccountId, Long productId) {
        return removeProductFromWishlist(ensureDefaultWishlist(userAccountId), productId);
    }

    @Override
    @Transactional
    public WishlistResponse removeProduct(Long userAccountId, Long wishlistId, Long productId) {
        return removeProductFromWishlist(wishlist(userAccountId, wishlistId), productId);
    }

    private WishlistResponse addItemToWishlist(Wishlist wishlist, WishlistItemRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "wishlist_item_request_required");
        }
        Product product = product(request.productId());
        ProductVariant variant = productVariant(request.productVariantId(), product.getId());
        Instant now = Instant.now();

        WishlistItem item = wishlistItemRepository.findByWishlist_IdAndProduct_Id(wishlist.getId(), product.getId())
                .orElseGet(() -> {
                    WishlistItem newItem = new WishlistItem();
                    newItem.setWishlist(wishlist);
                    newItem.setProduct(product);
                    newItem.setCreatedAt(now);
                    return newItem;
                });
        item.setProductVariant(variant);
        item.setNote(blankToNull(request.note()));
        item.setUpdatedAt(now);
        wishlistItemRepository.save(item);

        wishlist.setUpdatedAt(now);
        wishlistRepository.save(wishlist);
        return toResponse(wishlist);
    }

    private WishlistResponse removeProductFromWishlist(Wishlist wishlist, Long productId) {
        if (productId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_id_required");
        }
        wishlistItemRepository.findByWishlist_IdAndProduct_Id(wishlist.getId(), productId)
                .ifPresent(wishlistItemRepository::delete);
        wishlist.setUpdatedAt(Instant.now());
        wishlistRepository.save(wishlist);
        return toResponse(wishlist);
    }

    private Wishlist ensureDefaultWishlist(Long userAccountId) {
        Instant now = Instant.now();
        return wishlistRepository.findByUserAccount_IdAndName(userAccountId, DEFAULT_WISHLIST_NAME)
                .map(wishlist -> {
                    if (wishlist.getStatus() != WishlistStatus.ACTIVE || !Boolean.TRUE.equals(wishlist.getDefaultWishlist())) {
                        wishlist.setStatus(WishlistStatus.ACTIVE);
                        wishlist.setDefaultWishlist(true);
                        wishlist.setUpdatedAt(now);
                        return wishlistRepository.save(wishlist);
                    }
                    return wishlist;
                })
                .orElseGet(() -> {
                    Wishlist wishlist = new Wishlist();
                    wishlist.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
                    wishlist.setName(DEFAULT_WISHLIST_NAME);
                    wishlist.setDefaultWishlist(true);
                    wishlist.setStatus(WishlistStatus.ACTIVE);
                    wishlist.setCreatedAt(now);
                    wishlist.setUpdatedAt(now);
                    return wishlistRepository.save(wishlist);
                });
    }

    private Wishlist wishlist(Long userAccountId, Long wishlistId) {
        if (wishlistId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "wishlist_id_required");
        }
        return wishlistRepository.findByIdAndUserAccount_Id(wishlistId, userAccountId)
                .filter(wishlist -> wishlist.getStatus() == WishlistStatus.ACTIVE)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "wishlist_not_found"));
    }

    private Product product(Long productId) {
        if (productId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_id_required");
        }
        return productRepository.findById(productId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_not_found"));
    }

    private ProductVariant productVariant(Long productVariantId, Long productId) {
        if (productVariantId == null) {
            return null;
        }
        ProductVariant variant = productVariantRepository.findByIdWithProduct(productVariantId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_variant_not_found"));
        if (!variant.getProduct().getId().equals(productId)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "product_variant_mismatch");
        }
        return variant;
    }

    private WishlistResponse toResponse(Wishlist wishlist) {
        return toResponse(
                wishlist,
                wishlistItemRepository.findByWishlist_IdOrderByCreatedAtDescIdDesc(wishlist.getId())
        );
    }

    private WishlistResponse toResponse(Wishlist wishlist, List<WishlistItem> wishlistItems) {
        List<WishlistItemResponse> items = wishlistItems
                .stream()
                .map(WishlistServiceImpl::toItemResponse)
                .toList();
        return new WishlistResponse(
                wishlist.getId(),
                wishlist.getName(),
                wishlist.getDefaultWishlist(),
                wishlist.getStatus(),
                items.size(),
                items,
                wishlist.getCreatedAt(),
                wishlist.getUpdatedAt()
        );
    }

    private static WishlistItemResponse toItemResponse(WishlistItem item) {
        Product product = item.getProduct();
        return new WishlistItemResponse(
                item.getId(),
                product == null ? null : product.getId(),
                item.getProductVariant() == null ? null : item.getProductVariant().getId(),
                product == null ? null : product.getProductDisplayName(),
                product == null ? null : product.getProductDisplayNameVi(),
                product == null ? null : product.getBrandName(),
                product == null ? null : product.getMainImage(),
                item.getNote(),
                item.getCreatedAt(),
                item.getUpdatedAt()
        );
    }

    private static String blankToNull(String value) {
        return hasText(value) ? value.trim() : null;
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
