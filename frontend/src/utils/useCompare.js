import { useEffect, useState } from 'react';
import { getCompareList, EVENT_NAME } from './compare';

export function useCompare() {
    const [list, setList] = useState(getCompareList);

    useEffect(() => {
        const sync = () => setList(getCompareList());
        window.addEventListener(EVENT_NAME, sync);
        window.addEventListener('storage', sync);
        return () => {
            window.removeEventListener(EVENT_NAME, sync);
            window.removeEventListener('storage', sync);
        };
    }, []);

    return list;
}
