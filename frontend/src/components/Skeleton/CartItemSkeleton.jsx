import React from 'react';
import Skeleton from 'react-loading-skeleton';
import 'react-loading-skeleton/dist/skeleton.css';
import styles from './CartItemSkeleton.module.scss';

const CartItemSkeleton = ({ count = 1 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className={styles.skeletonItem}>
          <div className={styles.image}>
            <Skeleton height="100%" />
          </div>
          <div className={styles.details}>
            <Skeleton height={20} width="70%" style={{ marginBottom: 8 }} />
            <Skeleton height={16} width="50%" style={{ marginBottom: 12 }} />
            <Skeleton height={16} width="40%" />
          </div>
          <div className={styles.quantity}>
            <Skeleton height={40} width={120} />
          </div>
          <div className={styles.price}>
            <Skeleton height={24} width={100} />
          </div>
          <div className={styles.actions}>
            <Skeleton circle height={32} width={32} />
          </div>
        </div>
      ))}
    </>
  );
};

export default CartItemSkeleton;
