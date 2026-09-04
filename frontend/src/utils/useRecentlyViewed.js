import { useEffect, useState } from 'react';
import { getRecentlyViewed, EVENT_NAME } from './recentlyViewed';

export function useRecentlyViewed() {
    const [list, setList] = useState(getRecentlyViewed);

    useEffect(() => {
        const sync = () => setList(getRecentlyViewed());
        window.addEventListener(EVENT_NAME, sync);
        window.addEventListener('storage', sync);
        return () => {
            window.removeEventListener(EVENT_NAME, sync);
            window.removeEventListener('storage', sync);
        };
    }, []);

    return list;
}
