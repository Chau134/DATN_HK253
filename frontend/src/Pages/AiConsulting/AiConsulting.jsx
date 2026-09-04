import { useEffect, useRef, useState } from 'react';
import classNames from 'classnames/bind';
import { Image as ImageIcon, Layers, Search, X } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import Banner from '../Layouts/Banner/Banner';
import { aiApi, formatAiWarnings, getApiError } from '../../api/aiApi';
import { cropBoxOf, imagePayloadFromFile, imageWithDetections } from '../../utils/aiImage';
import ProductCard from '../../components/ProductCard';
import styles from './AiConsulting.module.scss';

const cx = classNames.bind(styles);

function StatusMessage({ error, message }) {
    if (!error && !message) return null;
    return <div className={cx('status-message', error && 'status-error')}>{error || message}</div>;
}

function AiConsulting() {
    const location = useLocation();
    const navigate = useNavigate();
    const [textQuery, setTextQuery] = useState('');
    const [imageOnly, setImageOnly] = useState(null);
    const [hybridQuery, setHybridQuery] = useState('');
    const [hybridImage, setHybridImage] = useState(null);
    const [searchResult, setSearchResult] = useState(null);
    const [loading, setLoading] = useState('');
    const [error, setError] = useState('');

    const products = searchResult?.products || [];
    const warnings = searchResult?.warnings || [];

    const runRequest = async (type, action) => {
        setLoading(type);
        setError('');
        setSearchResult(null);
        try {
            await action();
        } catch (err) {
            setError(getApiError(err));
        } finally {
            setLoading('');
        }
    };

    useEffect(() => {
        const headerSearch = location.state?.headerSearch;
        if (!headerSearch) return;

        const headerQuery = headerSearch.query?.trim() || '';
        const headerImage = headerSearch.image;
        if (!headerQuery && !headerImage) return;

        setSearchResult(null);
        navigate(location.pathname, { replace: true, state: null });

        if (!headerImage) {
            setTextQuery(headerQuery);
            runRequest('text-search', async () => {
                const data = await aiApi.textSearch({ query: headerQuery, top_k: 8 });
                setSearchResult(data);
            });
            return;
        }

        if (!headerQuery) {
            setImageOnly(headerImage);
            runRequest('image-search', async () => {
                const detectedImage = await imageWithDetections(headerImage);
                setImageOnly(detectedImage);
                const data = await aiApi.imageSearch({
                    image: detectedImage.payload,
                    crop_box: cropBoxOf(detectedImage),
                    top_k: 8,
                });
                setSearchResult(data);
            });
            return;
        }

        setHybridQuery(headerQuery);
        setHybridImage(headerImage);
        runRequest('hybrid-search', async () => {
            const detectedImage = await imageWithDetections(headerImage);
            setHybridImage(detectedImage);
            const data = await aiApi.hybridSearch({
                query: headerQuery,
                image: detectedImage.payload,
                crop_box: cropBoxOf(detectedImage),
                top_k: 8,
                strategy: 'weighted',
            });
            setSearchResult(data);
        });
    }, [location.pathname, location.state, navigate]);

    const handleTextSearch = (event) => {
        event.preventDefault();
        if (!textQuery.trim()) return;
        runRequest('text-search', async () => {
            const data = await aiApi.textSearch({ query: textQuery.trim(), top_k: 8 });
            setSearchResult(data);
        });
    };

    const handleImageSearch = (event) => {
        event.preventDefault();
        if (!imageOnly) return;
        runRequest('image-search', async () => {
            const data = await aiApi.imageSearch({
                image: imageOnly.payload,
                crop_box: cropBoxOf(imageOnly),
                top_k: 8,
            });
            setSearchResult(data);
        });
    };

    const handleHybridSearch = (event) => {
        event.preventDefault();
        if (!hybridQuery.trim() || !hybridImage) return;
        runRequest('hybrid-search', async () => {
            const data = await aiApi.hybridSearch({
                query: hybridQuery.trim(),
                image: hybridImage.payload,
                crop_box: cropBoxOf(hybridImage),
                top_k: 8,
                strategy: 'weighted',
            });
            setSearchResult(data);
        });
    };

    return (
        <div className={cx('wrapper')}>
            <header>
                <Header />
            </header>

            <div>
                <Banner />
            </div>

            <main className={cx('consulting-page')}>
                <section className={cx('page-heading')}>
                    <p>Tư vấn mua sắm</p>
                    <h2>Tìm sản phẩm theo nhu cầu</h2>
                </section>

                {loading || error || searchResult ? (
                    <section className={cx('search-results')} aria-live="polite">
                        <div className={cx('results-heading')}>
                            <p>Kết quả tìm kiếm</p>
                            {!loading && searchResult ? <span>{products.length} sản phẩm phù hợp</span> : null}
                        </div>

                        <StatusMessage error={error} />
                        {warnings.length ? <StatusMessage message={formatAiWarnings(warnings, ', ')} /> : null}
                        {loading ? <div className={cx('grid-note')}>Đang xử lý...</div> : null}
                        {!loading && searchResult && !products.length && !warnings.length ? (
                            <div className={cx('grid-note')}>Chưa tìm thấy sản phẩm phù hợp.</div>
                        ) : null}

                        {products.length ? (
                            <div className={cx('product-grid')}>
                                {products.map((product) => (
                                    <ProductCard key={product.product_id || product.id} product={product} />
                                ))}
                            </div>
                        ) : null}
                    </section>
                ) : null}

                <section className={cx('ai-panel-grid')}>
                    <form className={cx('form-grid')} onSubmit={handleTextSearch}>
                        <h3>Tìm theo từ khóa</h3>
                        <label>
                            Từ khóa
                            <input value={textQuery} onChange={(event) => setTextQuery(event.target.value)} placeholder="áo hoodie đen, giày đi chơi..." />
                        </label>
                        <button className={cx('primary-button')} disabled={!textQuery.trim() || loading === 'text-search'}>
                            <Search size={18} />
                            Tìm
                        </button>
                    </form>

                    <form className={cx('form-grid')} onSubmit={handleImageSearch}>
                        <h3>Tìm bằng ảnh</h3>
                        <LensImagePicker image={imageOnly} onChange={setImageOnly} label="Ảnh sản phẩm" />
                        <button className={cx('primary-button')} disabled={!imageOnly || loading === 'image-search'}>
                            <ImageIcon size={18} />
                            Tìm
                        </button>
                    </form>

                    <form className={cx('form-grid')} onSubmit={handleHybridSearch}>
                        <h3>Tìm kết hợp (từ khóa + ảnh)</h3>
                        <label>
                            Từ khóa
                            <input value={hybridQuery} onChange={(event) => setHybridQuery(event.target.value)} placeholder="áo khoác dáng rộng..." />
                        </label>
                        <LensImagePicker image={hybridImage} onChange={setHybridImage} label="Ảnh tham khảo" />
                        <button className={cx('primary-button')} disabled={!hybridQuery.trim() || !hybridImage || loading === 'hybrid-search'}>
                            <Layers size={18} />
                            Tìm
                        </button>
                    </form>
                </section>
            </main>

            <footer>
                <Footer />
            </footer>
        </div>
    );
}

