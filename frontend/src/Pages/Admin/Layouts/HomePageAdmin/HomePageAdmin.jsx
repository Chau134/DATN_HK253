import React from 'react';
import classNames from 'classnames';
import styles from './HomePageAdmin.module.scss';

import Dashboard from './DashBoard/DashBoard';
import Products from './Products/Products';
import OrderProducts from './OrderProducts/OrderProducts';
import Customers from './Customers/Customers';

import { useCallback, useEffect, useState } from 'react';
import Blogger from './Blog/Blogger';
import ChartLine from './ChartLine/ChartLine';
import Promotions from './Promotions/Promotions';
import Coupons from './Coupons/Coupons';
import { fetchAdminProducts } from '../../../../api/adminCatalogApi';

const cx = classNames.bind(styles);

function HomePage({ activeList }) {
    const [dataProducts, setDataProducts] = useState([]);
    const [show, setShow] = useState(false);
    const [showModalDelete, setShowModalDelete] = useState(false);
    const [showModalEdit, setShowModalEdit] = useState(false);
    const [idProduct, setIdProduct] = useState(null);
    const [valueType, setValueType] = useState('');

    const refreshProducts = useCallback(async () => {
        try {
            const products = await fetchAdminProducts();
            setDataProducts(products);
        } catch {
            setDataProducts([]);
        }
    }, []);

    useEffect(() => {
        refreshProducts();
    }, [refreshProducts]);

    const handleShowModalAddProduct = () => {
        setShow(true);
    };

    const handleShowModalDeleteProduct = (id) => {
        setIdProduct(id);
        setShowModalDelete(true);
    };

    const handleShowModalEditProduct = (id) => {
        setIdProduct(id);
        setShowModalEdit(true);
    };
    return (
        <div className={cx('wrapper')}>
            {activeList === 'dash' ? (
                <div className={cx('dash')}>
                    <Dashboard />
                </div>
            ) : (
                <></>
            )}
            {activeList === 'product' ? (
                <div className={cx('products')}>
                    <Products
                        dataProducts={dataProducts}
                        show={show}
                        setShow={setShow}
                        handleShowModalAddProduct={handleShowModalAddProduct}
                        showModalDelete={showModalDelete}
                        setShowModalDelete={setShowModalDelete}
                        handleShowModalDeleteProduct={handleShowModalDeleteProduct}
                        idProduct={idProduct}
                        handleShowModalEditProduct={handleShowModalEditProduct}
                        showModalEdit={showModalEdit}
                        setShowModalEdit={setShowModalEdit}
                        setValueType={setValueType}
                        valueType={valueType}
                        onProductChanged={refreshProducts}
                    />
                </div>
            ) : (
                <></>
            )}

            {activeList === 'order' ? (
                <div>
                    <OrderProducts />
                </div>
            ) : (
                <></>
            )}

            {activeList === 'customer' ? (
                <div>
                    <Customers />
                </div>
            ) : (
                <></>
            )}

            {activeList === 'blog' ? (
                <div>
                    <Blogger />
                </div>
            ) : (
                <></>
            )}
            {activeList === 'chart-line' ? (
                <div>
                    <ChartLine />
                </div>
            ) : (
                <></>
            )}
            {activeList === 'promotion' ? (
                <div className={cx('promotions')}>
                    <Promotions />
                </div>
            ) : (
                <></>
            )}
            {activeList === 'coupon' ? (
                <div className={cx('promotions')}>
                    <Coupons />
                </div>
            ) : (
                <></>
            )}
        </div>
    );
}

export default HomePage;
