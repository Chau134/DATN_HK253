import React from 'react';
import Skeleton from 'react-loading-skeleton';
import 'react-loading-skeleton/dist/skeleton.css';
import styles from './ProductCardSkeleton.module.scss';

const ProductCardSkeleton = () => {
  return (
    <div className={styles.skeletonCard}>
      <div className={styles.imageWrapper}>
        <Skeleton height={250} />
      </div>
      <div className={styles.content}>
        <Skeleton height={20} style={{ marginBottom: 8 }} />
        <Skeleton height={16} width="70%" style={{ marginBottom: 8 }} />
        <div className={styles.priceRow}>
          <Skeleton height={24} width={80} />
          <Skeleton height={20} width={60} />
        </div>
        <Skeleton height={16} width="50%" style={{ marginTop: 8 }} />
      </div>
    </div>
  );
};

export default ProductCardSkeleton;
