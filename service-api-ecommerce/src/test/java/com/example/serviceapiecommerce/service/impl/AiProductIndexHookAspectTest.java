package com.example.serviceapiecommerce.service.impl;

import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductAttribute;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.service.AiProductIndexHookService;
import java.util.List;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.Signature;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InOrder;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AiProductIndexHookAspectTest {
    @Mock
    private AiProductIndexHookService hookService;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private ProceedingJoinPoint joinPoint;

    @Mock
    private Signature signature;

    @Test
    void afterProductSaveSyncsSavedProduct() {
        AiProductIndexHookAspect aspect = aspect();

        aspect.afterProductSave(product(42L));

        verify(hookService).syncProductAfterCommit(42L);
    }

    @Test
    void afterProductSaveAllSyncsEachSavedProductOnce() {
        AiProductIndexHookAspect aspect = aspect();

        aspect.afterProductSave(List.of(product(42L), product(42L), product(43L)));

        verify(hookService).syncProductAfterCommit(42L);
        verify(hookService).syncProductAfterCommit(43L);
    }

    @Test
    void afterRelatedEntitySaveSyncsParentProduct() {
        AiProductIndexHookAspect aspect = aspect();
        Product product = product(42L);

        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        ProductPrice price = new ProductPrice();
        price.setProduct(product);
        ProductAttribute attribute = new ProductAttribute();
        attribute.setProduct(product);

        aspect.afterVariantSave(variant);
        aspect.afterPriceSave(price);
        aspect.afterAttributeSave(attribute);

        verify(hookService, org.mockito.Mockito.times(3)).syncProductAfterCommit(42L);
    }

    @Test
    void aroundProductDeleteDeletesFromAiIndexAfterRepositoryDeleteSucceeds() throws Throwable {
        AiProductIndexHookAspect aspect = aspect();
        when(joinPoint.getArgs()).thenReturn(new Object[] {42L});
        when(joinPoint.proceed()).thenReturn(null);

        aspect.aroundProductDelete(joinPoint);

        InOrder order = inOrder(joinPoint, hookService);
        order.verify(joinPoint).proceed();
        order.verify(hookService).deleteProductAfterCommit(42L);
    }

    @Test
    void aroundProductDeleteDoesNotDeleteFromAiIndexWhenRepositoryDeleteFails() throws Throwable {
        AiProductIndexHookAspect aspect = aspect();
        when(joinPoint.getArgs()).thenReturn(new Object[] {42L});
        when(joinPoint.proceed()).thenThrow(new IllegalStateException("delete failed"));

        try {
            aspect.aroundProductDelete(joinPoint);
        } catch (IllegalStateException ignored) {
        }

        verify(hookService, never()).deleteProductAfterCommit(42L);
    }

    @Test
    void aroundWholeRepositoryDeleteCapturesAllProductIdsBeforeDelete() throws Throwable {
        AiProductIndexHookAspect aspect = aspect();
        when(joinPoint.getArgs()).thenReturn(new Object[] {});
        when(joinPoint.getSignature()).thenReturn(signature);
        when(signature.getName()).thenReturn("deleteAll");
        when(productRepository.findAll()).thenReturn(List.of(product(42L), product(43L)));
        when(joinPoint.proceed()).thenReturn(null);

        aspect.aroundProductDelete(joinPoint);

        verify(hookService).deleteProductAfterCommit(42L);
        verify(hookService).deleteProductAfterCommit(43L);
    }

    private AiProductIndexHookAspect aspect() {
        return new AiProductIndexHookAspect(hookService, productRepository);
    }

    private static Product product(Long productId) {
        Product product = new Product();
        product.setId(productId);
        return product;
    }
}
