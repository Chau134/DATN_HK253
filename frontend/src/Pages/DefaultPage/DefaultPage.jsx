import React from 'react';
import classNames from 'classnames/bind';
import styles from './DefaultPage.module.scss';
import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import Banner from '../Layouts/Banner/Banner';
import SlideBar from '../Layouts/SlideBar/Slidebar';
import FilterSidebar from '../../components/FilterSidebar/FilterSidebar';
import HomePage from '../Layouts/HomePage/HomePage';
import { fetchCatalogProducts, fetchCatalogBrands } from '../../api/catalogApi';

import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

const cx = classNames.bind(styles);

const DEFAULT_PRICE_BOUNDS = [0, 10000000];

function DefaultPage() {
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);

    const [checkType2, setCheckType2] = useState(queryParams.get('type') || '');
    const [searchKeyword, setSearchKeyword] = useState(queryParams.get('keyword') || '');
    const [categoryId, setCategoryId] = useState(queryParams.get('category_id') || '');
    const [checkPrice, setCheckPrice] = useState('');
    const [dataProducts, setDataProducts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [totalPages, setTotalPages] = useState(0);
    const [currentPage, setCurrentPage] = useState(Number(queryParams.get('page') || 0));
    const [pageInfo, setPageInfo] = useState({ first: true, last: true, totalElements: 0 });
    const [priceRange, setPriceRange] = useState(DEFAULT_PRICE_BOUNDS);
    const [appliedPrice, setAppliedPrice] = useState(DEFAULT_PRICE_BOUNDS);
    const [selectedBrand, setSelectedBrand] = useState('');
    const [brands, setBrands] = useState([]);
    const perPage = 12;

    // Load the full brand list once (backend endpoint returns distinct brands across the catalog)
    useEffect(() => {
        let mounted = true;
        fetchCatalogBrands()
            .then((list) => {
                if (mounted) setBrands(list);
            })
            .catch(() => {
                if (mounted) setBrands([]);
            });
        return () => {
            mounted = false;
        };
    }, []);

    useEffect(() => {
        const params = new URLSearchParams();
        if (checkType2) params.set('type', checkType2);
        if (searchKeyword) params.set('keyword', searchKeyword);
        if (categoryId) params.set('category_id', categoryId);
        if (currentPage > 0) params.set('page', currentPage);

        const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`;
        window.history.replaceState({}, '', newUrl);
    }, [checkType2, searchKeyword, categoryId, currentPage]);

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        setCheckType2(params.get('type') || '');
        setSearchKeyword(params.get('keyword') || '');
        setCategoryId(params.get('category_id') || '');
        setCurrentPage(Number(params.get('page') || 0));
    }, [location.search]);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const response = await fetchCatalogProducts({
                    page: currentPage,
                    size: perPage,
                    sort: 'newest',
                    category_id: categoryId || undefined,
                    keyword: searchKeyword || checkType2 || undefined,
                    brand: selectedBrand || undefined,
                    min_price: appliedPrice[0] > DEFAULT_PRICE_BOUNDS[0] ? appliedPrice[0] : undefined,
                    max_price: appliedPrice[1] < DEFAULT_PRICE_BOUNDS[1] ? appliedPrice[1] : undefined,
                });
                let processedData = [...response.items];

                const kw = (searchKeyword || checkType2 || '').toLowerCase();
                if (kw.includes('shirt') && !kw.includes('t-shirt') && !kw.includes('tshirt')) {
                    processedData = processedData.filter((item) => {
                        const title = (item.nameProducts || '').toLowerCase();
                        return !title.includes('t-shirt') && !title.includes('tshirt') && !title.includes('thun');
                    });
                }

                if (checkPrice === '1') {
                    processedData.sort((a, b) => (b.priceNew || 0) - (a.priceNew || 0));
                } else if (checkPrice === '2') {
                    processedData.sort((a, b) => (a.priceNew || 0) - (b.priceNew || 0));
                }

                setDataProducts(processedData);
                setTotalPages(response.total_pages || 1);
                setPageInfo({
                    first: response.first ?? currentPage === 0,
                    last: response.last ?? currentPage + 1 >= (response.total_pages || 1),
                    totalElements: response.total_elements || processedData.length,
                });
            } catch (error) {
                console.error('Error fetching data:', error);
                setDataProducts([]);
                setTotalPages(0);
                setPageInfo({ first: true, last: true, totalElements: 0 });
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [checkType2, searchKeyword, categoryId, checkPrice, currentPage, selectedBrand, appliedPrice]);

    const handleSetCategoryId = (value) => {
        setCategoryId(value);
        setCurrentPage(0);
    };

    const handleSetCheckPrice = (value) => {
        setCheckPrice(value);
        setCurrentPage(0);
    };

    const handleSetCheckType2 = (value) => {
        setCheckType2(value);
        setCurrentPage(0);
    };

    // Commit the price range (fires on slider release) -> server-side filter, reset to page 0
    const handlePriceCommit = (range) => {
        setAppliedPrice(range);
        setCurrentPage(0);
    };

    const handleSelectBrand = (brand) => {
        setSelectedBrand((prev) => (prev === brand ? '' : brand));
        setCurrentPage(0);
    };

    const hasActiveFilters =
        !!selectedBrand ||
        appliedPrice[0] > DEFAULT_PRICE_BOUNDS[0] ||
        appliedPrice[1] < DEFAULT_PRICE_BOUNDS[1];

    const clearAllFilters = () => {
        setPriceRange(DEFAULT_PRICE_BOUNDS);
        setAppliedPrice(DEFAULT_PRICE_BOUNDS);
        setSelectedBrand('');
        setCurrentPage(0);
    };

    return (
        <div className={cx('wrapper')}>
            <header>
                <Header />
            </header>

            <div className={cx('banner')}>
                <Banner />
            </div>

            <main className={cx('main-category')}>
                <div className={cx('container')}>
                    <div>
                        <HomePage
                            dataProducts={dataProducts}
                            loading={loading}
                            totalPages={totalPages}
                            currentPage={currentPage}
                            firstPage={pageInfo.first}
                            lastPage={pageInfo.last}
                            totalElements={pageInfo.totalElements}
                            onPrevPage={() => setCurrentPage((page) => Math.max(page - 1, 0))}
                            onNextPage={() => setCurrentPage((page) => (totalPages ? Math.min(page + 1, totalPages - 1) : page + 1))}
                            filters={
                                <>
                                    <SlideBar
                                        setCategoryId={handleSetCategoryId}
                                        setCheckPrice={handleSetCheckPrice}
                                        categoryId={categoryId}
                                    />
                                    <FilterSidebar
                                        brands={brands}
                                        selectedBrand={selectedBrand}
                                        onSelectBrand={handleSelectBrand}
                                        priceRange={priceRange}
                                        priceBounds={DEFAULT_PRICE_BOUNDS}
                                        onPriceChange={setPriceRange}
                                        onPriceCommit={handlePriceCommit}
                                        hasActiveFilters={hasActiveFilters}
                                        onClearAll={clearAllFilters}
                                    />
                                </>
                            }
                        />
                    </div>
                </div>
            </main>

            <footer>
                <Footer />
            </footer>
        </div>
    );
}

export default DefaultPage;
