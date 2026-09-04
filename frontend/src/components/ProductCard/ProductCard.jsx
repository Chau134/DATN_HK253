import classNames from 'classnames/bind';
import { Link } from 'react-router-dom';
import { handleImageFallback, resolveImageUrl } from '../../utils/image';
import { formatCurrencyFromDb } from '../../utils/price';
import { currencyOf, priceOf, productIdOf, titleOf } from './productFields';
import styles from './ProductCard.module.scss';

const cx = classNames.bind(styles);

function imageOf(product) {
    return resolveImageUrl(product?.image_url || product?.image_urls?.[0] || product?.img || '');
}

function ProductCard({ product, variant = 'grid' }) {
    const productId = productIdOf(product);
    const image = imageOf(product);
    const title = titleOf(product);
    const soldOut = product?.available === false;
    const detailUrl = `/prodetail/${productId}`;

    return (
        <article className={cx('product-card', variant)}>
            <Link to={detailUrl} className={cx('product-image')}>
                {image ? (
                    <img src={image} alt={title} onError={handleImageFallback} />
                ) : (
                    <div className={cx('image-placeholder')}>Chưa có ảnh</div>
                )}
            </Link>
            <div className={cx('product-body')}>
                <div className={cx('product-info')}>
                    <p>{product?.brand || 'Thương hiệu đang cập nhật'}</p>
                    <h3>{title}</h3>
                </div>
                <div className={cx('product-meta')}>
                    <strong>{formatCurrencyFromDb(priceOf(product), currencyOf(product))}</strong>
                    <span className={cx(soldOut ? 'pill-danger' : 'pill')}>{soldOut ? 'Hết hàng' : 'Còn hàng'}</span>
                </div>
                <Link className={cx('primary-button')} to={detailUrl}>
                    Xem
                </Link>
            </div>
        </article>
    );
}

export default ProductCard;
