import React, { useRef, useState, useLayoutEffect } from 'react';

// Рендерить графік лише коли контейнер має ненульові розміри (без попереджень Recharts)
const SizedChart = ({ className = '', style, children }) => {
    const ref = useRef(null);
    const [size, setSize] = useState({ width: 0, height: 0 });

    useLayoutEffect(() => {
        const el = ref.current;
        if (!el) return undefined;
        const update = () => {
            const { clientWidth: width, clientHeight: height } = el;
            setSize((prev) => (prev.width === width && prev.height === height ? prev : { width, height }));
        };
        update();
        const ro = new ResizeObserver(update);
        ro.observe(el);
        return () => ro.disconnect();
    }, []);

    return (
        <div ref={ref} className={className} style={style}>
            {size.width > 0 && size.height > 0 && children(size)}
        </div>
    );
};

export default SizedChart;
