import React from 'react';
import Skeleton from 'react-loading-skeleton';
import 'react-loading-skeleton/dist/skeleton.css';
import styles from './ProductDetailSkeleton.module.scss';

const ProductDetailSkeleton = () => {
  return (
    <div className={styles.container}>
      <div className={styles.gallery}>
        <div className={styles.mainImage}>
          <Skeleton height="100%" />
        </div>
        <div className={styles.thumbnails}>
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} height={80} />
          ))}
        </div>
      </div>

      <div className={styles.info}>
        <Skeleton height={32} width="80%" style={{ marginBottom: 12 }} />
        <Skeleton height={24} width="40%" style={{ marginBottom: 16 }} />
        <Skeleton count={3} style={{ marginBottom: 8 }} />

        <div className={styles.variants}>
          <Skeleton height={20} width={60} style={{ marginBottom: 8 }} />
          <div className={styles.variantOptions}>
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} height={40} width={60} />
            ))}
          </div>
        </div>

        <div className={styles.quantity}>
          <Skeleton height={20} width={80} style={{ marginBottom: 8 }} />
          <Skeleton height={48} width={150} />
        </div>

        <div className={styles.actions}>
          <Skeleton height={48} width="48%" />
          <Skeleton height={48} width="48%" />
        </div>
      </div>
    </div>
  );
};

export default ProductDetailSkeleton;