function LensImagePicker({ image, onChange, label }) {
    const imageRef = useRef(null);
    const [dragStart, setDragStart] = useState(null);
    const [detecting, setDetecting] = useState(false);
    const [error, setError] = useState('');

    const detectImage = async (nextImage) => {
        if (!nextImage) return;
        setDetecting(true);
        setError('');
        try {
            const detectedImage = await imageWithDetections(nextImage);
            onChange((current) => {
                if (!current || current.filename !== nextImage.filename) return current;
                return {
                    ...current,
                    ...detectedImage,
                };
            });
        } catch (err) {
            setError(getApiError(err));
        } finally {
            setDetecting(false);
        }
    };

    const setCropBox = (cropBox, cropSource) => {
        onChange((current) => (current ? { ...current, cropBox, cropSource } : current));
    };

    const handleFile = async (file) => {
        if (!file) {
            onChange(null);
            return;
        }
        setError('');
        try {
            const nextImage = await imagePayloadFromFile(file);
            onChange(nextImage);
            detectImage(nextImage);
        } catch (err) {
            setError(err.message || 'Không đọc được ảnh đã chọn.');
        }
    };

    const handlePointerDown = (event) => {
        if (!image || event.target.closest('button')) return;
        const point = pointFromPointer(event, imageRef.current, image);
        if (!point) return;
        event.currentTarget.setPointerCapture(event.pointerId);
        setDragStart(point);
        setCropBox({ left: point.x, top: point.y, right: point.x + 1, bottom: point.y + 1 }, 'manual');
    };

    const handlePointerMove = (event) => {
        if (!image || !dragStart) return;
        const point = pointFromPointer(event, imageRef.current, image);
        if (!point) return;
        setCropBox(normalizeBox(dragStart, point), 'manual');
    };

    const handlePointerUp = () => {
        setDragStart(null);
    };

    const detections = image?.detections || [];
    const manualCrop = image?.cropSource === 'manual' ? image.cropBox : null;

    return (
        <label>
            {label}
            <div className={cx('image-upload')}>
                {image ? (
                    <>
                        <div
                            className={cx('image-preview')}
                            style={{ aspectRatio: `${image.width || 1} / ${image.height || 1}` }}
                            onPointerDown={handlePointerDown}
                            onPointerMove={handlePointerMove}
                            onPointerUp={handlePointerUp}
                            onPointerCancel={handlePointerUp}
                        >
                            <img ref={imageRef} src={image.preview} alt={image.filename} draggable="false" />
                            {detections.map((detection, index) => (
                                <button
                                    type="button"
                                    key={`${detection.bbox.left}-${detection.bbox.top}-${index}`}
                                    className={cx('crop-box', sameBox(image.cropBox, detection.bbox) && image.cropSource !== 'manual' && 'selected')}
                                    style={boxStyle(detection.bbox, image)}
                                    title={`Gợi ý vùng chọn ${Math.round((detection.confidence || 0) * 100)}%`}
                                    onClick={(event) => {
                                        event.preventDefault();
                                        event.stopPropagation();
                                        setCropBox(detection.bbox, 'yolo');
                                    }}
                                />
                            ))}
                            {manualCrop ? <span className={cx('crop-box', 'manual', 'selected')} style={boxStyle(manualCrop, image)} /> : null}
                            <button
                                type="button"
                                className={cx('icon-button', 'remove-image-button')}
                                aria-label="Xóa ảnh"
                                onClick={(event) => {
                                    event.preventDefault();
                                    event.stopPropagation();
                                    onChange(null);
                                }}
                            >
                                <X size={17} />
                            </button>
                        </div>
                        <div className={cx('crop-actions')}>
                            <button type="button" className={cx('ghost-button')} onClick={() => detectImage(image)} disabled={detecting}>
                                Gợi ý vùng chọn
                            </button>
                            <button type="button" className={cx('ghost-button')} onClick={() => setCropBox(null, 'full')}>
                                Toàn ảnh
                            </button>
                        </div>
                        {detecting ? <p className={cx('muted')}>Đang xử lý ảnh...</p> : null}
                        <StatusMessage error={error} />
                        {image.warnings?.length ? <StatusMessage message={formatAiWarnings(image.warnings, ', ')} /> : null}
                    </>
                ) : (
                    <>
                        <span className={cx('image-upload-empty')}>
                            <ImageIcon size={18} />
                            Chọn ảnh
                        </span>
                        <input
                            type="file"
                            accept="image/*"
                            onChange={(event) => {
                                const file = event.target.files?.[0];
                                event.target.value = '';
                                handleFile(file);
                            }}
                        />
                    </>
                )}
            </div>
        </label>
    );
}

function pointFromPointer(event, img, image) {
    if (!img || !image?.width || !image?.height) return null;
    const rect = img.getBoundingClientRect();
    const x = clamp(Math.round(((event.clientX - rect.left) / rect.width) * image.width), 0, image.width - 1);
    const y = clamp(Math.round(((event.clientY - rect.top) / rect.height) * image.height), 0, image.height - 1);
    return { x, y };
}

function normalizeBox(start, end) {
    const left = Math.min(start.x, end.x);
    const top = Math.min(start.y, end.y);
    const right = Math.max(start.x + 1, end.x + 1);
    const bottom = Math.max(start.y + 1, end.y + 1);
    return { left, top, right, bottom };
}

function boxStyle(box, image) {
    const width = image.width || 1;
    const height = image.height || 1;
    return {
        left: `${(box.left / width) * 100}%`,
        top: `${(box.top / height) * 100}%`,
        width: `${((box.right - box.left) / width) * 100}%`,
        height: `${((box.bottom - box.top) / height) * 100}%`,
    };
}

function sameBox(first, second) {
    return first && second && first.left === second.left && first.top === second.top && first.right === second.right && first.bottom === second.bottom;
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

export default AiConsulting;
