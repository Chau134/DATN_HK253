package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductAttribute;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.service.AiProductIndexHookService;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Optional;
import java.util.Set;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.AfterReturning;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

@Aspect
@Component
public class AiProductIndexHookAspect {
    private final AiProductIndexHookService hookService;
    private final ProductRepository productRepository;

    public AiProductIndexHookAspect(AiProductIndexHookService hookService, ProductRepository productRepository) {
        this.hookService = hookService;
        this.productRepository = productRepository;
    }

    @AfterReturning(
            pointcut = "execution(* com.example.serviceapiecommerce.repository.ProductRepository.save*(..))",
            returning = "result"
    )
    public void afterProductSave(Object result) {
        productIdsFromProducts(result).forEach(hookService::syncProductAfterCommit);
    }

    @AfterReturning(
            pointcut = "execution(* com.example.serviceapiecommerce.repository.ProductVariantRepository.save*(..))",
            returning = "result"
    )
    public void afterVariantSave(Object result) {
        productIdsFromVariantValues(result).forEach(hookService::syncProductAfterCommit);
    }

    @AfterReturning(
            pointcut = "execution(* com.example.serviceapiecommerce.repository.ProductPriceRepository.save*(..))",
            returning = "result"
    )
    public void afterPriceSave(Object result) {
        productIdsFromPriceValues(result).forEach(hookService::syncProductAfterCommit);
    }

    @AfterReturning(
            pointcut = "execution(* com.example.serviceapiecommerce.repository.ProductAttributeRepository.save*(..))",
            returning = "result"
    )
    public void afterAttributeSave(Object result) {
        productIdsFromAttributeValues(result).forEach(hookService::syncProductAfterCommit);
    }

    @Around("execution(* com.example.serviceapiecommerce.repository.ProductRepository.delete*(..))")
    public Object aroundProductDelete(ProceedingJoinPoint joinPoint) throws Throwable {
        Set<Long> productIds = productIdsFromDelete(joinPoint);
        Object result = joinPoint.proceed();
        productIds.forEach(hookService::deleteProductAfterCommit);
        return result;
    }

    private Set<Long> productIdsFromDelete(ProceedingJoinPoint joinPoint) {
        Set<Long> ids = productIdsFromProducts(joinPoint.getArgs());
        if (!ids.isEmpty()) {
            return ids;
        }

        if (isWholeRepositoryDelete(joinPoint)) {
            Set<Long> allProductIds = new LinkedHashSet<>();
            productRepository.findAll().forEach(product -> addProductId(allProductIds, product));
            return allProductIds;
        }

        return Set.of();
    }

    private static boolean isWholeRepositoryDelete(JoinPoint joinPoint) {
        String methodName = joinPoint.getSignature().getName();
        return joinPoint.getArgs().length == 0
                && ("deleteAll".equals(methodName) || "deleteAllInBatch".equals(methodName));
    }

    private static Set<Long> productIdsFromProducts(Object value) {
        Set<Long> ids = new LinkedHashSet<>();
        collect(value, item -> {
            if (item instanceof Product product) {
                addProductId(ids, product);
            } else if (item instanceof Long productId) {
                ids.add(productId);
            }
        });
        return ids;
    }

    private static Set<Long> productIdsFromVariantValues(Object value) {
        Set<Long> ids = new LinkedHashSet<>();
        collect(value, item -> {
            if (item instanceof ProductVariant variant) {
                addProductId(ids, variant.getProduct());
            }
        });
        return ids;
    }

    private static Set<Long> productIdsFromPriceValues(Object value) {
        Set<Long> ids = new LinkedHashSet<>();
        collect(value, item -> {
            if (item instanceof ProductPrice price) {
                addProductId(ids, price.getProduct());
            }
        });
        return ids;
    }

    private static Set<Long> productIdsFromAttributeValues(Object value) {
        Set<Long> ids = new LinkedHashSet<>();
        collect(value, item -> {
            if (item instanceof ProductAttribute attribute) {
                addProductId(ids, attribute.getProduct());
            }
        });
        return ids;
    }

    private static void addProductId(Set<Long> ids, Product product) {
        if (product != null && product.getId() != null) {
            ids.add(product.getId());
        }
    }

    private static void collect(Object value, ValueConsumer consumer) {
        if (value == null) {
            return;
        }
        if (value instanceof Optional<?> optional) {
            optional.ifPresent(item -> collect(item, consumer));
            return;
        }
        if (value instanceof Iterable<?> iterable) {
            iterable.forEach(item -> collect(item, consumer));
            return;
        }
        if (value instanceof Object[] values) {
            Arrays.stream(values).forEach(item -> collect(item, consumer));
            return;
        }

        consumer.accept(value);
    }

    @FunctionalInterface
    private interface ValueConsumer {
        void accept(Object value);
    }
}
