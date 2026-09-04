import React from 'react';
import './App.css';
import Footer from './Layouts/Footer/Footer';
import Header from './Layouts/Header/Header';
import Main from './Layouts/Main/Main';

import Loading from './Layouts/Loading/Loading';
import { useEffect, useState } from 'react';

function App() {
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        const handleLoad = () => setIsLoading(false);

        if (document.readyState === 'complete') {
            handleLoad();
            return undefined;
        }

        window.addEventListener('load', handleLoad);
        return () => window.removeEventListener('load', handleLoad);
    }, []);

    return (
        <div className="App">
            <Loading isLoading={isLoading} />
            <header>
                <Header />
            </header>

            <main>
                <Main />
            </main>
            <footer>
                <Footer />
            </footer>
        </div>
    );
}

export default App;
